"""Evaluate pilot/development, or a final corpus only with a locked candidate."""
import argparse
import json
from pathlib import Path
from src.data.normalize import read_jsonl
from src.data.sources import sha256_file
from src.fullpage.evaluation import evaluate_requests, claim_final_evaluation
from src.fullpage.curriculum import write_json
from src.training.engine import checkpoint_sha256


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--scope',choices=['pilot','development','final'],required=True)
    p.add_argument('--dataset-dir',default='data/processed/fullpage/v1')
    p.add_argument('--checkpoint',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); p.add_argument('--candidate'); p.add_argument('--resume',action='store_true')
    args=p.parse_args(); root=args.root.resolve(); directory=(root/args.dataset_dir).resolve()
    if not directory.is_relative_to(root): p.error('--dataset-dir must be inside --root')
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    path=directory/('test.requests.jsonl' if args.scope=='final' else 'validation.requests.jsonl')
    if sha256_file(path)!=manifest['files'][path.name]['sha256']: raise ValueError('Frozen request file changed')
    if args.scope=='final':
        if not args.candidate: raise ValueError('Final requires locked candidate')
        candidate=json.loads((root/args.candidate).read_text(encoding='utf-8'))
        if candidate['status']!='locked' or candidate['checkpoint_sha256']!=checkpoint_sha256(root/args.checkpoint): raise ValueError('Final candidate mismatch')
        if candidate['benchmark_manifest_sha256']!=sha256_file(root/'data/evaluation/fullpage/manifest.json'): raise ValueError('Final benchmark changed')
        if (root/args.report).exists(): raise ValueError('Final report already completed; do not evaluate again')
        identity={'checkpoint_sha256':candidate['checkpoint_sha256'],'candidate_sha256':sha256_file(root/args.candidate),
                  'benchmark_manifest_sha256':candidate['benchmark_manifest_sha256'],'request_file_sha256':sha256_file(path),
                  'output':str((root/args.output).resolve()),'report':str((root/args.report).resolve()),
                  'source_sha256':{name:sha256_file(root/name) for name in ('qa/evaluate_fullpage.py','src/fullpage/evaluation.py','src/fullpage/generation.py','src/fullpage/compose.py','src/fullpage/contracts.py')}}
        claim_final_evaluation(root/'data/evaluation/fullpage/final_consumption.json',identity,resume=args.resume)
    rows=list(read_jsonl(path))
    if args.scope=='pilot': rows=[r for r in rows if r['family_id'] in manifest['pilot_family_ids']['validation']]
    report=evaluate_requests([r['request'] for r in rows],checkpoint=root/args.checkpoint,root=root,output=root/args.output,resume=args.resume)
    report.update(scope=args.scope,request_file=path.relative_to(root).as_posix(),request_file_sha256=sha256_file(path),
                  dataset_manifest_sha256=sha256_file(directory/'manifest.json'),final_used=args.scope=='final')
    write_json(root/args.report,report); print(json.dumps({k:report[k] for k in ('scope','complete','total','model_gate')},indent=2))


if __name__=='__main__': main()
