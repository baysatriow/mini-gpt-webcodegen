"""Development-only candidate selection and separately locked final evaluation."""
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
from .generation import FullPageGenerator
from .curriculum import write_json
from .serialization import canonical
from src.data.sources import sha256_file
from src.training.engine import checkpoint_sha256,read_checkpoint


def evaluate_requests(requests,*,checkpoint,root,output,resume=False):
    root,output=Path(root),Path(output); checkpoint=Path(checkpoint)
    identity={'checkpoint_sha256':checkpoint_sha256(checkpoint),'requests_sha256':hashlib.sha256(canonical(requests).encode()).hexdigest(),'count':len(requests),
              'source_sha256':{p:sha256_file(root/p) for p in ('src/fullpage/generation.py','src/fullpage/compose.py','src/fullpage/contracts.py','src/fullpage/prompts.py')}}
    if output.exists():
        if not resume or json.loads((output/'identity.json').read_text(encoding='utf-8'))!=identity: raise ValueError('Evaluation output/identity differs')
    else: output.mkdir(parents=True); write_json(output/'identity.json',identity)
    generator=FullPageGenerator(checkpoint,root); results=[]; began=time.perf_counter()
    for number,request in enumerate(requests,1):
        directory=output/request['request_id']; directory.mkdir(exist_ok=True); prior=[]
        for p in sorted(directory.glob('attempt-*/result.json')):
            report=json.loads(p.read_text(encoding='utf-8'))
            if report['metadata']['checkpoint_sha256']!=identity['checkpoint_sha256']: raise ValueError('Prior page checkpoint differs')
            prior.append(report)
        if prior: result=prior[-1]
        else:
            attempt=1+len(list(directory.glob('attempt-*')))
            result=generator.generate(request,directory/f'attempt-{attempt:02d}')
        result={**result,'genre':request['genre'],'style_mode':request['style_mode']}; results.append(result)
        print(json.dumps({'page':number,'of':len(requests),'request_id':request['request_id'],'status':result['status'],'seconds':round(result['seconds'],3)}),flush=True)
    count=len(results); accepted=[r for r in results if r['status']=='accepted']
    groups={}
    for r in results:
        group=groups.setdefault(r['genre']+':'+r['style_mode'],{'total':0,'complete':0,'first_attempt':0})
        group['total']+=1; group['complete']+=r['status']=='accepted'; group['first_attempt']+=r['first_attempt_success']
    failures=Counter(e.split(':')[0] for r in results if r['status']!='accepted' for a in r['attempts'][-1:] for e in a.get('errors',[]))
    complete=len(accepted); roles=sum(r.get('required_roles',False) for r in results)
    report={**identity,'complete':complete,'total':count,'complete_rate':complete/count,'required_roles':roles,'required_roles_rate':roles/count,
            'first_attempt_complete':sum(r['first_attempt_success'] for r in results),'after_retry_complete':complete,
            'accepted_facts_links_assets_valid':all(r.get('facts_valid') and r.get('links_assets_valid') for r in accepted),
            'model_gate':complete/count>=.95 and roles/count>=.95 and bool(accepted),
            'groups':groups,'failures':dict(failures),'page_seconds':{'total':sum(r['seconds'] for r in results),'mean':sum(r['seconds'] for r in results)/count},
            'generation_tokens':sum(r['total_generated_tokens'] for r in results),'wall_seconds':time.perf_counter()-began,'output':str(output),
            'browser_status':'pending','human_review_status':'pending','results':[{'request_id':r['request_id'],'status':r['status'],'seconds':r['seconds']} for r in results]}
    return report


def lock_fullpage_candidate(development_report,checkpoint,destination):
    report=json.loads(Path(development_report).read_text(encoding='utf-8')); checkpoint=Path(checkpoint)
    if report['total']!=80 or not report['model_gate']: raise ValueError('Development model gate has not passed')
    if report['checkpoint_sha256']!=checkpoint_sha256(checkpoint): raise ValueError('Candidate SHA differs')
    state=read_checkpoint(checkpoint)
    if state['config']['scope']!='main' or state['global_step']==0: raise ValueError('Candidate must be trained main best ordinary CE')
    root=Path(__file__).resolve().parents[2]; summary=json.loads((root/f'reports/training/{state["run_id"]}.json').read_text(encoding='utf-8'))
    if summary['status']!='completed' or summary['best_checkpoint_sha256']!=report['checkpoint_sha256']: raise ValueError('Candidate is not completed-run best CE')
    candidate={'status':'locked','checkpoint':checkpoint.relative_to(root).as_posix(),'checkpoint_sha256':report['checkpoint_sha256'],
               'development_report_sha256':sha256_file(Path(development_report)),'development_complete':report['complete'],
               'training_config':state['config'],'benchmark_manifest_sha256':sha256_file(root/'data/evaluation/fullpage/manifest.json'),
               'selection_rule':'best full ordinary development CE in completed fixed budget run, generation gate>=95%; no final fitting'}
    write_json(Path(destination),candidate); return candidate
