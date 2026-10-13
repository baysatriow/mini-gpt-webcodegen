"""Inspect manual fixtures and token budgets; this is not model generation."""
import copy
import argparse
import json
from pathlib import Path
from tokenizers import Tokenizer
from src.fullpage.contracts import validate_request, validate_plan_wire, validate_section, validate_composed_page
from src.fullpage.serialization import encode_plan, serialize_task, check_budget, decode_plan
from src.fullpage.schema_definitions import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/analysis/AI-018_CONTRACT_INSPECTION.json')
    args = parser.parse_args()
    tokenizer = Tokenizer.from_file(str(ROOT / 'data/tokenizer/tokenizer.json'))
    examples = json.loads((ROOT / 'reports/analysis/AI-014_FULL_PAGE_SCOPE_VALID.json').read_text(encoding='utf-8'))
    catalog = {'assets': {}}
    rows = []
    for genre, original in examples['profiles'].items():
        spec = copy.deepcopy(original['spec'])
        request = {'request_id': 'manual-' + genre.replace('_', '-'), 'prompt': 'Buat halaman lengkap.',
                   'genre': genre, 'style_mode': spec['style_mode'], 'asset_ids': [], 'fictitious': True,
                   'business_facts': [{'id': 'name', 'kind': 'name', 'value': spec['title']},
                                      {'id': 'description', 'kind': 'description', 'value': 'Perusahaan demo fiktif.'},
                                      {'id': 'service', 'kind': 'service', 'value': {'title': 'Perencanaan', 'text': 'Layanan contoh.'}}]}
        roles = {'nav': 'navigation', 'main': 'hero', 'about': 'about', 'services': 'services', 'benefits': 'benefits',
                 'process': 'process', 'faq': 'faq', 'contact': 'contact', 'footer': 'footer', 'vision': 'values', 'projects': 'portfolio'}
        descriptors = []
        for section in spec['sections']:
            role = roles[section['id']]
            if role in ('services', 'benefits', 'process', 'faq', 'portfolio'):
                section['type'] = 'feature_grid'
                section['props'] = {'heading': section['props']['heading'], 'items': [{'heading': 'Informasi', 'text': section['props']['text']}]}
            section.update(role=role, variant={'navbar': 'inline', 'hero': 'split', 'feature_grid': 'cards', 'text_section': 'prose', 'contact_form': 'panel', 'footer': 'columns'}[section['type']])
            descriptors.append({**{k: section[k] for k in ('id', 'type', 'role', 'variant')}, 'fact_ids': ['name'], 'asset_ids': []})
        plan = {'schema_version': '1.0', 'genre': genre, **{k: spec[k] for k in ('title', 'language', 'style_mode', 'theme')}, 'sections': descriptors}
        wire = encode_plan(plan)
        spec.update(schema_version='2.0', genre=genre, fictitious=True)
        checks = {'request': validate_request(request, catalog), 'plan': validate_plan_wire(wire, request, catalog),
                  'page': validate_composed_page(spec), 'section': [e for s, d in zip(spec['sections'], descriptors) for e in validate_section(s, d, request, catalog)]}
        if any(checks.values()):
            raise ValueError(checks)
        if decode_plan(wire) != plan:
            raise ValueError('Codec did not preserve fields')
        tokens = len(tokenizer.encode(serialize_task('page_plan', plan)).ids) + 1
        bad = copy.deepcopy(wire); bad['sections'][1] = bad['sections'][1][:-1]
        if not validate_plan_wire(bad, request, catalog):
            raise ValueError('Malformed tuple accepted')
        for mutation in ('duplicate', 'unknown_fact', 'variant', 'required_role'):
            bad = copy.deepcopy(wire)
            if mutation == 'duplicate': bad['sections'][1][0] = bad['sections'][0][0]
            if mutation == 'unknown_fact': bad['sections'][1][4] = ['unknown']
            if mutation == 'variant': bad['sections'][0][3] = 'split'
            if mutation == 'required_role': bad['sections'] = bad['sections'][:2] + bad['sections'][3:]
            if not validate_plan_wire(bad, request, catalog): raise ValueError('Invalid plan accepted: ' + mutation)
        badpage = copy.deepcopy(spec); badpage['sections'][0]['props']['links'][0]['href'] = '#absent'
        if not validate_composed_page(badpage): raise ValueError('Broken anchor accepted')
        rows.append({'genre': genre, 'sections': len(descriptors), 'plan_tokens_with_eos': tokens, 'positive_valid': True, 'negative_rejections': 6})
        if tokens > 512: raise ValueError('Plan exceeds budget')
        longer = copy.deepcopy(wire)
        extra = copy.deepcopy(longer['sections'][2:5])
        for index, descriptor in enumerate(extra): descriptor[0] = 'extra' + str(index)
        longer['sections'][-1:-1] = extra
        errors = validate_plan_wire(longer, request, catalog)
        tokens12 = len(tokenizer.encode(serialize_task('page_plan', decode_plan(longer))).ids) + 1
        if errors or tokens12 > 512: raise ValueError({'12_section_plan': errors, 'tokens': tokens12})
        rows.append({'genre': genre, 'sections': 12, 'plan_tokens_with_eos': tokens12, 'positive_valid': True})
    for prefix, accepted in ((512, True), (513, False)):
        prompt = ' a' * (prefix - 3)
        if 3 + len(tokenizer.encode(prompt).ids) != prefix: raise ValueError('Tokenizer boundary fixture changed')
        try:
            check_budget(tokenizer, prompt, 1536)
            outcome = True
        except ValueError:
            outcome = False
        if outcome != accepted: raise ValueError('Incorrect prefix boundary result')
    report = {'scope': 'manual_fixture_schema_semantic_codec_budget_inspection', 'model_generation': False,
              'rows': rows, 'prefix_boundaries': {'512': 'accepted', '513': 'rejected'}, 'v1_schema_preserved': True}
    destination = args.output if args.output.is_absolute() else ROOT / args.output
    with destination.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(report, handle, indent=2); handle.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
