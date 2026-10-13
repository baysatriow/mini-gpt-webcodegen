"""Record actual saved-output and controlled mutation diagnostics, without model runs."""
import argparse
import copy
import json
import tempfile
from pathlib import Path
from src.fullpage.assets import load_asset_catalog
from src.fullpage.compose import compose_page, fact_errors
from src.fullpage.contracts import validate_section
from src.fullpage.curriculum import write_json
from src.data.sources import sha256_file


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', required=True)
    p.add_argument('--expect', choices=['before', 'after'], required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root/'outputs/fullpage/TRAIN-017-development-best/page0257-plain_css/attempt-01'
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    request, plan, page = read(source/'request.json'), read(source/'plan.json'), read(source/'website/page_spec.json')
    catalog = load_asset_catalog(root)
    checks = []
    try:
        compose_page(plan, page['sections'], request, catalog)
        name_errors = []
    except ValueError as error:
        name_errors = [str(error)]
    checks.append({'case':'saved_truncated_hero_name', 'requested_name':request['business_facts'][0]['value'],
                   'hero_heading':next(s['props']['heading'] for s in page['sections'] if s['role']=='hero'),
                   'errors':name_errors, 'rejected':bool(name_errors)})
    for fictitious in (False, True):
        req = {**request, 'fictitious':fictitious}
        for role in ('services', 'portfolio'):
            section = copy.deepcopy(next(s for s in page['sections'] if s['role']==role))
            descriptor = next(s for s in plan['sections'] if s['role']==role)
            section['props']['items'].append({'heading':'Invented client or offer', 'text':'Unsupported structured fact'})
            errors = validate_section(section, descriptor, req, catalog) + fact_errors(section, descriptor, req)
            checks.append({'case':f'extra_{role}_fictitious_{fictitious}', 'errors':errors, 'rejected':bool(errors)})
        section = {'id':'testimonials','role':'testimonials','type':'testimonial','variant':'quote',
                   'props':{'items':[{'quote':'An invented endorsement','author':'Invented person'}]}}
        descriptor = {k:section[k] for k in ('id','role','type','variant')}
        descriptor.update(fact_ids=[], asset_ids=[])
        errors = validate_section(section, descriptor, req, catalog) + fact_errors(section, descriptor, req)
        checks.append({'case':f'unprovided_testimonial_fictitious_{fictitious}', 'errors':errors, 'rejected':bool(errors)})
    # This diagnostic uses a temporary claim path and fake metadata, never final requests/targets.
    from src.fullpage import evaluation
    if hasattr(evaluation, 'claim_final_evaluation'):
        with tempfile.TemporaryDirectory(prefix='fullpage-final-claim-') as directory:
            claim = Path(directory)/'consumption.json'
            identity = {'checkpoint_sha256':'diagnostic-only','output':'same-output','report':'same-report'}
            evaluation.claim_final_evaluation(claim, identity, resume=False)
            evaluation.claim_final_evaluation(claim, identity, resume=True)
            rejections = []
            for changed, resume in ((identity,False), ({**identity,'output':'another-output'},True)):
                try: evaluation.claim_final_evaluation(claim, changed, resume=resume)
                except ValueError: rejections.append(True)
                else: rejections.append(False)
            checks.append({'case':'single_final_identity_and_matching_resume','rejected':all(rejections),
                           'matching_resume_allowed':True,'actual_final_data_opened':False})
    else:
        checks.append({'case':'single_final_identity_and_matching_resume','rejected':False,
                       'evidence':'No persistent consumption claim function exists','actual_final_data_opened':False})
    expected = args.expect == 'after'
    result = {'phase':args.expect,'diagnostic_not_unit_suite':True,'final_data_opened':False,
              'input_sha256':{n:sha256_file(source/n) for n in ('request.json','plan.json','website/page_spec.json')},
              'source_sha256':{n:sha256_file(root/n) for n in ('src/fullpage/compose.py','src/fullpage/contracts.py','src/fullpage/evaluation.py','qa/evaluate_fullpage.py')},
              'checks':checks,'matches_expected':all(c['rejected']==expected for c in checks)}
    write_json(root/args.report,result)
    print(json.dumps(result,indent=2))
    if not result['matches_expected']: raise RuntimeError('Diagnostic differs from expected review state')


if __name__ == '__main__': main()
