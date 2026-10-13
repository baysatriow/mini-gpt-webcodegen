"""Check explicit supported prompt facts after generation; never modify model output."""
import re


def assess_prompt_contract(prompt, spec):
    match = re.search(r'bernama (.+?) menggunakan (CSS biasa|Tailwind)\.', prompt)
    if not match:
        return {'checked': False, 'errors': ['Prompt belum mengikuti format nama/style yang didukung'], 'requested': {}}
    requested = {'title': match.group(1).strip(), 'style_mode': 'plain_css' if match.group(2) == 'CSS biasa' else 'tailwind'}
    for expression, key in ((r'Aksen (#[0-9a-fA-F]{6})', 'primary'), (r'font (sans|serif|mono)', 'font'), (r'teks (#[0-9a-fA-F]{6})', 'text')):
        value = re.search(expression, prompt)
        if value: requested[key] = value.group(1)
    if 'latar putih' in prompt: requested['background'] = '#ffffff'
    intro = re.search(r'Teks utama:\s*(.+?)(?=\s+(?:Gunakan menu responsif|Navbar statis)\.)', prompt)
    if intro: requested['main_text'] = intro.group(1)
    errors = []
    for required in ('primary', 'font', 'text', 'background', 'main_text'):
        if required not in requested: errors.append(f'Prompt belum menyebut {required} dalam format yang didukung')
    for field in ('title', 'style_mode'):
        if spec[field] != requested[field]: errors.append(f'{field}: diminta {requested[field]!r}, model menghasilkan {spec[field]!r}')
    for field in ('primary', 'background', 'text', 'font'):
        if field in requested and spec['theme'][field].lower() != requested[field].lower():
            errors.append(f'theme.{field}: tidak sesuai prompt')
    if intro and not any(section['props'].get('text') == requested['main_text'] for section in spec['sections'] if section['type'] in ('hero', 'text_section')):
        errors.append('Teks utama tidak sesuai prompt')
    sections = {section['id']: section for section in spec['sections']}
    def require(identifier, kind, props):
        section = sections.get(identifier)
        if section is None or section['type'] != kind or section['props'] != props:
            errors.append(f'Section {identifier}: isi tidak sesuai kontrak prompt')
    title = requested['title']
    if spec['language'] != 'id': errors.append('Bahasa halaman harus Indonesia')
    expected_ids = {'nav', 'main', 'footer'}
    require('nav', 'navbar', {'brand': title, 'links': [{'label': 'Beranda', 'href': '#main'}]})
    require('footer', 'footer', {'text': title})
    if intro:
        if 'teks profil' in prompt:
            require('main', 'text_section', {'heading': 'Profil', 'text': requested['main_text']})
        elif 'hero centered dengan judul nama situs' in prompt:
            require('main', 'hero', {'heading': title, 'text': requested['main_text'], 'layout': 'centered'})
        else: errors.append('Format section utama belum didukung')
    pair = re.search(r'Tambahkan dua kartu layanan: (.+?) dan (.+?)\.', prompt)
    if pair:
        expected_ids.add('features')
        require('features', 'feature_grid', {'heading': 'Layanan', 'items': [
            {'heading': label, 'text': 'Informasi ' + label.lower() + '.'} for label in pair.groups()]})
    pricing = 'Tambahkan paket' in prompt
    if pricing:
        expected_ids.add('pricing')
        clause = 'Tambahkan paket Dasar Rp49.000 dengan Layanan dasar dan Plus Rp99.000 dengan Layanan lengkap.'
        if clause not in prompt: errors.append('Kontrak harga belum didukung')
        require('pricing', 'pricing_table', {'heading': 'Paket', 'plans': [
            {'name': 'Dasar', 'price': 'Rp49.000', 'features': ['Layanan dasar']},
            {'name': 'Plus', 'price': 'Rp99.000', 'features': ['Layanan lengkap']}]})
    if 'form Hubungi Kami' in prompt:
        expected_ids.add('contact')
        require('contact', 'contact_form', {'heading': 'Hubungi Kami', 'fields': [
            {'name': 'nama', 'label': 'Nama', 'type': 'text'},
            {'name': 'email', 'label': 'Email', 'type': 'email'},
            {'name': 'pesan', 'label': 'Pesan', 'type': 'textarea'}], 'submit_label': 'Kirim'})
    if 'testimoni fiktif' in prompt:
        expected_ids.add('testimonials')
        if 'Testimoni Contoh: Ini testimoni contoh. oleh Pengguna Demo.' not in prompt:
            errors.append('Kontrak testimonial belum didukung')
        require('testimonials', 'testimonial', {'heading': 'Testimoni Contoh', 'items': [
            {'quote': 'Ini testimoni contoh.', 'author': 'Pengguna Demo'}]})
    if set(sections) != expected_ids or len(sections) != len(spec['sections']):
        errors.append('ID section tambahan, duplikat atau hilang')
    order = [identifier for identifier in ('nav', 'main', 'features', 'pricing', 'testimonials', 'contact', 'footer') if identifier in expected_ids]
    if [section['id'] for section in spec['sections']] != order:
        errors.append('Urutan section tidak sesuai kontrak katalog')
    kinds = {section['type'] for section in spec['sections']}
    for phrase, kind in (('navbar Beranda', 'navbar'), ('hero centered', 'hero'), ('teks profil', 'text_section'), ('footer nama situs', 'footer'), ('dua kartu layanan', 'feature_grid'), ('Tambahkan paket', 'pricing_table'), ('testimoni fiktif', 'testimonial'), ('form Hubungi Kami', 'contact_form')):
        if phrase in prompt and kind not in kinds: errors.append(f'Section {kind} yang diminta tidak tersedia')
    requested_interactions = set()
    for phrase, kind in (('menu responsif', 'menu_toggle'), ('validasi form', 'form_validate'), ('interaksi accordion', 'accordion'), ('interaksi tabs', 'tabs'), ('interaksi filter', 'filter'), ('modal informasi', 'modal')):
        if phrase in prompt: requested_interactions.add(kind)
    if {i['type'] for i in spec['interactions']} != requested_interactions:
        errors.append('Katalog interaksi tidak sesuai permintaan yang eksplisit')
    targets = {'menu_toggle': 'nav', 'form_validate': 'contact', 'modal': 'main',
               'accordion': 'features', 'tabs': 'features', 'filter': 'features'}
    if (len(spec['interactions']) != len(requested_interactions) or
            any(i['target_id'] != targets[i['type']] for i in spec['interactions'])):
        errors.append('Target interaksi atau jumlah interaksi tidak sesuai kontrak')
    return {'checked': True, 'requested': requested, 'errors': errors}
