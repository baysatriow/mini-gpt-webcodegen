"""Download a pinned public WebMC release and inspect it as untrusted data."""
import argparse
import hashlib
import json
import shutil
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from src.fullpage.curriculum import write_json


def fetch(url, limit=8*2**20):
    request=urllib.request.Request(url,headers={'User-Agent':'MiniGPT-coursework-dataset-inspection/1.0'})
    with urllib.request.urlopen(request,timeout=60) as response:
        body=response.read(limit+1)
        if len(body)>limit: raise ValueError('Public download exceeds declared inspection limit')
        return body


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report',default='reports/data/WEBMC_DOWNLOAD_INSPECTION_V1.json'); args=parser.parse_args(); root=args.root.resolve()
    free=shutil.disk_usage(root).free
    if free<15*2**30+16*2**20: raise OSError('Insufficient disk reserve for bounded download')
    meta=json.loads(fetch('https://huggingface.co/api/datasets/IFM/WebMC'))
    revision=meta['sha']; filenames=[s['rfilename'] for s in meta['siblings']]
    directory=root/'data/raw/candidates/webmc'/revision
    if directory.exists(): raise ValueError('Pinned candidate already exists; preserve previous download')
    directory.mkdir(parents=True); saved={}
    for name in ('README.md','WebMC.json'):
        if name not in filenames: raise ValueError('Expected public file unavailable: '+name)
        url=f'https://huggingface.co/datasets/IFM/WebMC/resolve/{revision}/{name}'
        body=fetch(url)
        with (directory/name).open('xb') as handle: handle.write(body)
        saved[name]={'url':url,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}
    data=json.loads((directory/'WebMC.json').read_text(encoding='utf-8'))
    rows=data if isinstance(data,list) else list(data.values()) if isinstance(data,dict) else []
    keys=Counter(k for row in rows if isinstance(row,dict) for k in row)
    def preview(value):
        if isinstance(value,str): return value[:900]
        if isinstance(value,list): return [preview(v) for v in value[:5]]
        if isinstance(value,dict): return {k:preview(v) for k,v in list(value.items())[:12]}
        return value
    webdev_status={}
    try:
        webdev=json.loads(fetch('https://huggingface.co/api/datasets/Hoglet-33/webdev-coding-dataset'))
        webdev_status={'public_metadata_accessible':True,'sha':webdev['sha'],'files':[s['rfilename'] for s in webdev.get('siblings',[])]}
    except urllib.error.HTTPError as error:
        webdev_status={'public_metadata_accessible':False,'http_status':error.code,'meaning':'Could be unavailable, renamed or private; status alone does not distinguish these'}
    report={'repository':'IFM/WebMC','revision':revision,'repository_files':filenames,'declared_license':meta.get('cardData',{}).get('license'),
            'output':str(directory.relative_to(root)),'files':saved,'root_type':type(data).__name__,'root_records':len(rows),
            'root_keys':list(data)[:12] if isinstance(data,dict) else None,'record_key_counts':dict(keys),'sample_records':[preview(r) for r in rows[:2]],
            'webdev_current_public_status':webdev_status,'training_pipeline_modified_by_download':False,'candidate_not_added_to_training':True,
            'storage_free_before':free,'storage_free_after':shutil.disk_usage(root).free}
    write_json(root/args.report,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
