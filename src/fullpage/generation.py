"""Greedy staged generation; raw model text is validated and never repaired."""
import json
import time
from pathlib import Path
import torch
from tokenizers import Tokenizer
from src.data.sources import sha256_file
from src.training.engine import read_checkpoint, checkpoint_sha256, _autocast, seed_everything
from src.models.minigpt import MiniGPT
from .assets import load_asset_catalog
from .contracts import validate_request, validate_plan_wire, validate_section
from .compose import compose_page, fact_errors
from .serialization import OUTPUT_BUDGETS, check_budget, decode_plan
from .prompts import plan_prompt, section_prompt, retry_prompt
from .renderer import export_fullpage
from .curriculum import write_json


def generate_task(model, tokenizer, prompt, *, task, config):
    budget=OUTPUT_BUDGETS[task]; check=check_budget(tokenizer,prompt,budget)
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
        if state['model_config']['block_size']!=2048: raise ValueError('Fullpage requires context2048')
        lineage=state['config']['lineage']; actual=sha256_file(self.root/'data/tokenizer/tokenizer.json')
        if lineage['tokenizer_sha256']!=actual: raise ValueError('Tokenizer differs from checkpoint')
        if not (lineage.get('migration_kind')=='position_extension' or state['config'].get('data_origin')=='fullpage_curriculum'):
            raise ValueError('Missing project fullpage ancestry')
        if state['config'].get('data_origin')=='fullpage_curriculum':
            for name,digest in lineage['schema_sha256'].items():
                if sha256_file(self.root/'configs/fullpage'/name)!=digest: raise ValueError('Generation schema differs from training')
            if sha256_file(self.root/'src/fullpage/prompts.py')!=lineage['source_sha256']['src/fullpage/prompts.py']:
                raise ValueError('Task prompts differ from training')
            ancestor=lineage['initialization_parent']
        else: ancestor=lineage
        if ancestor.get('source_checkpoint_sha256')!='3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638':
            raise ValueError('Project source ancestry mismatch')
        seed_everything(self.config['seed']); self.model=MiniGPT(state['model_config']).to('cuda')
        self.model.load_state_dict(state['model']); self.model.set_attention_backend('sdpa'); self.model.eval()
        self.tokenizer=Tokenizer.from_file(str(self.root/'data/tokenizer/tokenizer.json')); self.catalog=load_asset_catalog(self.root)
        self.metadata={'checkpoint_sha256':checkpoint_sha256(self.checkpoint),'checkpoint_run_id':state['run_id'],
                       'checkpoint_step':state['global_step'],'tokenizer_sha256':actual,'config':self.config,
                       'schemas_sha256':{p.name:sha256_file(p) for p in (self.root/'configs/fullpage').glob('*.schema.json')},
                       'prompt_source_sha256':sha256_file(self.root/'src/fullpage/prompts.py')}

    def generate(self,request,output):
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


def generate_full_page(request,*,checkpoint,root,output):
    return FullPageGenerator(Path(root)/checkpoint,root).generate(request,Path(output))
