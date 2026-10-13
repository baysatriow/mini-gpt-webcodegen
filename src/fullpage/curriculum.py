"""Disclosed synthetic complete-page tasks; family partitions are immutable."""
import hashlib
import json
import random
import shutil
from collections import Counter
from pathlib import Path
from tokenizers import Tokenizer

from src.data.sources import sha256_file
from .assets import load_asset_catalog, create_project_catalog
from .contracts import validate_request, validate_plan_wire, validate_section, validate_composed_page
from .serialization import canonical, encode_plan, serialize_task, check_budget, OUTPUT_BUDGETS
from .prompts import plan_prompt, section_prompt, retry_prompt

STORAGE_RESERVE = 15 * 2**30
SECTORS = [
    ('Studio', 'desain dan komunikasi', ('Desain identitas', 'Konten usaha', 'Halaman informasi')),
    ('Kafe', 'minuman dan ruang berkumpul', ('Minuman pilihan', 'Ruang pertemuan', 'Paket acara')),
    ('Kursus', 'pendampingan belajar', ('Kelas dasar', 'Kelas lanjutan', 'Pendampingan')),
    ('Toko', 'produk kebutuhan harian', ('Pilihan produk', 'Konsultasi produk', 'Pemesanan')),
]
SYLLABLES = ('nu', 'sa', 'ra', 'ta', 'mi', 'ka', 'la', 'di', 'wi', 'na', 'pu', 'ri', 'ma', 'ya', 'ti', 'ba')


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2); handle.write('\n')


def make_page(index, split, style, name):
    genre = 'landing_page' if index % 2 == 0 else 'company_profile'
    sector, topic, service_names = SECTORS[(index // 2) % len(SECTORS)]
    facts = [{'id': 'name', 'kind': 'name', 'value': name},
             {'id': 'about', 'kind': 'description', 'value': f'{name} adalah usaha demo fiktif di bidang {topic}. Kami membantu pelanggan memahami pilihan layanan, menentukan kebutuhan dan memulai konsultasi dengan informasi yang jelas.'},
             {'id': 'values', 'kind': 'value', 'value': 'Kami mengutamakan komunikasi terbuka, informasi yang mudah dipahami dan proses yang disepakati bersama.'}]
    for j, title in enumerate(service_names):
        facts.append({'id': 'srv' + str(j), 'kind': 'service', 'value': {'title': title, 'text': f'{title} disusun sesuai kebutuhan pelanggan. Diskusikan tujuan, pilihan dan lingkup layanan sebelum memulai agar prosesnya dapat dipahami.'}})
    facts += [{'id': 'step' + str(j), 'kind': 'process', 'value': {'title': title, 'text': body}} for j, (title, body) in enumerate([
        ('Sampaikan kebutuhan', 'Ceritakan kebutuhan melalui formulir konsultasi. Informasi awal membantu kami memahami tujuan Anda.'),
        ('Bahas pilihan', 'Kami membahas pilihan layanan dan materi yang tersedia. Lingkup pekerjaan ditentukan bersama sebelum memulai.'),
        ('Mulai bersama', 'Lanjutkan proses sesuai kesepakatan. Penyesuaian dibahas melalui komunikasi yang jelas selama pengerjaan.')])]
    if genre == 'landing_page':
        facts += [{'id': 'faq' + str(j), 'kind': 'faq', 'value': {'title': q, 'text': a}} for j, (q, a) in enumerate([
            ('Bagaimana cara memulai?', 'Isi formulir konsultasi untuk menyampaikan kebutuhan. Kami membahas informasi dan pilihan layanan sebelum Anda mengambil keputusan.'),
            ('Apakah layanan dapat disesuaikan?', 'Kebutuhan dan materi dibahas terlebih dahulu. Pilihan penyesuaian mengikuti lingkup yang disepakati bersama.'),
            ('Apakah formulir ini mengirim pesan?', 'Ini halaman demo fiktif. Formulir memvalidasi isian secara lokal dan belum mengirim pesan ke layanan eksternal.')])]
    else:
        facts += [{'id': 'project' + str(j), 'kind': 'project', 'value': {'title': title, 'text': body}} for j, (title, body) in enumerate([
            ('Profil usaha demo', 'Ilustrasi fiktif untuk menjelaskan identitas, layanan dan alur kontak sebuah usaha.'),
            ('Informasi layanan demo', 'Ilustrasi fiktif yang membantu pembaca memahami pilihan layanan. Bukan klaim proyek klien nyata.')])]
    request = {'request_id': f'page{index:04d}-{style}', 'prompt': f'Buat {genre} lengkap untuk {name}. Gunakan aksen #2563eb dan font sans. Ini contoh fiktif, gunakan menu responsif dan kontak lokal.',
               'genre': genre, 'style_mode': style, 'business_facts': facts,
               'asset_ids': ['studio-shapes' if genre == 'landing_page' else 'company-shapes'], 'fictitious': True}
    fact_map = {f['id']: f for f in facts}
    roles = ['navigation', 'hero', 'about', 'services', 'benefits' if genre == 'landing_page' else 'values', 'process', 'faq' if genre == 'landing_page' else 'portfolio', 'contact', 'footer']
    # Combinations withheld for development/final, while component vocabulary is shared.
    if split == 'validation': roles[3], roles[4] = roles[4], roles[3]
    if split == 'test': roles[5], roles[6] = roles[6], roles[5]
    descriptors, sections = [], []
    for role in roles:
        identifier = {'navigation': 'nav', 'hero': 'main'}.get(role, role)
        kind = {'navigation': 'navbar', 'hero': 'hero', 'about': 'text_section', 'services': 'feature_grid',
                'benefits': 'feature_grid', 'values': 'text_section', 'process': 'feature_grid', 'faq': 'feature_grid',
                'portfolio': 'feature_grid', 'contact': 'contact_form', 'footer': 'footer'}[role]
        variant = {'navbar': 'inline', 'hero': 'split' if index % 4 < 2 else 'centered', 'text_section': 'prose',
                   'feature_grid': 'numbered' if role == 'process' else 'cards', 'contact_form': 'panel', 'footer': 'columns'}[kind]
        refs = {'navigation': ['name'], 'hero': ['name'], 'about': ['about'], 'services': ['srv0', 'srv1', 'srv2'],
                'benefits': ['values'], 'values': ['values'], 'process': ['step0', 'step1', 'step2'],
                'faq': ['faq0', 'faq1', 'faq2'], 'portfolio': ['project0', 'project1'], 'contact': [], 'footer': ['name']}[role]
        asset_ids = request['asset_ids'] if role == 'hero' else []
        descriptor = {'id': identifier, 'type': kind, 'role': role, 'variant': variant, 'fact_ids': refs, 'asset_ids': asset_ids}
        descriptors.append(descriptor)
        link = {'label': 'Diskusikan kebutuhan', 'href': '#contact'}
        if role == 'navigation': props = {'brand': name, 'links': [{'label': 'Tentang', 'href': '#about'}, {'label': 'Layanan', 'href': '#services'}, {'label': 'Kontak', 'href': '#contact'}]}
        elif role == 'hero': props = {'heading': name, 'text': f'Kenali layanan {topic} dan diskusikan kebutuhan Anda. Demo fiktif.', 'layout': variant, 'button': link, 'media': {'asset_id': asset_ids[0], 'alt': 'Ilustrasi usaha demo fiktif'}}
        elif role == 'about': props = {'heading': 'Tentang ' + name, 'text': fact_map['about']['value']}
        elif role == 'values': props = {'heading': 'Visi dan nilai', 'text': fact_map['values']['value']}
        elif role == 'benefits': props = {'heading': 'Mengapa memilih kami', 'items': [{'heading': 'Komunikasi terbuka', 'text': fact_map['values']['value']}, {'heading': 'Kebutuhan yang jelas', 'text': 'Bahas pilihan dan tujuan sebelum memulai.'}]}
        elif role in ('services', 'process', 'faq', 'portfolio'):
            heading = {'services': 'Layanan utama', 'process': 'Cara memulai', 'faq': 'Pertanyaan umum', 'portfolio': 'Ilustrasi proyek fiktif'}[role]
            props = {'heading': heading, 'items': [{'heading': fact_map[r]['value']['title'], 'text': fact_map[r]['value']['text']} for r in refs]}
        elif role == 'contact': props = {'heading': 'Diskusikan kebutuhan Anda', 'fields': [{'name': 'name', 'label': 'Nama', 'type': 'text'}, {'name': 'email', 'label': 'Email', 'type': 'email'}, {'name': 'message', 'label': 'Pesan', 'type': 'textarea'}], 'submit_label': 'Kirim'}
        else: props = {'text': name, 'links': [{'label': 'Tentang', 'href': '#about'}, {'label': 'Kontak', 'href': '#contact'}]}
        sections.append({**{k: descriptor[k] for k in ('id', 'type', 'role', 'variant')}, 'props': props})
    plan = {'schema_version': '1.0', 'title': name, 'genre': genre, 'language': 'id', 'style_mode': style,
            'theme': {'primary': '#2563eb', 'background': '#ffffff', 'text': '#111827', 'font': 'sans'}, 'sections': descriptors}
    interactions = [{'type': 'menu_toggle', 'target_id': 'nav'}, {'type': 'form_validate', 'target_id': 'contact'}]
    if genre == 'landing_page': interactions.append({'type': 'accordion', 'target_id': 'faq'})
    page = {'schema_version': '2.0', 'genre': genre, **{k: plan[k] for k in ('title', 'language', 'style_mode', 'theme')},
            'sections': sections, 'interactions': interactions, 'fictitious': True}
    return request, plan, sections, page


def build_curriculum(root, output, *, seed=424242):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Curriculum directory exists')
    if shutil.disk_usage(root).free < STORAGE_RESERVE + 96 * 2**20: raise OSError('Insufficient reserve for curriculum')
    catalog = load_asset_catalog(root) if (root / 'assets/fullpage/catalog.json').exists() else create_project_catalog(root)
    tokenizer = Tokenizer.from_file(str(root / 'data/tokenizer/tokenizer.json'))
    rng = random.Random(seed); names = set()
    while len(names) < 320:
        names.add(''.join(rng.choices(SYLLABLES, k=4)).capitalize())
    names = sorted(names); rng.shuffle(names)
    output.mkdir(parents=True)
    handles = {s: (output / (s + '.jsonl')).open('x', encoding='utf-8', newline='\n') for s in ('train', 'validation', 'test')}
    requests_handles = {s: (output / (s + '.requests.jsonl')).open('x', encoding='utf-8', newline='\n') for s in handles}
    allocation, counts, profiles, pilot_ids = {}, Counter(), [], {'train': [], 'validation': []}
    long_train = 0
    try:
        for index, suffix in enumerate(names):
            split = 'train' if index < 240 else ('validation' if index < 280 else 'test')
            family = f'family{index:04d}'; allocation[family] = split
            if split in pilot_ids and len(pilot_ids[split]) < (40 if split == 'train' else 10): pilot_ids[split].append(family)
            name = SECTORS[(index // 2) % 4][0] + ' ' + suffix
            for style in ('plain_css', 'tailwind'):
                request, plan, sections, page = make_page(index, split, style, name)
                errors = validate_request(request, catalog) + validate_plan_wire(encode_plan(plan), request, catalog) + validate_composed_page(page)
                if errors: raise ValueError(errors)
                tasks = [('page_plan', plan_prompt(request), plan)]
                for descriptor, section in zip(plan['sections'], sections):
                    errors = validate_section(section, descriptor, request, catalog)
                    if errors: raise ValueError(errors)
                    tasks.append(('section_content', section_prompt(request, plan, descriptor), section))
                request_record = {'family_id': family, 'split': split, 'request': request}
                requests_handles[split].write(canonical(request_record) + '\n')
                for number, (task, prompt, target) in enumerate(tasks):
                    budget = check_budget(tokenizer, prompt, OUTPUT_BUDGETS[task])
                    target_text = serialize_task(task, target)
                    target_ids = tokenizer.encode(target_text).ids
                    if len(target_ids) + 1 > OUTPUT_BUDGETS[task]: raise ValueError('Target exceeds task output budget')
                    total = budget['prefix_tokens'] + len(target_ids) + 1
                    row = {'example_id': request['request_id'] + '-' + str(number), 'family_id': family, 'split': split,
                           'task': task, 'prompt': prompt, 'target': target_text, 'length': total - 1,
                           'human_reviewed': False, 'origin': 'project-authored synthetic fullpage curriculum',
                           'genre': request['genre'], 'style_mode': style, 'retry': False}
                    handles[split].write(canonical(row) + '\n'); counts[split] += 1
                    if split == 'train' and total > 1024: long_train += 1
                    profiles.append((split, task, budget['prefix_tokens'], len(target_ids) + 1, total))
                    if split != 'test' and number % 5 == 0:
                        retried = {**row, 'example_id': row['example_id'] + '-retry', 'retry': True,
                                   'prompt': retry_prompt(prompt, 'Use exact request identity and all required fields.')}
                        rb = check_budget(tokenizer, retried['prompt'], OUTPUT_BUDGETS[task])
                        retried['length'] = rb['prefix_tokens'] + len(target_ids)
                        handles[split].write(canonical(retried) + '\n'); counts[split] += 1
    finally:
        for handle in list(handles.values()) + list(requests_handles.values()): handle.close()
    if long_train < 32: raise ValueError('Insufficient natural supervised positions above 1024')
    files = {p.name: {'sha256': sha256_file(p), 'bytes': p.stat().st_size} for p in output.glob('*.jsonl')}
    manifest = {'version': 'fullpage-v1', 'origin': 'synthetic project-owned', 'human_reviewed': False, 'seed': seed,
                'family_counts': {'train': 240, 'validation': 40, 'test': 40}, 'task_counts': dict(counts), 'allocation': allocation,
                'pilot_family_ids': pilot_ids, 'files': files, 'tokenizer_sha256': sha256_file(root / 'data/tokenizer/tokenizer.json'),
                'schema_sha256': {p.name: sha256_file(p) for p in (root / 'configs/fullpage').glob('*.schema.json')},
                'serialization': 'canonical_nested_keys_plan_six_tuple_v1', 'block_size': 2048,
                'output_budgets': OUTPUT_BUDGETS, 'long_train_rows': long_train,
                'max_prefix': {task: max(p[2] for p in profiles if p[1] == task) for task in OUTPUT_BUDGETS},
                'max_target_with_eos': {task: max(p[3] for p in profiles if p[1] == task) for task in OUTPUT_BUDGETS},
                'max_total_tokens': max(p[4] for p in profiles), 'bytes': sum(p['bytes'] for p in files.values()),
                'final_status': 'frozen_unopened_for_model_selection', 'final_pages': 80}
    write_json(output / 'manifest.json', manifest)
    return manifest
