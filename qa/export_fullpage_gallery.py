"""Export only accepted raw model pages, with byte manifests and review blanks."""
import argparse
import csv
import html
import json
import shutil
import zipfile
from pathlib import Path
from src.data.sources import sha256_file
from src.fullpage.curriculum import write_json


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--report',required=True); p.add_argument('--output',required=True)
    args=p.parse_args(); root=args.root.resolve(); report_path=root/args.report; report=json.loads(report_path.read_text(encoding='utf-8'))
    output=root/args.output
    if output.exists(): raise ValueError('Gallery exists')
    output.mkdir(parents=True); selected=[]
    for row in report['results']:
        if row['status']!='accepted': continue
        directory=Path(report['output'])/row['request_id']; matches=sorted(directory.glob('attempt-*/result.json'))
        source=matches[-1].parent; result=json.loads(matches[-1].read_text(encoding='utf-8'))
        if result['status']!='accepted' or result['metadata']['checkpoint_sha256']!=report['checkpoint_sha256']: raise ValueError('Gallery source identity changed')
        destination=output/row['request_id']; shutil.copytree(source/'website',destination)
        for name in ('request.json','plan.json','result.json'): shutil.copyfile(source/name,destination/name)
        selected.append({'request_id':row['request_id'],'path':row['request_id']+'/index.html','model_output':True,'browser_status':'pending'})
    links=''.join('<li><a href="'+html.escape(v['path'],quote=True)+'">'+html.escape(v['request_id'])+'</a></li>' for v in selected)
    note=f'{len(selected)}/{report["total"]} halaman development diterima. Model gate: {report["model_gate"]}. Review manusia dan browser belum selesai.'
    if report['scope']=='final': note=f'{len(selected)}/{report["total"]} halaman final diterima. Review manusia dan browser belum selesai.'
    (output/'index.html').write_text('<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mini GPT halaman utuh</title><style>body{font:16px/1.7 Arial;margin:40px auto;max-width:900px;padding:20px}li{margin:12px 0}a{color:#2563eb}</style></head><body><h1>Raw model output, halaman utuh</h1><p>'+html.escape(note)+'</p><p>Setiap halaman berasal dari plan dan bagian model yang lolos validator. Formulir adalah demo lokal.</p><ul>'+links+'</ul></body></html>',encoding='utf-8')
    manifest={'evaluation_report_sha256':sha256_file(report_path),'checkpoint_sha256':report['checkpoint_sha256'],'scope':report['scope'],'pages':selected,
              'files':{p.relative_to(output).as_posix():sha256_file(p) for p in output.rglob('*') if p.is_file()},'browser_status':'pending','human_review_status':'pending'}
    write_json(output/'manifest.json',manifest)
    archive=output/'websites.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(output.rglob('*')):
            if path.is_file() and path!=archive: z.write(path,path.relative_to(output).as_posix())
    with zipfile.ZipFile(archive) as z:
        import hashlib
        for name,digest in manifest['files'].items():
            if hashlib.sha256(z.read(name)).hexdigest()!=digest: raise ValueError('ZIP bytes differ')
    write_json(root/'reports/fullpage'/('GALLERY_'+output.name+'.json'),{'pages':len(selected),'total':report['total'],'output':str(output),'archive_sha256':sha256_file(archive),'zip_file_bytes_verified':True})
    if report['scope']=='final':
        frozen=json.loads((root/'data/evaluation/fullpage/manifest.json').read_text(encoding='utf-8'))
        with (output/'review.csv').open('x',encoding='utf-8',newline='') as h:
            writer=csv.DictWriter(h,fieldnames=['request_id','available','reviewer','relevance','text_quality','layout_hierarchy','consistency','viewport390','viewport1440','notes']); writer.writeheader()
            for group,ids in frozen['review_ids'].items():
                for identifier in ids: writer.writerow({'request_id':identifier,'available':any(v['request_id']==identifier for v in selected)})
    print(json.dumps({'pages':len(selected),'gallery':str(output),'model_gate':report['model_gate'],'browser_status':'pending'},indent=2))


if __name__=='__main__': main()
