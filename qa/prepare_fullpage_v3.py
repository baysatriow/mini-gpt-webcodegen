"""Prepare targeted train-only examples for exact identity and supported facts."""
import argparse
import copy
import json
import random
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from tokenizers import Tokenizer

from src.data.normalize import read_jsonl
from src.data.sources import sha256_file
from src.fullpage.assets import load_asset_catalog
from src.fullpage.compose import compose_page
from src.fullpage.contracts import validate_plan_wire, validate_request
from src.fullpage.curriculum import make_page, write_json
from src.fullpage.dataset import encode_task_row
from src.fullpage.prompts import plan_prompt, section_prompt
from src.fullpage.serialization import (
    OUTPUT_BUDGETS,
    canonical,
    encode_plan,
    serialize_task,
    check_budget,
)

ROOT = Path(__file__).resolve().parents[1]
STORAGE_RESERVE = 15 * 2**30
BASE_STYLES = ('plain_css', 'tailwind')
ALIASES = ('Harmoni', 'Sejahtera')
COLORS = ('#2563eb', '#0f766e', '#7c3aed', '#b45309')
FONTS = ('sans', 'serif')
TARGET_ROLES = ('navigation', 'hero', 'services', 'footer')


def business_name(request):
    return next(f['value'] for f in request['business_facts'] if f['kind'] == 'name')


def prepare(source, output, report):
    source, output, report = Path(source).resolve(), Path(output).resolve(), Path(report).resolve()
    if not source.is_relative_to(ROOT) or not output.is_relative_to(ROOT) or not report.is_relative_to(ROOT):
        raise ValueError('Source, output, and report must stay inside the project root')
    if output.exists() or report.exists():
        raise ValueError('V3 destination or report already exists; preserve previous artifacts')
    if shutil.disk_usage(ROOT).free < STORAGE_RESERVE + 256 * 2**20:
        raise OSError('Need at least 15 GiB reserve plus 256 MiB for immutable dataset preparation')

    parent_manifest_path = source / 'manifest.json'
    parent = json.loads(parent_manifest_path.read_text(encoding='utf-8'))
    if parent.get('version') != 'fullpage-v2' or parent.get('human_reviewed') is not False:
        raise ValueError('V3 must extend the disclosed fullpage-v2 synthetic curriculum')
    for name, info in parent['files'].items():
        path = source / name
        if sha256_file(path) != info['sha256']:
            raise ValueError('V2 source file differs from its manifest: ' + name)

    train_requests = list(read_jsonl(source / 'train.requests.jsonl'))
    development_requests = list(read_jsonl(source / 'validation.requests.jsonl'))
    development_names = {business_name(row['request']) for row in development_requests}
    all_training_names = {business_name(row['request']) for row in train_requests}
    base_requests = [
        row for row in train_requests
        if row['request']['request_id'].endswith('-' + row['request']['style_mode'])
    ]
    base_keys = {(row['family_id'], row['request']['style_mode']) for row in base_requests}
    families = {row['family_id'] for row in base_requests}
    if len(families) != 240 or len(base_requests) != 480 or len(base_keys) != 480:
        raise ValueError('Expected one base request per each of 240 train families and two styles')
    if any(row['split'] != 'train' for row in base_requests):
        raise ValueError('A non-training request entered the targeted source set')

    source_task_ids = {row['example_id'] for row in read_jsonl(source / 'train.jsonl')}
    tokenizer = Tokenizer.from_file(str(ROOT / 'data/tokenizer/tokenizer.json'))
    catalog = load_asset_catalog(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.fullpage-v3-', dir=output.parent))
    added_task_ids = set()
    added_names = {}
    counts = Counter()
    prefix_max = {task: parent['max_prefix'][task] for task in OUTPUT_BUDGETS}
    target_max = {task: parent['max_target_with_eos'][task] for task in OUTPUT_BUDGETS}
    total_max = parent['max_total_tokens']
    requests_added = 0

    try:
        for name in parent['files']:
            shutil.copyfile(source / name, temp / name)

        with (temp / 'train.jsonl').open('a', encoding='utf-8', newline='\n') as tasks_file, \
                (temp / 'train.requests.jsonl').open('a', encoding='utf-8', newline='\n') as requests_file:
            for record in sorted(base_requests, key=lambda row: (row['family_id'], row['request']['style_mode'])):
                family = record['family_id']
                source_request = record['request']
                index = int(family.removeprefix('family'))
                style = source_request['style_mode']
                source_name = business_name(source_request)
                for variant, suffix in enumerate(ALIASES):
                    name = f'{source_name} {suffix}'
                    name_key = (family, suffix)
                    previous = added_names.setdefault(name_key, name)
                    if previous != name or name in all_training_names or name in development_names:
                        raise ValueError('Alias collides with a train or development business identity')
                    if len(name.split()) < 3:
                        raise ValueError('Targeted alias must contain at least three words')

                    request, plan, sections, _ = make_page(index, 'train', style, name)
                    request['request_id'] = f"{source_request['request_id']}-v3-{variant}"
                    accent = COLORS[(index + variant) % len(COLORS)]
                    font = FONTS[(index + variant) % len(FONTS)]
                    request['prompt'] = (
                        f"Buat {request['genre']} lengkap untuk {name}. Salin nama usaha, jenis halaman, "
                        f"dan gaya persis. Gunakan hanya informasi yang diberikan tanpa menambah layanan, "
                        f"FAQ, proyek, atau klaim. Gunakan aksen {accent} dan font {font}."
                    )
                    plan['theme'].update(primary=accent, font=font)

                    pairs = list(zip(plan['sections'][2:-1], sections[2:-1], strict=True))
                    random.Random(271828 + index * 2 + variant).shuffle(pairs)
                    plan['sections'] = plan['sections'][:2] + [d for d, _ in pairs] + plan['sections'][-1:]
                    sections = sections[:2] + [section for _, section in pairs] + sections[-1:]
                    page = compose_page(plan, sections, request, catalog)
                    if validate_request(request, catalog) or validate_plan_wire(encode_plan(plan), request, catalog):
                        raise ValueError('Generated v3 request or plan failed its strict contract')

                    request_record = {'family_id': family, 'split': 'train',
                                      'augmentation': 'targeted-identity-facts-v3', 'request': request}
                    requests_file.write(canonical(request_record) + '\n')
                    requests_added += 1
                    request_id = request['request_id']
                    descriptors = {descriptor['role']: descriptor for descriptor in plan['sections']}
                    sections_by_id = {section['id']: section for section in sections}
                    faq_or_portfolio = 'faq' if request['genre'] == 'landing_page' else 'portfolio'
                    roles = (*TARGET_ROLES[:3], faq_or_portfolio, TARGET_ROLES[3])
                    task_rows = [('page_plan', plan_prompt(request), plan)]
                    task_rows += [
                        ('section_content', section_prompt(request, plan, descriptors[role]),
                         sections_by_id[descriptors[role]['id']])
                        for role in roles
                    ]

                    for number, (task, prompt, target) in enumerate(task_rows):
                        budget = check_budget(tokenizer, prompt, OUTPUT_BUDGETS[task])
                        target_text = serialize_task(task, target)
                        target_tokens = len(tokenizer.encode(target_text).ids) + 1
                        if target_tokens > OUTPUT_BUDGETS[task]:
                            raise ValueError('Target exceeds the declared output budget')
                        row = {
                            'example_id': f'{request_id}-target-{number}',
                            'family_id': family,
                            'split': 'train',
                            'task': task,
                            'prompt': prompt,
                            'target': target_text,
                            'length': budget['prefix_tokens'] + target_tokens - 1,
                            'human_reviewed': False,
                            'origin': 'project-authored targeted synthetic identity and fact exercise',
                            'genre': request['genre'],
                            'style_mode': style,
                            'retry': False,
                            'augmentation': 'targeted-identity-facts-v3',
                        }
                        if row['example_id'] in source_task_ids or row['example_id'] in added_task_ids:
                            raise ValueError('Duplicate v3 task ID')
                        encode_task_row(row, tokenizer)
                        added_task_ids.add(row['example_id'])
                        tasks_file.write(canonical(row) + '\n')
                        counts[task] += 1
                        prefix_max[task] = max(prefix_max[task], budget['prefix_tokens'])
                        target_max[task] = max(target_max[task], target_tokens)
                        total_max = max(total_max, budget['prefix_tokens'] + target_tokens)

                    if not page or len(task_rows) != 6:
                        raise ValueError('Expected one plan task and five targeted section tasks per new page')

        manifest = copy.deepcopy(parent)
        manifest.update(version='fullpage-v3', seed=271828,
                        parent_manifest_sha256=sha256_file(parent_manifest_path))
        manifest['task_counts']['train'] += sum(counts.values())
        manifest['files'] = {
            path.name: {'sha256': sha256_file(path), 'bytes': path.stat().st_size}
            for path in sorted(temp.glob('*.jsonl'))
        }
        manifest['augmentation'] = {
            'train_pages_added': requests_added,
            'train_pages_total': len(train_requests) + requests_added,
            'train_families': len(families),
            'independent_families_added': 0,
            'new_name_aliases': len(added_names),
            'added_tasks': dict(counts),
            'development_names_in_train': False,
            'development_requests_unchanged': True,
            'final_parsed': False,
            'human_reviewed': False,
            'policy': 'Two three-word aliases per existing train family and style; final files copied and hashed but never parsed.',
            'source_sha256': sha256_file(Path(__file__)),
            'prompt_sha256': sha256_file(ROOT / 'src/fullpage/prompts.py'),
        }
        manifest['max_prefix'] = prefix_max
        manifest['max_target_with_eos'] = target_max
        manifest['max_total_tokens'] = total_max
        manifest['bytes'] = sum(info['bytes'] for info in manifest['files'].values())
        for name in ('validation.jsonl', 'validation.requests.jsonl', 'test.jsonl', 'test.requests.jsonl'):
            if manifest['files'][name]['sha256'] != parent['files'][name]['sha256']:
                raise ValueError('A held-out file changed during v3 preparation: ' + name)
        if len(added_task_ids) != 5760 or requests_added != 960 or len(added_names) != 480:
            raise ValueError('V3 targeted augmentation counts differ from the declared design')
        if counts != Counter({'page_plan': 960, 'section_content': 4800}):
            raise ValueError('V3 targeted task mix differs from the declared design')
        if len(development_requests) != 80 or development_names & set(added_names.values()):
            raise ValueError('Frozen development identities overlap with v3 aliases')
        if (temp / 'train.jsonl').read_bytes()[:(source / 'train.jsonl').stat().st_size] != (source / 'train.jsonl').read_bytes():
            raise ValueError('Original v2 train task bytes were not preserved as a prefix')

        write_json(temp / 'manifest.json', manifest)
        temp.rename(output)
        write_json(report, manifest)
        return {
            'version': manifest['version'],
            'source_manifest_sha256': manifest['parent_manifest_sha256'],
            'manifest_sha256': sha256_file(output / 'manifest.json'),
            'train_families': len(families),
            'new_pages': requests_added,
            'new_name_aliases': len(added_names),
            'new_tasks': dict(counts),
            'train_task_rows': manifest['task_counts']['train'],
            'max_total_tokens': total_max,
            'validation_unchanged': True,
            'final_parsed': False,
        }
    except BaseException:
        if temp.exists() and temp.is_relative_to(output.parent) and temp.name.startswith('.fullpage-v3-'):
            shutil.rmtree(temp)
        raise


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--source', default='data/processed/fullpage/v2')
    parser.add_argument('--output', default='data/processed/fullpage/v3')
    parser.add_argument('--report', default='reports/data/FULLPAGE_CURRICULUM_V3.json')
    args = parser.parse_args()
    root = args.root.resolve()
    ROOT = root
    result = prepare(root / args.source, root / args.output, root / args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
