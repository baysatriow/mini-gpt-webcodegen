"""Generate a complete page using raw validated stages from a project checkpoint."""
import argparse
import json
from pathlib import Path
from src.fullpage.generation import generate_full_page


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--request',required=True); p.add_argument('--checkpoint',required=True); p.add_argument('--output',required=True)
    args=p.parse_args(); root=args.root.resolve()
    request=json.loads((root/args.request).read_text(encoding='utf-8'))
    report=generate_full_page(request,checkpoint=args.checkpoint,root=root,output=root/args.output)
    print(json.dumps({k:report[k] for k in ('request_id','status','seconds','total_generated_tokens')},indent=2))


if __name__=='__main__': main()
