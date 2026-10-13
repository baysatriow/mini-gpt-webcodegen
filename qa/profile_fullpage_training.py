"""Fresh CUDA profiling of accumulated worst-length fullpage batches."""
import argparse
import json
import os
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--report-id',required=True)
    p.add_argument('--dataset-dir',default='data/processed/fullpage/v1'); p.add_argument('--plan-probability',type=float,default=.3)
    p.add_argument('--batch',type=int); p.add_argument('--child',action='store_true'); p.add_argument('--representative',action='store_true'); args=p.parse_args(); root=args.root.resolve()
    if not 0 < args.plan_probability < 1: p.error('--plan-probability must be between zero and one')
    dataset_dir=(root/args.dataset_dir).resolve()
    if not dataset_dir.is_relative_to(root): p.error('--dataset-dir must be inside --root')
    if not args.child:
        import subprocess, sys
        from src.fullpage.curriculum import write_json
        results=[]
        report_path=root/f'reports/training/{args.report_id}.json'
        if report_path.exists(): raise ValueError('Profile report exists')
        for batch in (4,8,12,16):
            env={**os.environ,'PYTORCH_ALLOC_CONF':'expandable_segments:True','PYTHONIOENCODING':'utf-8'}
            command=[sys.executable,'-m','qa.profile_fullpage_training','--root',str(root),'--report-id',args.report_id,
                     '--dataset-dir',str(dataset_dir),'--plan-probability',str(args.plan_probability),'--batch',str(batch),'--child']
            if args.representative: command.append('--representative')
            completed=subprocess.run(command,cwd=root,env=env)
            path=root/f'reports/training/{args.report_id}-B{batch}.json'
            result=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'batch':batch,'status':'child_failed','returncode':completed.returncode}
            results.append(result)
            if result['status']!='stable': break
        stable=[r for r in results if r['status']=='stable']
        worst_report=None
        if args.representative:
            worst_report=json.loads((root/'reports/training/FULLPAGE-GPU-001.json').read_text(encoding='utf-8'))
            stable=[r for r in stable if any(w['batch']==r['batch'] and w['status']=='stable' for w in worst_report['results'])]
        if not stable: raise ValueError('No stable batch configuration')
        selected=max(stable,key=lambda r:r['tokens_per_second'])
        write_json(report_path,{'dataset_dir':str(dataset_dir.relative_to(root)).replace('\\','/'),'plan_probability':args.plan_probability,
                                'results':results,'selected':selected,'worst_context_report':'reports/training/FULLPAGE-GPU-001.json' if args.representative else None,
                                'final_data_opened':False,'probe_weights_discarded':True})
        print(json.dumps({'selected_batch':selected['batch'],'accumulation':selected['accumulation'],'tokens_per_second':selected['tokens_per_second']},indent=2)); return
    # Allocator was set in the parent before any torch import in this child.
    import time, shutil, torch
    from tokenizers import Tokenizer
    from src.models.minigpt import MiniGPT
    from src.training.engine import read_checkpoint, train_one_step, seed_everything
    from src.training.performance import GpuMonitor
    from src.fullpage.curriculum import write_json
    from src.fullpage.dataset import TaskDataset,TaskBatchSampler,trim_collate
    if shutil.disk_usage(root).free<15*2**30+64*2**20: raise OSError('Disk reserve failed')
    seed_everything(42); tokenizer=Tokenizer.from_file(str(root/'data/tokenizer/tokenizer.json'))
    dataset=TaskDataset(dataset_dir/'train.jsonl',tokenizer)
    sample=max(dataset.encoded,key=lambda r:r['length'])
    # Same real supervised example, padded to2048 to measure worst attention length. Padding remains masked.
    worst={'input_ids':sample['input_ids']+[0]*(2048-sample['length']), 'labels':sample['labels']+[-100]*(2048-sample['length']), 'length':2048}
    batch=trim_collate([worst]*args.batch); accumulation=48//args.batch
    sampler=TaskBatchSampler(dataset.lengths,dataset.task_kinds,args.batch,42,plan_probability=args.plan_probability)
    stream=iter(sampler)
    def update_batches():
        nonlocal stream
        if not args.representative: return [batch]*accumulation
        result=[]
        for _ in range(accumulation):
            try: indices=next(stream)
            except StopIteration: stream=iter(sampler); indices=next(stream)
            result.append(trim_collate([dataset[i] for i in indices]))
        return result
    state=read_checkpoint(root/'checkpoints/INIT-2048-001/initial.pt'); model=MiniGPT(state['model_config']).to('cuda'); model.load_state_dict(state['model'])
    model.set_attention_backend('sdpa'); model.supervised_only_logits=True
    torch.backends.cuda.matmul.allow_tf32=True
    optimizer=torch.optim.AdamW(model.parameters(),lr=5e-5,betas=(.9,.95),weight_decay=.1,fused=True)
    monitor=GpuMonitor(root/f'outputs/metrics/{args.report_id}-B{args.batch}_gpu.jsonl').start()
    result={'batch':args.batch,'accumulation':accumulation,'effective_batch':48,'length':'trimmed representative tasks' if args.representative else 2048,
            'dataset_dir':str(dataset_dir.relative_to(root)).replace('\\','/'),'plan_probability':args.plan_probability,
            'real_target_tokens':sum(l!=-100 for l in sample['labels']),'warmup_updates':6,'measured_updates':20,'status':'failed'}
    try:
        for _ in range(6): train_one_step(model,update_batches(),optimizer,None,'sft',precision='bf16')
        torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats(); began=time.perf_counter(); tokens=0
        for _ in range(20):
            step=train_one_step(model,update_batches(),optimizer,None,'sft',precision='bf16'); tokens+=step['valid_tokens']
        torch.cuda.synchronize(); seconds=time.perf_counter()-began
        free,total=torch.cuda.mem_get_info()
        result.update(status='stable' if free>=512*2**20 else 'insufficient_headroom',seconds=seconds,valid_tokens=tokens,tokens_per_second=tokens/seconds,
                      peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),free_device_bytes=free,total_device_bytes=total,last_step=step,gpu=torch.cuda.get_device_name())
    except Exception as error: result.update(status='oom' if isinstance(error,torch.OutOfMemoryError) else 'failed',error_type=type(error).__name__,error=str(error))
    finally:
        result['telemetry']=monitor.finish(); write_json(root/f'reports/training/{args.report_id}-B{args.batch}.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='telemetry'},indent=2))


if __name__=='__main__': main()
