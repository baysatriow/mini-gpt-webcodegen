"""Explicit plan wire codec and conservative generation token budgets."""
import json
from src.data.tokenizer import SPECIAL_TOKENS

SECTION_FIELDS = ('id', 'type', 'role', 'variant', 'fact_ids', 'asset_ids')
OUTPUT_BUDGETS = {'page_plan': 512, 'section_content': 1536}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def encode_plan(plan):
    return {**plan, 'sections': [[section[key] for key in SECTION_FIELDS] for section in plan['sections']]}


def decode_plan(wire):
    sections = []
    for values in wire['sections']:
        if not isinstance(values, list) or len(values) != 6:
            raise ValueError('Invalid section tuple length')
        sections.append(dict(zip(SECTION_FIELDS, values, strict=True)))
    return {**wire, 'sections': sections}


def serialize_task(task, value):
    if task not in OUTPUT_BUDGETS:
        raise ValueError('Unknown full-page task')
    return canonical(encode_plan(value) if task == 'page_plan' else value)


def check_budget(tokenizer, prompt, output_budget, block_size=2048):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('Empty task prompt')
    if any(token in prompt for token in SPECIAL_TOKENS):
        raise ValueError('Reserved delimiter in task prompt')
    if type(output_budget) is not int or not 1 <= output_budget <= 1536 or block_size != 2048:
        raise ValueError('Full-page tasks require context 2048 and output in 1..1536')
    prefix = 3 + len(tokenizer.encode(prompt, add_special_tokens=False).ids)
    if prefix + output_budget > block_size:
        raise ValueError(f'Budget overflow: prefix={prefix}, output={output_budget}, context={block_size}')
    return {'prefix_tokens': prefix, 'max_new_tokens': output_budget, 'block_size': block_size}
