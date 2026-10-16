"""Build an isolated prompt-extraction corpus without reading old validation/final data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tokenizers import Tokenizer

from src.data.normalize import read_jsonl
from src.fullpage.request_extract_contracts import (
    CANONICAL_FORMAT,
    CONTRACT_VERSION,
    EXTRACTION_SCOPES,
    MAX_BRIEF_CHARS,
    canonical,
    extractor_prompt,
    scope_output,
    validate_scoped_output,
)
from src.fullpage.serialization import check_budget
from src.data.sources import sha256_file


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path("data/processed/fullpage/v5")
DESTINATION = Path("data/processed/request_extract/v1")
V5_MANIFEST_VERSION = "fullpage-v5-source-bound-v1"
BLOCK_SIZE = 2048
GENRE_LABELS = {"landing_page": "landing page", "company_profile": "company profile"}
STYLE_LABELS = {"tailwind": "Tailwind CSS", "plain_css": "CSS biasa"}
STATUS_LABELS = {True: "usaha fiktif", False: "usaha nyata"}
FACT_ORDER = ("name", "description", "value", "service", "process", "faq", "project")
SCALAR_KINDS = {"name", "description", "value"}
DEV_BUCKET_SIZES = {
    "input_incomplete": 50,
    "correction_single_value": 50,
    "correction_list_value": 50,
    "conflict_fact_value": 50,
    "conflict_page_setting": 50,
    "negation_future_reference": 50,
    "known_catalog_unsupported": 50,
    "out_of_catalog_unsupported": 50,
    "known_catalog_retraction": 50,
    "out_of_catalog_retraction": 50,
    "setting_retraction_without_replacement": 50,
    "setting_correction": 50,
    "style_retraction_without_replacement": 50,
    "style_correction": 50,
    "business_status_correction": 50,
}
TRAIN_TEMPLATES = ("train_labeled", "train_narrative", "train_outline")
DEV_TEMPLATES = ("dev_letter", "dev_prose", "dev_summary", "dev_chat")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload = "".join(canonical(row) + "\n" for row in rows).encode("utf-8")
    path.write_bytes(payload)
    return {"rows": len(rows), "bytes": len(payload), "sha256": _sha256_bytes(payload)}


def _fact_records(request: dict[str, Any]) -> list[dict[str, Any]]:
    facts = request.get("business_facts")
    if not isinstance(facts, list):
        raise ValueError("Request has no business_facts list")
    result = []
    for item in facts:
        if not isinstance(item, dict) or item.get("kind") not in FACT_ORDER:
            raise ValueError("Request contains an unknown business fact")
        kind = item["kind"]
        value = item.get("value")
        if kind in SCALAR_KINDS:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Invalid scalar fact: {kind}")
            result.append({"kind": kind, "value": value})
            continue
        if (not isinstance(value, dict) or not isinstance(value.get("title"), str)
                or not isinstance(value.get("text"), str) or not value["title"].strip()
                or not value["text"].strip()):
            raise ValueError(f"Invalid structured fact: {kind}")
        result.append({"kind": kind, "title": value["title"], "text": value["text"]})
    return sorted(result, key=lambda item: (FACT_ORDER.index(item["kind"]), item.get("title", "")))


def _render_fact_lines(facts: list[dict[str, Any]], template: str, allowed: set[str] | None = None) -> list[str]:
    chosen = [fact for fact in facts if allowed is None or fact["kind"] in allowed]
    lines: list[str] = []
    for fact in chosen:
        kind = fact["kind"]
        if kind in SCALAR_KINDS:
            label = {"name": "Nama usaha", "description": "Tentang usaha", "value": "Nilai utama"}[kind]
            if template == "dev_prose":
                label = {"name": "Usaha ini dikenal sebagai", "description": "Cerita singkatnya", "value": "Yang dijaga oleh usaha ini"}[kind]
            elif template == "dev_letter":
                label = {"name": "Nama brand", "description": "Informasi usaha", "value": "Keunggulan"}[kind]
            elif template == "dev_summary":
                label = {"name": "Brand", "description": "Deskripsi", "value": "Keunikan"}[kind]
            elif template == "dev_chat":
                label = {"name": "Nama bisnis", "description": "Sedikit konteks", "value": "Nilai yang ditawarkan"}[kind]
            lines.append(f"{label}: {fact['value']}")
        else:
            if template == "dev_prose":
                heading = {"service": "Pilihan yang tersedia", "process": "Biasanya dimulai dengan", "faq": "Yang sering ditanyakan", "project": "Contoh karya"}[kind]
            elif template == "dev_letter":
                heading = {"service": "Ruang lingkup layanan", "process": "Alur kolaborasi", "faq": "Pertanyaan umum", "project": "Portofolio pilihan"}[kind]
            elif template == "dev_summary":
                heading = {"service": "Layanan utama", "process": "Tahap kerja", "faq": "FAQ", "project": "Proyek terpilih"}[kind]
            elif template == "dev_chat":
                heading = {"service": "Yang bisa dipesan", "process": "Urutannya", "faq": "FAQ halaman", "project": "Karya yang ditampilkan"}[kind]
            else:
                heading = {"service": "Layanan", "process": "Proses", "faq": "FAQ", "project": "Proyek"}[kind]
            lines.append(f"{heading}: {fact['title']} | {fact['text']}")
    return lines


def _render_brief(profile: dict[str, Any], template: str, *, allowed: set[str] | None = None) -> tuple[str, dict[str, str]]:
    facts = _fact_records(profile)
    genre = profile["genre"]
    style = profile["style_mode"]
    fictitious = profile["fictitious"]
    genre_phrase = GENRE_LABELS[genre]
    style_phrase = STYLE_LABELS[style]
    status_phrase = STATUS_LABELS[fictitious]
    if allowed is not None:
        opening = "Saya ingin memperkenalkan usaha ini melalui halaman website."
    elif template == "train_labeled":
        opening = f"Buat halaman website untuk {next(item['value'] for item in facts if item['kind'] == 'name')}."
    elif template == "train_narrative":
        opening = f"Saya ingin menyiapkan situs bagi {next(item['value'] for item in facts if item['kind'] == 'name')}."
    elif template == "train_outline":
        opening = "Tolong rancang halaman dengan informasi usaha berikut."
    elif template == "dev_letter":
        opening = "Kami membutuhkan sebuah website untuk memperkenalkan usaha ini."
    elif template == "dev_prose":
        opening = "Bayangkan halaman yang memperkenalkan layanan kami."
    elif template == "dev_summary":
        opening = "Saya sedang merapikan informasi untuk sebuah situs."
    else:
        opening = "Bantu susun situs dari catatan ini."
    lines = [opening, *_render_fact_lines(facts, template, allowed)]
    if allowed is None or ("setting" in (allowed or set())):
        if template in {"dev_prose", "dev_chat"}:
            lines.extend([f"Jenis halaman yang saya pilih adalah {genre_phrase}.", f"Untuk styling, gunakan {style_phrase}.", f"Ini adalah {status_phrase}."])
        elif template == "dev_letter":
            lines.extend([f"Formatnya {genre_phrase}.", f"Tampilan dibuat memakai {style_phrase}.", f"Status bisnis: {status_phrase}."])
        else:
            lines.extend([f"Jenis halaman: {genre_phrase}.", f"Gaya CSS: {style_phrase}.", f"Status: {status_phrase}."])
    text = "\n".join(lines)
    return text, {"genre": genre_phrase, "style_mode": style_phrase, "fictitious": status_phrase}


def _new_target() -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "fact_mentions": [],
        "setting_mentions": [],
        "business_status_mentions": [],
        "capability_mentions": [],
        "out_of_catalog_mentions": [],
        "corrections": [],
    }


def _add_facts(target: dict[str, Any], facts: list[dict[str, Any]], message_id: str, allowed: set[str] | None = None) -> None:
    for fact in facts:
        if allowed is not None and fact["kind"] not in allowed:
            continue
        if fact["kind"] in SCALAR_KINDS:
            target["fact_mentions"].append({
                "kind": fact["kind"], "value": fact["value"], "source_message_id": message_id,
            })
        else:
            target["fact_mentions"].append({
                "kind": fact["kind"], "title": fact["title"], "text": fact["text"],
                "title_source_message_id": message_id, "text_source_message_id": message_id,
            })


def _context_for(text: str, phrase: str, from_offset: int = 0) -> str:
    position = text.find(phrase, from_offset)
    if position < 0:
        raise ValueError("Target phrase is absent from its source message")
    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    if end < 0:
        end = len(text)
    return text[start:end].strip()


def _occurrence_index(text: str, phrase: str, context: str) -> int:
    phrase_pos = text.find(context)
    if phrase_pos < 0:
        raise ValueError("Mention context is absent from its source message")
    phrase_pos += context.find(phrase)
    if phrase_pos < 0:
        raise ValueError("Mention phrase is absent from its context")
    return len(list(re.finditer(re.escape(phrase), text[:phrase_pos])))


def _mention(text: str, message_id: str, phrase: str, intent: str, *, kind: str | None = None, value: Any = None) -> dict[str, Any]:
    context = _context_for(text, phrase)
    result = {
        "phrase": phrase,
        "context": context,
        "source_message_id": message_id,
        "occurrence_index": _occurrence_index(text, phrase, context),
        "intent": intent,
    }
    if kind is not None:
        result["kind"] = kind
        result["value"] = value
    return result


def _add_default_settings(target: dict[str, Any], profile: dict[str, Any], text: str, message_id: str) -> None:
    genre_phrase = GENRE_LABELS[profile["genre"]]
    style_phrase = STYLE_LABELS[profile["style_mode"]]
    status_phrase = STATUS_LABELS[profile["fictitious"]]
    genre = _mention(text, message_id, genre_phrase, "requested", kind="genre", value=profile["genre"])
    style = _mention(text, message_id, style_phrase, "requested", kind="style_mode", value=profile["style_mode"])
    status = _mention(text, message_id, status_phrase, "requested")
    status["value"] = profile["fictitious"]
    target["setting_mentions"].extend([genre, style])
    target["business_status_mentions"].append(status)


def _base_case(profile: dict[str, Any], template: str, *, incomplete: bool = False) -> tuple[list[dict[str, str]], dict[str, Any]]:
    allowed = {"name", "description"} if incomplete else None
    text, _ = _render_brief(profile, template, allowed=allowed)
    if incomplete:
        # The first two lines only contain a page framing and the two user facts.
        text = "\n".join(text.splitlines()[:3])
    messages = [{"id": "m1", "text": text}]
    target = _new_target()
    _add_facts(target, _fact_records(profile), "m1", allowed)
    if not incomplete:
        _add_default_settings(target, profile, text, "m1")
    return messages, target


def _add_fact_mention(target: dict[str, Any], kind: str, value: str | dict[str, str], message_id: str) -> None:
    if kind in SCALAR_KINDS:
        target["fact_mentions"].append({"kind": kind, "value": value, "source_message_id": message_id})
    else:
        assert isinstance(value, dict)
        target["fact_mentions"].append({
            "kind": kind, "title": value["title"], "text": value["text"],
            "title_source_message_id": message_id, "text_source_message_id": message_id,
        })


def _replace_fact_mention(
    target: dict[str, Any], kind: str, previous: str | dict[str, str], replacement: str | dict[str, str], message_id: str,
) -> None:
    for index, item in enumerate(target["fact_mentions"]):
        if item["kind"] != kind:
            continue
        if kind in SCALAR_KINDS and item.get("value") == previous:
            target["fact_mentions"][index] = {
                "kind": kind, "value": replacement, "source_message_id": message_id,
            }
            break
        if kind not in SCALAR_KINDS and isinstance(previous, dict) and item.get("title") == previous["title"] and item.get("text") == previous["text"]:
            assert isinstance(replacement, dict)
            target["fact_mentions"][index] = {
                "kind": kind, "title": replacement["title"], "text": replacement["text"],
                "title_source_message_id": message_id, "text_source_message_id": message_id,
            }
            break
    else:
        raise ValueError("Correction previous value does not match a prior fact mention")


def _add_capability(target: dict[str, Any], text: str, message_id: str, capability_id: str, phrase: str, intent: str) -> None:
    mention = _mention(text, message_id, phrase, intent)
    mention["capability_id"] = capability_id
    target["capability_mentions"].append(mention)


def _add_unknown(target: dict[str, Any], text: str, message_id: str, phrase: str, intent: str) -> None:
    target["out_of_catalog_mentions"].append(_mention(text, message_id, phrase, intent))


def _scenario_case(profile: dict[str, Any], split: str, scenario: str, template: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    messages, target = _base_case(profile, template, incomplete=scenario == "input_incomplete")
    if scenario == "complete" or scenario == "input_incomplete":
        return messages, target

    if scenario == "correction_single_value":
        old = next(item["value"] for item in _fact_records(profile) if item["kind"] == "name")
        replacement = old + (" Studio" if split == "train" else " Collective")
        cue = "Koreksi nama" if split == "train" else "Saya ralat nama brand"
        line = f"{cue}: bukan {old}, yang benar {replacement}."
        messages.append({"id": "m2", "text": line})
        _replace_fact_mention(target, "name", old, replacement, "m2")
        target["corrections"].append({
            "kind": "name", "previous_value": old, "replacement_value": replacement,
            "correction_phrase": line.strip(), "source_message_id": "m2",
        })
    elif scenario == "correction_list_value":
        old_fact = next(item for item in _fact_records(profile) if item["kind"] == "service")
        replacement = {
            "title": old_fact["title"] + (" Plus" if split == "train" else " Terpadu"),
            "text": f"{old_fact['text']} Pilihan ini dijelaskan sesuai kebutuhan keluarga {profile['family_index']}.",
        }
        cue = "Koreksi layanan" if split == "train" else "Tolong revisi layanan"
        line = f"{cue} {old_fact['title']}: bukan pilihan lama, yang benar {replacement['title']} | {replacement['text']}"
        messages.append({"id": "m2", "text": line})
        _replace_fact_mention(
            target,
            "service",
            {"title": old_fact["title"], "text": old_fact["text"]},
            replacement,
            "m2",
        )
        target["corrections"].append({
            "kind": "service",
            "previous_value": {"title": old_fact["title"], "text": old_fact["text"]},
            "replacement_value": replacement,
            "correction_phrase": line.split(" | ", 1)[0],
            "source_message_id": "m2",
        })
    elif scenario == "conflict_fact_value":
        old = next(item["value"] for item in _fact_records(profile) if item["kind"] == "name")
        alternative = old + (" Cabang" if split == "train" else " Utama")
        line = f"Nama usaha: {alternative}."
        messages.append({"id": "m2", "text": line})
        _add_fact_mention(target, "name", alternative, "m2")
    elif scenario == "conflict_page_setting":
        old_genre = profile["genre"]
        alternative = "company_profile" if old_genre == "landing_page" else "landing_page"
        phrase = GENRE_LABELS[alternative]
        line = f"Saya juga mempertimbangkan {phrase} untuk halaman ini."
        messages.append({"id": "m2", "text": line})
        target["setting_mentions"].append(_mention(line, "m2", phrase, "requested", kind="genre", value=alternative))
    elif scenario == "negation_future_reference":
        if split == "train":
            lines = [
                "Saya tidak meminta login untuk halaman ini.",
                "integrasi api masih rencana masa depan.",
                "payment gateway hanya contoh referensi.",
            ]
        else:
            lines = [
                "Untuk versi ini, saya tidak ingin fitur sign in.",
                "external api masih sebatas rencana nanti.",
                "online payment hanya saya sebut sebagai referensi.",
            ]
        text = "\n".join(lines)
        messages.append({"id": "m2", "text": text})
        by_line = [(lines[0], "authentication", "login" if split == "train" else "sign in", "negated"),
                   (lines[1], "external_api", "integrasi api" if split == "train" else "external api", "future"),
                   (lines[2], "payment_processing", "payment gateway" if split == "train" else "online payment", "reference")]
        for line, capability, phrase, intent in by_line:
            _add_capability(target, line, "m2", capability, phrase, intent)
    elif scenario == "known_catalog_unsupported":
        phrase = "database backend" if split == "train" else "payment gateway"
        capability = "backend" if split == "train" else "payment_processing"
        line = f"Tambahkan {phrase} pada halaman ini."
        messages.append({"id": "m2", "text": line})
        _add_capability(target, line, "m2", capability, phrase, "requested")
    elif scenario == "out_of_catalog_unsupported":
        phrase = "blockchain rewards" if split == "train" else "voice recognition module"
        line = f"Saya ingin {phrase} terhubung pada situs ini."
        messages.append({"id": "m2", "text": line})
        _add_unknown(target, line, "m2", phrase, "requested")
    elif scenario == "known_catalog_retraction":
        phrase = "database backend" if split == "train" else "payment gateway"
        capability = "backend" if split == "train" else "payment_processing"
        first = f"Tambahkan {phrase} pada halaman ini."
        second = f"Batalkan permintaan {phrase}; jangan sertakan lagi."
        messages.extend([{"id": "m2", "text": first}, {"id": "m3", "text": second}])
        _add_capability(target, first, "m2", capability, phrase, "requested")
        _add_capability(target, second, "m3", capability, phrase, "retracted")
    elif scenario == "out_of_catalog_retraction":
        phrase = "blockchain rewards" if split == "train" else "voice recognition module"
        first = f"Saya ingin {phrase} terhubung pada situs ini."
        second = f"Tidak perlu lagi {phrase}; batalkan permintaan itu."
        messages.extend([{"id": "m2", "text": first}, {"id": "m3", "text": second}])
        _add_unknown(target, first, "m2", phrase, "requested")
        _add_unknown(target, second, "m3", phrase, "retracted")
    elif scenario == "setting_retraction_without_replacement":
        old = profile["genre"]
        phrase = GENRE_LABELS[old]
        line = f"Batalkan pilihan {phrase}."
        messages.append({"id": "m2", "text": line})
        target["setting_mentions"].append(_mention(line, "m2", phrase, "retracted", kind="genre", value=old))
    elif scenario == "style_retraction_without_replacement":
        old = profile["style_mode"]
        phrase = STYLE_LABELS[old]
        line = f"Batalkan pilihan gaya {phrase}."
        messages.append({"id": "m2", "text": line})
        target["setting_mentions"].append(_mention(line, "m2", phrase, "retracted", kind="style_mode", value=old))
    elif scenario == "setting_correction":
        kind = "genre"
        old_value = profile["genre"]
        replacement = "company_profile" if old_value == "landing_page" else "landing_page"
        old_phrase, new_phrase = GENRE_LABELS[old_value], GENRE_LABELS[replacement]
        cue = "Koreksi jenis halaman" if split == "train" else "Saya ralat format situs"
        line = f"{cue}: bukan {old_phrase}, yang benar {new_phrase}."
        messages.append({"id": "m2", "text": line})
        target["setting_mentions"].append(_mention(line, "m2", old_phrase, "negated", kind=kind, value=old_value))
        target["setting_mentions"].append(_mention(line, "m2", new_phrase, "requested", kind=kind, value=replacement))
        target["corrections"].append({
            "kind": kind, "previous_value": old_value, "replacement_value": replacement,
            "correction_phrase": line, "source_message_id": "m2",
        })
    elif scenario == "style_correction":
        kind = "style_mode"
        old_value = profile["style_mode"]
        replacement = "plain_css" if old_value == "tailwind" else "tailwind"
        old_phrase, new_phrase = STYLE_LABELS[old_value], STYLE_LABELS[replacement]
        cue = "Koreksi gaya CSS" if split == "train" else "Saya ralat pilihan styling"
        line = f"{cue}: bukan {old_phrase}, yang benar {new_phrase}."
        messages.append({"id": "m2", "text": line})
        target["setting_mentions"].append(_mention(line, "m2", old_phrase, "negated", kind=kind, value=old_value))
        target["setting_mentions"].append(_mention(line, "m2", new_phrase, "requested", kind=kind, value=replacement))
        target["corrections"].append({
            "kind": kind, "previous_value": old_value, "replacement_value": replacement,
            "correction_phrase": line, "source_message_id": "m2",
        })
    elif scenario == "business_status_correction":
        old_value = profile["fictitious"]
        replacement = not old_value
        old_phrase, new_phrase = STATUS_LABELS[old_value], STATUS_LABELS[replacement]
        cue = "Koreksi status usaha" if split == "train" else "Saya ralat keterangan bisnis"
        line = f"{cue}: bukan {old_phrase}, yang benar {new_phrase}."
        messages.append({"id": "m2", "text": line})
        old_mention = _mention(line, "m2", old_phrase, "negated")
        old_mention["value"] = old_value
        new_mention = _mention(line, "m2", new_phrase, "requested")
        new_mention["value"] = replacement
        target["business_status_mentions"].extend([old_mention, new_mention])
        target["corrections"].append({
            "kind": "fictitious", "previous_value": old_value, "replacement_value": replacement,
            "correction_phrase": line, "source_message_id": "m2",
        })
    else:
        raise ValueError("Unknown extraction scenario: " + scenario)

    return messages, target


def _row(
    profile: dict[str, Any], split: str, scenario: str, template: str,
    scope: str, messages: list[dict[str, str]], complete_target: dict[str, Any], tokenizer: Tokenizer,
) -> dict[str, Any]:
    target = scope_output(complete_target, scope)
    errors = validate_scoped_output(target, scope)
    if errors:
        raise ValueError(f"Invalid target for {split}/{profile['family_id']}/{scenario}/{scope}: {errors[:3]}")
    prompt = extractor_prompt(messages, scope)
    prefix_tokens = 3 + len(tokenizer.encode(prompt, add_special_tokens=False).ids)
    target_text = canonical(target)
    target_tokens = len(tokenizer.encode(target_text, add_special_tokens=False).ids) + 1
    if target_tokens > 1536:
        raise ValueError(
            f"Extraction target over maximum output for {split}/{profile['family_id']}/{scenario}/{scope}: "
            f"{target_tokens}>1536"
        )
    if sum(len(message["text"]) for message in messages) > MAX_BRIEF_CHARS:
        raise ValueError(f"Brief exceeds {MAX_BRIEF_CHARS} characters")
    return {
        "example_id": f"{split}-{profile['family_id']}-{scenario}-{template}-{scope}",
        "family_id": profile["family_id"],
        "split": split,
        "scenario": scenario,
        "scope": scope,
        "prompt_pattern_id": template,
        "source_family_ids": profile["source_family_ids"],
        "canonical_format": CANONICAL_FORMAT,
        "messages": messages,
        "prompt": prompt,
        "target": target_text,
        "budget": {
            "prefix_tokens": prefix_tokens,
            "output_tokens": target_tokens,
            "reserved_output_tokens": target_tokens,
            "total_tokens": prefix_tokens + target_tokens,
        },
        "genre": profile["genre"],
        "scenario": scenario,
    }


def _rows_for_case(profile: dict[str, Any], split: str, scenario: str, template: str, tokenizer: Tokenizer) -> list[dict[str, Any]]:
    messages, target = _scenario_case(profile, split, scenario, template)
    return [
        _row(profile, split, scenario, template, scope, messages, target, tokenizer)
        for scope in EXTRACTION_SCOPES
    ]


def _freeze_scope_budgets(rows: list[dict[str, Any]], tokenizer: Tokenizer) -> dict[str, int]:
    maximum_target = {
        scope: max(row["budget"]["output_tokens"] for row in rows if row["scope"] == scope)
        for scope in EXTRACTION_SCOPES
    }
    budgets = {
        scope: min(1536, target + max(24, int(target * 0.08 + 0.999)))
        for scope, target in maximum_target.items()
    }
    for row in rows:
        budget = budgets[row["scope"]]
        if row["budget"]["prefix_tokens"] + budget > BLOCK_SIZE:
            raise ValueError(
                f"Scoped request still exceeds context for {row['example_id']}/{row['scope']}: "
                f"prefix={row['budget']['prefix_tokens']}, target={budget}, context={BLOCK_SIZE}"
            )
        if row["budget"]["output_tokens"] > budget:
            raise ValueError("Frozen scope budget is smaller than a target")
        check_budget(tokenizer, row["prompt"], budget, block_size=BLOCK_SIZE)
        row["budget"]["reserved_output_tokens"] = budget
        row["budget"]["total_tokens"] = row["budget"]["prefix_tokens"] + budget
    return budgets


def _training_profiles(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data_dir = root / SOURCE_DIR
    manifest_path = data_dir / "manifest.json"
    request_path = data_dir / "train.requests.jsonl"
    if not manifest_path.is_file() or not request_path.is_file():
        raise FileNotFoundError("Frozen V5 training request file or manifest is missing")
    parent_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if parent_manifest.get("version") != V5_MANIFEST_VERSION:
        raise ValueError("Expected the frozen source-bound V5 dataset")
    train_info = parent_manifest.get("files", {}).get("train.requests.jsonl", {})
    if sha256_file(request_path) != train_info.get("sha256"):
        raise ValueError("V5 training request checksum differs from its manifest")
    train_family_ids = set(parent_manifest.get("family_ids", {}).get("train", []))
    profiles: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(request_path):
        if row.get("split") != "train":
            raise ValueError("Training request file contains a non-training row")
        family_id = row.get("family_id")
        request = row.get("request")
        if not isinstance(family_id, str) or family_id not in train_family_ids or not isinstance(request, dict):
            raise ValueError("Training request row is outside the frozen training family manifest")
        if family_id not in profiles:
            profiles[family_id] = {
                "family_id": family_id,
                "family_index": len(profiles),
                "source_family_ids": [family_id],
                "genre": request.get("genre"),
                "style_mode": request.get("style_mode"),
                "fictitious": request.get("fictitious"),
                "business_facts": request.get("business_facts"),
            }
    if set(profiles) != train_family_ids:
        raise ValueError("Training request rows do not cover the frozen training family list")
    if any(profile["genre"] not in GENRE_LABELS or profile["style_mode"] not in STYLE_LABELS
           or type(profile["fictitious"]) is not bool for profile in profiles.values()):
        raise ValueError("V5 training profiles have an unsupported setting or missing business status")
    counts = Counter(profile["genre"] for profile in profiles.values())
    if any(counts[genre] < 100 for genre in GENRE_LABELS):
        raise ValueError("Need at least 100 distinct training families for each page genre")
    return list(profiles.values()), parent_manifest


def _dev_profile(index: int, genre: str) -> dict[str, Any]:
    prefixes = ["Ruang", "Rona", "Temu", "Awan", "Pijar", "Nusa", "Loka", "Sela", "Kawan", "Rimba"]
    nouns = ["Bumi", "Aksara", "Perca", "Rasa", "Lensa", "Tumbuh", "Suara", "Daya", "Pagi", "Karya"]
    offerings = ["kerajinan", "pendampingan", "ilustrasi", "kelas kreatif", "produk lokal", "ruang belajar", "jasa desain", "konsultasi", "fotografi", "arsitektur"]
    suffix = f"{index:04d}"
    offer = offerings[index % len(offerings)]
    name = f"{prefixes[index % len(prefixes)]} {nouns[(index // len(prefixes)) % len(nouns)]} {suffix}"
    services = [
        (f"Rancang {offer} {suffix}", f"Kami menyiapkan {offer} dengan ruang lingkup yang dibahas sejak awal untuk keluarga {suffix}."),
        (f"Sesi konsultasi {suffix}", f"Percakapan terarah membantu pelanggan menyusun tujuan dan langkah untuk keluarga {suffix}."),
        (f"Paket pendampingan {suffix}", f"Pilihan layanan dijelaskan sebelum kegiatan dimulai bagi kelompok {suffix}."),
    ]
    processes = [
        ("Ceritakan kebutuhan", f"Pelanggan menyampaikan tujuan awal untuk layanan keluarga {suffix}."),
        ("Pilih pendekatan", f"Kami membahas pilihan yang sesuai dengan kebutuhan kelompok {suffix}."),
        ("Mulai bekerja", f"Pekerjaan dimulai setelah ruang lingkup disepakati untuk keluarga {suffix}."),
    ]
    facts: list[dict[str, Any]] = [
        {"kind": "name", "value": name},
        {"kind": "description", "value": f"Usaha {offer} yang menyusun layanan terarah dengan komunikasi jelas untuk pelanggan keluarga {suffix}."},
        {"kind": "value", "value": f"Setiap pilihan diterangkan secara terbuka agar pelanggan keluarga {suffix} dapat memutuskan dengan nyaman."},
    ]
    facts.extend({"kind": "service", "value": {"title": title, "text": text}} for title, text in services)
    facts.extend({"kind": "process", "value": {"title": title, "text": text}} for title, text in processes)
    facts.extend([
        {"kind": "faq", "value": {"title": "Bagaimana memulai?", "text": f"Hubungi kami untuk menyampaikan kebutuhan layanan keluarga {suffix}."}},
        {"kind": "faq", "value": {"title": "Apakah bisa menyesuaikan layanan?", "text": f"Pilihan dibicarakan sesuai lingkup yang disepakati bersama keluarga {suffix}."}},
        {"kind": "faq", "value": {"title": "Kapan pekerjaan dimulai?", "text": f"Pekerjaan dimulai setelah kebutuhan keluarga {suffix} dipahami."}},
        {"kind": "project", "value": {"title": f"Koleksi pilihan {suffix}", "text": f"Satu rangkaian karya {offer} ditampilkan sebagai contoh proses keluarga {suffix}."}},
        {"kind": "project", "value": {"title": f"Eksplorasi bentuk {suffix}", "text": f"Karya pilihan memperlihatkan pendekatan visual untuk keluarga {suffix}."}},
    ])
    return {
        "family_id": f"dev-family-{index:05d}",
        "family_index": index,
        "source_family_ids": [f"dev-family-{index:05d}"],
        "genre": genre,
        "style_mode": "tailwind" if index % 2 == 0 else "plain_css",
        "fictitious": True,
        "business_facts": facts,
    }


def _build_rows(root: Path, tokenizer: Tokenizer) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    train_profiles, parent_manifest = _training_profiles(root)
    train_rows: list[dict[str, Any]] = []
    for profile in train_profiles:
        for template in TRAIN_TEMPLATES:
            train_rows.extend(_rows_for_case(profile, "train", "complete", template, tokenizer))
        for scenario in DEV_BUCKET_SIZES:
            train_rows.extend(_rows_for_case(profile, "train", scenario, "train_outline", tokenizer))

    dev_profiles: list[dict[str, Any]] = []
    next_index = 0
    for genre in GENRE_LABELS:
        for _ in range(100):
            dev_profiles.append(_dev_profile(next_index, genre))
            next_index += 1
    for scenario, family_count in DEV_BUCKET_SIZES.items():
        for _ in range(family_count):
            genre = "landing_page" if next_index % 2 == 0 else "company_profile"
            dev_profiles.append(_dev_profile(next_index, genre))
            next_index += 1

    dev_rows: list[dict[str, Any]] = []
    bucket_family_ids: dict[str, set[str]] = defaultdict(set)
    genre_family_ids: dict[str, set[str]] = defaultdict(set)
    complete_families = dev_profiles[:200]
    for index, profile in enumerate(complete_families):
        genre_family_ids[profile["genre"]].add(profile["family_id"])
        dev_rows.extend(_rows_for_case(profile, "development", "complete", DEV_TEMPLATES[index % len(DEV_TEMPLATES)], tokenizer))
    cursor = 200
    for scenario, family_count in DEV_BUCKET_SIZES.items():
        for index in range(family_count):
            profile = dev_profiles[cursor]
            cursor += 1
            genre_family_ids[profile["genre"]].add(profile["family_id"])
            bucket_family_ids[scenario].add(profile["family_id"])
            dev_rows.extend(_rows_for_case(profile, "development", scenario, DEV_TEMPLATES[index % len(DEV_TEMPLATES)], tokenizer))
    if cursor != len(dev_profiles):
        raise ValueError("Development profile assignment did not consume the frozen family bank")

    source_path = root / SOURCE_DIR / "train.requests.jsonl"
    v5_manifest_path = root / SOURCE_DIR / "manifest.json"
    aliases_path = root / "configs/fullpage/request-extract-v1-aliases.json"
    schema_path = root / "configs/fullpage/request-extract-v1.schema.json"
    source_info = {
        "data/processed/fullpage/v5/train.requests.jsonl": sha256_file(source_path),
        "data/processed/fullpage/v5/manifest.json": sha256_file(v5_manifest_path),
        "configs/fullpage/request-extract-v1-aliases.json": sha256_file(aliases_path),
        "configs/fullpage/request-extract-v1.schema.json": sha256_file(schema_path),
        "src/fullpage/request_extract_contracts.py": sha256_file(root / "src/fullpage/request_extract_contracts.py"),
        "qa/prepare_request_extract_v1.py": sha256_file(Path(__file__).resolve()),
    }
    dev_family_ids = sorted({row["family_id"] for row in dev_rows})
    train_family_ids = sorted({row["family_id"] for row in train_rows})
    if set(train_family_ids) & set(dev_family_ids):
        raise ValueError("Training and new development families overlap")
    train_patterns = sorted({row["prompt_pattern_id"] for row in train_rows})
    dev_patterns = sorted({row["prompt_pattern_id"] for row in dev_rows})
    if set(train_patterns) & set(dev_patterns):
        raise ValueError("Training and development prompt patterns overlap")
    output_budgets = _freeze_scope_budgets(train_rows + dev_rows, tokenizer)
    training_fact_family_counts = {}
    for kind in FACT_ORDER:
        training_fact_family_counts[kind] = len({
            row["family_id"] for row in train_rows
            if any(item["kind"] == kind for item in json.loads(row["target"])["fact_mentions"])
        })
    training_genre_family_counts = {
        genre: len({row["family_id"] for row in train_rows if row["genre"] == genre})
        for genre in GENRE_LABELS
    }
    return train_rows, dev_rows, {
        "parent_manifest": parent_manifest,
        "source_sha256": source_info,
        "train_family_ids": train_family_ids,
        "development_family_ids": dev_family_ids,
        "train_patterns": train_patterns,
        "development_patterns": dev_patterns,
        "output_budgets": output_budgets,
        "train_fact_family_counts": training_fact_family_counts,
        "train_genre_family_counts": training_genre_family_counts,
        "development_bucket_family_counts": {name: len(ids) for name, ids in bucket_family_ids.items()},
        "development_genre_family_counts": {genre: len(ids) for genre, ids in genre_family_ids.items()},
    }


def build_request_extract_dataset(root: Path, output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    root, output_dir = Path(root).resolve(), Path(output_dir)
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(root):
        raise ValueError("Output directory must stay inside the project root")
    if output_dir.exists() and not force:
        raise FileExistsError("Extractor dataset already exists; use --force only to rebuild this derived directory")
    tokenizer_path = root / "data/tokenizer/tokenizer.json"
    if not tokenizer_path.is_file():
        raise FileNotFoundError("Project tokenizer is missing")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    train_rows, dev_rows, audit = _build_rows(root, tokenizer)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="request-extract-v1-", dir=str(output_dir.parent)))
    try:
        train_info = _write_jsonl(temporary / "train.jsonl", train_rows)
        development_info = _write_jsonl(temporary / "development.jsonl", dev_rows)
        maxima = {}
        for name, rows in (("train", train_rows), ("development", dev_rows)):
            maxima[name] = {
                "prefix_tokens": max(row["budget"]["prefix_tokens"] for row in rows),
                "target_tokens_with_eos": max(row["budget"]["output_tokens"] for row in rows),
                "reserved_output_tokens": max(row["budget"]["reserved_output_tokens"] for row in rows),
                "total_tokens": max(row["budget"]["total_tokens"] for row in rows),
            }
        manifest = {
            "version": CONTRACT_VERSION,
            "canonical_format": CANONICAL_FORMAT,
            "dataset_dir": output_dir.relative_to(root).as_posix(),
            "human_reviewed": False,
            "development_frozen_before_training": True,
            "existing_validation_used": False,
            "existing_test_used": False,
            "final_opened": False,
            "final_used": False,
            "block_size": BLOCK_SIZE,
            "output_budgets": audit["output_budgets"],
            "extraction_scopes": list(EXTRACTION_SCOPES),
            "hard_brief_char_limit": MAX_BRIEF_CHARS,
            "parent_v5_manifest_sha256": audit["source_sha256"]["data/processed/fullpage/v5/manifest.json"],
            "tokenizer_sha256": sha256_file(tokenizer_path),
            "source_sha256": audit["source_sha256"],
            "files": {"train.jsonl": train_info, "development.jsonl": development_info},
            "family_counts": {"train": len(audit["train_family_ids"]), "development": len(audit["development_family_ids"])},
            "row_counts": {"train": len(train_rows), "development": len(dev_rows)},
            "family_ids": {"train": audit["train_family_ids"], "development": audit["development_family_ids"]},
            "prompt_pattern_ids": {"train": audit["train_patterns"], "development": audit["development_patterns"]},
            "train_fact_family_counts": audit["train_fact_family_counts"],
            "train_genre_family_counts": audit["train_genre_family_counts"],
            "development_bucket_family_counts": audit["development_bucket_family_counts"],
            "development_genre_family_counts": audit["development_genre_family_counts"],
            "maxima": maxima,
        }
        (temporary / "manifest.json").write_text(canonical(manifest) + "\n", encoding="utf-8")
        if output_dir.exists():
            shutil.rmtree(output_dir)
        os.replace(temporary, output_dir)
        return manifest
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=DESTINATION)
    parser.add_argument("--force", action="store_true", help="Replace only the derived extractor dataset directory")
    args = parser.parse_args()
    manifest = build_request_extract_dataset(args.root, args.output_dir, force=args.force)
    print(json.dumps({
        "dataset_dir": manifest["dataset_dir"],
        "family_counts": manifest["family_counts"],
        "row_counts": manifest["row_counts"],
        "train_fact_family_counts": manifest["train_fact_family_counts"],
        "train_genre_family_counts": manifest["train_genre_family_counts"],
        "development_bucket_family_counts": manifest["development_bucket_family_counts"],
        "output_budgets": manifest["output_budgets"],
        "maxima": manifest["maxima"],
        "final_used": manifest["final_used"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
