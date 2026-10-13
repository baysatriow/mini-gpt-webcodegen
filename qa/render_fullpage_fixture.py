"""Export disclosed manual fixtures and inspect local file/fragment contracts."""
import argparse
import copy
import json
import re
from pathlib import Path
from src.data.sources import sha256_file
from src.fullpage.assets import load_asset_catalog, resolve_asset
from src.fullpage.curriculum import make_page, write_json
from src.fullpage.compose import compose_page
from src.fullpage.renderer import export_fullpage


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',default='examples/generated/AI-018-manual'); p.add_argument('--report',default='reports/fullpage/AI-018_RENDER_FIXTURES.json')
    args=p.parse_args(); root=args.root.resolve(); destination=root/args.output
    if destination.exists(): raise ValueError('Fixture directory exists')
    catalog=load_asset_catalog(root); source_hash=sha256_file(root/'src/rendering/renderer.py'); results=[]
    for index in range(2):
        for style in ('plain_css','tailwind'):
            request,plan,sections,_=make_page(index,'train',style,'Studio Fixture' if not index else 'Kafe Fixture')
            spec=compose_page(plan,sections,request,catalog)
            output=destination/(request['genre']+'-'+style); exported=export_fullpage(spec,output,root=root)
            markup=(output/'index.html').read_text(encoding='utf-8'); ids=set(re.findall(r'\bid="([^"]+)"',markup))
            refs=re.findall(r'(?:src|href)="([^"]+)"',markup)
            for ref in refs:
                if ref.startswith('#'):
                    if ref[1:] not in ids: raise ValueError('Broken fragment')
                elif not (output/ref).is_file(): raise ValueError('Missing local reference')
            if len(re.findall(r'\bid="([^"]+)"',markup))!=len(ids): raise ValueError('Duplicate HTML IDs')
            if 'max-width:680px' not in (output/'styles.css').read_text(encoding='utf-8'): raise ValueError('Missing responsive CSS')
            bad=copy.deepcopy(sections); next(s for s in bad if s['role']=='services')['props']['items'][0]['text']='Changed fact'
            try: compose_page(plan,bad,request,catalog)
            except ValueError: pass
            else: raise ValueError('Fact mismatch accepted')
            escaped=copy.deepcopy(spec); escaped['sections'][1]['props']['text']='<script>alert("x")</script>'
            from src.fullpage.renderer import render_fullpage
            text=render_fullpage(escaped,catalog,root)['index.html']
            if '<script>alert' in text or '&lt;script&gt;' not in text: raise ValueError('Text escaping failed')
            results.append({'genre':request['genre'],'style':style,'sections':len(spec['sections']),'label':'manual curriculum fixture, not model output',**exported})
    bad_catalog=copy.deepcopy(catalog); bad_catalog['assets']['studio-shapes']['path']='../secret.svg'
    try: resolve_asset('studio-shapes',bad_catalog,root)
    except ValueError: pass
    else: raise ValueError('Asset traversal accepted')
    if sha256_file(root/'src/rendering/renderer.py')!=source_hash: raise ValueError('Legacy renderer changed')
    report={'fixtures':results,'local_refs_and_fragments_valid':True,'fact_mismatch_rejected':True,'text_escaped':True,
            'asset_traversal_rejected':True,'legacy_renderer_unchanged_sha256':source_hash,'browser_status':'pending','viewports_planned':[390,1440]}
    write_json(root/args.report,report); print(json.dumps({'fixtures':len(results),'sections_each':9,'browser_status':'pending'},indent=2))


if __name__=='__main__': main()
