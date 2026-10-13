"""Local prompt -> project Mini GPT -> validated PageSpec -> standalone website export."""
import argparse
import json
from pathlib import Path

from tokenizers import Tokenizer

from src.data.curriculum import verify_manifest
from src.data.integrity import reuse_tokenization
from src.data.sources import sha256_file, write_manifest
from src.evaluation.generate import _generate, assess_output
from src.evaluation.prompt_contract import assess_prompt_contract
from src.models.minigpt import MiniGPT
from src.rendering.renderer import export_page
from src.training.engine import read_checkpoint, checkpoint_sha256, load_checkpoint
from src.training.lineage import pretrain_descriptor

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--prompt-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.output.exists(): raise ValueError('Use a new output folder')
    evidence = json.loads(args.evidence.read_text(encoding='utf-8'))
    sha = checkpoint_sha256(args.checkpoint)
    if evidence['split'] != 'final' or not evidence['contract_gate_passed'] or evidence['checkpoint_sha256'] != sha:
        raise ValueError('Requires checkpoint with passing locked synthetic contract evaluation')
    state = read_checkpoint(args.checkpoint)
    cfg, lineage = state['config'], state['config']['lineage']
    directory = ROOT / cfg['dataset_dir']
    manifest = verify_manifest(directory)
    summary = json.loads((ROOT / 'data/manifests/pipeline_summary.json').read_text(encoding='utf-8'))
    reuse_tokenization(ROOT, summary, summary['split'], json.loads((ROOT / 'configs/tokenizer.json').read_text()))
    if (cfg.get('data_origin') != 'synthetic_curriculum' or lineage['human_reviewed'] is not False
            or lineage['synthetic_manifest_sha256'] != sha256_file(directory / 'manifest.json')
            or lineage['pretrain_fingerprint'] != pretrain_descriptor(ROOT, summary)):
        raise ValueError('Curriculum/pretraining lineage changed')
    prompt = args.prompt_file.read_text(encoding='utf-8').strip()
    tokenizer = Tokenizer.from_file(str(ROOT / cfg['tokenizer']))
    model = MiniGPT(state['model_config']).cuda().eval()
    load_checkpoint(args.checkpoint, model, None, None, restore_rng=False)
    config = {'precision': 'bf16', 'temperature': 0, 'seed': 42, 'max_new_tokens': 768}
    raw, stop, count = _generate(model, tokenizer, prompt, config)
    assessment = assess_output(raw)
    spec = assessment['parsed_spec']
    contract = assess_prompt_contract(prompt, spec) if spec is not None else {'checked': False, 'errors': ['JSON/schema tidak valid'], 'requested': {}}
    accepted = spec is not None and contract['checked'] and not contract['errors']
    metadata = {'checkpoint_sha256': sha, 'prompt_file_sha256': sha256_file(args.prompt_file),
        'evidence_sha256': sha256_file(args.evidence), 'decode_config': config, 'stop_reason': stop,
        'generated_tokens': count, 'parse_status': assessment['parse_status'], 'schema_errors': assessment['schema_errors'],
        'parse_error': assessment['parse_error'], 'status': 'accepted' if accepted else 'rejected',
        'prompt_contract_checked': contract['checked'], 'prompt_contract': contract, 'review_kind': manifest['review_kind'],
        'limits': ['Controlled prompt patterns are supported; arbitrary wording is not established',
                   'Only explicitly extracted facts are checked; no human/browser quality approval', 'No JSON repair or fallback target']}
    if accepted:
        try:
            export_page(spec, args.output)
        except Exception as error:
            args.output.mkdir(parents=True, exist_ok=True)
            metadata['status'] = 'render_failed'
            metadata['render_error'] = str(error)
    else: args.output.mkdir(parents=True)
    (args.output / 'raw_output.txt').write_text(raw, encoding='utf-8')
    (args.output / 'prompt.txt').write_text(prompt + '\n', encoding='utf-8')
    write_manifest(args.output / 'generation.json', metadata)
    print(json.dumps({'status': metadata['status'], 'output': str(args.output), 'stop': stop, 'tokens': count}))
    return 0 if metadata['status'] == 'accepted' else 1 if metadata['status'] == 'render_failed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
