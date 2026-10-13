"""Save accepted actual model-generated websites as small reviewable repository examples."""
import argparse
import json
import shutil
import zipfile
from pathlib import Path

from src.data.sources import sha256_file, write_manifest
from src.evaluation.generate import assess_output
from src.evaluation.prompt_contract import assess_prompt_contract

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', action='append', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if ROOT / 'examples/generated' not in output.parents:
        raise ValueError('Snapshot must stay inside examples/generated')
    if output.exists() or args.report.exists(): raise ValueError('Preserve existing snapshots/reports')
    validated = []
    names = ('index.html', 'styles.css', 'app.js', 'page_spec.json', 'raw_output.txt', 'prompt.txt', 'generation.json')
    for source in args.source:
        source = source.resolve()
        if ROOT not in source.parents: raise ValueError('Source must be a project artifact')
        metadata = json.loads((source / 'generation.json').read_text(encoding='utf-8'))
        spec = json.loads((source / 'page_spec.json').read_text(encoding='utf-8'))
        raw = (source / 'raw_output.txt').read_text(encoding='utf-8')
        contract = assess_prompt_contract((source / 'prompt.txt').read_text(encoding='utf-8'), spec)
        if (metadata['status'] != 'accepted' or assess_output(raw)['parsed_spec'] != spec
                or not contract['checked'] or contract['errors']):
            raise ValueError('Snapshot requires unmodified accepted generation')
        validated.append((source, metadata, {name: sha256_file(source / name) for name in names}))
    output.mkdir(parents=True)
    entries = []
    for source, metadata, hashes in validated:
        destination = output / source.name
        destination.mkdir()
        for name in names: shutil.copyfile(source / name, destination / name)
        if any(sha256_file(destination / name) != digest for name, digest in hashes.items()):
            raise ValueError('Snapshot file copy changed')
        entries.append({'source': str(source.relative_to(ROOT)), 'destination': str(destination.relative_to(ROOT)),
                        'checkpoint_sha256': metadata['checkpoint_sha256'], 'files': hashes})
    archive = output / 'examples.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for entry in entries:
            destination = ROOT / entry['destination']
            for name in names: bundle.write(destination / name, (Path(destination.name) / name).as_posix())
    links = '\n'.join(f'- [{Path(e["destination"]).name}]({Path(e["destination"]).name}/index.html)' for e in entries)
    (output / 'README.md').write_text('# Snapshot hasil Mini GPT\n\nWebsite ini berasal dari keluaran model proyek yang diterima validator, tanpa repair atau mengganti jawaban dengan target. Raw output, prompt dan checkpoint SHA disertakan. Snapshot statis ini bisa dibuka tanpa bobot model; generasi baru tetap memerlukan checkpoint lokal.\n\n' + links + '\n\n[Unduh contoh HTML/CSS/JavaScript](examples.zip). Form hanya demo lokal, tanpa pengiriman. Browser/visual belum terverifikasi.\n', encoding='utf-8')
    report = {'kind': 'accepted runtime generation snapshots', 'count': len(entries), 'entries': entries,
              'archive_sha256': sha256_file(archive), 'browser_evaluated': False}
    write_manifest(args.report, report)
    print(json.dumps({'snapshots': len(entries), 'output': str(output)}))


if __name__ == '__main__': main()
