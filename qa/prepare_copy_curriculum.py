"""Augment train-only rare lexical pieces in varied names and full PageSpec contexts."""
import argparse
from collections import Counter
import copy
import itertools
import json
import random
import shutil
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer

from src.data.curriculum import ROOT, PREFIXES, RECIPES, COLORS, INTROS, PAIRS, OPENERS, SYLLABLES
from src.data.curriculum import digest, make_example, serialize_spec, verify_manifest
from src.data.dataset import encode_sft
from src.data.normalize import read_jsonl
from src.data.schema import validate_page_spec
from src.data.sources import sha256_file, write_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/processed/curriculum/v5')
    parser.add_argument('--destination', type=Path, default=ROOT / 'data/processed/curriculum/v6')
    args = parser.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    destination.relative_to(ROOT / 'data/processed/curriculum')
    if destination.exists(): raise ValueError('Preserve previous dataset revisions')
    if shutil.disk_usage(ROOT).free < 17 * 2**30: raise ValueError('Need 15GiB reserve plus 2GiB for data/training')
    previous = verify_manifest(source)
    if previous['revision'] != 'synthetic-contract-v5': raise ValueError('Expected frozen v5 source')
    tokenizer = Tokenizer.from_file(str(ROOT / 'data/tokenizer/tokenizer.json'))
    records = list(read_jsonl(source / 'train.jsonl'))
    title_counts = Counter(i for row in records for i in set(tokenizer.encode(row['target_spec']['title']).ids))
    # Eligibility and frequency are derived exclusively from train vocabulary and train names.
    rare = [i for i in range(tokenizer.get_vocab_size()) if 0 < title_counts[i] < 64
            and (piece := tokenizer.decode([i]).strip()).isascii() and piece.isalpha() and len(piece) <= 6]
    reserved = set(previous['allocation'])
    # Historical heldout titles are excluded by their existing membership hashes, without parsing targets.
    for path in sorted((ROOT / 'data/processed/curriculum').glob('v[1-5]/manifest.json')):
        reserved.update(json.loads(path.read_text(encoding='utf-8'))['allocation'])
    allocation = dict(previous['allocation'])
    seen = {row['example_id'] for row in records}
    rng = random.Random(424242)
    added = Counter(); skipped = []
    choices = list(itertools.product(RECIPES, ('plain_css', 'tailwind')))
    for identifier in rare:
        piece = tokenizer.decode([identifier]).strip()
        for variant in range(8):
            title = None
            for attempt in range(200):
                left = ''.join(rng.choices(SYLLABLES, k=rng.choice((1, 2))))
                right = ''.join(rng.choices(SYLLABLES, k=rng.choice((1, 2))))
                # Alternate ordinary syllables and neutral boundaries when BPE would merge a piece away.
                brand = (left + piece + right) if attempt < 100 else (left + 'aa' + piece + 'aa' + right)
                if len(brand) > 28: continue
                brand = brand.capitalize()
                candidate = rng.choice(PREFIXES) + ' ' + brand
                if identifier not in tokenizer.encode(candidate).ids: continue
                # Checking every prefix excludes a reused brand even if its prefix changes.
                memberships = {digest({'title': prefix + ' ' + brand}) for prefix in PREFIXES}
                if memberships & reserved: continue
                title = candidate; reserved.update(memberships)
                break
            if title is None:
                skipped.append({'token_id': identifier, 'variant': variant}); continue
            group_id = digest({'title': title}); allocation[group_id] = 'train'
            for recipe, style in rng.sample(choices, 2):
                row = make_example(title, recipe, style, rng.choice(COLORS), rng.choice(('sans', 'serif', 'mono')),
                    rng.choice(INTROS), rng.choice(PAIRS), bool(rng.getrandbits(1)), rng.randrange(len(OPENERS)))
                row.update(split='train', copy_drill=True, copy_piece_id=identifier, copy_context_variant=variant)
                if row['example_id'] in seen: raise ValueError('Duplicate augmented pair')
                seen.add(row['example_id']); records.append(row); added[identifier] += 1
    destination.mkdir(parents=True)
    n = len(records)
    inputs = np.lib.format.open_memmap(destination / 'train.inputs.npy', mode='w+', dtype=np.int32, shape=(n, 1024))
    labels = np.lib.format.open_memmap(destination / 'train.labels.npy', mode='w+', dtype=np.int32, shape=(n, 1024))
    coverage = {'sections': Counter(), 'interactions': Counter()}; max_tokens = 0; after = Counter()
    with (destination / 'train.jsonl').open('x', encoding='utf-8') as handle:
        for index, row in enumerate(records):
            if allocation[row['group_id']] != 'train': raise ValueError('Train family overlaps heldout membership')
            if row.get('human_reviewed') is not False: raise ValueError('Synthetic examples must remain disclosed')
            errors = validate_page_spec(row['target_spec'])
            if errors: raise ValueError(errors)
            x, y = encode_sft(row['prompt'], serialize_spec(row['target_spec'], previous['serialization']), tokenizer, 1024)
            inputs[index], labels[index] = x, y
            max_tokens = max(max_tokens, sum(i != tokenizer.token_to_id('<pad>') for i in x))
            coverage['sections'].update(s['type'] for s in row['target_spec']['sections'])
            coverage['interactions'].update(i['type'] for i in row['target_spec']['interactions'])
            after.update(set(tokenizer.encode(row['target_spec']['title']).ids))
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    inputs.flush(); labels.flush(); del inputs, labels
    manifest = copy.deepcopy(previous)
    manifest.update(revision='synthetic-contract-v6', seed=424242, allocation=allocation,
        max_sequence_tokens=max(max_tokens, previous['max_sequence_tokens']),
        controlled_change='train-only varied lexical copying contexts; ordinary CE; byte-identical validation/test/final',
        parent_manifest_sha256=sha256_file(source / 'manifest.json'))
    manifest['files']['train'] = {kind: {'path': str((destination / ('train.' + suffix)).relative_to(ROOT)),
        'sha256': sha256_file(destination / ('train.' + suffix))}
        for kind, suffix in [('rows', 'jsonl'), ('inputs', 'inputs.npy'), ('labels', 'labels.npy')]}
    manifest['counts']['train'] = {'rows': n, 'families': len({r['group_id'] for r in records})}
    manifest['coverage']['train'] = {key: dict(value) for key, value in coverage.items()}
    # Copy unopened heldout files verbatim. Hash equality is verified before publishing the manifest.
    for split in ('validation', 'test'):
        for kind, record in manifest['files'][split].items():
            original = ROOT / previous['files'][split][kind]['path']
            target = destination / original.name
            shutil.copy2(original, target)
            if sha256_file(target) != record['sha256']: raise ValueError('Heldout file changed')
            record['path'] = str(target.relative_to(ROOT))
    final = destination / 'final_prompts.jsonl'
    shutil.copy2(ROOT / previous['final_suite']['path'], final)
    if sha256_file(final) != previous['final_suite']['sha256']: raise ValueError('Locked final changed')
    manifest['final_suite']['path'] = str(final.relative_to(ROOT))
    manifest['lexical_copy_augmentation'] = {'eligible_definition': 'train name row frequency 1..63; train-only BPE ASCII alphabetic pieces length<=6',
        'source_train_rows': previous['counts']['train']['rows'], 'added_rows': n - previous['counts']['train']['rows'],
        'attempted_piece_ids': rare, 'skipped_variants': skipped,
        'rows_per_piece': [{'token_id': i, 'piece': tokenizer.decode([i]), 'before': title_counts[i], 'after': after[i],
            'added_targeted_rows': added[i]} for i in rare],
        'title_variants_per_piece': 8, 'recipe_style_pairs_per_title': 2,
        'no_development_or_final_labels_used': True, 'human_reviewed': False}
    # v4 coverage is historical provenance, not the exposure count for augmented v6.
    manifest['copy_vocabulary_coverage']['scope'] = 'Inherited v4 baseline; v6 counts are lexical_copy_augmentation'
    write_manifest(destination / 'manifest.json', manifest)
    verify_manifest(destination)
    write_manifest(ROOT / 'reports/data/SYNTHETIC_CURRICULUM_V6.json', manifest)
    print(json.dumps({'revision': manifest['revision'], 'counts': manifest['counts'], 'added_rows': n - previous['counts']['train']['rows'],
        'rare_piece_count': len(rare), 'skipped_variants': len(skipped), 'max_sequence_tokens': manifest['max_sequence_tokens'],
        'heldout_hashes_preserved': True, 'final_read': False, 'free_GiB': shutil.disk_usage(ROOT).free / 2**30}))


if __name__ == '__main__': main()
