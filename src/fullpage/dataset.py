"""Shifted task labels and reproducible length buckets without fixed padding."""
import hashlib
import json
import math
import random
import torch
from torch.utils.data import Dataset
from src.data.normalize import read_jsonl
from src.data.tokenizer import SPECIAL_TOKENS
from src.training.engine import ResumableBatchSampler
from .serialization import canonical, check_budget, OUTPUT_BUDGETS, output_budget_for
from .contracts import schema_errors


def encode_task_row(row, tokenizer):
    if row['task'] not in OUTPUT_BUDGETS: raise ValueError('Unknown task')
    target = json.loads(row['target'])
    contract_version = target.get('contract_version') if isinstance(target, dict) else None
    if contract_version == 'source-bound-v1':
        schema_name = 'plan-source-bound-v1' if row['task'] == 'page_plan' else 'section-source-bound-v1'
    elif contract_version is None:
        schema_name = 'plan' if row['task'] == 'page_plan' else 'section'
    else:
        raise ValueError(f'Unsupported fullpage target contract: {contract_version}')
    errors = schema_errors(schema_name, target)
    if errors: raise ValueError(errors)
    output_budget = output_budget_for(row['task'], contract_version)
    check_budget(tokenizer, row['prompt'], output_budget)
    if any(t in row['target'] for t in SPECIAL_TOKENS): raise ValueError('Reserved delimiter in target')
    special = {t: tokenizer.token_to_id(t) for t in SPECIAL_TOKENS}
    if any(v is None for v in special.values()): raise ValueError('Missing tokenizer delimiter')
    if special['<pad>'] != 0: raise ValueError('Collator requires the frozen project pad ID 0')
    prefix = [special['<bos>'], special['<prompt>']] + tokenizer.encode(row['prompt']).ids + [special['<target>']]
    target = tokenizer.encode(row['target']).ids + [special['<eos>']]
    if len(target) > output_budget: raise ValueError('Target exceeds output budget')
    sequence = prefix + target
    if len(sequence) > 2048: raise ValueError('Oversize task sequence')
    ids, labels = sequence[:-1], sequence[1:]
    labels[:len(prefix) - 1] = [-100] * (len(prefix) - 1)
    if row['length'] != len(ids): raise ValueError('Task length metadata mismatch')
    return {'input_ids': ids, 'labels': labels, 'length': len(ids)}


class TaskDataset(Dataset):
    def __init__(self, path, tokenizer, family_ids=None):
        self.rows = [r for r in read_jsonl(path) if family_ids is None or r['family_id'] in family_ids]
        if not self.rows: raise ValueError('Empty task dataset')
        self.encoded = [encode_task_row(r, tokenizer) for r in self.rows]
        self.lengths = [r['length'] for r in self.encoded]
        self.task_kinds = [r['task'] for r in self.rows]

    def __len__(self): return len(self.rows)

    def __getitem__(self, index): return self.encoded[index]


class TaskBatchSampler(ResumableBatchSampler):
    def __init__(self, lengths, task_kinds, batch_size, seed, balanced=True, plan_probability=.3):
        super().__init__(len(lengths), batch_size, seed)
        if not 0 < plan_probability < 1: raise ValueError('Plan probability must be between zero and one')
        self.plan_probability = plan_probability
        self.balanced = balanced
        identity = [lengths, task_kinds, balanced]
        if plan_probability != .3: identity.append(plan_probability)
        self.fingerprint = hashlib.sha256(canonical(identity).encode()).hexdigest()
        self.groups = {}
        for index, (length, task) in enumerate(zip(lengths, task_kinds, strict=True)):
            bucket = next(b for b in (256, 512, 1024, 2048) if length <= b)
            self.groups.setdefault((task, bucket), []).append(index)
        if balanced and set(task_kinds) != set(OUTPUT_BUDGETS): raise ValueError('Balanced sampling requires both tasks')

    def batches(self, epoch):
        rng = random.Random(self.seed + epoch)
        if not self.balanced:
            order = list(range(self.size))
            return [order[i:i+self.batch_size] for i in range(0, self.size, self.batch_size)]
        batches = []
        for _ in range(self.batches_per_epoch):
            task = 'page_plan' if rng.random() < self.plan_probability else 'section_content'
            groups = [v for (kind, bucket), v in self.groups.items() if kind == task]
            pool = rng.choices(groups, weights=[len(v) for v in groups], k=1)[0]
            batches.append(rng.choices(pool, k=self.batch_size))
        return batches

    def __iter__(self):
        epoch, offset = divmod(self.cursor, self.batches_per_epoch)
        for batch in self.batches(epoch)[offset:]:
            self.cursor += 1
            yield batch

    def state_dict(self):
        return {**super().state_dict(), 'fingerprint': self.fingerprint, 'balanced': self.balanced}

    def load_state_dict(self, state):
        if state['fingerprint'] != self.fingerprint or state['balanced'] != self.balanced:
            raise ValueError('Task sampler data/ratio mismatch')
        super().load_state_dict(state)


def trim_collate(rows):
    length = max(row['length'] for row in rows)
    ids, labels = [], []
    for row in rows:
        pad = length - row['length']
        ids.append(row['input_ids'] + [0] * pad)
        labels.append(row['labels'] + [-100] * pad)
    return {'input_ids': torch.tensor(ids, dtype=torch.long), 'labels': torch.tensor(labels, dtype=torch.long)}
