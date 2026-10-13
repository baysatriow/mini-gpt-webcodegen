"""Augment train identities/plans while preserving development/final bytes."""
import argparse
import copy
import json
import random
import shutil
from collections import Counter
from pathlib import Path
from tokenizers import Tokenizer
from src.data.normalize import read_jsonl
from src.data.sources import sha256_file
from src.fullpage.assets import load_asset_catalog
from src.fullpage.compose import compose_page
from src.fullpage.curriculum import make_page, write_json
from src.fullpage.prompts import plan_prompt, section_prompt, retry_prompt
from src.fullpage.serialization import canonical, serialize_task, check_budget, OUTPUT_BUDGETS


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',default='data/processed/fullpage/v2'); p.add_argument('--report',default='reports/data/FULLPAGE_CURRICULUM_V2.json')
    args=p.parse_args(); root=args.root.resolve(); source=root/'data/processed/fullpage/v1'; output=root/args.output
    if output.exists(): raise ValueError('New curriculum exists')
    if shutil.disk_usage(root).free<15*2**30+100*2**20: raise OSError('Data write would breach disk reserve')
    old=json.loads((source/'manifest.json').read_text(encoding='utf-8')); output.mkdir(parents=True)
    for name,info in old['files'].items():
        if sha256_file(source/name)!=info['sha256']: raise ValueError('Frozen parent bytes changed')
        shutil.copyfile(source/name,output/name)
    tokenizer=Tokenizer.from_file(str(root/'data/tokenizer/tokenizer.json')); catalog=load_asset_catalog(root)
    base_requests=list(read_jsonl(source/'train.requests.jsonl')); development=list(read_jsonl(source/'validation.requests.jsonl'))
    dev_names={f['value'] for r in development for f in r['request']['business_facts'] if f['kind']=='name'}
    train_family_ids={r['family_id'] for r in base_requests}; tasks=Counter(); requests_added=0; lengths=[]; aliases=set()
    rng=random.Random(424243)
    with (output/'train.jsonl').open('a',encoding='utf-8',newline='\n') as tasks_file, (output/'train.requests.jsonl').open('a',encoding='utf-8',newline='\n') as requests_file:
        for record in base_requests:
            family=record['family_id']; original=record['request']; index=int(family.removeprefix('family'))
            original_name=next(f['value'] for f in original['business_facts'] if f['kind']=='name')
            names=[original_name+' Nusantara','Demo '+original_name,original_name+' Utama',original_name+' Bersama']
            for variant,name in enumerate(names):
                if name in dev_names or len(name.split())<3: raise ValueError('Alias identity/split collision')
                aliases.add(name); request,plan,sections,_=make_page(index,'train',original['style_mode'],name)
                request['request_id']=original['request_id']+'-v'+str(variant)
                accent=('#2563eb','#0f766e','#7c3aed','#b45309')[variant]; font=('sans','serif')[variant%2]
                plan['theme'].update(primary=accent,font=font)
                request['prompt']=f"Buat {request['genre']} lengkap untuk {name}. Gunakan aksen {accent} dan font {font}. Ini contoh fiktif, gunakan menu responsif dan kontak lokal."
                pairs=list(zip(plan['sections'][2:-1],sections[2:-1])); rng.shuffle(pairs)
                plan['sections']=plan['sections'][:2]+[d for d,s in pairs]+plan['sections'][-1:]
                sections=sections[:2]+[s for d,s in pairs]+sections[-1:]
                hero=next(s for s in sections if s['role']=='hero'); hd=next(d for d in plan['sections'] if d['role']=='hero')
                hero['variant']=hd['variant']=hero['props']['layout']=('centered','split')[variant%2]
                compose_page(plan,sections,request,catalog)
                requests_file.write(canonical({'family_id':family,'split':'train','augmentation':variant,'request':request})+'\n'); requests_added+=1
                generated=[('page_plan',plan_prompt(request),plan)]
                generated += [('section_content',section_prompt(request,plan,d),s) for d,s in zip(plan['sections'],sections) if s['role'] in ('hero','about','footer')]
                for number,(task,prompt,target) in enumerate(generated):
                    for retry in (False,True) if number in (0,1) else (False,):
                        text=retry_prompt(prompt,'Use exact request identity and all required fields.') if retry else prompt
                        budget=check_budget(tokenizer,text,OUTPUT_BUDGETS[task]); target_text=serialize_task(task,target); target_tokens=len(tokenizer.encode(target_text).ids)+1
                        if target_tokens>OUTPUT_BUDGETS[task]: raise ValueError('Augmented target budget exceeded')
                        row={'example_id':request['request_id']+'-'+str(number)+('-retry' if retry else ''),'family_id':family,'split':'train',
                             'task':task,'prompt':text,'target':target_text,'length':budget['prefix_tokens']+target_tokens-1,
                             'human_reviewed':False,'origin':'project-authored train-only fullpage augmentation','genre':request['genre'],
                             'style_mode':request['style_mode'],'retry':retry,'augmentation':variant}
                        tasks_file.write(canonical(row)+'\n'); tasks[task]+=1; lengths.append((task,budget['prefix_tokens'],target_tokens,row['length']+1))
    manifest=copy.deepcopy(old); manifest.update(version='fullpage-v2',seed=424243,parent_manifest_sha256=sha256_file(source/'manifest.json'))
    manifest['task_counts']['train']+=sum(tasks.values())
    manifest['files']={p.name:{'sha256':sha256_file(p),'bytes':p.stat().st_size} for p in output.glob('*.jsonl')}
    manifest['augmentation']={'train_pages_added':requests_added,'train_pages_total':len(base_requests)+requests_added,'train_families':len(train_family_ids),
                              'new_name_aliases':len(aliases),'added_tasks':dict(tasks),'development_names_in_train':False,
                              'final_parsed':False,'policy':'aliases have at least three words, whereas original frozen name recipe has exactly two; no final names inspected',
                              'independent_families_not_added':True,'source_sha256':sha256_file(Path(__file__))}
    for task in OUTPUT_BUDGETS:
        manifest['max_prefix'][task]=max(old['max_prefix'][task],max(p[1] for p in lengths if p[0]==task))
        manifest['max_target_with_eos'][task]=max(old['max_target_with_eos'][task],max(p[2] for p in lengths if p[0]==task))
    manifest['max_total_tokens']=max(old['max_total_tokens'],max(p[3] for p in lengths))
    manifest['bytes']=sum(info['bytes'] for info in manifest['files'].values())
    for name in ('validation.jsonl','validation.requests.jsonl','test.jsonl','test.requests.jsonl'):
        if manifest['files'][name]['sha256']!=old['files'][name]['sha256']: raise ValueError('Heldout bytes changed')
    write_json(output/'manifest.json',manifest); write_json(root/args.report,manifest)
    print(json.dumps({k:manifest[k] for k in ('version','task_counts','augmentation','max_prefix','max_target_with_eos','max_total_tokens','bytes')},indent=2))


if __name__=='__main__': main()
