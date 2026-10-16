"""Greedy request extraction and selected-checkpoint wrapper."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
from tokenizers import Tokenizer

from src.data.sources import sha256_file
from src.fullpage.request_extract_contracts import (
    EXTRACTION_SCOPES,
    MAX_BRIEF_CHARS,
    MAX_MESSAGES,
    canonical,
    extractor_prompt,
    validate_request_extract,
    validate_scoped_output,
)
from src.fullpage.request_extract_lineage import verify_request_extract_sources
from src.fullpage.serialization import check_budget
from src.models.minigpt import MiniGPT
from src.training.engine import checkpoint_sha256, read_checkpoint


SELECTION_PACKAGE = Path("training/selected/request-extract-v1/selection.json")


class RequestExtractionError(RuntimeError):
    """A controlled failure that must not be converted into a partial draft."""


class RequestExtractionBudgetError(RequestExtractionError):
    """The full source messages and reserved output do not fit the frozen context."""


def greedy_generate(model, tokenizer: Tokenizer, prompt: str, budget: int, device: torch.device) -> tuple[str, int, bool]:
    special = {token: tokenizer.token_to_id(token) for token in ("<bos>", "<prompt>", "<target>", "<eos>")}
    if any(value is None for value in special.values()):
        raise RequestExtractionError("Tokenizer is missing request-extraction delimiters")
    token_ids = [special["<bos>"], special["<prompt>"]]
    token_ids.extend(tokenizer.encode(prompt, add_special_tokens=False).ids)
    token_ids.append(special["<target>"])
    if len(token_ids) + budget > model.config["block_size"]:
        raise RequestExtractionBudgetError("Brief plus reserved output exceeds the model context")
    generated: list[int] = []
    with torch.inference_mode():
        for _ in range(budget):
            input_ids = torch.tensor([token_ids + generated], dtype=torch.long, device=device)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                logits = model(input_ids)
            token = int(logits[0, -1].float().argmax().item())
            generated.append(token)
            if token == special["<eos>"]:
                break
    stopped = bool(generated and generated[-1] == special["<eos>"])
    body = generated[:-1] if stopped else generated
    return tokenizer.decode(body, skip_special_tokens=True), len(generated), stopped


class RequestExtractor:
    """Load one gated extractor checkpoint and merge its 16 validated scope outputs."""

    def __init__(self, checkpoint: Path, root: Path, *, config_path: Path | None = None, device: str = "cuda"):
        self.root = Path(root).resolve()
        self.checkpoint_path = Path(checkpoint)
        self.checkpoint_path = self.checkpoint_path if self.checkpoint_path.is_absolute() else self.root / self.checkpoint_path
        self.checkpoint_path = self.checkpoint_path.resolve()
        if not self.checkpoint_path.is_relative_to(self.root) or not self.checkpoint_path.is_file():
            raise RequestExtractionError("Selected extractor checkpoint is missing or outside the project")
        self.config_path = Path(config_path or "configs/fullpage/training-request-extract-v1.json")
        self.config_path = self.config_path if self.config_path.is_absolute() else self.root / self.config_path
        self.config_path = self.config_path.resolve()
        self.device = torch.device(device)
        selection_path = self.root / SELECTION_PACKAGE
        if not selection_path.is_file():
            raise RequestExtractionError("No extractor passed the development gate; use the manual detail editor")
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        verify_request_extract_sources(self.config, self.root)
        digest = checkpoint_sha256(self.checkpoint_path)
        if (selection.get("status") != "passed"
                or selection.get("automatic_extraction_promoted") is not True
                or selection.get("selected_checkpoint_sha256") != digest
                or selection.get("selected_checkpoint_path") != self.checkpoint_path.relative_to(self.root).as_posix()
                or selection.get("training_config_sha256") != sha256_file(self.config_path)
                or selection.get("final_opened") is not False
                or selection.get("final_used") is not False):
            raise RequestExtractionError("Selected extractor package does not match a passing sealed-data selection")
        state = read_checkpoint(self.checkpoint_path)
        if (state.get("config") != self.config or state.get("weights_only") is not True
                or state.get("global_step") not in {1800, 3600}):
            raise RequestExtractionError("Selected extractor checkpoint metadata is invalid")
        self.tokenizer = Tokenizer.from_file(str(self.root / self.config["tokenizer"]))
        self.model = MiniGPT(self.config["model_config"]).to(self.device)
        self.model.load_state_dict(state["model"], strict=True)
        self.model.set_attention_backend(self.config["performance"]["attention_backend"])
        self.model.eval()
        self.output_budgets = self.config["generation_contract"]["output_budgets"]
        self.checkpoint_sha256 = digest

    def extract(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
            raise RequestExtractionError("Expected an ordered user-message history within the message limit")
        seen: set[str] = set()
        total_chars = 0
        for message in messages:
            if (not isinstance(message, dict) or set(message) != {"id", "text"}
                    or not isinstance(message["id"], str) or not message["id"].strip()
                    or not isinstance(message["text"], str) or not message["text"].strip()
                    or message["id"] in seen):
                raise RequestExtractionError("Prompt messages need unique IDs and non-empty text")
            seen.add(message["id"])
            total_chars += len(message["text"])
        if total_chars > MAX_BRIEF_CHARS:
            raise RequestExtractionBudgetError(f"Brief exceeds the {MAX_BRIEF_CHARS}-character limit")

        merged: dict[str, Any] = {
            "contract_version": "request-extract-v1",
            "fact_mentions": [],
            "setting_mentions": [],
            "business_status_mentions": [],
            "capability_mentions": [],
            "out_of_catalog_mentions": [],
            "corrections": [],
        }
        for scope in EXTRACTION_SCOPES:
            prompt = extractor_prompt(messages, scope)
            budget = self.output_budgets[scope]
            try:
                check_budget(self.tokenizer, prompt, budget, block_size=self.config["block_size"])
            except ValueError as error:
                raise RequestExtractionBudgetError("Brief is too long for the frozen model context; shorten it without removing required details") from error
            raw, _, stopped = greedy_generate(self.model, self.tokenizer, prompt, budget, self.device)
            if not stopped:
                raise RequestExtractionError(f"Extractor scope {scope} did not finish within its output budget")
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as error:
                raise RequestExtractionError(f"Extractor scope {scope} returned malformed JSON") from error
            errors = validate_scoped_output(value, scope)
            if errors:
                raise RequestExtractionError(f"Extractor scope {scope} failed schema validation: {errors[0]}")
            for key in merged:
                if key != "contract_version":
                    merged[key].extend(value[key])
        errors = validate_request_extract(merged)
        if errors:
            raise RequestExtractionError("Merged extractor output failed schema validation: " + errors[0])
        return merged
