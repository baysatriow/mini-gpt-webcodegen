"""Freeze final review IDs before seeing any trained fullpage output."""
import argparse
import hashlib
import json
import random
from pathlib import Path
from src.fullpage.curriculum import make_page,write_json
from src.data.sources import sha256_file


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); args=p.parse_args(); root=args.root.resolve()
    manifest=json.loads((root/'data/processed/fullpage/v1/manifest.json').read_text(encoding='utf-8')); groups={}
    for family,split in manifest['allocation'].items():
        if split!='test': continue
        index=int(family.removeprefix('family'))
        for style in ('plain_css','tailwind'):
            # ID/genre metadata only, final task targets and request facts are not read.
            key=('landing_page' if index%2==0 else 'company_profile')+':'+style
            groups.setdefault(key,[]).append(f'page{index:04d}-{style}')
    rng=random.Random(42); selected={k:sorted(rng.sample(v,3)) for k,v in groups.items()}
    output={'seed':42,'final_requests_sha256':manifest['files']['test.requests.jsonl']['sha256'],'final_tasks_sha256':manifest['files']['test.jsonl']['sha256'],
            'final_pages':80,'model_gate':{'complete_min':76,'required_roles_min':76,'accepted_fact_link_asset_rate':1.0},
            'review_ids':selected,'ratings':['relevance','text_quality','layout_hierarchy','consistency'],
            'review_gate':{'mean_min':4,'individual_min':3,'reviewer_identity_required':True},'viewports':[390,1440],
            'status':'frozen_before_training','final_targets_opened':False}
    write_json(root/'data/evaluation/fullpage/manifest.json',output); print(json.dumps(output,indent=2))


if __name__=='__main__': main()
