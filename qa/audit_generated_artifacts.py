"""Audit exported bytes, ZIP membership and local resources without browser claims."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import zipfile

from src.data.curriculum import ROOT
from src.data.sources import sha256_file, write_manifest
from src.evaluation.generate import assess_output
from src.evaluation.prompt_contract import assess_prompt_contract


class Resources(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get('id'): self.ids.add(attributes['id'])
        for key in ('src', 'href'):
            if attributes.get(key): self.links.append(attributes[key])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gallery-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--staged-evidence', action='store_true', help='Check frozen references against staged Git bytes')
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('Preserve audit records')
    gallery = json.loads(args.gallery_report.read_text(encoding='utf-8'))
    directory = ROOT / gallery['output_dir']; archive = directory / 'websites.zip'
    if sha256_file(archive) != gallery['archive_sha256']: raise ValueError('ZIP changed')
    expected = {}
    for entry in gallery['entries']:
        page = ROOT / entry['directory']
        raw = (page / 'raw_output.txt').read_text(encoding='utf-8')
        spec = assess_output(raw)['parsed_spec']
        if spec != json.loads((page / 'page_spec.json').read_text(encoding='utf-8')):
            raise ValueError('Rendered spec differs from raw model output')
        contract = assess_prompt_contract((page / 'prompt.txt').read_text(encoding='utf-8').strip(), spec)
        if not contract['checked'] or contract['errors']: raise ValueError('Prompt contract failed')
        parsed = Resources(); parsed.feed((page / 'index.html').read_text(encoding='utf-8'))
        for link in parsed.links:
            if link.startswith('#'):
                if link[1:] not in parsed.ids: raise ValueError(f'Unresolved fragment {link}')
            elif '://' not in link and not link.startswith(('mailto:', 'tel:')):
                if not (page / link).is_file(): raise ValueError(f'Missing local resource {link}')
        for name, metadata in entry['files'].items():
            path = page / name
            if sha256_file(path) != metadata['sha256']: raise ValueError('Export file changed')
            expected[path.relative_to(directory).as_posix()] = metadata['sha256']
    with zipfile.ZipFile(archive) as bundle:
        if set(bundle.namelist()) != set(expected): raise ValueError('ZIP membership changed')
        for name, digest in expected.items():
            if hashlib.sha256(bundle.read(name)).hexdigest() != digest: raise ValueError('ZIP bytes changed')
    snapshot_files = 0
    if args.snapshot:
        snapshot = args.snapshot.resolve()
        metadata = json.loads((snapshot / 'generation.json').read_text(encoding='utf-8'))
        if metadata['status'] != 'accepted': raise ValueError('Snapshot was not accepted')
        spec = assess_output((snapshot / 'raw_output.txt').read_text(encoding='utf-8'))['parsed_spec']
        if spec != json.loads((snapshot / 'page_spec.json').read_text(encoding='utf-8')): raise ValueError('Snapshot substitution')
        snapshot_files = len(list(snapshot.iterdir()))
    staged_checks = 0
    if args.staged_evidence:
        selection = json.loads((ROOT / 'reports/training/TRAIN-015_FINAL_SELECTION.json').read_text(encoding='utf-8'))
        gate = json.loads((ROOT / 'reports/training/TRAIN-015_FINAL_GATE.json').read_text(encoding='utf-8'))
        checks = {
            'reports/training/TRAIN-015.json': selection['training_report_sha256'],
            'reports/training/TRAIN-015-DEV_curriculum_evaluation.json': selection['development_report_sha256'],
            'docs/superpowers/plans/2026-10-13-copying-quality-continuation.md': selection['policy_sha256'],
            'reports/training/TRAIN-015_FINAL_SELECTION.json': gate['selection_sha256'],
            'reports/training/TRAIN-015-FINAL_curriculum_evaluation.json': gate['final_report_sha256'],
            'reports/data/SYNTHETIC_CURRICULUM_V6.json': selection.get('synthetic_manifest_sha256') or
                json.loads((ROOT / 'reports/training/TRAIN-015.json').read_text(encoding='utf-8'))['config']['lineage']['synthetic_manifest_sha256'],
        }
        for path, digest in checks.items():
            blob = subprocess.check_output(['git', 'show', ':' + path], cwd=ROOT)
            if hashlib.sha256(blob).hexdigest() != digest: raise ValueError(f'Staged frozen evidence changed: {path}')
        staged_checks = len(checks)
    result = {'exported_websites':len(gallery['entries']), 'archive_files':len(expected),
        'zip_bytes_verified':True, 'local_resources_and_fragments_verified':True,
        'snapshot_files':snapshot_files, 'staged_evidence_hashes_verified':staged_checks, 'browser_evaluated':False,
        'limits':['Static artifact checks do not execute JavaScript or inspect layout/interactions in a browser']}
    write_manifest(args.output, result); print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
