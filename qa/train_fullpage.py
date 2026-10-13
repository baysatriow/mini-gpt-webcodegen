"""Immutable fullpage data lineage and exact-resume project training wrapper."""
import argparse
import json
import os
from pathlib import Path


def run_fullpage_training(config_path,*,run_id,resume=None,root,stop_after=None):
    import torch
    from torch.utils.data import DataLoader
    from tokenizers import Tokenizer
    from src.fullpage.dataset import TaskDataset,TaskBatchSampler,trim_collate
    from src.data.sources import sha256_file
    from src.training.engine import run_training
    root=Path(root).resolve(); config_path=Path(config_path); config=json.loads(config_path.read_text(encoding='utf-8'))
    directory=root/config['dataset_dir']; manifest_path=directory/'manifest.json'; manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    lineage=config['lineage']
    if sha256_file(manifest_path)!=lineage['fullpage_manifest_sha256']: raise ValueError('Fullpage manifest changed')
    for name,info in manifest['files'].items():
        if sha256_file(directory/name)!=info['sha256']: raise ValueError('Frozen data file changed: '+name)
    for name,digest in manifest['schema_sha256'].items():
        if sha256_file(root/'configs/fullpage'/name)!=digest: raise ValueError('Data schema changed')
    for path,digest in lineage['source_sha256'].items():
        if sha256_file(root/path)!=digest: raise ValueError('Training source changed: '+path)
    if sha256_file(root/config['tokenizer'])!=lineage['tokenizer_sha256']: raise ValueError('Tokenizer changed')
    tokenizer=Tokenizer.from_file(str(root/config['tokenizer'])); loaders={}
    for split in ('train','validation'):
        families=set(manifest['pilot_family_ids'][split]) if config['scope']=='pilot' else None
        dataset=TaskDataset(directory/(split+'.jsonl'),tokenizer,families)
        sampler=TaskBatchSampler(dataset.lengths,dataset.task_kinds,config['batch_size'],config['seed'],balanced=split=='train',
                                 plan_probability=config.get('plan_batch_probability',.3) if split=='train' else .3)
        loaders[split]=DataLoader(dataset,batch_sampler=sampler,collate_fn=trim_collate,num_workers=0,pin_memory=True)
    return run_training(config_path,loaders['train'],loaders['validation'],run_id,resume=resume,root=root,stop_after=stop_after)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--config',required=True); p.add_argument('--run-id',required=True); p.add_argument('--resume')
    p.add_argument('--stop-after',type=int); args=p.parse_args()
    # Set before torch and fullpage.dataset import.
    os.environ['PYTORCH_ALLOC_CONF']='expandable_segments:True'
    checkpoint=run_fullpage_training(args.root/args.config,run_id=args.run_id,resume=args.root/args.resume if args.resume else None,root=args.root,stop_after=args.stop_after)
    print(json.dumps({'last_checkpoint':str(checkpoint)}))


if __name__=='__main__': main()
