"""Render the supported catalog without executing script or HTML from model strings."""
import html
import json
from pathlib import Path
import subprocess
import uuid

from src.data.schema import validate_page_spec
from qa.prepare_annotation_review import local_link_findings

ROOT = Path(__file__).resolve().parents[2]

CSS = '''
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--background);color:var(--text);font-family:var(--font);line-height:1.65}button,input,textarea{font:inherit}a{color:inherit;text-decoration:none}a:hover{text-decoration:underline}button{cursor:pointer}button,a,input,textarea,summary{outline-offset:5px}button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible,summary:focus-visible{outline:3px solid var(--primary)}.site-shell{max-width:1120px;margin:auto;padding:0 28px}.navbar{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:24px 0;border-bottom:2px solid var(--primary)}.brand{font-size:1.1rem;font-weight:700}.nav-links{display:flex;gap:24px;align-items:center}.mobile-toggle{display:none}section{padding:52px 0;scroll-margin-top:20px}h1{font-size:clamp(2.4rem,7vw,5.2rem);line-height:1.08;letter-spacing:-.045em;margin:0 0 24px;font-weight:700;max-width:18ch}h2{font-size:clamp(1.6rem,3vw,2.4rem);line-height:1.2;letter-spacing:-.025em;margin:0 0 24px}h3{font-size:1.2rem;line-height:1.4;margin:0 0 12px}p{max-width:70ch;margin:12px 0;white-space:pre-line}.hero{padding:88px 0 72px}.hero.centered{text-align:center}.hero.centered h1,.hero.centered p{margin-left:auto;margin-right:auto}.hero p{font-size:1.15rem}.hero.split{display:grid;grid-template-columns:1.2fr 1fr;gap:40px;align-items:center}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.card{padding:28px;border:1px solid #d1d5db;border-top:3px solid var(--primary);border-radius:12px;background:var(--background)}.price{font-size:2.2rem;font-weight:700;letter-spacing:-.03em}.button{display:inline-block;border:0;background:var(--primary);color:var(--button-text);padding:12px 20px;border-radius:6px;margin-top:16px;font-weight:700}.button:hover{filter:brightness(.93)}.footer{padding:32px 0;border-top:1px solid #d1d5db;margin-top:24px;display:flex;justify-content:space-between;gap:24px}.footer p{margin:0}.form{max-width:700px;display:grid;gap:20px}.field{display:grid;gap:8px}.field input,.field textarea,.filter-input{width:100%;background:var(--background);color:var(--text);padding:12px;border:1px solid #9ca3af;border-radius:6px}.field textarea{min-height:120px;resize:vertical}.notice,.form-status{font-size:.9rem}.accordion details{border-top:1px solid #9ca3af;padding:20px 0}.accordion summary{cursor:pointer;font-weight:700}.tabs-controls{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}.tab-button{border:1px solid #9ca3af;padding:10px 18px;border-radius:6px;background:var(--background);color:var(--text)}.tab-button[aria-selected=true]{background:var(--primary);color:var(--button-text);border-color:var(--primary)}.filter-input{max-width:420px;margin:0 0 24px}.quote{font-size:1.15rem;margin:0}.quote-author{font-weight:700}.modal{max-width:640px;width:calc(100% - 40px);border:0;border-top:6px solid var(--primary);padding:32px;border-radius:12px;background:var(--background);color:var(--text)}.modal::backdrop{background:#111827aa}[hidden]{display:none!important}ul{padding-left:20px}blockquote{margin:0}@media(max-width:680px){.site-shell{padding:0 20px}.navbar{flex-wrap:wrap}.mobile-toggle{display:block}.nav-links{gap:16px}.navbar[data-menu] .nav-links{display:none;width:100%}.navbar[data-menu].menu-open .nav-links{display:flex}.hero{padding:60px 0}.hero.split,.cards{grid-template-columns:1fr}section{padding:36px 0}.footer{flex-direction:column}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
'''

JS = '''
document.querySelectorAll('[data-menu]').forEach(root=>{const button=root.querySelector('[data-menu-button]');button.addEventListener('click',()=>{const open=root.classList.toggle('menu-open');button.setAttribute('aria-expanded',String(open));});});
document.querySelectorAll('[data-accordion]').forEach(root=>{root.querySelectorAll('details').forEach(item=>item.addEventListener('toggle',()=>{if(item.open)root.querySelectorAll('details').forEach(other=>{if(other!==item)other.open=false;});}));});
document.querySelectorAll('[data-tabs]').forEach(root=>{const buttons=[...root.querySelectorAll('[role=tab]')],panels=[...root.querySelectorAll('[role=tabpanel]')];function select(index){buttons.forEach((button,i)=>{button.setAttribute('aria-selected',String(i===index));button.tabIndex=i===index?0:-1;panels[i].hidden=i!==index;});}buttons.forEach((button,i)=>{button.addEventListener('click',()=>select(i));button.addEventListener('keydown',event=>{let index=i;if(event.key==='ArrowRight')index=(i+1)%buttons.length;else if(event.key==='ArrowLeft')index=(i+buttons.length-1)%buttons.length;else if(event.key==='Home')index=0;else if(event.key==='End')index=buttons.length-1;else return;event.preventDefault();select(index);buttons[index].focus();});});});
document.querySelectorAll('[data-filter]').forEach(root=>{const input=root.querySelector('[data-filter-input]'),cards=[...root.querySelectorAll('[data-filter-card]')],empty=root.querySelector('[data-filter-empty]');input.addEventListener('input',()=>{const query=input.value.trim().toLocaleLowerCase('id');cards.forEach(card=>{card.hidden=!card.textContent.toLocaleLowerCase('id').includes(query);});empty.hidden=cards.some(card=>!card.hidden);});});
document.querySelectorAll('[data-modal-open]').forEach(button=>{const dialog=document.getElementById(button.getAttribute('aria-controls'));button.addEventListener('click',()=>dialog.showModal());dialog.querySelector('[data-modal-close]').addEventListener('click',()=>dialog.close());});
document.querySelectorAll('[data-form-validate]').forEach(form=>{form.addEventListener('submit',event=>{event.preventDefault();if(!form.checkValidity()){form.reportValidity();return;}form.querySelector('[data-form-status]').textContent='Data formulir valid. Ini demo lokal, belum ada pengiriman.';});});
'''


def e(value):
    return html.escape(str(value), quote=True)


def link(value, class_name=''):
    return f'<a class="{class_name}" href="{e(value["href"])}">{e(value["label"])}</a>'


def render_page(spec):
    errors = validate_page_spec(spec) + local_link_findings(spec)
    if errors: raise ValueError('Cannot render invalid PageSpec: ' + '; '.join(errors))
    by_target = {}
    for interaction in spec['interactions']:
        by_target.setdefault(interaction['target_id'], set()).add(interaction['type'])
    used_ids = {s['id'] for s in spec['sections']}
    def internal_id(base):
        identifier = 'wcg-' + base
        while identifier in used_ids: identifier += '-x'
        used_ids.add(identifier)
        return identifier
    parts = []
    for section in spec['sections']:
        identifier, kind, props = section['id'], section['type'], section['props']
        actions = by_target.get(identifier, set())
        heading = f'<h2>{e(props["heading"])}</h2>' if 'heading' in props else ''
        content = ''
        attrs = ''
        if kind == 'navbar':
            links_id = internal_id(identifier + '-links')
            toggle = f'<button type="button" class="mobile-toggle" data-menu-button aria-expanded="false" aria-controls="{links_id}">Menu</button>' if 'menu_toggle' in actions else ''
            parts.append(f'<nav id="{identifier}" class="navbar flex items-center justify-between" aria-label="Navigasi utama" {"data-menu" if toggle else ""}><span class="brand">{e(props["brand"])}</span>{toggle}<div id="{links_id}" class="nav-links">{"".join(link(v) for v in props["links"])}</div></nav>')
            continue
        if kind == 'hero':
            content = f'<div><h1>{e(props["heading"])}</h1></div><div><p>{e(props.get("text", ""))}</p>'
            if 'button' in props: content += link(props['button'], 'button')
            content += '</div>'
        elif kind == 'text_section':
            content = heading + f'<p>{e(props["text"])}</p>'
        elif kind == 'feature_grid':
            items = props['items']
            content = heading
            if 'accordion' in actions:
                attrs = 'data-accordion'
                content += '<div class="accordion">' + ''.join(f'<details><summary>{e(item["heading"])}</summary><p>{e(item.get("text", ""))}</p>{link(item["link"]) if "link" in item else ""}</details>' for item in items) + '</div>'
            elif 'tabs' in actions:
                attrs = 'data-tabs'
                ids = [(internal_id(identifier + f'-tab-{i}'), internal_id(identifier + f'-panel-{i}')) for i in range(len(items))]
                content += '<div class="tabs-controls" role="tablist" aria-label="Pilihan layanan">' + ''.join(f'<button type="button" id="{ids[i][0]}" class="tab-button" role="tab" aria-controls="{ids[i][1]}" aria-selected="{str(i == 0).lower()}" tabindex="{0 if i == 0 else -1}">{e(item["heading"])}</button>' for i, item in enumerate(items)) + '</div>'
                content += ''.join(f'<div class="card" role="tabpanel" id="{ids[i][1]}" aria-labelledby="{ids[i][0]}" {"hidden" if i else ""}><h3>{e(item["heading"])}</h3><p>{e(item.get("text", ""))}</p>{link(item["link"]) if "link" in item else ""}</div>' for i, item in enumerate(items))
            else:
                if 'filter' in actions:
                    attrs = 'data-filter'
                    content += '<label>Cari layanan<input class="filter-input" type="search" data-filter-input></label>'
                content += '<div class="cards grid gap-6 md:grid-cols-2">' + ''.join(f'<article class="card rounded-xl p-6" {"data-filter-card" if "filter" in actions else ""}><h3>{e(item["heading"])}</h3><p>{e(item.get("text", ""))}</p>{link(item["link"]) if "link" in item else ""}</article>' for item in items) + '</div>'
                if 'filter' in actions: content += '<p hidden data-filter-empty role="status">Tidak ada layanan yang cocok.</p>'
        elif kind == 'pricing_table':
            content = heading + '<div class="cards grid gap-6 md:grid-cols-2">' + ''.join(f'<article class="card rounded-xl p-6"><h3>{e(plan["name"])}</h3><p class="price">{e(plan["price"])}</p><ul>{"".join("<li>" + e(v) + "</li>" for v in plan["features"])}</ul>{link(plan["button"], "button") if "button" in plan else ""}</article>' for plan in props['plans']) + '</div>'
        elif kind == 'testimonial':
            content = heading + '<div class="cards grid gap-6 md:grid-cols-2">' + ''.join(f'<figure class="card rounded-xl p-6"><blockquote class="quote">{e(item["quote"])}</blockquote><figcaption class="quote-author">{e(item["author"])}</figcaption></figure>' for item in props['items']) + '</div>'
        elif kind == 'contact_form':
            fields = []
            for field in props['fields']:
                fid = internal_id(identifier + '-' + field['name'])
                control = f'<textarea id="{fid}" name="{e(field["name"])}" required></textarea>' if field['type'] == 'textarea' else f'<input id="{fid}" name="{e(field["name"])}" type="{field["type"]}" required>'
                fields.append(f'<label class="field" for="{fid}">{e(field["label"])}{control}</label>')
            validate = 'form_validate' in actions
            content = heading + '<p class="notice">Formulir contoh. Pesan tidak dikirim.</p>'
            content += f'<form class="form" {"data-form-validate" if validate else ""}>{"".join(fields)}<button class="button" type="{"submit" if validate else "button"}">{e(props["submit_label"])}</button><p data-form-status class="form-status" role="status"></p></form>'
        elif kind == 'footer':
            parts.append(f'<footer id="{identifier}" class="footer"><p>{e(props["text"])}</p><div>{" ".join(link(v) for v in props.get("links", []))}</div></footer>')
            continue
        if 'modal' in actions:
            did = internal_id(identifier + '-modal')
            content += f'<button class="button" type="button" data-modal-open aria-controls="{did}">Lihat informasi</button><dialog class="modal" id="{did}"><h2>{e(props.get("heading", spec["title"]))}</h2><p>{e(props.get("text", ""))}</p><button class="button" type="button" data-modal-close>Tutup</button></dialog>'
        classes = 'hero ' + props.get('layout', 'centered') if kind == 'hero' else 'content-section'
        parts.append(f'<section id="{identifier}" class="{classes}" {attrs}>{content}</section>')
    theme = spec['theme']
    rgb = [int(theme['primary'][i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055)**2.4 for v in rgb]
    luminance = sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))
    button_text = '#ffffff' if luminance < .179 else '#111827'
    font = {'sans': '"Trebuchet MS",Arial,sans-serif', 'serif': 'Georgia,"Times New Roman",serif', 'mono': 'Consolas,"Courier New",monospace'}[theme['font']]
    css = f':root{{--primary:{theme["primary"]};--background:{theme["background"]};--text:{theme["text"]};--font:{font};--button-text:{button_text}}}\n' + CSS
    script = '<script src="app.js" defer></script>' if spec['interactions'] else ''
    markup = f'<!doctype html>\n<html lang="{spec["language"]}"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(spec["title"])}</title><link rel="stylesheet" href="styles.css">{script}</head><body class="min-h-screen antialiased"><main class="site-shell mx-auto max-w-6xl px-6">{"".join(parts)}</main></body></html>\n'
    return {'index.html': markup, 'styles.css': css, 'app.js': JS if spec['interactions'] else '// Halaman statis, tanpa interaksi JavaScript.\n'}


def export_page(spec, output_dir):
    output_dir = Path(output_dir).resolve()
    if output_dir.exists(): raise ValueError('Output already exists; preserve earlier examples')
    files = render_page(spec)
    output_dir.mkdir(parents=True)
    for name, text in files.items(): (output_dir / name).write_text(text, encoding='utf-8')
    compiler = ROOT / 'tooling/tailwind/node_modules/@tailwindcss/cli/dist/index.mjs'
    if spec['style_mode'] == 'tailwind':
        if not compiler.is_file(): raise ValueError('Install pinned offline Tailwind compiler first')
        scratch = ROOT / 'tooling/tailwind/.tmp'
        scratch.mkdir(exist_ok=True)
        source = scratch / (uuid.uuid4().hex + '.css')
        relative = Path(__import__('os').path.relpath(output_dir / 'index.html', scratch)).as_posix()
        source.write_text('@import "tailwindcss";\n@source "' + relative + '";\n' + files['styles.css'], encoding='utf-8')
        subprocess.run(['node', str(compiler), '-i', str(source), '-o', str(output_dir / 'styles.css'), '--minify'], cwd=ROOT / 'tooling/tailwind', check=True, capture_output=True, text=True)
    (output_dir / 'page_spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return output_dir
