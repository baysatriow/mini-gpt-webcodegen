"""Build a new full-page family split and freeze its final before training."""
import argparse
import json
from pathlib import Path
from src.fullpage.curriculum import build_curriculum, write_json
from src.fullpage.schema_definitions import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, default=Path('reports/data/FULLPAGE_CURRICULUM_V1.json'))
    args = parser.parse_args()
    report = build_curriculum(args.root, args.root / args.output)
    write_json(args.root / args.report, report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('allocation','files','pilot_family_ids','schema_sha256')},indent=2))


if __name__ == '__main__': main()
