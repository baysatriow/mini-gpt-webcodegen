"""Project-owned decoder-only Transformer with explicit causal multi-head attention."""
import math

import torch
from torch import nn
from torch.nn import functional as F


class CausalSelfAttention(nn.Module):
    def __init__(self, config):
        super().__init__()
        width = config["n_embd"]
        self.heads = config["n_head"]
        self.head_dim = width // self.heads
        self.qkv = nn.Linear(width, 3 * width)
        self.projection = nn.Linear(width, width)
        self.attention_dropout = nn.Dropout(config["dropout"])
        self.output_dropout = nn.Dropout(config["dropout"])
        # Runtime choice only: checkpoint tensor names and architecture stay compatible.
        self.backend = "manual"
        self.register_buffer("causal_mask", torch.tril(torch.ones(config["block_size"], config["block_size"], dtype=torch.bool)), persistent=False)

    def forward(self, x):
        batch, length, width = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        q, k, v = [item.reshape(batch, length, self.heads, self.head_dim).transpose(1, 2) for item in (q, k, v)]
        if self.backend == "sdpa":
            attended = F.scaled_dot_product_attention(q, k, v, is_causal=True,
                dropout_p=self.attention_dropout.p if self.training else 0.0)
        else:
            scores = (torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)).float()
            scores = scores.masked_fill(~self.causal_mask[:length, :length], float("-inf"))
            weights = self.attention_dropout(torch.softmax(scores, dim=-1).to(v.dtype))
            attended = torch.matmul(weights, v)
        attended = attended.transpose(1, 2).contiguous().reshape(batch, length, width)
        return self.output_dropout(self.projection(attended))


class Block(nn.Module):
    def __init__(self, config):
        super().__init__()
        width = config["n_embd"]
        self.attention_norm = nn.LayerNorm(width)
        self.attention = CausalSelfAttention(config)
        self.mlp_norm = nn.LayerNorm(width)
        self.mlp = nn.Sequential(nn.Linear(width, 4 * width), nn.GELU(),
                                 nn.Linear(4 * width, width), nn.Dropout(config["dropout"]))

    def forward(self, x):
        x = x + self.attention(self.attention_norm(x))
        return x + self.mlp(self.mlp_norm(x))


class MiniGPT(nn.Module):
    def __init__(self, config: dict):
        super().__init__()
        self.config = {**config, "dropout": config.get("dropout", 0.1), "tie_embeddings": config.get("tie_embeddings", True)}
        for name in ("vocab_size", "block_size", "n_layer", "n_head", "n_embd"):
            if type(self.config.get(name)) is not int or self.config[name] < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.config["n_embd"] % self.config["n_head"] or not 0 <= self.config["dropout"] < 1:
            raise ValueError("Embedding must divide evenly into heads; dropout must be in [0,1)")
        width = self.config["n_embd"]
        self.token_embedding = nn.Embedding(self.config["vocab_size"], width)
        self.position_embedding = nn.Embedding(self.config["block_size"], width)
        self.embedding_dropout = nn.Dropout(self.config["dropout"])
        self.blocks = nn.Sequential(*(Block(self.config) for _ in range(self.config["n_layer"])))
        self.final_norm = nn.LayerNorm(width)
        self.lm_head = nn.Linear(width, self.config["vocab_size"], bias=False)
        self.apply(self._initialize)
        if self.config["tie_embeddings"]:
            self.lm_head.weight = self.token_embedding.weight

    @staticmethod
    def _initialize(module):
        if isinstance(module, (nn.Embedding, nn.Linear)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)

    def forward(self, input_ids, *, output_mask=None):
        if input_ids.ndim != 2 or input_ids.dtype != torch.long:
            raise ValueError("input_ids must be int64 [batch, sequence]")
        length = input_ids.shape[1]
        if not 1 <= length <= self.config["block_size"]:
            raise ValueError("Sequence length exceeds context or is empty")
        positions = torch.arange(length, device=input_ids.device)
        embedded = self.token_embedding(input_ids) + self.position_embedding(positions)
        hidden = self.final_norm(self.blocks(self.embedding_dropout(embedded)))
        if output_mask is not None:
            if output_mask.shape != input_ids.shape or output_mask.dtype != torch.bool:
                raise ValueError("Output mask must be bool with input shape")
            hidden = hidden[output_mask]
        return self.lm_head(hidden)

    def parameter_count(self):
        return sum(parameter.numel() for parameter in self.parameters())

    def set_attention_backend(self, backend):
        if backend not in {"manual", "sdpa"}:
            raise ValueError("Attention backend must be manual or sdpa")
        for block in self.blocks:
            block.attention.backend = backend
