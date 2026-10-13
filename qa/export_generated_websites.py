"""Export real model outputs after the locked synthetic contract gate passes."""
import argparse
import hashlib
import html
import json
import zipfile
from pathlib import Path

from src.data.sources import sha256_file, write_manifest
from src.evaluation.generate import assess_output
from src.evaluation.prompt_contract import assess_prompt_contract
from src.rendering.renderer import export_page

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    args.output, args.report, args.evaluation = args.output.resolve(), args.report.resolve(), args.evaluation.resolve()
    if ROOT not in args.output.parents or ROOT not in args.report.parents:
        raise ValueError('Gallery output/report must stay inside this project')
    if args.output.exists() or args.report.exists(): raise ValueError('Use new output/report paths')
    report = json.loads(args.evaluation.read_text(encoding='utf-8'))
    if report['split'] != 'final' or not report['contract_gate_passed']:
        raise ValueError('Only completed locked-final contract evaluation can export this demo gallery')
    raw_path = ROOT / report['outputs_path']
    if 'outputs_sha256' in report and sha256_file(raw_path) != report['outputs_sha256']:
        raise ValueError('Raw generation artifacts changed since evaluation')
    records = json.loads(raw_path.read_text(encoding='utf-8'))
    if len(records) != report['count']: raise ValueError('Output count changed')
    entries, rejected = [], []
    for index, row in enumerate(records):
        # Render parsed raw generation, never substitute target_spec.
        spec = assess_output(row['raw_output'])['parsed_spec']
        contract = assess_prompt_contract(row['prompt'], spec) if spec else {'checked': False, 'errors': ['Invalid schema']}
        if (spec is None or not contract['checked'] or contract['errors'] or spec != row['target_spec']):
            rejected.append({'example_id': row['example_id'], 'contract': contract})
            continue
        name = f'{index + 1:02d}-{row["recipe"]}-{spec["style_mode"]}'
        directory = export_page(spec, args.output / name)
        (directory / 'prompt.txt').write_text(row['prompt'] + '\n', encoding='utf-8')
        (directory / 'raw_output.txt').write_text(row['raw_output'], encoding='utf-8')
        metadata = {'example_id': row['example_id'], 'checkpoint_sha256': report['checkpoint_sha256'],
                    'raw_output_sha256': hashlib.sha256(row['raw_output'].encode()).hexdigest(),
                    'origin': 'raw Mini GPT output -> schema validation -> deterministic renderer',
                    'synthetic_demo': True, 'style_mode': spec['style_mode'], 'exact_contract': spec == row['target_spec'],
                    'prompt_contract': contract}
        write_manifest(directory / 'generation.json', metadata)
        entries.append({'directory': str(directory.relative_to(ROOT)), 'title': spec['title'], 'recipe': row['recipe'],
                        **metadata, 'files': {p.name: {'sha256': sha256_file(p), 'bytes': p.stat().st_size} for p in directory.iterdir() if p.is_file()}})
    cards = ''.join(f'<li><a href="{Path(e["directory"]).name}/index.html">{html.escape(e["title"])}: {e["recipe"]}, {e["style_mode"]}</a> <a href="{Path(e["directory"]).name}/page_spec.json">JSON</a></li>' for e in entries)
    page = '<!doctype html><html lang="id"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hasil Mini GPT WebCodeGen</title><style>body{font:17px/1.7 Georgia,serif;color:#111827;background:#fafafa;max-width:1000px;margin:50px auto;padding:24px}h1{font-size:2.6rem;line-height:1.2}a{color:#1d4ed8}li{padding:8px 0}p{max-width:75ch}</style></head><body><h1>Hasil Mini GPT WebCodeGen</h1><p>' + str(len(entries)) + ' contoh website fiktif dari keluaran model pada prompt final sintetis. HTML/CSS/JavaScript disusun renderer dari JSON model yang valid dan sesuai kontrak prompt, tanpa mengganti jawabannya dengan target.</p><p>Halaman bisa dibuka lokal. Form hanya memvalidasi data, tanpa pengiriman. Ini contoh pipeline, belum antarmuka aplikasi generator untuk prompt bebas.</p><p><a href="websites.zip" download>Unduh seluruh contoh HTML, CSS, JavaScript dan JSON</a></p><ul>' + cards + '</ul></body></html>'
    (args.output / 'index.html').write_text(page, encoding='utf-8')
    archive = args.output / 'websites.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for entry in entries:
            directory = ROOT / entry['directory']
            for path in directory.iterdir():
                if path.is_file(): bundle.write(path, path.relative_to(args.output))
    value = {'checkpoint_sha256': report['checkpoint_sha256'], 'source_evaluation_sha256': sha256_file(args.evaluation),
             'output_count': len(entries), 'output_dir': str(args.output.relative_to(ROOT)),
             'rejected': rejected, 'raw_output_sha256': sha256_file(raw_path),
             'raw_hash_bound_at_evaluation': 'outputs_sha256' in report,
             'archive_sha256': sha256_file(archive), 'tailwind_version': '4.3.3', 'entries': entries,
             'browser_evaluated': False, 'limits': ['Fictional controlled prompts, not arbitrary real-world generation',
             'No generator application/API', 'Forms do not send data', 'Browser/visual scores require separate inspection']}
    write_manifest(args.report, value)
    print(json.dumps({'generated': len(entries), 'gallery': str(args.output / 'index.html'), 'zip': str(archive)}))


if __name__ == '__main__':
    main()
