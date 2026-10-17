"""Evidence-first request preparation and safe generation status mapping."""

from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from .assets import load_asset_catalog
from .contracts import validate_request
from .serialization import OUTPUT_BUDGETS, canonical, check_budget
from .source_bound_prompts import source_bound_plan_prompt

ROOT = Path(__file__).resolve().parents[2]
DRAFT_SCHEMA_PATH = ROOT / "configs/fullpage/request-draft-source-bound-v1.schema.json"
MAX_PROMPT_CHARS = 4000
CONTRACT_VERSION = "request-draft-source-bound-v1"
_DRAFT_SCHEMA = json.loads(DRAFT_SCHEMA_PATH.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(_DRAFT_SCHEMA)
_DRAFT_VALIDATOR = Draft202012Validator(_DRAFT_SCHEMA)

_SCALAR_KINDS = {"name", "description", "value"}
_STRUCTURED_KINDS = {"service", "project", "process", "faq"}
_FACT_KIND_ORDER = ("name", "description", "value", "service", "process", "faq", "project")
_FACT_IDS = {"name": "name", "description": "about", "value": "values"}
_FACT_ID_PREFIXES = {"service": "srv", "process": "step", "faq": "faq", "project": "project"}
_FACT_FIELD_NAMES = {
    "name": "business_facts.name",
    "description": "business_facts.description",
    "value": "business_facts.value",
    "service": "business_facts.service",
    "process": "business_facts.process",
    "faq": "business_facts.faq",
    "project": "business_facts.project",
}
_REQUIRED_FACT_COUNTS = {
    "landing_page": {"name": 1, "description": 1, "value": 1, "service": 3, "process": 3, "faq": 3},
    "company_profile": {"name": 1, "description": 1, "value": 1, "service": 3, "process": 3, "project": 2},
}
_GENRE_ASSETS = {"landing_page": "studio-shapes", "company_profile": "company-shapes"}
_FIELD_LABELS = {
    "genre": "jenis halaman",
    "style_mode": "gaya CSS",
    "business_facts.name": "nama usaha",
    "business_facts.description": "deskripsi usaha",
    "business_facts.value": "nilai atau keunggulan usaha",
    "business_facts.service": "3 layanan usaha",
    "business_facts.process": "3 langkah proses usaha",
    "business_facts.faq": "3 pertanyaan dan jawaban untuk FAQ",
    "business_facts.project": "2 proyek atau karya untuk portofolio",
    "business_facts": "fakta usaha",
    "business_facts.ids": "ID fakta usaha yang berbeda",
    "requested_features": "kemampuan yang diminta",
    "asset_ids": "ilustrasi lokal sesuai jenis halaman",
    "fictitious": "status contoh atau usaha nyata",
    "prompt": "prompt asli",
    "request_draft": "format data request",
}


@dataclass(frozen=True)
class IntakeResult:
    status: str
    message: str
    missing_fields: tuple[str, ...] = ()
    request: dict | None = None


def load_intake_catalog(root=None) -> dict:
    """Load the fixed capability list and trusted local assets for intake."""
    root = Path(root or ROOT)
    assets = load_asset_catalog(root).get("assets")
    capabilities = json.loads((root / "configs/fullpage/capability-catalog-v1.json").read_text(encoding="utf-8"))
    if not isinstance(assets, dict) or not isinstance(capabilities, dict):
        raise ValueError("Invalid local intake catalog")
    if capabilities.get("contract_version") != "capability-catalog-v1":
        raise ValueError("Unsupported capability catalog version")
    if not isinstance(capabilities.get("unsupported_capabilities"), list):
        raise ValueError("Capability catalog has no unsupported-capability list")
    return {"assets": assets, "capabilities": capabilities}


def _catalog_parts(request_catalog):
    if not isinstance(request_catalog, dict) or not isinstance(request_catalog.get("assets"), dict):
        raise ValueError("Request catalog requires trusted asset metadata")
    capability_document = request_catalog.get("capabilities")
    if not isinstance(capability_document, dict):
        raise ValueError("Request catalog requires the versioned capability catalog")
    if capability_document.get("contract_version") != "capability-catalog-v1":
        raise ValueError("Unsupported capability catalog version")
    genres = capability_document.get("supported_genres")
    styles = capability_document.get("supported_style_modes")
    unsupported = capability_document.get("unsupported_capabilities")
    if not all(isinstance(value, list) for value in (genres, styles, unsupported)):
        raise ValueError("Malformed capability catalog")
    if any(not isinstance(value, str) or not value for value in genres + styles):
        raise ValueError("Malformed supported genre or style entry")
    by_id = {}
    for item in unsupported:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("Malformed unsupported capability entry")
        phrases = item.get("evidence_phrases")
        if (
            item["id"] in by_id
            or not isinstance(item.get("label"), str)
            or not isinstance(phrases, list)
            or not phrases
            or any(not isinstance(phrase, str) or not phrase for phrase in phrases)
        ):
            raise ValueError("Duplicate or malformed unsupported capability entry")
        by_id[item["id"]] = item
    return request_catalog["assets"], capability_document, by_id


def _clean_fact(fact):
    if not isinstance(fact, dict):
        return None
    identifier, kind, value = fact.get("id"), fact.get("kind"), fact.get("value")
    if kind in _SCALAR_KINDS:
        clean_value = value
    elif kind in _STRUCTURED_KINDS and isinstance(value, dict):
        clean_value = {key: value[key] for key in ("title", "text") if key in value}
    else:
        return None
    return {"id": identifier, "kind": kind, "value": clean_value}


def _request_candidate(prompt, draft):
    source = draft if isinstance(draft, dict) else {}
    raw_facts = source.get("business_facts", [])
    facts = []
    kind_counts = {}
    for raw_fact in raw_facts if isinstance(raw_facts, list) else []:
        fact = _clean_fact(raw_fact)
        if fact is None:
            continue
        kind = fact["kind"]
        if kind in _FACT_IDS:
            fact["id"] = _FACT_IDS[kind]
        else:
            index = kind_counts.get(kind, 0)
            fact["id"] = f"{_FACT_ID_PREFIXES[kind]}{index}"
            kind_counts[kind] = index + 1
        facts.append(fact)
    facts.sort(key=lambda fact: _FACT_KIND_ORDER.index(fact["kind"]))
    candidate = {
        "request_id": "intake-pending",
        "prompt": prompt,
        "genre": source.get("genre"),
        "style_mode": source.get("style_mode"),
        "business_facts": facts,
        "asset_ids": source.get("asset_ids", []),
        "fictitious": source.get("fictitious"),
    }
    identity = {key: value for key, value in candidate.items() if key != "request_id"}
    digest = hashlib.sha256(canonical(identity).encode("utf-8")).hexdigest()[:24]
    candidate["request_id"] = "intake-" + digest
    return candidate


def _ordered_unique(values):
    return tuple(dict.fromkeys(value for value in values if isinstance(value, str) and value))


def _source_span_matches(evidence, value, prompt):
    if not isinstance(evidence, dict) or set(evidence) != {"source_span"}:
        return False
    span = evidence.get("source_span")
    if not isinstance(span, dict) or set(span) != {"start", "end"}:
        return False
    start, end = span.get("start"), span.get("end")
    if type(start) is not int or type(end) is not int or start < 0 or end <= start or end > len(prompt):
        return False
    return isinstance(value, str) and prompt[start:end] == value


def _fact_evidence_matches(evidence, value, prompt):
    return evidence == {"user_confirmed": True} or _source_span_matches(evidence, value, prompt)


def _capability_evidence_matches(evidence, item, prompt):
    if evidence == {"user_confirmed": True}:
        return True
    if not isinstance(evidence, dict) or set(evidence) != {"source_span"}:
        return False
    span = evidence.get("source_span")
    if not isinstance(span, dict) or set(span) != {"start", "end", "quote"}:
        return False
    start, end, quote = span.get("start"), span.get("end"), span.get("quote")
    if type(start) is not int or type(end) is not int or start < 0 or end <= start or end > len(prompt):
        return False
    if not isinstance(quote, str) or prompt[start:end] != quote:
        return False
    phrases = item.get("evidence_phrases", [])
    return any(isinstance(phrase, str) and quote.casefold() == phrase.casefold() for phrase in phrases)


def _prompt_mentions_value(prompt, value):
    if not isinstance(value, str) or not value.strip():
        return False
    pattern = r"(?<!\w)" + re.escape(value.strip()) + r"(?!\w)"
    return re.search(pattern, prompt, flags=re.IGNORECASE) is not None


def _prompt_capability_occurrences(prompt, item):
    """Find catalog phrases with exact spans for conservative mention handling."""
    for phrase in item.get("evidence_phrases", []):
        if not isinstance(phrase, str) or not phrase.strip():
            continue
        pattern = r"(?<!\w)" + re.escape(phrase.strip()) + r"(?!\w)"
        for match in re.finditer(pattern, prompt, flags=re.IGNORECASE):
            yield phrase, match.start(), match.end()


def _prompt_mentions_capability(prompt, item, capability_id, assessments=None):
    """Keep unclassified catalog mentions fail-closed, while honoring verified inactive spans."""
    inactive_intents = {"retracted", "negated", "future", "reference", "unclear"}
    for phrase, start, end in _prompt_capability_occurrences(prompt, item):
        suppressed = any(
            isinstance(assessment, dict)
            and assessment.get("capability_id") == capability_id
            and assessment.get("start") == start
            and assessment.get("end") == end
            and isinstance(assessment.get("phrase"), str)
            and assessment.get("phrase", "").casefold() == phrase.casefold()
            and assessment.get("intent") in inactive_intents
            for assessment in assessments or []
        )
        if not suppressed:
            return True
    return False


def _requested_capabilities(draft, prompt, by_id, capability_assessments=None):
    unsupported = []
    missing = []
    features = draft.get("requested_features") if isinstance(draft, dict) else None
    if not isinstance(features, list):
        return unsupported, ["requested_features"]
    seen = set()
    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            missing.append(f"requested_features.{index}")
            continue
        capability_id = feature.get("capability_id")
        if not isinstance(capability_id, str) or not capability_id:
            missing.append(f"requested_features.{index}.capability_id")
            continue
        if capability_id in seen:
            missing.append("requested_features")
        seen.add(capability_id)
        item = by_id.get(capability_id)
        if item is None:
            missing.append(f"requested_features.{capability_id}")
        elif _capability_evidence_matches(feature.get("evidence"), item, prompt):
            unsupported.append(item)
        else:
            missing.append(f"requested_features.{capability_id}.evidence")
    for capability_id, item in by_id.items():
        if capability_id not in seen and _prompt_mentions_capability(
            prompt, item, capability_id, capability_assessments
        ):
            unsupported.append(item)
    return unsupported, missing


def _fact_missing_fields(draft, prompt, assets):
    missing = []
    facts = draft.get("business_facts") if isinstance(draft, dict) else None
    if not isinstance(facts, list):
        return ["business_facts", "business_facts.name", "business_facts.description", "business_facts.service"]
    if not 3 <= len(facts) <= 24:
        missing.append("business_facts")

    counts = {kind: 0 for kind in _FACT_FIELD_NAMES}
    identifiers = []
    for index, fact in enumerate(facts):
        if not isinstance(fact, dict):
            missing.append(f"business_facts.{index}")
            continue
        identifier, kind, value = fact.get("id"), fact.get("kind"), fact.get("value")
        if isinstance(identifier, str) and identifier:
            identifiers.append(identifier)
        if kind in counts:
            counts[kind] += 1
        if kind in _SCALAR_KINDS:
            if not isinstance(value, str) or not value.strip():
                missing.append(f"business_facts.{identifier or index}.value")
            elif not _fact_evidence_matches(fact.get("evidence"), value, prompt):
                missing.append(f"business_facts.{identifier or index}.evidence")
        elif kind in _STRUCTURED_KINDS:
            if not isinstance(value, dict):
                missing.append(f"business_facts.{identifier or index}.value")
                continue
            for key in ("title", "text"):
                field_value = value.get(key)
                evidence_key = key + "_evidence"
                if not isinstance(field_value, str) or not field_value.strip():
                    missing.append(f"business_facts.{identifier or index}.value.{key}")
                elif not _fact_evidence_matches(value.get(evidence_key), field_value, prompt):
                    missing.append(f"business_facts.{identifier or index}.value.{evidence_key}")
        else:
            missing.append(f"business_facts.{identifier or index}.kind")

    if len(identifiers) != len(set(identifiers)):
        missing.append("business_facts.ids")
    required_counts = _REQUIRED_FACT_COUNTS.get(draft.get("genre"), {})
    for kind, minimum in required_counts.items():
        invalid_count = counts[kind] != minimum if kind in _FACT_IDS else counts[kind] < minimum
        if invalid_count:
            missing.append(_FACT_FIELD_NAMES[kind])

    asset_ids = draft.get("asset_ids")
    expected_asset = _GENRE_ASSETS.get(draft.get("genre"))
    if not isinstance(asset_ids, list) or any(not isinstance(identifier, str) for identifier in asset_ids):
        missing.append("asset_ids")
    elif len(set(asset_ids)) != len(asset_ids) or any(identifier not in assets for identifier in asset_ids):
        missing.append("asset_ids")
    elif expected_asset and expected_asset not in asset_ids:
        missing.append("asset_ids")
    return missing


def _schema_is_valid(draft):
    try:
        return not any(_DRAFT_VALIDATOR.iter_errors(draft))
    except (TypeError, ValueError):
        return False


def _clarification(fields):
    fields = _ordered_unique(fields) or ("request_draft",)
    labels = [_FIELD_LABELS.get(field, field.replace("_", " ").replace(".", " ")) for field in fields]
    message = "Saya belum bisa menyiapkan halaman. Lengkapi atau konfirmasi: " + ", ".join(labels) + ". Tidak ada halaman atau berkas yang dibuat saat intake."
    return IntakeResult("needs_clarification", message, fields, None)


def _unsupported(message):
    return IntakeResult("unsupported_request", message, (), None)


def prepare_intake(
    prompt: str,
    draft: dict,
    tokenizer,
    request_catalog: dict,
    *,
    capability_assessments: list[dict] | None = None,
) -> IntakeResult:
    """Validate one user-provided RequestDraft without extracting facts from prose."""
    if not isinstance(prompt, str) or not prompt.strip():
        return _clarification(["prompt"])
    if len(prompt) > MAX_PROMPT_CHARS:
        return IntakeResult(
            "input_too_long",
            "Prompt melebihi 4.000 karakter. Ringkas prompt secara manual; sistem tidak memotong teks.",
            (),
            None,
        )

    assets, capabilities, capability_by_id = _catalog_parts(request_catalog)
    try:
        candidate = _request_candidate(prompt, draft)
        task_prompt = source_bound_plan_prompt(candidate)
        check_budget(tokenizer, task_prompt, OUTPUT_BUDGETS["page_plan"])
    except ValueError as error:
        if str(error).startswith("Budget overflow:"):
            return IntakeResult(
                "input_too_long",
                "Request dan rancangan melebihi budget konteks halaman. Ringkas fakta secara manual; sistem tidak memotong teks.",
                (),
                None,
            )
        return _clarification(["prompt"])
    except (TypeError, KeyError, AttributeError):
        return _clarification(["request_draft"])

    if not isinstance(draft, dict):
        return _clarification(["request_draft"])

    unsupported_capabilities, capability_missing = _requested_capabilities(
        draft, prompt, capability_by_id, capability_assessments
    )
    genre, style = draft.get("genre"), draft.get("style_mode")
    unsupported_genre = (
        isinstance(genre, str)
        and bool(genre.strip())
        and genre not in capabilities["supported_genres"]
        and _prompt_mentions_value(prompt, genre)
    )
    unsupported_style = (
        isinstance(style, str)
        and bool(style.strip())
        and style not in capabilities["supported_style_modes"]
        and _prompt_mentions_value(prompt, style)
    )
    if unsupported_capabilities or unsupported_genre or unsupported_style:
        descriptions = [item.get("label", item["id"]) for item in unsupported_capabilities]
        if unsupported_genre or unsupported_style:
            descriptions.append("jenis halaman atau gaya implementasi yang belum didukung")
        scope = capabilities.get("scope_message", "Saat ini hanya jenis halaman dan gaya dari katalog lokal yang didukung.")
        return _unsupported("Permintaan ini berada di luar cakupan karena membutuhkan: " + ", ".join(descriptions) + ". " + scope)

    missing = list(capability_missing)
    if draft.get("prompt") != prompt:
        missing.append("prompt")
    if draft.get("contract_version") != CONTRACT_VERSION:
        missing.append("request_draft")
    if not isinstance(genre, str) or not genre.strip():
        missing.append("genre")
    if not isinstance(style, str) or not style.strip():
        missing.append("style_mode")
    missing.extend(_fact_missing_fields(draft, prompt, assets))
    if not isinstance(draft.get("fictitious"), bool):
        missing.append("fictitious")
    if not _schema_is_valid(draft):
        missing.append("request_draft")
    if missing:
        return _clarification(missing)

    if genre not in capabilities["supported_genres"] or style not in capabilities["supported_style_modes"]:
        unsupported_fields = []
        if genre not in capabilities["supported_genres"]:
            unsupported_fields.append("genre")
        if style not in capabilities["supported_style_modes"]:
            unsupported_fields.append("style_mode")
        return _clarification(unsupported_fields)

    request = candidate
    request_errors = validate_request(request, request_catalog)
    if request_errors:
        request_fields = []
        for error in request_errors:
            if "name required" in error:
                request_fields.append("business_facts.name")
            elif "description required" in error:
                request_fields.append("business_facts.description")
            elif "service required" in error:
                request_fields.append("business_facts.service")
            elif "asset" in error.lower():
                request_fields.append("asset_ids")
            else:
                request_fields.append("request_draft")
        return _clarification(request_fields)

    return IntakeResult(
        "ready",
        "Informasi utama sudah terverifikasi. Tinjau ringkasan request sebelum generation; intake belum membuat halaman atau berkas.",
        (),
        request,
    )


def map_generation_result(report: dict) -> IntakeResult:
    """Map internal generation statuses without exposing raw model or validator text."""
    status = report.get("status") if isinstance(report, dict) else None
    if status == "accepted":
        return IntakeResult("completed", "Halaman berhasil dibuat dan hasil renderer siap ditinjau.")
    if status == "missing_information":
        return IntakeResult(
            "needs_clarification",
            "Informasi usaha belum lengkap. Lengkapi nama, deskripsi, atau layanan utama lalu siapkan request kembali.",
            ("business_facts",),
        )
    if status == "input_too_long":
        return IntakeResult(
            "input_too_long",
            "Request melebihi budget konteks. Ringkas prompt atau fakta secara manual; sistem tidak memotong teks.",
        )
    return IntakeResult(
        "generation_failed",
        "Halaman belum berhasil dibuat karena salah satu pemeriksaan generation gagal. Tidak ada hasil yang siap ditinjau.",
    )
