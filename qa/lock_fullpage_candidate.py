"""Lock a completed main best-CE checkpoint after the80-page development gate."""
import argparse
import json
from pathlib import Path
from src.fullpage.evaluation import lock_fullpage_candidate


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--development-report',required=True); p.add_argument('--checkpoint',required=True); p.add_argument('--output',required=True)
    args=p.parse_args(); root=args.root.resolve()
    candidate=lock_fullpage_candidate(root/args.development_report,root/args.checkpoint,root/args.output)
    print(json.dumps({k:candidate[k] for k in ('status','checkpoint_sha256','development_complete')},indent=2))


if __name__=='__main__': main()
