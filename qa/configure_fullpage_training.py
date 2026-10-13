"""Freeze a training budget after a successful independent GPU profile."""
import argparse
import json
import re
from pathlib import Path
from src.fullpage.curriculum import write_json
from src.data.sources import sha256_file
from src.training.engine import read_checkpoint,checkpoint_sha256


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--scope',choices=['pilot','main'],required=True); p.add_argument('--profile',default='reports/training/FULLPAGE-GPU-001.json'); p.add_argument('--output',required=True)
    p.add_argument('--dataset-dir'); p.add_argument('--plan-probability',type=float); p.add_argument('--max-steps',type=int); p.add_argument('--warmup-steps',type=int)
    p.add_argument('--validation-interval',type=int); p.add_argument('--checkpoint-interval',type=int); p.add_argument('--storage-phase-id'); p.add_argument('--selection-rule')
    args=p.parse_args(); root=args.root.resolve(); profile=json.loads((root/args.profile).read_text(encoding='utf-8')); selected=profile['selected']
    dataset_dir=args.dataset_dir or profile.get('dataset_dir','data/processed/fullpage/v1')
    dataset_path=(root/dataset_dir).resolve()
    if not dataset_path.is_relative_to(root): p.error('--dataset-dir must be inside --root')
    dataset_dir=dataset_path.relative_to(root).as_posix()
    plan_probability=args.plan_probability if args.plan_probability is not None else profile.get('plan_probability',.3)
    if not 0 < plan_probability < 1: p.error('--plan-probability must be between zero and one')
    if args.storage_phase_id and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}',args.storage_phase_id): p.error('Invalid --storage-phase-id')
    initial='checkpoints/INIT-2048-001/initial.pt'; parent=read_checkpoint(root/initial)
    manifest_path=dataset_path/'manifest.json'; manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    config={'mode':'sft','scope':args.scope,'data_origin':'fullpage_curriculum','human_reviewed':False,'dataset_dir':dataset_dir,
            'plan_batch_probability':plan_probability,
            'seed':42,'block_size':2048,'tokenizer':'data/tokenizer/tokenizer.json','model_config_path':'configs/model_fullpage_2048.json','model_config':parent['model_config'],
            'device':'cuda','precision':'bf16','batch_size':selected['batch'],'gradient_accumulation':selected['accumulation'],
            'max_steps':args.max_steps if args.max_steps is not None else (600 if args.scope=='pilot' else 2400),
            'warmup_steps':args.warmup_steps if args.warmup_steps is not None else (60 if args.scope=='pilot' else 120),
            'learning_rate':5e-5,'min_learning_rate':5e-6,'betas':[.9,.95],'weight_decay':.1,'grad_clip':1,
            'validation_interval':args.validation_interval if args.validation_interval is not None else (100 if args.scope=='pilot' else 400),
            'validation_batches':None,'checkpoint_interval':args.checkpoint_interval if args.checkpoint_interval is not None else (100 if args.scope=='pilot' else 400),
            'log_interval':100,'reserve_free_bytes':15*2**30,'initial_checkpoint':initial,'initial_checkpoint_sha256':checkpoint_sha256(root/initial),
            'performance':{'attention_backend':'sdpa','fused_adamw':True,'pin_memory':True,'tf32':True,'supervised_only_logits':True,
                           'validation_supervised_only_logits':True,'allocator_config':'expandable_segments:True','gpu_telemetry':True,'selected_by':args.profile},
            'selection_rule':args.selection_rule or 'Fixed budget, best full ordinary development CE. Generation development gate required before final. Main initializes independently from INIT2048, not pilot selection.',
            'lineage':{'tokenizer_sha256':manifest['tokenizer_sha256'],'fullpage_manifest_sha256':sha256_file(manifest_path),
                       'initialization_parent':parent['config']['lineage'],'schema_sha256':manifest['schema_sha256'],
                       'source_sha256':{p.relative_to(root).as_posix():sha256_file(p) for p in [root/'src/training/engine.py',root/'src/models/minigpt.py',root/'src/fullpage/dataset.py',root/'src/fullpage/prompts.py']},
                       'profile_sha256':sha256_file(root/args.profile)}}
    if args.storage_phase_id: config['storage_phase_id']=args.storage_phase_id
    config['performance']['best_weights_only']=args.scope=='main'
    write_json(root/args.output,config); print(json.dumps({k:config[k] for k in ('scope','batch_size','gradient_accumulation','max_steps','learning_rate')},indent=2))


if __name__=='__main__': main()
