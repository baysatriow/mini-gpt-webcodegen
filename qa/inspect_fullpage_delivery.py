"""Inspect saved delivery bytes, links and notebook outputs; no browser/model runs."""
import argparse
import ast
import hashlib
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import nbformat
from src.data.sources import sha256_file
from src.fullpage.assets import load_asset_catalog
from src.fullpage.compose import compose_page
from src.fullpage.curriculum import write_json


class References(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ids=set()
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if 'id' in attrs: self.ids.add(attrs['id'])
        self.links += [attrs[k] for k in ('src','href') if k in attrs]


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--report',required=True); args=p.parse_args()
    root=Path(__file__).resolve().parents[1]; read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    catalog=load_asset_catalog(root); galleries=[]; html_files=0; files_verified=0
    for suffix in ('best','last'):
        report=read(root/f'reports/fullpage/TRAIN-017_DEVELOPMENT_{suffix.upper()}_V2.json')
        gallery=root/f'examples/generated/AI-018-{suffix}-v2'
        manifest=read(gallery/'manifest.json'); summary=read(root/f'reports/fullpage/GALLERY_AI-018-{suffix}-v2.json')
        if len(manifest['pages'])!=report['complete'] or manifest['validation_revision']!='review-v2': raise ValueError('Gallery identity/count differs')
        if sha256_file(gallery/'websites.zip')!=summary['archive_sha256']: raise ValueError('Archive hash differs')
        with zipfile.ZipFile(gallery/'websites.zip') as archive:
            for name,digest in manifest['files'].items():
                if sha256_file(gallery/name)!=digest or hashlib.sha256(archive.read(name)).hexdigest()!=digest:
                    raise ValueError('Gallery/ZIP bytes differ: '+name)
                files_verified+=1
        for row in manifest['pages']:
            directory=gallery/row['request_id']; request=read(directory/'request.json'); page=read(directory/'page_spec.json'); plan=read(directory/'plan.json')
            if compose_page(plan,page['sections'],request,catalog)!=page: raise ValueError('Composed raw page changed')
            validation=read(directory/'revalidation.json')
            for name,digest in validation['validation']['raw_source_sha256'].items():
                mapped='page_spec.json' if name=='website/page_spec.json' else name
                if sha256_file(directory/mapped)!=digest: raise ValueError('Copied raw bytes differ')
        for html_path in gallery.rglob('*.html'):
            parser=References(); parser.feed(html_path.read_text(encoding='utf-8')); html_files+=1
            for url in parser.links:
                parsed=urlsplit(url)
                if parsed.scheme or parsed.netloc: continue
                if not parsed.path:
                    if parsed.fragment and parsed.fragment not in parser.ids: raise ValueError('Unknown fragment: '+url)
                elif not (html_path.parent/unquote(parsed.path)).is_file(): raise ValueError('Missing HTML local asset: '+url)
        # Historical index bytes and ZIP remain recoverable; notice is explicitly superseded.
        historical=root/f'examples/generated/AI-018-{suffix}'
        old_manifest=read(historical/'manifest.json')
        if sha256_file(historical/'index_pre_review.html')!=old_manifest['files']['index.html']: raise ValueError('Historical index changed')
        old_summary=read(root/f'reports/fullpage/GALLERY_AI-018-{suffix}.json')
        if sha256_file(historical/'websites.zip')!=old_summary['archive_sha256']: raise ValueError('Historical ZIP changed')
        galleries.append({'name':gallery.name,'pages':len(manifest['pages']),'complete_rate':report['complete_rate'],'model_gate':report['model_gate']})
    notebooks=[]
    for prefix,name in (('10','10_fullpage_data_context_dan_gpu.ipynb'),('11','11_fullpage_training_dan_generation.ipynb')):
        nb=nbformat.read(root/'notebooks'/name,as_version=4); nbformat.validate(nb)
        cells=[c for c in nb.cells if c.cell_type=='code']
        if any(c.execution_count is None or any(o.output_type=='error' for o in c.outputs) for c in cells): raise ValueError('Notebook execution incomplete')
        notebooks.append({'name':name,'executed_cells':len(cells),'sha256':sha256_file(root/'notebooks'/name)})
    for relative in ('reports/FULL_PAGE_PROGRESS_2026-10-13.md','README.md'):
        text=(root/relative).read_text(encoding='utf-8')
        if relative=='README.md': text=text.split('## Halaman utuh, AI-018',1)[1].split('## Pengembangan terbaru',1)[0]
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if urlsplit(target).scheme: continue
            if not (root/relative).parent.joinpath(target.split('#')[0]).is_file(): raise ValueError('Missing document link: '+target)
        if '\u2014' in text: raise ValueError('Em dash in new project documentation')
    for relative in ('qa/diagnose_fullpage_review.py','qa/revalidate_fullpage_evaluation.py','qa/inspect_fullpage_delivery.py',
                     'qa/evaluate_fullpage.py','qa/export_fullpage_gallery.py','qa/record_fullpage_progress.py','qa/finalize_fullpage_documentation.py',
                     'src/fullpage/compose.py','src/fullpage/contracts.py','src/fullpage/evaluation.py'):
        ast.parse((root/relative).read_text(encoding='utf-8'))
    progress=read(root/'reports/fullpage/AI-018_PROGRESS.json')
    if progress['status']!='needs_more_model_work' or progress['final_evaluated']: raise ValueError('Progress disposition changed')
    for relative,evidence in progress['evidence'].items():
        if sha256_file(root/relative)!=evidence['sha256']: raise ValueError('Progress evidence drift: '+relative)
    if (root/'data/evaluation/fullpage/final_consumption.json').exists(): raise ValueError('Final unexpectedly claimed')
    report={'galleries':galleries,'files_and_zip_bytes_verified':files_verified,'html_files_static_links_checked':html_files,
            'notebooks':notebooks,'document_links_checked':True,'changed_python_syntax_checked':True,
            'final_claimed':False,'model_runtime_activated':False,'browser_status':'pending','human_review_status':'pending',
            'unit_suite_run':False,'storage_free_bytes':__import__('shutil').disk_usage(root).free}
    write_json(root/args.report,report); print(json.dumps(report,indent=2))


if __name__=='__main__': main()
