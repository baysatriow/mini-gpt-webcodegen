"""Inspect the published Vulcan corpus without executing generated code."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/dataset_audit/vulcan'
RAW.mkdir(parents=True, exist_ok=True)
LIMIT = 12 * 1024 * 1024

def get(url):
    with urllib.request.urlopen(url, timeout=50) as response:
        body = response.read(LIMIT + 1)
    if len(body) > LIMIT:
        raise ValueError('Response exceeded audit size limit')
    return body

meta = json.loads(get('https://huggingface.co/api/datasets/xlelords/vulcan'))
revision = meta['sha']
RAW.joinpath('metadata.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')

def download(name):
    body = get(f'https://huggingface.co/datasets/xlelords/vulcan/resolve/{revision}/{name}')
    RAW.joinpath(name).write_bytes(body)
    if name.endswith('.jsonl'):
        return name, [json.loads(line) for line in body.decode('utf-8').splitlines() if line.strip()]
    return name, None

with ThreadPoolExecutor(max_workers=4) as pool:
    files = dict(pool.map(download, ['frontend_sft.jsonl', 'train.jsonl', 'val.jsonl', 'README.md']))

def role(row, name):
    return '\n'.join(m['content'] for m in row['messages'] if m['role'] == name)

def normalized(text):
    return re.sub(r'\s+', ' ', text).strip()

def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

rows = files['frontend_sft.jsonl']
prompts = Counter(role(row, 'user') for row in rows)
code = [role(row, 'assistant') for row in rows]
scripts = [normalized(s) for c in code for s in re.findall(r'<script\b[^>]*>(.*?)</script\s*>', c, re.I | re.S) if s.strip()]
train_prompts = {role(r, 'user') for r in files['train.jsonl']}
val_prompts = {role(r, 'user') for r in files['val.jsonl']}
train_outputs = {normalized(role(r, 'assistant')) for r in files['train.jsonl']}
validation = files['val.jsonl']
summary = {
    'audited_at': datetime.now(timezone(timedelta(hours=7))).isoformat(),
    'source': 'https://huggingface.co/datasets/xlelords/vulcan',
    'revision': revision,
    'license_declared': meta.get('cardData', {}).get('license'),
    'rows': len(rows),
    'train_rows': len(files['train.jsonl']),
    'validation_rows': len(validation),
    'unique_user_prompts': len(prompts),
    'prompt_frequency': dict(prompts),
    'unique_assistant_outputs_exact': len({digest(c) for c in code}),
    'unique_assistant_outputs_whitespace_normalized': len({digest(normalized(c)) for c in code}),
    'rows_with_script_tag': sum(bool(re.search(r'<script\b', c, re.I)) for c in code),
    'rows_with_addEventListener': sum('addEventListener' in c for c in code),
    'unique_nonempty_script_bodies_whitespace_normalized': len(set(scripts)),
    'rows_with_tailwind_reference': sum('tailwind' in c.lower() for c in code),
    'rows_with_bootstrap_reference': sum('bootstrap' in c.lower() for c in code),
    'rows_with_doctype': sum(bool(re.search(r'<!doctype\s+html', c, re.I)) for c in code),
    'train_validation_shared_unique_prompts': len(train_prompts & val_prompts),
    'validation_rows_with_prompt_seen_in_train': sum(role(r, 'user') in train_prompts for r in validation),
    'validation_rows_with_normalized_output_seen_in_train': sum(normalized(role(r, 'assistant')) in train_outputs for r in validation),
    'limitations': ['Static text audit only; generated code was not executed.', 'Exact prompt overlap does not measure semantic template similarity.', 'No model training or model evaluation was performed.'],
}
out = ROOT / 'outputs/dataset_audit/vulcan_summary.json'
out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k != 'prompt_frequency'}, indent=2))
