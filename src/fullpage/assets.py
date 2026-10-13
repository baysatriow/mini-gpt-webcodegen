"""Resolve only approved project assets with byte integrity checks."""
import json
from pathlib import Path
from src.data.sources import sha256_file


def load_asset_catalog(root):
    return json.loads((Path(root) / 'assets/fullpage/catalog.json').read_text(encoding='utf-8'))


def resolve_asset(asset_id, catalog, root):
    root = Path(root).resolve()
    if asset_id not in catalog['assets']:
        raise ValueError('Unknown asset id')
    info = catalog['assets'][asset_id]
    path = (root / info['path']).resolve()
    if not path.is_relative_to((root / 'assets/fullpage').resolve()) or not path.is_file():
        raise ValueError('Asset escaped trusted directory or is missing')
    if path.suffix.lower() != '.svg' or sha256_file(path) != info['sha256']:
        raise ValueError('Asset format/checksum mismatch')
    return path


def create_project_catalog(root):
    root = Path(root)
    assets = {}
    for name in ('studio-shapes', 'company-shapes'):
        path = root / f'assets/fullpage/{name}.svg'
        assets[name] = {'path': path.relative_to(root).as_posix(), 'width': 640, 'height': 520,
                        'origin': 'project-authored vector illustration', 'license': 'Project-owned demo asset; permitted for this project and its generated pages',
                        'sha256': sha256_file(path)}
    destination = root / 'assets/fullpage/catalog.json'
    with destination.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump({'version': '1.0', 'assets': assets}, handle, ensure_ascii=False, indent=2); handle.write('\n')
    return load_asset_catalog(root)
