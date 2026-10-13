"""Actual per-task ordinary CE, long-position labels and projection equivalence."""
import argparse
import json
import shutil
from pathlib import Path
import torch
from tokenizers import Tokenizer
from src.models.minigpt import MiniGPT
from src.training.engine import read_checkpoint,checkpoint_sha256,loss_sum,_autocast
from src.fullpage.dataset import TaskDataset,trim_collate
from src.fullpage.curriculum import write_json


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--checkpoint',required=True); p.add_argument('--report',required=True)
    args=p.parse_args(); root=args.root.resolve(); state=read_checkpoint(root/args.checkpoint)
    directory=root/state['config']['dataset_dir']; manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    ids=set(manifest['pilot_family_ids']['validation']) if state['config']['scope']=='pilot' else None
    tokenizer=Tokenizer.from_file(str(root/'data/tokenizer/tokenizer.json')); dataset=TaskDataset(directory/'validation.jsonl',tokenizer,ids)
    model=MiniGPT(state['model_config']).to('cuda'); model.load_state_dict(state['model']); model.set_attention_backend('sdpa'); model.eval()
    stats={}; max_difference=0
    with torch.inference_mode():
        for task in ('page_plan','section_content'):
            rows=[d for r,d in zip(dataset.rows,dataset.encoded) if r['task']==task]; total=0; count=0; above=0; above_loss=0
            for offset in range(0,len(rows),16):
                batch={k:v.cuda() for k,v in trim_collate(rows[offset:offset+16]).items()}; active=batch['labels']!=-100
                with _autocast(torch.device('cuda'),'bf16'): logits=model(batch['input_ids'],output_mask=active)
                loss,tokens=loss_sum(logits,batch['labels'][active]); total+=float(loss); count+=tokens
                positions=torch.arange(batch['input_ids'].shape[1],device='cuda').expand_as(active)
                long_mask=positions[active]>=1024
                if long_mask.any():
                    long_loss,long_count=loss_sum(logits[long_mask],batch['labels'][active][long_mask]); above_loss+=float(long_loss); above+=long_count
            stats[task]={'loss':total/count,'valid_tokens':count,'rows':len(rows),'tokens_after_position_1024':above,'loss_after_position_1024':above_loss/above if above else None}
            batch={k:v.cuda() for k,v in trim_collate([rows[0]]).items()}; active=batch['labels']!=-100
            with _autocast(torch.device('cuda'),'bf16'):
                full=model(batch['input_ids']); selected=model(batch['input_ids'],output_mask=active)
            difference=float((full[active].float()-selected.float()).abs().max()); max_difference=max(max_difference,difference)
            first,_=loss_sum(full,batch['labels']); second,_=loss_sum(selected,batch['labels'][active])
            if abs(float(first-second))>1e-3*int(active.sum()): raise ValueError('Projection loss discrepancy')
    output={'checkpoint_sha256':checkpoint_sha256(root/args.checkpoint),'scope':state['config']['scope'],'step':state['global_step'],
            'ordinary_ce_by_task':stats,'selected_vs_full_projection_max_abs_difference':max_difference,'projection_ce_equivalent_within_1e_3_per_token':True,
            'final_data_opened':False,'disk_free_bytes':shutil.disk_usage(root).free}
    write_json(root/args.report,output); print(json.dumps(output,indent=2))


if __name__=='__main__': main()
