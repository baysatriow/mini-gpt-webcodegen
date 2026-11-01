"""Source-verified prompt extraction and one-pass RequestDraft resolution."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from apps.api.schemas import (
    IntakeConflict,
    IntakeExtractResponse,
    RequestDraft,
    SourceEvidence,
    UnsupportedRequest,
)
from apps.api.services.intake import validate_intake
from apps.api.services.runtime import Runtime
from src.fullpage.request_extract_contracts import (
    MAX_BRIEF_CHARS,
    validate_request_extract,
)


FACT_ORDER = ("name", "description", "value", "service", "process", "faq", "project")
SCALAR_IDS = {"name": "name", "description": "about", "value": "values"}
FACT_PREFIXES = {"service": "srv", "process": "step", "faq": "faq", "project": "project"}
FACT_FIELDS = {
    "name": "business_facts.name",
    "description": "business_facts.description",
    "value": "business_facts.value",
    "service": "business_facts.service",
    "process": "business_facts.process",
    "faq": "business_facts.faq",
    "project": "business_facts.project",
}
ACTIVE_INTENT = "requested"
INACTIVE_INTENTS = {"negated", "future", "reference", "retracted"}


class PromptExtractionBudgetError(ValueError):
    """The complete brief or its generated draft cannot fit a frozen context budget."""


class PromptExtractionFailure(RuntimeError):
    """Extraction was malformed, ungrounded, or unavailable and must fail closed."""


def canonicalize_messages(messages: list[dict[str, str]]) -> tuple[str, dict[str, dict[str, Any]]]:
    parts: list[str] = []
    segments: dict[str, dict[str, Any]] = {}
    cursor = 0
    for index, message in enumerate(messages):
        if index:
            parts.append("\n")
            cursor += 1
        text = message["text"]
        start = cursor
        parts.append(text)
        cursor += len(text)
        segments[message["id"]] = {
            "id": message["id"],
            "text": text,
            "index": index,
            "prompt_start": start,
            "prompt_end": cursor,
        }
    return "".join(parts), segments


def _utf16_offset(text: str, offset: int) -> int:
    return len(text[:offset].encode("utf-16-le")) // 2


def _source_evidence(
    field: str,
    segment: dict[str, Any],
    quote: str,
    start: int,
    end: int,
) -> dict[str, Any]:
    if start < 0 or end <= start or end > len(segment["text"]) or segment["text"][start:end] != quote:
        raise PromptExtractionFailure("Extracted source span does not match the original message")
    prompt_start = segment["prompt_start"] + start
    prompt_end = segment["prompt_start"] + end
    return {
        "field": field,
        "source_message_id": segment["id"],
        "quote": quote,
        "start": start,
        "end": end,
        "utf16_start": _utf16_offset(segment["text"], start),
        "utf16_end": _utf16_offset(segment["text"], end),
        "prompt_start": prompt_start,
        "prompt_end": prompt_end,
    }


def _occurrences(text: str, value: str) -> list[int]:
    if not value:
        return []
    offsets: list[int] = []
    start = 0
    while True:
        found = text.find(value, start)
        if found < 0:
            return offsets
        offsets.append(found)
        start = found + 1


def _exact_fact_evidence(
    segments: dict[str, dict[str, Any]],
    message_id: str,
    value: str,
    field: str,
) -> dict[str, Any]:
    segment = segments.get(message_id)
    if segment is None:
        raise PromptExtractionFailure("Extractor referenced an unknown source message")
    starts = _occurrences(segment["text"], value)
    if not starts:
        raise PromptExtractionFailure("Extracted fact is not an exact value in its cited source message")
    start = starts[0]
    return _source_evidence(field, segment, value, start, start + len(value))


def _validated_mentions(
    mentions: list[dict[str, Any]],
    segments: dict[str, dict[str, Any]],
    field_prefix: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for mention in mentions:
        segment = segments.get(mention["source_message_id"])
        if segment is None:
            raise PromptExtractionFailure("Extractor referenced an unknown source message")
        phrase = mention["phrase"]
        starts = _occurrences(segment["text"], phrase)
        occurrence = mention["occurrence_index"]
        if occurrence >= len(starts):
            raise PromptExtractionFailure("Mention phrase occurrence is absent from its cited message")
        start = starts[occurrence]
        end = start + len(phrase)
        context = mention["context"]
        context_starts = _occurrences(segment["text"], context)
        if not any(left <= start and end <= left + len(context) for left in context_starts):
            raise PromptExtractionFailure("Mention context does not contain its exact cited phrase")
        evidence = _source_evidence(
            f"{field_prefix}.{mention.get('kind', mention.get('capability_id', 'out_of_catalog'))}",
            segment,
            phrase,
            start,
            end,
        )
        output.append({**mention, "_evidence": evidence, "_source_index": segment["index"], "_start": start})
    return output


def _structured_value(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"title", "text"}


def _fact_candidates(
    mentions: list[dict[str, Any]],
    segments: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    counts: defaultdict[str, int] = defaultdict(int)
    order_counts: defaultdict[str, int] = defaultdict(int)
    for mention in mentions:
        kind = mention["kind"]
        if kind in {"name", "description", "value"}:
            value = mention["value"]
            evidence = _exact_fact_evidence(
                segments,
                mention["source_message_id"],
                value,
                FACT_FIELDS[kind],
            )
            candidate = {
                "kind": kind,
                "value": value,
                "evidence": [evidence],
                "source_ids": [mention["source_message_id"]],
                "source_index": segments[mention["source_message_id"]]["index"],
            }
        else:
            title = mention["title"]
            text = mention["text"]
            title_id = mention["title_source_message_id"]
            text_id = mention["text_source_message_id"]
            index = counts[kind]
            counts[kind] += 1
            value = {"title": title, "text": text}
            title_evidence = _exact_fact_evidence(
                segments,
                title_id,
                title,
                f"{FACT_FIELDS[kind]}.{index}.title",
            )
            text_evidence = _exact_fact_evidence(
                segments,
                text_id,
                text,
                f"{FACT_FIELDS[kind]}.{index}.text",
            )
            candidate = {
                "kind": kind,
                "value": value,
                "evidence": [title_evidence, text_evidence],
                "source_ids": [title_id, text_id],
                "source_index": min(segments[title_id]["index"], segments[text_id]["index"]),
            }
        candidate["order_index"] = order_counts[kind]
        order_counts[kind] += 1
        candidates.append(candidate)
    return candidates


def _same_value(left: Any, right: Any) -> bool:
    return json.dumps(left, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == json.dumps(
        right, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _prior_exact_value(
    value: Any,
    before_index: int,
    messages: list[dict[str, str]],
) -> bool:
    parts = [value] if isinstance(value, str) else [value.get("title"), value.get("text")] if _structured_value(value) else []
    if not parts:
        return False
    for part in parts:
        matches = [
            (index, position)
            for index, message in enumerate(messages[:before_index])
            for position in _occurrences(message["text"], part)
        ]
        if len(matches) != 1:
            return False
    return True


def _conflict(field: str, message: str, candidates: list[dict[str, Any]]) -> IntakeConflict:
    return IntakeConflict(field=field, message=message, candidates=candidates)


def _candidate_view(candidate: dict[str, Any]) -> dict[str, Any]:
    return {"value": candidate["value"], "evidence": candidate["evidence"]}


def _kind_field(kind: str) -> str:
    return FACT_FIELDS.get(kind, kind)


def _resolve_corrections(
    corrections: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    settings: list[dict[str, Any]],
    statuses: list[dict[str, Any]],
    messages: list[dict[str, str]],
    segments: dict[str, dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[IntakeConflict], list[str]]:
    ordered = sorted(
        corrections,
        key=lambda item: (segments[item["source_message_id"]]["index"], item["correction_phrase"]),
    )
    conflicts: list[IntakeConflict] = []
    missing: list[str] = []
    for correction in ordered:
        kind = correction["kind"]
        field = _kind_field(kind)
        message_id = correction["source_message_id"]
        segment = segments.get(message_id)
        if segment is None:
            raise PromptExtractionFailure("Correction referenced an unknown source message")
        phrase = correction["correction_phrase"]
        phrase_spans = _occurrences(segment["text"], phrase)
        if len(phrase_spans) != 1:
            raise PromptExtractionFailure("Correction phrase is not uniquely grounded in its cited message")
        evidence.append(
            _source_evidence(f"corrections.{kind}", segment, phrase, phrase_spans[0], phrase_spans[0] + len(phrase))
        )
        previous = correction["previous_value"]
        replacement = correction["replacement_value"]
        before_index = segment["index"]

        if kind in FACT_FIELDS:
            previous_grounded = _prior_exact_value(previous, before_index, messages)
            if isinstance(replacement, str):
                replacement_evidence = _exact_fact_evidence(
                    segments, message_id, replacement, field
                )
                replacement_candidate = {
                    "kind": kind,
                    "value": replacement,
                    "evidence": [replacement_evidence],
                    "source_ids": [message_id],
                    "source_index": before_index,
                }
            elif _structured_value(replacement):
                replacement_evidence = [
                    _exact_fact_evidence(segments, message_id, replacement["title"], f"{field}.title"),
                    _exact_fact_evidence(segments, message_id, replacement["text"], f"{field}.text"),
                ]
                replacement_candidate = {
                    "kind": kind,
                    "value": replacement,
                    "evidence": replacement_evidence,
                    "source_ids": [message_id, message_id],
                    "source_index": before_index,
                }
            else:
                previous_grounded = False
                replacement_candidate = None

            matching = [index for index, item in enumerate(facts) if item["kind"] == kind and _same_value(item["value"], previous)]
            if not previous_grounded or replacement_candidate is None or len(matching) > 1:
                conflicts.append(_conflict(field, "Koreksi perlu dikonfirmasi karena nilai asalnya ambigu.", [
                    {"value": previous}, {"value": replacement}
                ]))
                missing.append(field)
                continue
            if matching:
                original = facts[matching[0]]
                replacement_candidate["order_index"] = original.get("order_index", matching[0])
                replacement_candidate["source_index"] = original.get("source_index", replacement_candidate["source_index"])
                facts[matching[0]] = replacement_candidate
            else:
                replacement_matches = [
                    index for index, item in enumerate(facts)
                    if item["kind"] == kind and _same_value(item["value"], replacement)
                ]
                if kind in {"name", "description", "value"} and not replacement_matches:
                    facts.append(replacement_candidate)
                elif len(replacement_matches) != 1:
                    conflicts.append(_conflict(field, "Posisi fakta yang dikoreksi belum dapat dipastikan.", [
                        {"value": previous}, {"value": replacement}
                    ]))
                    missing.append(field)
                    continue
            evidence.extend(replacement_candidate["evidence"])
            continue

        if kind in {"genre", "style_mode"}:
            source_items = settings
            matching_previous = [
                item for item in source_items
                if item["kind"] == kind and item["value"] == previous and item["_source_index"] < before_index
            ]
            replacement_items = [
                item for item in source_items
                if item["kind"] == kind and item["value"] == replacement
                and item["_source_index"] == before_index and item["intent"] == ACTIVE_INTENT
            ]
            grounded = len(matching_previous) == 1 and len(replacement_items) == 1
            if grounded:
                settings[:] = [
                    item for item in settings
                    if not (item["kind"] == kind and item["value"] == previous and item["_source_index"] < before_index)
                ]
            else:
                conflicts.append(_conflict(kind, "Koreksi jenis halaman atau gaya perlu dikonfirmasi.", [
                    {"value": previous}, {"value": replacement}
                ]))
                missing.append(kind)
            continue

        if kind == "fictitious":
            matching_previous = [
                item for item in statuses
                if item["value"] is previous and item["_source_index"] < before_index
                and item["intent"] == ACTIVE_INTENT
            ]
            replacement_items = [
                item for item in statuses
                if item["value"] is replacement and item["_source_index"] == before_index
                and item["intent"] == ACTIVE_INTENT
            ]
            if len(matching_previous) == 1 and len(replacement_items) == 1:
                statuses[:] = [
                    item for item in statuses
                    if not (item["value"] is previous and item["_source_index"] < before_index)
                ]
            else:
                conflicts.append(_conflict("fictitious", "Koreksi status usaha perlu dikonfirmasi.", [
                    {"value": previous}, {"value": replacement}
                ]))
                missing.append("fictitious")
    return facts, settings, statuses, conflicts, missing


def _resolve_one(
    kind: str,
    candidates: list[dict[str, Any]],
    field: str,
    conflicts: list[IntakeConflict],
) -> dict[str, Any] | None:
    unique: list[dict[str, Any]] = []
    for candidate in candidates:
        if not any(_same_value(candidate["value"], item["value"]) for item in unique):
            unique.append(candidate)
    if len(unique) > 1:
        conflicts.append(_conflict(field, "Ada beberapa nilai berbeda. Konfirmasi satu nilai sebelum melanjutkan.", [
            _candidate_view(item) for item in unique
        ]))
        return None
    return unique[0] if unique else None


def _draft_fact(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    kind = candidate["kind"]
    if kind in SCALAR_IDS:
        evidence = candidate["evidence"][0]
        return {
            "id": SCALAR_IDS[kind],
            "kind": kind,
            "value": candidate["value"],
            "evidence": {"source_span": {"start": evidence["prompt_start"], "end": evidence["prompt_end"]}},
        }
    prefix = FACT_PREFIXES[kind]
    title_evidence, text_evidence = candidate["evidence"]
    title_evidence["field"] = f"{FACT_FIELDS[kind]}.{index}.title"
    text_evidence["field"] = f"{FACT_FIELDS[kind]}.{index}.text"
    return {
        "id": f"{prefix}{index}",
        "kind": kind,
        "value": {
            "title": candidate["value"]["title"],
            "title_evidence": {"source_span": {"start": title_evidence["prompt_start"], "end": title_evidence["prompt_end"]}},
            "text": candidate["value"]["text"],
            "text_evidence": {"source_span": {"start": text_evidence["prompt_start"], "end": text_evidence["prompt_end"]}},
        },
    }


def _catalog_occurrences(
    prompt: str,
    segments: dict[str, dict[str, Any]],
    capability_by_id: dict[str, dict[str, Any]],
    assessments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for capability_id, item in capability_by_id.items():
        for phrase in item["evidence_phrases"]:
            pattern = r"(?<!\w)" + re.escape(phrase.strip()) + r"(?!\w)"
            for match in re.finditer(pattern, prompt, flags=re.IGNORECASE):
                key = (capability_id, match.start(), match.end())
                if key in seen:
                    continue
                seen.add(key)
                assessed = any(
                    entry["capability_id"] == capability_id
                    and entry["start"] == match.start()
                    and entry["end"] == match.end()
                    and entry["phrase"].casefold() == prompt[match.start():match.end()].casefold()
                    for entry in assessments
                )
                if assessed:
                    continue
                segment = next(
                    (
                        candidate for candidate in segments.values()
                        if candidate["prompt_start"] <= match.start()
                        and match.end() <= candidate["prompt_end"]
                    ),
                    None,
                )
                if segment is None:
                    continue
                local_start = match.start() - segment["prompt_start"]
                evidence = _source_evidence(
                    f"capability.{capability_id}",
                    segment,
                    segment["text"][local_start:local_start + (match.end() - match.start())],
                    local_start,
                    local_start + (match.end() - match.start()),
                )
                result.append({
                    "kind": "known_capability",
                    "id": capability_id,
                    "label": item["label"],
                    "phrase": evidence["quote"],
                    "context": evidence["quote"],
                    "intent": "unclear",
                    "evidence": evidence,
                })
    return result


def build_extraction_response(
    messages: list[dict[str, str]],
    extracted: dict[str, Any],
    runtime: Runtime,
) -> IntakeExtractResponse:
    errors = validate_request_extract(extracted)
    if errors:
        raise PromptExtractionFailure("Extractor output failed the frozen JSON contract")

    prompt, segments = canonicalize_messages(messages)
    evidence: list[dict[str, Any]] = []
    fact_candidates = _fact_candidates(extracted["fact_mentions"], segments)
    for candidate in fact_candidates:
        evidence.extend(candidate["evidence"])

    settings = _validated_mentions(extracted["setting_mentions"], segments, "settings")
    statuses = _validated_mentions(extracted["business_status_mentions"], segments, "business_status")
    capabilities = _validated_mentions(extracted["capability_mentions"], segments, "capabilities")
    out_of_catalog = _validated_mentions(extracted["out_of_catalog_mentions"], segments, "out_of_catalog")
    for group in (settings, statuses, capabilities, out_of_catalog):
        evidence.extend(item["_evidence"] for item in group)

    settings = [item for item in settings if item["intent"] == ACTIVE_INTENT or item["intent"] == "unclear"]
    statuses = [item for item in statuses if item["intent"] == ACTIVE_INTENT or item["intent"] == "unclear"]
    facts, settings, statuses, correction_conflicts, correction_missing = _resolve_corrections(
        extracted["corrections"],
        fact_candidates,
        settings,
        statuses,
        messages,
        segments,
        evidence,
    )

    conflicts = list(correction_conflicts)
    resolved_scalars: dict[str, dict[str, Any] | None] = {}
    for kind in ("name", "description", "value"):
        resolved_scalars[kind] = _resolve_one(
            kind,
            [item for item in facts if item["kind"] == kind],
            FACT_FIELDS[kind],
            conflicts,
        )

    for kind in ("service", "process", "faq", "project"):
        unique_items: list[dict[str, Any]] = []
        for item in facts:
            if item["kind"] != kind:
                continue
            if not any(_same_value(item["value"], previous["value"]) for previous in unique_items):
                unique_items.append(item)
        facts[:] = [item for item in facts if item["kind"] != kind] + unique_items

    selected_settings: dict[str, Any | None] = {"genre": None, "style_mode": None}
    for kind in ("genre", "style_mode"):
        current = [item for item in settings if item["kind"] == kind and item["intent"] == ACTIVE_INTENT]
        distinct_values = list(dict.fromkeys(item["value"] for item in current))
        if len(distinct_values) > 1:
            conflicts.append(_conflict(kind, "Ada beberapa pilihan yang berbeda. Konfirmasi satu pilihan.", [
                {"value": value, "evidence": [item["_evidence"] for item in current if item["value"] == value]}
                for value in distinct_values
            ]))
        elif distinct_values:
            selected_settings[kind] = distinct_values[0]

    unclear_capabilities = [item for item in capabilities if item["intent"] == "unclear"]
    active_unsupported: list[UnsupportedRequest] = []
    capability_assessments: list[dict[str, Any]] = []
    catalog = runtime.get_intake_catalog()["capabilities"]
    capability_by_id = {item["id"]: item for item in catalog["unsupported_capabilities"]}
    for mention in capabilities:
        capability_id = mention["capability_id"]
        item = capability_by_id.get(capability_id)
        if item is None:
            raise PromptExtractionFailure("Extractor returned a capability outside the trusted catalog")
        source = mention["_evidence"]
        capability_assessments.append({
            "capability_id": capability_id,
            "phrase": mention["phrase"],
            "start": source["prompt_start"],
            "end": source["prompt_end"],
            "intent": mention["intent"],
        })
        if mention["intent"] == ACTIVE_INTENT:
            active_unsupported.append(UnsupportedRequest(
                kind="known_capability",
                id=capability_id,
                label=item["label"],
                phrase=mention["phrase"],
                context=mention["context"],
                intent=mention["intent"],
                evidence=SourceEvidence.model_validate(source),
            ))

    for mention in out_of_catalog:
        if mention["intent"] == ACTIVE_INTENT:
            active_unsupported.append(UnsupportedRequest(
                kind="out_of_catalog",
                id=None,
                label="Permintaan di luar katalog",
                phrase=mention["phrase"],
                context=mention["context"],
                intent=mention["intent"],
                evidence=SourceEvidence.model_validate(mention["_evidence"]),
            ))

    unresolved_catalog = _catalog_occurrences(prompt, segments, capability_by_id, capability_assessments)
    known_unclear = [
        UnsupportedRequest.model_validate(item)
        for item in [
            {
                "kind": mention["kind"], "id": mention["id"], "label": mention["label"],
                "phrase": mention["phrase"], "context": mention["context"], "intent": mention["intent"],
                "evidence": mention["evidence"],
            }
            for mention in unresolved_catalog
        ]
    ]
    evidence.extend(item["evidence"] for item in known_unclear)

    unresolved_out_of_catalog = [item for item in out_of_catalog if item["intent"] == "unclear"]
    for mention in unresolved_out_of_catalog:
        unclear_capabilities.append(mention)

    business_status_values = list(dict.fromkeys(
        item["value"] for item in statuses if item["intent"] == ACTIVE_INTENT
    ))
    selected_fictitious: bool | None = None
    if len(business_status_values) > 1:
        conflicts.append(_conflict("fictitious", "Status usaha memiliki beberapa nilai yang bertentangan.", [
            {"value": value, "evidence": [item["_evidence"] for item in statuses if item["value"] is value]}
            for value in business_status_values
        ]))
    elif business_status_values:
        selected_fictitious = business_status_values[0]

    selected_facts = [
        resolved_scalars[kind]
        for kind in ("name", "description", "value")
        if resolved_scalars[kind] is not None
    ]
    selected_facts.extend(item for item in facts if item["kind"] in {"service", "process", "faq", "project"})
    selected_facts.sort(key=lambda item: (FACT_ORDER.index(item["kind"]), item.get("order_index", 0)))
    per_kind_indices: defaultdict[str, int] = defaultdict(int)
    draft_facts = []
    for candidate in selected_facts:
        index = per_kind_indices[candidate["kind"]]
        per_kind_indices[candidate["kind"]] += 1
        draft_facts.append(_draft_fact(candidate, index))

    asset_id = {
        "landing_page": "studio-shapes",
        "company_profile": "company-shapes",
    }.get(selected_settings["genre"])
    partial = {
        "contract_version": "request-draft-source-bound-v1",
        "prompt": prompt,
        "genre": selected_settings["genre"],
        "style_mode": selected_settings["style_mode"],
        "business_facts": draft_facts,
        "requested_features": [],
        "asset_ids": [asset_id] if asset_id else [],
        "fictitious": selected_fictitious,
    }
    draft = RequestDraft.model_validate(partial)

    missing: list[str] = list(correction_missing)
    if any(item["intent"] == "unclear" for item in settings):
        missing.extend(item["kind"] for item in settings if item["intent"] == "unclear")
    if any(item["intent"] == "unclear" for item in statuses):
        missing.append("fictitious")
    if unclear_capabilities or known_unclear:
        missing.append("requested_features")

    if active_unsupported:
        return IntakeExtractResponse(
            status="unsupported",
            message="Brief meminta fitur yang belum tersedia dalam versi ini. Hapus atau ganti permintaan tersebut sebelum membuat halaman.",
            missing_fields=list(dict.fromkeys(missing)),
            draft=draft,
            evidence=[SourceEvidence.model_validate(item) for item in evidence],
            conflicts=conflicts,
            unsupported_requests=active_unsupported,
        )

    if unresolved_catalog or unclear_capabilities:
        all_unsupported = [*known_unclear]
        for mention in unresolved_out_of_catalog:
            all_unsupported.append(UnsupportedRequest(
                kind="out_of_catalog",
                id=None,
                label="Permintaan yang perlu diklarifikasi",
                phrase=mention["phrase"],
                context=mention["context"],
                intent="unclear",
                evidence=SourceEvidence.model_validate(mention["_evidence"]),
            ))
        return IntakeExtractResponse(
            status="needs_clarification",
            message="Saya menemukan fitur yang perlu Anda konfirmasi. Jelaskan apakah fitur itu memang diminta untuk versi halaman ini.",
            missing_fields=list(dict.fromkeys([*missing, "requested_features"])),
            draft=draft,
            evidence=[SourceEvidence.model_validate(item) for item in evidence],
            conflicts=conflicts,
            unsupported_requests=all_unsupported,
        )

    if selected_settings["genre"] is None:
        missing.extend(["genre", "style_mode"] if selected_settings["style_mode"] is None else ["genre"])
        for kind in ("name", "description", "value"):
            if resolved_scalars[kind] is None:
                missing.append(FACT_FIELDS[kind])
        fact_counts = defaultdict(int)
        for item in facts:
            fact_counts[item["kind"]] += 1
        for kind, required in (("service", 3), ("process", 3), ("faq", 3), ("project", 2)):
            if fact_counts[kind] < required:
                missing.append(FACT_FIELDS[kind])
        if selected_fictitious is None:
            missing.append("fictitious")
        return IntakeExtractResponse(
            status="needs_clarification",
            message="Pilih jenis halaman dan gaya CSS, lalu lengkapi fakta yang ditandai. Untuk landing page, sertakan 3 FAQ; untuk company profile, sertakan 2 proyek atau karya.",
            missing_fields=list(dict.fromkeys(missing)),
            draft=draft,
            evidence=[SourceEvidence.model_validate(item) for item in evidence],
            conflicts=conflicts,
        )

    prepared = validate_intake(
        prompt,
        draft.model_dump(exclude_none=True),
        runtime=runtime,
        capability_assessments=capability_assessments,
    )
    if prepared.status == "input_too_long":
        raise PromptExtractionBudgetError("Resolved request exceeds the selected generator context budget")

    missing = list(dict.fromkeys([*missing, *prepared.missing_fields]))
    if conflicts:
        missing = list(dict.fromkeys(missing))
    if prepared.status == "unsupported_request":
        return IntakeExtractResponse(
            status="unsupported",
            message=prepared.message,
            missing_fields=missing,
            draft=draft,
            evidence=[SourceEvidence.model_validate(item) for item in evidence],
            conflicts=conflicts,
            unsupported_requests=[],
        )
    if prepared.status != "ready" or missing or conflicts:
        message = prepared.message
        if conflicts:
            message = "Ada beberapa nilai atau koreksi yang belum pasti. Konfirmasi semuanya dalam satu balasan sebelum membuat halaman."
        return IntakeExtractResponse(
            status="needs_clarification",
            message=message,
            missing_fields=missing,
            draft=draft,
            evidence=[SourceEvidence.model_validate(item) for item in evidence],
            conflicts=conflicts,
        )

    token = runtime.issue_intake_token(prompt, capability_assessments)
    return IntakeExtractResponse(
        status="ready",
        message="Brief sudah siap ditinjau. Periksa fakta dan sumbernya sebelum meminta pembuatan halaman.",
        draft=draft,
        evidence=[SourceEvidence.model_validate(item) for item in evidence],
        resolution_token=token,
    )


def extract_prompt_messages(
    messages: list[dict[str, str]],
    runtime: Runtime,
) -> IntakeExtractResponse:
    prompt, _ = canonicalize_messages(messages)
    if len(prompt) > MAX_BRIEF_CHARS:
        raise PromptExtractionBudgetError(f"Brief exceeds the {MAX_BRIEF_CHARS}-character limit")
    runtime.ensure_project_importable()

    from src.fullpage.request_extract_contracts import EXTRACTION_SCOPES, extractor_prompt
    from src.fullpage.serialization import check_budget

    tokenizer = runtime.get_tokenizer()
    config_path = runtime.project_root / "configs/fullpage/training-request-extract-v1-r1.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    budgets = config["generation_contract"]["output_budgets"]
    try:
        for scope in EXTRACTION_SCOPES:
            check_budget(
                tokenizer,
                extractor_prompt(messages, scope),
                budgets[scope],
                block_size=config["block_size"],
            )
    except (KeyError, TypeError, ValueError) as error:
        raise PromptExtractionBudgetError("Brief exceeds a frozen extractor scope budget") from error

    try:
        from src.fullpage.request_extract_model import RequestExtractionBudgetError, RequestExtractionError

        extractor = runtime.get_extractor()
        extracted = extractor.extract(messages)
    except RequestExtractionBudgetError as error:
        raise PromptExtractionBudgetError("Brief exceeds a frozen extractor context budget") from error
    except (RequestExtractionError, FileNotFoundError, OSError, ValueError) as error:
        raise PromptExtractionFailure("Selected extractor is unavailable or returned an invalid result") from error
    return build_extraction_response(messages, extracted, runtime)
