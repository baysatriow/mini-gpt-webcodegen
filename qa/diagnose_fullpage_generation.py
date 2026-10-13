"""Real INIT generation diagnosis, with explicit untrained-output labeling."""
import argparse
import json
from pathlib import Path
from src.fullpage.curriculum import make_page, write_json
from src.fullpage.generation import FullPageGenerator


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--output',default='outputs/fullpage/init-raw-v1')
    args=p.parse_args(); root=args.root.resolve()
    request,_,_,_=make_page(0,'train','plain_css','Studio Diagnosis')
    generator=FullPageGenerator(root/'checkpoints/INIT-2048-001/initial.pt',root)
    report=generator.generate(request,root/args.output)
    write_json(root/'reports/fullpage/INIT_GENERATION_DIAGNOSIS.json',{'label':'real model output before fullpage training, not an accepted website',**report})
    print(json.dumps({'status':report['status'],'attempts':len(report['attempts']),'seconds':report['seconds']},indent=2))


if __name__=='__main__': main()
