"""Project-authored fictional instruction curriculum, separate from human-reviewed HF data."""
import hashlib
import argparse
import itertools
import json
import random
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset
from tokenizers import Tokenizer

from src.data.dataset import encode_sft
from src.data.schema import validate_page_spec
from src.data.sources import sha256_file, write_manifest

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'data/processed/curriculum/v1'
PREFIXES = ('Studio', 'Kafe', 'Toko', 'Kursus', 'Bengkel', 'Galeri', 'Kebun', 'Rumah', 'Klinik', 'Pustaka', 'Dapur', 'Komunitas')
NAMES = ('Mentari', 'Nusantara', 'Pelangi', 'Cendana', 'Mutiara', 'Bintang', 'Senja', 'Purnama', 'Cahaya', 'Angkasa', 'Lestari', 'Bahagia', 'Harmoni', 'Melati', 'Kenanga', 'Sejahtera', 'Mandiri', 'Bersama', 'Utama', 'Indah', 'Ceria', 'Damai', 'Aman', 'Kreatif')
RECIPES = ('profile', 'features', 'article', 'pricing', 'testimonial', 'contact', 'accordion', 'tabs', 'filter', 'modal', 'features_contact', 'pricing_contact')
COLORS = ('#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4')
INTROS = ('Temukan layanan pilihan kami.', 'Kenali produk dan layanan kami.', 'Bersama membangun pengalaman terbaik.', 'Solusi sederhana untuk kebutuhan Anda.')
PAIRS = (('Desain', 'Konsultasi'), ('Produk', 'Layanan'), ('Pelatihan', 'Pendampingan'), ('Kualitas', 'Kenyamanan'))
OPENERS = ('Buat website', 'Rancang halaman', 'Tolong buat situs', 'Saya ingin halaman')
SYLLABLES = ('ca', 'ka', 'ra', 'wa', 'la', 'ma', 'na', 'sa', 'ta', 'da', 'pa', 'ba', 'ga', 'fa', 'ha', 'ja', 'ki', 'ri', 'mi', 'ni', 'si', 'ti', 'di', 'pi', 'bi', 'gi', 'lo', 'no', 'so', 'to', 'do', 'po', 'bo', 'go', 'cak', 'raw', 'ala', 'sun', 'light', 'flow', 'code', 'craft', 'tech', 'work', 'web', 'lab', 'star', 'wave', 'green', 'blue', 'smart', 'bright')
VERBS = ('membantu', 'mendampingi', 'mendukung', 'melayani')
AUDIENCES = ('usaha kecil', 'tim kreatif', 'komunitas lokal', 'pelanggan baru', 'pemilik bisnis', 'pelajar Indonesia', 'mitra usaha', 'keluarga modern')
PURPOSES = ('membangun identitas digital', 'menemukan solusi praktis', 'mengelola layanan secara mudah', 'memilih produk berkualitas', 'meningkatkan pengalaman pengguna', 'mengembangkan gagasan baru', 'merencanakan kegiatan bersama', 'belajar dengan nyaman')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def serialize_spec(spec, policy):
    normalized = json.loads(canonical(spec))
    if policy == 'sorted_keys':
        return canonical(spec)
    if policy != 'appearance_before_sections':
        raise ValueError('Unknown serialization policy')
    order = ('interactions', 'language', 'schema_version', 'style_mode', 'theme', 'sections', 'title')
    # Only top-level ordering changes; nested objects retain canonical order.
    return json.dumps({key: normalized[key] for key in order}, ensure_ascii=False, separators=(',', ':'))


def make_example(title, recipe, style, color, font, intro, pair, menu, wording):
    """Every requested fact is explicit; fixed defaults are disclosed in the contract."""
    sections = []
    def section(identifier, kind, props):
        sections.append({'id': identifier, 'type': kind, 'props': props})
    section('nav', 'navbar', {'brand': title, 'links': [{'label': 'Beranda', 'href': '#main'}]})
    if recipe == 'article':
        section('main', 'text_section', {'heading': 'Profil', 'text': intro})
    else:
        section('main', 'hero', {'heading': title, 'text': intro, 'layout': 'centered'})
    interactions = [{'type': 'menu_toggle', 'target_id': 'nav'}] if menu else []
    details = []
    if recipe in ('features', 'accordion', 'tabs', 'filter', 'features_contact'):
        section('features', 'feature_grid', {'heading': 'Layanan', 'items': [{'heading': label, 'text': 'Informasi ' + label.lower() + '.'} for label in pair]})
        details.append('Tambahkan dua kartu layanan: ' + ' dan '.join(pair) + '.')
        if recipe in ('accordion', 'tabs', 'filter'):
            interactions.append({'type': recipe, 'target_id': 'features'})
            details.append('Aktifkan interaksi ' + recipe + ' pada kartu layanan.')
    if recipe in ('pricing', 'pricing_contact'):
        section('pricing', 'pricing_table', {'heading': 'Paket', 'plans': [
            {'name': 'Dasar', 'price': 'Rp49.000', 'features': ['Layanan dasar']},
            {'name': 'Plus', 'price': 'Rp99.000', 'features': ['Layanan lengkap']}]})
        details.append('Tambahkan paket Dasar Rp49.000 dengan Layanan dasar dan Plus Rp99.000 dengan Layanan lengkap.')
    if recipe == 'testimonial':
        section('testimonials', 'testimonial', {'heading': 'Testimoni Contoh', 'items': [{'quote': 'Ini testimoni contoh.', 'author': 'Pengguna Demo'}]})
        details.append('Tambahkan testimoni fiktif berjudul Testimoni Contoh: Ini testimoni contoh. oleh Pengguna Demo.')
    if recipe in ('contact', 'features_contact', 'pricing_contact'):
        section('contact', 'contact_form', {'heading': 'Hubungi Kami', 'fields': [
            {'name': 'nama', 'label': 'Nama', 'type': 'text'},
            {'name': 'email', 'label': 'Email', 'type': 'email'},
            {'name': 'pesan', 'label': 'Pesan', 'type': 'textarea'}], 'submit_label': 'Kirim'})
        interactions.append({'type': 'form_validate', 'target_id': 'contact'})
        details.append('Tambahkan form Hubungi Kami, kolom Nama, Email dan Pesan, tombol Kirim, serta validasi form.')
    if recipe == 'modal':
        interactions.append({'type': 'modal', 'target_id': 'main'})
        details.append('Tambahkan modal informasi pada hero.')
    section('footer', 'footer', {'text': title})
    style_label = 'CSS biasa' if style == 'plain_css' else 'Tailwind'
    lead = f'{OPENERS[wording]} Indonesia bernama {title} menggunakan {style_label}.'
    appearance = f'Aksen {color}, latar putih, teks #111827 dan font {font}.'
    body = f'Tampilkan navbar Beranda, {"teks profil" if recipe == "article" else "hero centered dengan judul nama situs"}, dan footer nama situs. Teks utama: {intro}'
    behavior = 'Gunakan menu responsif.' if menu else 'Navbar statis.'
    prompt = ' '.join([lead, appearance, body, behavior] + details)
    spec = {'schema_version': '1.0', 'title': title, 'language': 'id', 'style_mode': style,
            'theme': {'primary': color, 'background': '#ffffff', 'text': '#111827', 'font': font},
            'sections': sections, 'interactions': interactions}
    return {'prompt': prompt, 'target_spec': spec, 'recipe': recipe,
            'annotation_status': 'programmatic_contract', 'human_reviewed': False,
            'group_id': digest({'title': title}), 'example_id': digest({'prompt': prompt, 'spec': spec}),
            'origin': 'project-authored fictional synthetic exercise; not a WebSight/Vulcan annotation'}


def prepare(revision='v1', serialization='sorted_keys'):
    if revision not in ('v1', 'v2', 'v3', 'v4'):
        raise ValueError('Unknown curriculum revision')
    directory = ROOT / 'data/processed/curriculum' / revision
    if directory.exists():
        raise ValueError('Curriculum revision exists; preserve it and use a new revision')
    if shutil.disk_usage(ROOT).free < 15 * 2**30 + 1024**3:
        raise OSError('Insufficient storage while preserving 15 GiB reserve')
    tokenizer = Tokenizer.from_file(str(ROOT / 'data/tokenizer/tokenizer.json'))
    titles = [' '.join(pair) for pair in itertools.product(PREFIXES, NAMES)]
    if revision in ('v3', 'v4'):
        lexical_rng = random.Random(271828)
        brands = set()
        while len(brands) < 2400:
            brand = ''.join(lexical_rng.choices(SYLLABLES, k=lexical_rng.choice((2, 3, 4)))).capitalize()
            # Failed runtime probe remains excluded; it is development evidence, never a heldout claim.
            if brand not in ('Cakrawala',) and len(brand) <= 18:
                brands.add(brand)
        titles = [PREFIXES[i % len(PREFIXES)] + ' ' + brand for i, brand in enumerate(sorted(brands))]
    random.Random(42).shuffle(titles)
    train_count = 1920 if revision in ('v3', 'v4') else 230
    val_end = 2160 if revision in ('v3', 'v4') else 259
    allocation = {title: 'train' if i < train_count else 'validation' if i < val_end else 'test' for i, title in enumerate(titles)}
    records = {split: [] for split in ('train', 'validation', 'test')}
    rng = random.Random(31415)
    seen = set()
    for title in titles:
        split = allocation[title]
        combinations = list(itertools.product(RECIPES, ('plain_css', 'tailwind'), range(2)))
        if revision in ('v3', 'v4'): combinations = rng.sample(combinations, 6)
        for recipe, style, variant in combinations:
            color, font = rng.choice(COLORS), rng.choice(('sans', 'serif', 'mono'))
            intro = rng.choice(INTROS)
            if revision in ('v3', 'v4') and rng.random() < .8:
                intro = f'Kami {rng.choice(VERBS)} {rng.choice(AUDIENCES)} untuk {rng.choice(PURPOSES)}.'
            row = make_example(title, recipe, style, color, font,
                               intro, rng.choice(PAIRS), bool(variant), rng.randrange(len(OPENERS)))
            row['split'] = split
            if row['example_id'] in seen:
                raise ValueError('Duplicate synthetic pair')
            seen.add(row['example_id'])
            records[split].append(row)
    copy_coverage = None
    if revision == 'v4':
        # Vocabulary comes from pretraining train only, not heldout labels/names.
        eligible = {i for i in range(tokenizer.get_vocab_size())
                    if (piece := tokenizer.decode([i]).strip()).isascii() and piece.isalpha() and len(piece) <= 6}
        covered = {i for row in records['train'] for i in tokenizer.encode(row['target_spec']['title']).ids}
        initial_missing = sorted(eligible - covered)
        drill_count, unrepresented = 0, []
        for identifier in initial_missing:
            if identifier in covered: continue
            word = tokenizer.decode([identifier]).strip()
            candidates = ('Studio ' + word, 'Studio Aa' + word + 'aa', 'Studio ' + word + 'aa',
                          'Studio Aa' + word, 'Studio ' + word + ' Bb')
            title = next((t for t in candidates if identifier in tokenizer.encode(t).ids
                          and t not in allocation), None)
            if title is None:
                unrepresented.append(identifier)
                continue
            allocation[title] = 'train'
            covered.update(tokenizer.encode(title).ids)
            for style in ('plain_css', 'tailwind'):
                row = make_example(title, 'profile', style, rng.choice(COLORS), rng.choice(('sans', 'serif', 'mono')),
                                   rng.choice(INTROS), PAIRS[0], False, rng.randrange(len(OPENERS)))
                row['split'] = 'train'
                row['copy_drill'] = True
                if row['example_id'] in seen: raise ValueError('Duplicate copy drill')
                seen.add(row['example_id']); records['train'].append(row); drill_count += 1
        # Title membership hashes, including all base partitions, stay globally disjoint.
        groups = [{row['group_id'] for row in records[s]} for s in ('train', 'validation', 'test')]
        if any(groups[i] & groups[j] for i in range(3) for j in range(i+1, 3)):
            raise ValueError('Copy drills overlap heldout title family')
        copy_coverage = {'source': 'train-only BPE vocabulary, alphabetic ASCII pieces of length <=6',
                         'eligible_token_ids': sorted(eligible), 'initial_uncovered_count': len(initial_missing),
                         'covered_count': len(eligible & covered), 'unrepresented_token_ids': unrepresented,
                         'added_train_rows': drill_count, 'not_human_reviewed': True}
    directory.mkdir(parents=True)
    files, counts, coverage, lengths = {}, {}, {}, []
    for split, rows in records.items():
        path = directory / f'{split}.jsonl'
        inputs = np.lib.format.open_memmap(directory / f'{split}.inputs.npy', mode='w+', dtype=np.int32, shape=(len(rows), 1024))
        labels = np.lib.format.open_memmap(directory / f'{split}.labels.npy', mode='w+', dtype=np.int32, shape=(len(rows), 1024))
        with path.open('x', encoding='utf-8') as handle:
            for index, row in enumerate(rows):
                errors = validate_page_spec(row['target_spec'])
                if errors: raise ValueError(errors)
                x, y = encode_sft(row['prompt'], serialize_spec(row['target_spec'], serialization), tokenizer, 1024)
                inputs[index], labels[index] = x, y
                lengths.append(sum(value != tokenizer.token_to_id('<pad>') for value in x))
                handle.write(json.dumps(row, ensure_ascii=False) + '\n')
        inputs.flush(); labels.flush(); del inputs, labels
        files[split] = {kind: {'path': str((directory / f'{split}.{suffix}').relative_to(ROOT)),
                              'sha256': sha256_file(directory / f'{split}.{suffix}')}
                       for kind, suffix in [('rows', 'jsonl'), ('inputs', 'inputs.npy'), ('labels', 'labels.npy')]}
        counts[split] = {'rows': len(rows), 'families': len({r['group_id'] for r in rows})}
        coverage[split] = {'sections': dict(Counter(s['type'] for r in rows for s in r['target_spec']['sections'])),
                           'interactions': dict(Counter(i['type'] for r in rows for i in r['target_spec']['interactions']))}
    # A locked 48-row final suite is selected now, before any curriculum training.
    final = []
    for recipe, style in itertools.product(RECIPES, ('plain_css', 'tailwind')):
        candidates = [r for r in records['test'] if r['recipe'] == recipe and r['target_spec']['style_mode'] == style]
        final.extend((candidates[0], candidates[-1]))
    final_path = directory / 'final_prompts.jsonl'
    final_path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in final), encoding='utf-8')
    manifest = {'revision': 'synthetic-contract-' + revision, 'serialization': serialization, 'status': 'complete', 'seed': 42, 'counts': counts,
        'files': files, 'coverage': coverage, 'max_sequence_tokens': max(lengths),
        'tokenizer_sha256': sha256_file(ROOT / 'data/tokenizer/tokenizer.json'),
        'allocation': {digest({'title': title}): split for title, split in allocation.items()},
        'split_policy': 'disjoint fictional title families; shared component templates across partitions',
        'human_reviewed_rows': 0, 'review_kind': 'programmatic_contract',
        'final_suite': {'path': str(final_path.relative_to(ROOT)), 'sha256': sha256_file(final_path), 'count': len(final)},
        'acceptance': {'schema_valid_rate': 0.95, 'exact_contract_rate': 0.90, 'repair_allowed': False},
        'limits': ['Synthetic template transfer only, not arbitrary real-world website generalization',
                   'Not human-reviewed production SFT; existing 12 reviewed rows and all HF manifests remain unchanged',
                   'No factual businesses or real testimonials; no external data license attribution claimed']}
    if revision == 'v4':
        manifest['copy_vocabulary_coverage'] = copy_coverage
        previous = json.loads((ROOT / 'data/processed/curriculum/v3/manifest.json').read_text(encoding='utf-8'))
        if (any(previous['files'][s]['rows']['sha256'] != manifest['files'][s]['rows']['sha256'] for s in ('validation', 'test'))
                or previous['final_suite']['sha256'] != manifest['final_suite']['sha256']):
            raise ValueError('Copy-vocabulary augmentation must preserve untouched heldout partitions')
        manifest['controlled_change'] = 'add train-only subword copy drills; preserve all base rows and heldout/final files'
    if revision == 'v2':
        previous = json.loads((DIRECTORY / 'manifest.json').read_text(encoding='utf-8'))
        if (previous['allocation'] != manifest['allocation'] or previous['final_suite']['sha256'] != manifest['final_suite']['sha256']
                or any(previous['files'][s]['rows']['sha256'] != manifest['files'][s]['rows']['sha256'] for s in records)):
            raise ValueError('Serialization experiment must preserve all prompts/targets/family partitions')
        manifest['controlled_change'] = 'top-level style_mode/theme precede sections; no prompt/target semantics, split, nested key order, or budget changes'
    write_manifest(directory / 'manifest.json', manifest)
    write_manifest(ROOT / f'reports/data/SYNTHETIC_CURRICULUM_{revision.upper()}.json', manifest)
    print(json.dumps({k: v for k, v in manifest.items() if k not in ('allocation', 'files')}, indent=2))


def verify_manifest(directory=DIRECTORY):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['review_kind'] != 'programmatic_contract' or manifest['human_reviewed_rows'] != 0:
        raise ValueError('Synthetic data must never claim human approval')
    if sha256_file(ROOT / 'data/tokenizer/tokenizer.json') != manifest['tokenizer_sha256']:
        raise ValueError('Tokenizer changed')
    for split in ('train', 'validation', 'test'):
        for record in manifest['files'][split].values():
            if sha256_file(ROOT / record['path']) != record['sha256']:
                raise ValueError('Synthetic file checksum changed')
    return manifest


class CurriculumDataset(Dataset):
    """Masked synthetic labels, explicitly distinct from reviewed PageSpecDataset."""
    def __init__(self, manifest, split):
        self.inputs = np.load(ROOT / manifest['files'][split]['inputs']['path'], mmap_mode='r')
        self.labels = np.load(ROOT / manifest['files'][split]['labels']['path'], mmap_mode='r')
        if self.inputs.shape != self.labels.shape or self.inputs.shape != (manifest['counts'][split]['rows'], 1024):
            raise ValueError('Invalid curriculum cache shape')

    def __len__(self):
        return len(self.inputs)

    def __getitem__(self, index):
        return {'input_ids': torch.tensor(self.inputs[index], dtype=torch.long),
                'labels': torch.tensor(self.labels[index], dtype=torch.long)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', choices=('v1', 'v2', 'v3', 'v4'), default='v1')
    parser.add_argument('--serialization', choices=('sorted_keys', 'appearance_before_sections'), default='sorted_keys')
    args = parser.parse_args()
    prepare(args.revision, args.serialization)
