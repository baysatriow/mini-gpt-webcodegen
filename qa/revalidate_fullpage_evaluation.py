"""Revalidate saved accepted model bytes without regeneration, repair or final access."""
import argparse
import copy
import json
from pathlib import Path
from src.data.sources import sha256_file
from src.fullpage.assets import load_asset_catalog
from src.fullpage.compose import compose_page
from src.fullpage.curriculum import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    original_path = root/args.original
    original = read(original_path)
    if original['scope'] != 'development' or original['final_used']:
        raise ValueError('This correction is development-only')
    catalog = load_asset_catalog(root)
    results, groups, revoked, first = [], {}, [], 0
    for row in original['results']:
        source = sorted((Path(original['output'])/row['request_id']).glob('attempt-*/result.json'))[-1].parent
        result = read(source/'result.json')
        if result['metadata']['checkpoint_sha256'] != original['checkpoint_sha256'] or result['status'] != row['status']:
            raise ValueError('Historical source identity changed')
        request = read(source/'request.json')
        revised = {**row, 'historical_status':row['status'], 'revalidation_errors':[]}
        if row['status'] == 'accepted':
            plan, page = read(source/'plan.json'), read(source/'website/page_spec.json')
            try:
                composed = compose_page(plan, page['sections'], request, catalog)
                if composed != page: raise ValueError('Saved composed page differs')
            except ValueError as error:
                revised.update(status='revalidation_failed', revalidation_errors=[str(error)])
                revoked.append(row['request_id'])
            revised['raw_source_sha256'] = {n:sha256_file(source/n) for n in ('request.json','plan.json','result.json','website/page_spec.json')}
        revised['facts_valid'] = revised['status'] == 'accepted'
        revised['links_assets_valid'] = revised['status'] == 'accepted'
        revised['required_roles'] = revised['status'] == 'accepted'
        revised['first_attempt_success'] = revised['status']=='accepted' and result['first_attempt_success']
        first += revised['first_attempt_success']
        group = groups.setdefault(request['genre']+':'+request['style_mode'], {'total':0,'complete':0,'first_attempt':0})
        group['total'] += 1
        group['complete'] += revised['status']=='accepted'
        group['first_attempt'] += revised['first_attempt_success']
        results.append(revised)
    complete = sum(r['status']=='accepted' for r in results)
    report = copy.deepcopy(original)
    report.update(complete=complete, complete_rate=complete/original['total'], required_roles=complete,
                  required_roles_rate=complete/original['total'], first_attempt_complete=first, after_retry_complete=complete,
                  model_gate=complete/original['total']>=.95, accepted_facts_links_assets_valid=bool(complete),
                  results=results, groups=groups, validation_revision='review-v2',
                  historical_metrics={k:original[k] for k in ('complete','first_attempt_complete','model_gate','source_sha256')},
                  revalidation={'original_report':args.original,'original_report_sha256':sha256_file(original_path),
                                'revoked_request_ids':revoked,'generation_repeated':False,'raw_outputs_modified':False,
                                'final_opened':False,'structured_fact_policy':'Supplied referenced items only, including fictional demos',
                                'source_sha256':{p:sha256_file(root/p) for p in ('src/fullpage/compose.py','src/fullpage/contracts.py','qa/revalidate_fullpage_evaluation.py')}})
    if revoked: report['failures']['review_v2_fact_validation'] = len(revoked)
    write_json(root/args.report, report)
    print(json.dumps({'complete':complete,'total':report['total'],'revoked':revoked,'model_gate':report['model_gate'],
                      'generation_repeated':False,'final_opened':False},indent=2))


if __name__ == '__main__': main()
