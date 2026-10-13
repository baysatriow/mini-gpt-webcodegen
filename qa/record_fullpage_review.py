"""Record actual named human ratings; blank rows never count as approval."""
import argparse
import csv
import json
import statistics
from pathlib import Path
from src.fullpage.curriculum import write_json
from src.data.sources import sha256_file


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--review',required=True); p.add_argument('--report',required=True)
    args=p.parse_args(); root=args.root.resolve(); path=root/args.review
    benchmark=json.loads((root/'data/evaluation/fullpage/manifest.json').read_text(encoding='utf-8'))
    expected={i for ids in benchmark['review_ids'].values() for i in ids}
    rows=list(csv.DictReader(path.open(encoding='utf-8',newline='')))
    if len(rows)!=12 or {r['request_id'] for r in rows}!=expected: raise ValueError('Review sample IDs differ from frozen benchmark')
    dimensions=benchmark['ratings']; complete=all(r['reviewer'].strip() and all(r[d].strip() for d in dimensions) and r['viewport390'].strip() and r['viewport1440'].strip() for r in rows)
    result={'status':'review_pending','review_csv_sha256':sha256_file(path),'benchmark_manifest_sha256':sha256_file(root/'data/evaluation/fullpage/manifest.json'),'reviewers':sorted({r['reviewer'].strip() for r in rows if r['reviewer'].strip()}),'human_review_passed':False,'browser_review_passed':False,'sample_count':12}
    if complete:
        scores={d:[int(r[d]) for r in rows] for d in dimensions}
        if any(not 1<=s<=5 for v in scores.values() for s in v): raise ValueError('Ratings must be1..5')
        if any(r[k] not in ('pass','fail') for r in rows for k in ('viewport390','viewport1440')): raise ValueError('Browser entries must be pass/fail based on actual inspection')
        means={d:statistics.mean(v) for d,v in scores.items()}
        human=all(v>=4 for v in means.values()) and all(s>=3 for v in scores.values() for s in v)
        browser=all(r[k]=='pass' for r in rows for k in ('viewport390','viewport1440'))
        result.update(status='review_passed' if human and browser else 'review_failed',dimension_means=means,human_review_passed=human,browser_review_passed=browser)
    write_json(root/args.report,result); print(json.dumps(result,indent=2))


if __name__=='__main__': main()
