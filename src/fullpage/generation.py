"""Greedy staged generation; raw model text is validated and never repaired."""
import json
import shutil
import time
import uuid
from pathlib import Path
import torch
from tokenizers import Tokenizer
from src.data.sources import sha256_file
from src.training.engine import read_checkpoint, checkpoint_sha256, _autocast, seed_everything
from src.models.minigpt import MiniGPT
from .assets import load_asset_catalog
from .contracts import validate_request, validate_plan_wire, validate_section
from .compose import compose_page, fact_errors
from .serialization import check_budget, decode_plan, output_budget_for
from .prompts import plan_prompt, section_prompt, retry_prompt
from .renderer import export_fullpage
from .curriculum import write_json
from .source_bound_contracts import CONTRACT_VERSION, load_copy_catalog, validate_page_plan, validate_section_draft
from .source_bound_compose import compose_source_bound_page
from .source_bound_prompts import source_bound_plan_prompt, source_bound_section_prompt

SOURCE_BOUND_LINEAGE_FILES = (
    "src/fullpage/source_bound_prompts.py",
    "src/fullpage/source_bound_serialization.py",
    "src/fullpage/source_bound_contracts.py",
    "src/fullpage/source_bound_compose.py",
    "src/fullpage/source_bound_resolver.py",
    "configs/fullpage/source-bound-copy-v1.json",
)
SOURCE_BOUND_SCHEMA_FILES = (
    "plan-source-bound-v1.schema.json",
    "section-source-bound-v1.schema.json",
)
MAX_REQUEST_PROMPT_CHARS = 1000
SOURCE_BOUND_RETRY_INSTRUCTION = "Output only a contract-valid JSON object using existing request and catalog IDs."


def checkpoint_contract_version(config: dict) -> str | None:
    if not isinstance(config, dict):
        raise ValueError("Checkpoint config must be an object")
    version = config.get("fullpage_contract_version")
    if version not in (None, CONTRACT_VERSION):
        raise ValueError("Unsupported fullpage contract version")
    return version


def generate_task(model, tokenizer, prompt, *, task, config, contract_version=None):
    budget=output_budget_for(task,contract_version); check=check_budget(tokenizer,prompt,budget)
    prefix=[tokenizer.token_to_id('<bos>'),tokenizer.token_to_id('<prompt>')]+tokenizer.encode(prompt).ids+[tokenizer.token_to_id('<target>')]
    ids=torch.tensor([prefix],device=next(model.parameters()).device,dtype=torch.long)
    generated=[]; eos=tokenizer.token_to_id('<eos>'); stop='token_limit'; began=time.perf_counter()
    model.eval()
    with torch.inference_mode():
        for _ in range(budget):
            mask=torch.zeros_like(ids,dtype=torch.bool); mask[:,-1]=True
            with _autocast(ids.device,config['precision']): logits=model(ids,output_mask=mask)[0].float()
            if not torch.isfinite(logits).all(): raise FloatingPointError('Nonfinite generation logits')
            token=int(logits.argmax().item())
            if token==eos: stop='eos'; break
            generated.append(token)
            ids=torch.cat((ids,torch.tensor([[token]],device=ids.device,dtype=torch.long)),dim=1)
    raw=tokenizer.decode(generated,skip_special_tokens=False)
    return {'raw':raw,'stop_reason':stop,'generated_tokens':len(generated)+(stop=='eos'),
            'prefix_tokens':check['prefix_tokens'],'max_new_tokens':budget,'seconds':time.perf_counter()-began}


class FullPageGenerator:
    def __init__(self,checkpoint,root,config=None):
        self.root=Path(root).resolve(); self.checkpoint=Path(checkpoint).resolve()
        self.config=config or {'precision':'bf16','temperature':0,'seed':42}
        if self.config.get('temperature')!=0: raise ValueError('Frozen evaluation requires greedy decoding')
        state=read_checkpoint(self.checkpoint)
        self.contract_version = checkpoint_contract_version(state['config'])
        if state['model_config']['block_size']!=2048: raise ValueError('Fullpage requires context2048')
        lineage=state['config']['lineage']; actual=sha256_file(self.root/'data/tokenizer/tokenizer.json')
        if lineage['tokenizer_sha256']!=actual: raise ValueError('Tokenizer differs from checkpoint')
        if not (lineage.get('migration_kind')=='position_extension' or state['config'].get('data_origin')=='fullpage_curriculum'):
            raise ValueError('Missing project fullpage ancestry')
        if state['config'].get('data_origin')=='fullpage_curriculum':
            for name,digest in lineage['schema_sha256'].items():
                if sha256_file(self.root/'configs/fullpage'/name)!=digest: raise ValueError('Generation schema differs from training')
            prompt_file = 'src/fullpage/source_bound_prompts.py' if self.contract_version else 'src/fullpage/prompts.py'
            if sha256_file(self.root/prompt_file)!=lineage['source_sha256'][prompt_file]:
                raise ValueError('Task prompts differ from training')
            if self.contract_version:
                for name in SOURCE_BOUND_SCHEMA_FILES:
                    if lineage['schema_sha256'].get(name) != sha256_file(self.root/'configs/fullpage'/name):
                        raise ValueError('Source-bound generation schema differs from training')
                for relative_path in SOURCE_BOUND_LINEAGE_FILES:
                    if lineage['source_sha256'].get(relative_path) != sha256_file(self.root/relative_path):
                        raise ValueError('Source-bound generation source differs from training')
            ancestor=lineage['initialization_parent']
        else: ancestor=lineage
        if ancestor.get('source_checkpoint_sha256')!='3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638':
            raise ValueError('Project source ancestry mismatch')
        seed_everything(self.config['seed']); self.model=MiniGPT(state['model_config']).to('cuda')
        self.model.load_state_dict(state['model']); self.model.set_attention_backend('sdpa'); self.model.eval()
        self.tokenizer=Tokenizer.from_file(str(self.root/'data/tokenizer/tokenizer.json')); self.catalog=load_asset_catalog(self.root)
        self.copy_catalog=load_copy_catalog(self.root) if self.contract_version else None
        self.metadata={'checkpoint_sha256':checkpoint_sha256(self.checkpoint),'checkpoint_run_id':state['run_id'],
                       'checkpoint_step':state['global_step'],'tokenizer_sha256':actual,'config':self.config,
                       'schemas_sha256':{p.name:sha256_file(p) for p in (self.root/'configs/fullpage').glob('*.schema.json')},
                       'prompt_source_sha256':sha256_file(self.root/'src/fullpage/prompts.py')}
        if self.contract_version:
            self.metadata['fullpage_contract_version'] = self.contract_version
            self.metadata['source_bound_prompt_sha256'] = sha256_file(self.root/'src/fullpage/source_bound_prompts.py')

    def generate(self,request,output):
        if self.contract_version == CONTRACT_VERSION:
            return self._generate_source_bound(request, output)
        return self._generate_legacy(request, output)

    def _generate_legacy(self,request,output):
        output=Path(output)
        if output.exists(): raise ValueError('Generation output exists')
        output.mkdir(parents=True)
        began=time.perf_counter(); attempts=[]
        report={'request_id':request.get('request_id'),'metadata':self.metadata,'attempts':attempts,'status':'stage_failed'}
        write_json(output/'request.json',request)
        errors=validate_request(request,self.catalog)
        def stage(task,prompt,validator,identifier):
            current=prompt
            for retry in range(2):
                try:
                    result=generate_task(self.model,self.tokenizer,current,task=task,config=self.config)
                    result.update(task=task,stage=identifier,retry=bool(retry))
                    if result['stop_reason']!='eos': result['errors']=['Missing EOS: '+result['stop_reason']]
                    else:
                        try: value=json.loads(result['raw']); result['errors']=validator(value)
                        except (ValueError,TypeError,KeyError) as error: result['errors']=['Invalid JSON/contract: '+str(error)]
                except (ValueError,FloatingPointError) as error:
                    result={'task':task,'stage':identifier,'retry':bool(retry),'errors':[str(error)],'stop_reason':'precheck_failed','generated_tokens':0,'seconds':0}
                attempts.append(result); write_json(output/f'attempt-{len(attempts):02d}.json',result)
                if not result['errors']: return value
                current=retry_prompt(prompt,'Use exact request identity and all required fields.')
            return None
        if errors:
            report.update(status='missing_information' if any('missing_information' in e for e in errors) else 'stage_failed',errors=errors)
        else:
            wire=stage('page_plan',plan_prompt(request),lambda v:validate_plan_wire(v,request,self.catalog),'plan')
            if wire is not None:
                plan=decode_plan(wire); write_json(output/'plan.json',plan); sections=[]
                for descriptor in plan['sections']:
                    section=stage('section_content',section_prompt(request,plan,descriptor),
                                  lambda v:validate_section(v,descriptor,request,self.catalog) or fact_errors(v,descriptor,request),descriptor['id'])
                    if section is None: break
                    sections.append(section)
                if len(sections)==len(plan['sections']):
                    try:
                        page=compose_page(plan,sections,request,self.catalog)
                        exported=export_fullpage(page,output/'website',root=self.root)
                        report.update(status='accepted',export=exported,sections=len(sections),required_roles=True,facts_valid=True,links_assets_valid=True)
                    except ValueError as error: report['errors']=[str(error)]
        report.update(seconds=time.perf_counter()-began,total_generated_tokens=sum(a['generated_tokens'] for a in attempts),
                      first_attempt_success=report['status']=='accepted' and not any(a['retry'] for a in attempts),browser_status='pending')
        write_json(output/'result.json',report); return report

    def _execute_task(self, prompt, task, *, contract_version=None):
        return generate_task(self.model, self.tokenizer, prompt, task=task, config=self.config,
                             contract_version=contract_version)

    def _generate_source_bound(self, request, output):
        output = Path(output)
        if output.exists():
            raise ValueError('Generation output exists')
        output.mkdir(parents=True)
        began = time.perf_counter()
        attempts = []
        report = {
            'request_id': request.get('request_id') if isinstance(request, dict) else None,
            'metadata': self.metadata,
            'attempts': attempts,
            'status': 'stage_failed',
        }
        write_json(output/'request.json', request)

        def finish():
            report.update(
                seconds=time.perf_counter()-began,
                total_generated_tokens=sum(attempt.get('generated_tokens', 0) for attempt in attempts),
                first_attempt_success=report['status']=='accepted' and not any(attempt.get('retry') for attempt in attempts),
                browser_status='pending',
            )
            write_json(output/'result.json', report)
            return report

        prompt_text = request.get('prompt') if isinstance(request, dict) else None
        if isinstance(prompt_text, str) and len(prompt_text) > MAX_REQUEST_PROMPT_CHARS:
            report.update(status='input_too_long', errors=[f'Prompt exceeds {MAX_REQUEST_PROMPT_CHARS} characters'])
            return finish()

        request_errors = validate_request(request, self.catalog)
        if request_errors:
            status = 'missing_information' if any('missing_information' in error for error in request_errors) else 'stage_failed'
            report.update(status=status, errors=request_errors)
            return finish()

        def precheck(prompt, task):
            return check_budget(self.tokenizer, prompt, output_budget_for(task, self.contract_version))

        def stage(task, prompt, validator, identifier):
            current = prompt
            for retry in range(2):
                if retry:
                    current = retry_prompt(prompt, SOURCE_BOUND_RETRY_INSTRUCTION)
                try:
                    result = self._execute_task(current, task, contract_version=self.contract_version)
                    result.update(task=task, stage=identifier, retry=bool(retry))
                    if result['stop_reason'] != 'eos':
                        result['errors'] = ['Missing EOS: ' + result['stop_reason']]
                    else:
                        try:
                            value = json.loads(result['raw'])
                            result['errors'] = validator(value)
                        except (ValueError, TypeError, KeyError) as error:
                            result['errors'] = ['Invalid JSON/contract: ' + str(error)]
                except (ValueError, FloatingPointError) as error:
                    result = {
                        'task': task,
                        'stage': identifier,
                        'retry': bool(retry),
                        'errors': [str(error)],
                        'stop_reason': 'precheck_failed',
                        'generated_tokens': 0,
                        'seconds': 0,
                    }
                attempts.append(result)
                write_json(output/f'attempt-{len(attempts):02d}.json', result)
                if not result['errors']:
                    return value
            return None

        try:
            plan_prompt = source_bound_plan_prompt(request)
            precheck(plan_prompt, 'page_plan')
            precheck(retry_prompt(plan_prompt, SOURCE_BOUND_RETRY_INSTRUCTION), 'page_plan')
        except ValueError as error:
            report.update(status='input_too_long', errors=[str(error)])
            return finish()

        page_plan = stage(
            'page_plan',
            plan_prompt,
            lambda value: validate_page_plan(value, request, self.copy_catalog),
            'plan',
        )
        if page_plan is None:
            report.update(status='stage_failed', errors=attempts[-1].get('errors', []))
            return finish()
        write_json(output/'plan.json', page_plan)

        section_prompts = []
        try:
            for descriptor in page_plan['sections']:
                prompt = source_bound_section_prompt(request, page_plan, descriptor)
                precheck(prompt, 'section_content')
                precheck(retry_prompt(prompt, SOURCE_BOUND_RETRY_INSTRUCTION), 'section_content')
                section_prompts.append((descriptor, prompt))
        except ValueError as error:
            report.update(status='input_too_long', errors=[str(error)])
            return finish()

        drafts = []
        for descriptor, prompt in section_prompts:
            draft = stage(
                'section_content',
                prompt,
                lambda value, selected=descriptor: validate_section_draft(value, selected, request, self.copy_catalog),
                descriptor['id'],
            )
            if draft is None:
                report.update(status='stage_failed', errors=attempts[-1].get('errors', []))
                return finish()
            drafts.append(draft)

        try:
            page = compose_source_bound_page(request, page_plan, drafts, self.copy_catalog)
        except ValueError as error:
            report.update(status='stage_failed', errors=[str(error)])
            return finish()

        website = output/'website'
        staging = output/('.website-staging-' + uuid.uuid4().hex)
        try:
            exported = export_fullpage(page, staging, root=self.root)
            if not staging.is_dir():
                raise OSError('Renderer did not create the staging directory')
            staging.replace(website)
            exported['path'] = str(website)
            report.update(
                status='accepted',
                export=exported,
                sections=len(drafts),
                required_roles=True,
                facts_valid=True,
                links_assets_valid=True,
            )
        except Exception as error:
            report.update(status='stage_failed', errors=['Source-bound export failed: ' + str(error)])
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
        return finish()


def generate_full_page(request,*,checkpoint,root,output):
    return FullPageGenerator(Path(root)/checkpoint,root).generate(request,Path(output))
