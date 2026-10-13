"""Standalone responsive PageSpec2 renderer with a trusted local asset catalog."""
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from src.rendering.renderer import CSS, JS, e, link, export_page
from src.data.sources import sha256_file
from .assets import load_asset_catalog, resolve_asset
from .contracts import validate_composed_page, media_ids

FULL_CSS = '''
.site-shell{max-width:1200px}.navbar{border:0;padding:26px 0}.brand{font-size:1.15rem}.nav-links a{font-size:.95rem;font-weight:600}.hero{border-radius:28px;padding:72px 48px;background:color-mix(in srgb,var(--primary) 7%,var(--background));margin:12px 0 40px}.hero.split{grid-template-columns:1.1fr 1fr}.hero h1{font-size:clamp(2.5rem,5vw,4.8rem);overflow-wrap:anywhere}.hero.centered .media{max-width:480px;margin:36px auto 0}.media{margin:0}.media img{display:block;width:100%;height:auto;border-radius:20px}.media figcaption{font-size:.85rem;margin-top:10px}.eyebrow{color:var(--primary);text-transform:uppercase;letter-spacing:.12em;font-size:.75rem;font-weight:700;margin-bottom:18px}.content-section{padding:60px 0}.section-heading{max-width:740px;margin-bottom:28px}.cards{grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}.card{border:1px solid #dbe2ef;border-top:0;border-radius:18px;padding:28px;box-shadow:0 8px 28px #11182706}.card h3{font-size:1.12rem}.card p{font-size:.97rem}.step-number{display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;border-radius:50%;background:var(--primary);color:var(--button-text);font-weight:700;margin-bottom:22px}.prose{max-width:860px}.text-split{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:center}.contact-panel{padding:44px;border-radius:24px;background:color-mix(in srgb,var(--primary) 6%,var(--background));display:grid;grid-template-columns:1fr 1.3fr;gap:48px}.contact-panel h2{max-width:15ch}.field input,.field textarea{background:var(--background);border-radius:10px}.button{border-radius:10px}.footer{padding:38px 0 44px}.footer-links{display:flex;gap:24px;flex-wrap:wrap}.demo-note{font-size:.8rem;max-width:50ch;color:var(--text)}.accordion details{border:1px solid #dbe2ef;border-radius:12px;padding:20px 24px;margin:12px 0}.accordion summary{list-style-position:outside}.content-section:nth-of-type(even){border-top:1px solid #eef0f5}@media(max-width:900px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.hero{padding:48px 28px}.contact-panel{gap:24px}}@media(max-width:680px){.site-shell{padding:0 18px}.hero{padding:38px 24px;border-radius:20px}.hero.split,.cards,.text-split,.contact-panel{grid-template-columns:1fr}.hero.split{gap:28px}.hero h1{font-size:2.6rem}.content-section{padding:36px 0}.contact-panel{padding:26px}.nav-links{flex-direction:column;align-items:flex-start;padding:16px 0}.footer-links{gap:16px}.footer{flex-direction:column}.mobile-toggle{border:1px solid #dbe2ef;border-radius:8px;background:var(--background);color:var(--text);padding:8px 14px}}
'''


def render_fullpage(spec, catalog, root):
    errors = validate_composed_page(spec)
    if errors: raise ValueError(errors)
    for identifier in set(media_ids(spec)): resolve_asset(identifier, catalog, root)
    used = {s['id'] for s in spec['sections']}
    def uid(base):
        name = 'wcg-' + base
        while name in used: name += '-x'
        used.add(name); return name
    def media(value):
        info = catalog['assets'][value['asset_id']]
        caption = '<figcaption>' + e(value['caption']) + '</figcaption>' if 'caption' in value else ''
        return f'<figure class="media"><img src="assets/{e(value["asset_id"])}.svg" width="{info["width"]}" height="{info["height"]}" alt="{e(value["alt"])}">{caption}</figure>'
    parts = []
    for s in spec['sections']:
        identifier, kind, p = s['id'], s['type'], s['props']; role, variant = s['role'], s['variant']
        heading = '<h2>' + e(p['heading']) + '</h2>' if 'heading' in p else ''
        if kind == 'navbar':
            lid = uid(identifier+'-links')
            parts.append(f'<nav id="{identifier}" class="navbar flex items-center justify-between" aria-label="Navigasi utama" data-menu><span class="brand">{e(p["brand"])}</span><button class="mobile-toggle" type="button" data-menu-button aria-expanded="false" aria-controls="{lid}">Menu</button><div id="{lid}" class="nav-links">{"".join(link(v) for v in p["links"])}</div></nav>'); continue
        if kind == 'footer':
            note = '<p class="demo-note">Contoh usaha fiktif untuk demonstrasi.</p>' if spec['fictitious'] else ''
            parts.append(f'<footer id="{identifier}" class="footer"><div><strong>{e(p["text"])}</strong>{note}</div><div class="footer-links">{"".join(link(v) for v in p.get("links",[]))}</div></footer>'); continue
        attrs = ''; classes = 'content-section'; content = ''
        if kind == 'hero':
            classes = 'hero ' + variant
            content = '<div><p class="eyebrow">' + ('Kenali usaha kami' if spec['genre']=='company_profile' else 'Mari mulai bersama') + '</p><h1>' + e(p['heading']) + '</h1><p>' + e(p.get('text','')) + '</p>' + (link(p['button'],'button') if 'button' in p else '') + '</div>'
            if 'media' in p: content += media(p['media'])
        elif kind == 'text_section':
            content = '<div class="prose">'+heading+'<p>'+e(p['text'])+'</p></div>'
            if 'media' in p: content = '<div class="text-split">'+content+media(p['media'])+'</div>'
        elif kind == 'feature_grid':
            content = '<div class="section-heading">'+heading+'</div>'
            if role == 'faq':
                attrs = 'data-accordion'; content += '<div class="accordion">'+''.join('<details><summary>'+e(i['heading'])+'</summary><p>'+e(i.get('text',''))+'</p>'+ (link(i['link']) if 'link' in i else '')+'</details>' for i in p['items'])+'</div>'
            else:
                cards = []
                for number,item in enumerate(p['items'],1):
                    badge = '<span class="step-number">'+str(number).zfill(2)+'</span>' if variant=='numbered' else ''
                    cards.append('<article class="card rounded-xl p-6">'+badge+(media(item['media']) if 'media' in item else '')+'<h3>'+e(item['heading'])+'</h3><p>'+e(item.get('text',''))+'</p>'+(link(item['link']) if 'link' in item else '')+'</article>')
                content += '<div class="cards grid gap-6 md:grid-cols-3">'+''.join(cards)+'</div>'
        elif kind == 'contact_form':
            fields = []
            for field in p['fields']:
                fid = uid(identifier+'-'+field['name']); name = e(field['name'])
                control = f'<textarea id="{fid}" name="{name}" required></textarea>' if field['type']=='textarea' else f'<input id="{fid}" name="{name}" type="{field["type"]}" required>'
                fields.append(f'<label class="field" for="{fid}">{e(field["label"])}{control}</label>')
            content = '<div class="contact-panel"><div>'+heading+'<p>Isi kebutuhan awal untuk memulai percakapan.</p><p class="notice">Demo lokal. Pesan belum dikirim.</p></div><form class="form" data-form-validate>'+''.join(fields)+'<button class="button" type="submit">'+e(p['submit_label'])+'</button><p data-form-status role="status"></p></form></div>'
        elif kind == 'pricing_table':
            content = heading+'<div class="cards">'+''.join('<article class="card"><h3>'+e(i['name'])+'</h3><p class="price">'+e(i['price'])+'</p><ul>'+''.join('<li>'+e(v)+'</li>' for v in i['features'])+'</ul>'+(link(i['button'],'button') if 'button' in i else '')+'</article>' for i in p['plans'])+'</div>'
        elif kind == 'testimonial':
            content = heading+'<div class="cards">'+''.join('<figure class="card"><blockquote>'+e(i['quote'])+'</blockquote><figcaption>'+e(i['author'])+'</figcaption></figure>' for i in p['items'])+'</div>'
        parts.append(f'<section id="{identifier}" class="{classes}" {attrs}>{content}</section>')
    t = spec['theme']; font = {'sans':'Arial,sans-serif','serif':'Georgia,serif','mono':'Consolas,monospace'}[t['font']]
    rgb = [int(t['primary'][i:i+2],16)/255 for i in (1,3,5)]
    lum = sum((v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)*w for v,w in zip(rgb,(.2126,.7152,.0722)))
    css = f':root{{--primary:{t["primary"]};--background:{t["background"]};--text:{t["text"]};--font:{font};--button-text:{"#fff" if lum<.179 else "#111827"}}}\n'+CSS+FULL_CSS
    markup = '<!doctype html>\n<html lang="id"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(spec['title'])+'</title><link rel="stylesheet" href="styles.css"><script src="app.js" defer></script></head><body class="min-h-screen antialiased"><main class="site-shell mx-auto max-w-6xl px-6">'+''.join(parts)+'</main></body></html>\n'
    return {'index.html':markup,'styles.css':css,'app.js':JS}


def export_fullpage(spec, output, *, root):
    root, output = Path(root).resolve(), Path(output).resolve()
    if spec.get('schema_version') == '1.0': return {'path':str(export_page(spec,output)), 'version':'1.0'}
    if output.exists(): raise ValueError('Output exists')
    catalog = load_asset_catalog(root); files = render_fullpage(spec,catalog,root)
    compiler = root/'tooling/tailwind/node_modules/@tailwindcss/cli/dist/index.mjs'
    if spec['style_mode']=='tailwind' and not compiler.is_file(): raise ValueError('Pinned Tailwind compiler is missing')
    output.mkdir(parents=True)
    for name,text in files.items():
        with (output/name).open('x',encoding='utf-8',newline='\n') as h: h.write(text)
    selected = {}
    if media_ids(spec): (output/'assets').mkdir()
    for identifier in set(media_ids(spec)):
        shutil.copyfile(resolve_asset(identifier,catalog,root),output/f'assets/{identifier}.svg'); selected[identifier]=catalog['assets'][identifier]
    if spec['style_mode']=='tailwind':
        scratch = root/'tooling/tailwind/.tmp'; scratch.mkdir(exist_ok=True)
        source = scratch/(uuid.uuid4().hex+'.css')
        relative = Path(os.path.relpath(output/'index.html',scratch)).as_posix()
        source.write_text('@import "tailwindcss";\n@source "'+relative+'";\n'+files['styles.css'],encoding='utf-8')
        subprocess.run(['node',str(compiler),'-i',str(source),'-o',str(output/'styles.css'),'--minify'],cwd=root/'tooling/tailwind',check=True,capture_output=True,text=True)
    from .curriculum import write_json
    write_json(output/'page_spec.json',spec); write_json(output/'asset_attribution.json',selected)
    return {'path':str(output),'files':{p.relative_to(output).as_posix():sha256_file(p) for p in output.rglob('*') if p.is_file()},'browser_status':'pending'}
