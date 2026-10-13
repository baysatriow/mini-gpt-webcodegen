"""Check staged evidence bytes or the published revision without changing Git state."""
import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path
from src.fullpage.curriculum import write_json


def git(root,*args):
    return subprocess.run(['git',*args],cwd=root,check=True,capture_output=True).stdout


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--report',required=True); p.add_argument('--remote',action='store_true'); args=p.parse_args()
    root=Path(__file__).resolve().parents[1]; branch=git(root,'branch','--show-current').decode().strip()
    if branch!='feature/pipeline-data-model-training': raise ValueError('Unexpected delivery branch')
    result={'branch':branch}
    if args.remote:
        head=git(root,'rev-parse','HEAD').decode().strip()
        remote=git(root,'ls-remote','origin','refs/heads/'+branch).decode().split()[0]
        if head!=remote: raise ValueError('Remote revision differs')
        repository=json.loads(subprocess.run(['gh','repo','view','--json','isPrivate,nameWithOwner,url'],cwd=root,check=True,capture_output=True).stdout)
        if not repository['isPrivate']: raise ValueError('Repository is not private')
        body=git(root,'log','-1','--format=%B').decode()
        if 'co-authored-by' in body.lower(): raise ValueError('Unexpected co-author footer')
        result.update(head=head,remote_head=remote,repository=repository,no_coauthor_footer=True)
    else:
        paths=git(root,'diff','--cached','--name-only','-z').decode().split('\0')[:-1]
        output=subprocess.run(['git','cat-file','--batch'],cwd=root,input=''.join(':'+n+'\n' for n in paths).encode(),check=True,capture_output=True).stdout
        reader=io.BytesIO(output); normalized_logs=0
        for name in paths:
            header=reader.readline().decode().split(); size=int(header[2]); staged=reader.read(size); reader.read(1)
            local=(root/name).read_bytes()
            if staged!=local:
                if not name.startswith('logs/') or staged!=local.replace(b'\r\n',b'\n'): raise ValueError('Staged raw evidence bytes differ: '+name)
                normalized_logs+=1
        for suffix in ('BEST','LAST'):
            report=json.loads((root/f'reports/fullpage/TRAIN-017_DEVELOPMENT_{suffix}_V2.json').read_text(encoding='utf-8'))
            for name,digest in report['revalidation']['source_sha256'].items():
                if hashlib.sha256(git(root,'show',':'+name)).hexdigest()!=digest: raise ValueError('Staged revalidation source hash differs')
        git(root,'diff','--cached','--check')
        if git(root,'diff','--cached','--name-only','--','examples/generated/AI-013','src/runtime/renderer.py').strip(): raise ValueError('Historical runtime/gallery changed')
        result.update(staged_files=len(paths),evidence_bytes_identical=True,log_newline_normalizations=normalized_logs,
                      staged_revalidation_sources_match=True,historical_runtime_gallery_unchanged=True,diff_check=True)
    write_json(root/args.report,result); print(json.dumps(result,indent=2))


if __name__=='__main__': main()
