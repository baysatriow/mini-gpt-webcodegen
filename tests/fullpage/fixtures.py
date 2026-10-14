"""Small source-bound request fixtures shared by contract tests."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source_bound_fixture(genre="company_profile", style="plain_css"):
    catalog = json.loads((ROOT / "configs/fullpage/source-bound-copy-v1.json").read_text(encoding="utf-8"))
    request = {
        "request_id": "fixture-source-bound",
        "prompt": "Buat company profile Studio Mapurana.",
        "genre": genre,
        "style_mode": style,
        "business_facts": [
            {"id": "name", "kind": "name", "value": "Studio Mapurana"},
            {"id": "about", "kind": "description", "value": "Studio Mapurana membuat keramik untuk rumah."},
            {"id": "values", "kind": "value", "value": "Bahan dan proses dijelaskan secara terbuka."},
            {"id": "srv0", "kind": "service", "value": {"title": "Kelas keramik", "text": "Kelas untuk pemula."}},
            {"id": "srv1", "kind": "service", "value": {"title": "Karya pesanan", "text": "Pembuatan karya berdasarkan diskusi kebutuhan."}},
            {"id": "step0", "kind": "process", "value": {"title": "Pilih tanah liat", "text": "Tentukan bahan yang akan digunakan."}},
            {"id": "faq0", "kind": "faq", "value": {"title": "Bagaimana memulai?", "text": "Hubungi studio untuk berdiskusi."}},
            {"id": "project0", "kind": "project", "value": {"title": "Cangkir pagi", "text": "Contoh karya keramik."}},
        ],
        "asset_ids": ["company-shapes" if genre == "company_profile" else "studio-shapes"],
        "fictitious": True,
    }
    landing_roles = ["navigation", "hero", "about", "services", "benefits", "process", "faq", "contact", "footer"]
    company_roles = ["navigation", "hero", "about", "services", "values", "process", "portfolio", "contact", "footer"]
    role_facts = {
        "navigation": ["name"], "hero": ["name"], "about": ["about"],
        "services": ["srv0", "srv1"], "benefits": ["values"], "values": ["values"],
        "process": ["step0"], "faq": ["faq0"], "portfolio": ["project0"],
        "contact": [], "footer": ["name"],
    }
    sections = []
    for role in landing_roles if genre == "landing_page" else company_roles:
        role_spec = catalog["roles"][role]
        sections.append({
            "id": {"navigation": "nav", "hero": "main"}.get(role, role),
            "type": role_spec["component"],
            "role": role,
            "variant": role_spec["variants"][0],
            "copy_id": role_spec["copy_ids"][0],
            "fact_ids": role_facts[role],
            "asset_ids": request["asset_ids"] if role == "hero" else [],
        })
    plan = {"contract_version": "source-bound-v1", "theme_id": "studio-blue", "sections": sections}
    navigation_draft = {
        "contract_version": "source-bound-v1",
        "section_id": "nav",
        "fact_slots": [{"slot_id": "brand", "fact_id": "name"}],
        "asset_slots": [],
    }
    return request, catalog, plan, navigation_draft


def full_source_bound_fixture(genre="company_profile", style="plain_css"):
    request, catalog, plan, _ = source_bound_fixture(genre, style)
    facts = {fact["id"]: fact for fact in request["business_facts"]}
    drafts = []
    for descriptor in plan["sections"]:
        role_spec = catalog["roles"][descriptor["role"]]
        fact_slots = []
        for fact_id in descriptor["fact_ids"]:
            fact = facts[fact_id]
            slot_id = next(
                identifier
                for identifier in role_spec["slot_ids"]
                if fact["kind"] in catalog["slots"][identifier]["fact_kinds"]
            )
            fact_slots.append({"slot_id": slot_id, "fact_id": fact_id})
        asset_slots = [
            {"slot_id": slot_id, "asset_id": asset_id}
            for slot_id, asset_id in zip(role_spec["asset_slot_ids"], descriptor["asset_ids"], strict=True)
        ]
        drafts.append({
            "contract_version": "source-bound-v1",
            "section_id": descriptor["id"],
            "fact_slots": fact_slots,
            "asset_slots": asset_slots,
        })
    return request, catalog, plan, drafts


class _FixtureTokenizer:
    def __init__(self, token_count=None):
        self.token_count = token_count or (lambda text: (len(text) + 3) // 4)

    def encode(self, text, add_special_tokens=False):
        from types import SimpleNamespace

        return SimpleNamespace(ids=[0] * self.token_count(text))


def fake_source_bound_generator(root, *, contract_version, model_outputs, tokenizer=None):
    from pathlib import Path

    from src.fullpage.assets import load_asset_catalog
    from src.fullpage.generation import FullPageGenerator
    from src.fullpage.source_bound_contracts import load_copy_catalog

    generator = object.__new__(FullPageGenerator)
    generator.root = Path(root).resolve()
    generator.checkpoint = generator.root / "fake-checkpoint.pt"
    generator.config = {"precision": "bf16", "temperature": 0, "seed": 42}
    generator.contract_version = contract_version
    generator.model = object()
    generator.tokenizer = tokenizer or _FixtureTokenizer()
    generator.catalog = load_asset_catalog(generator.root)
    generator.copy_catalog = load_copy_catalog(generator.root)
    generator.metadata = {
        "checkpoint_sha256": "0" * 64,
        "checkpoint_run_id": "FAKE",
        "checkpoint_step": 1800,
        "fullpage_contract_version": contract_version,
    }
    outputs = iter(model_outputs)
    calls = []

    def execute(prompt, task):
        calls.append({"prompt": prompt, "task": task})
        try:
            value = next(outputs)
        except StopIteration as error:
            raise AssertionError("Fake model output list was exhausted") from error
        result = dict(value) if isinstance(value, dict) else {"raw": value}
        result.setdefault("raw", "")
        result.setdefault("stop_reason", "eos")
        result.setdefault("generated_tokens", 1)
        result.setdefault("prefix_tokens", 1)
        result.setdefault("max_new_tokens", 512 if task == "page_plan" else 1536)
        result.setdefault("seconds", 0.0)
        return result

    generator._execute_task = execute
    generator._fixture_calls = calls
    return generator


def intake_fixture(
    prompt="Buat company profile Studio Mapurana. Deskripsi: Studio Mapurana membuat keramik untuk rumah. Layanan: Kelas keramik. Detail: Kelas untuk pemula.",
    *,
    include_name=True,
    evidence="confirmed",
    tokenizer=None,
):
    from src.fullpage.intake import load_intake_catalog

    def proof(value):
        if evidence == "span":
            start = prompt.index(value)
            return {"source_span": {"start": start, "end": start + len(value)}}
        return {"user_confirmed": True}

    facts = []
    if include_name:
        value = "Studio Mapurana"
        facts.append({"id": "name", "kind": "name", "value": value, "evidence": proof(value)})
    description = "Studio Mapurana membuat keramik untuk rumah."
    facts.extend(
        [
            {"id": "about", "kind": "description", "value": description, "evidence": proof(description)},
            {
                "id": "srv0",
                "kind": "service",
                "value": {
                    "title": "Kelas keramik",
                    "title_evidence": proof("Kelas keramik"),
                    "text": "Kelas untuk pemula.",
                    "text_evidence": proof("Kelas untuk pemula."),
                },
            },
            {
                "id": "values",
                "kind": "value",
                "value": "Bahan dan proses dijelaskan secara terbuka.",
                "evidence": {"user_confirmed": True},
            },
            {
                "id": "step0",
                "kind": "process",
                "value": {
                    "title": "Pilih tanah liat",
                    "title_evidence": {"user_confirmed": True},
                    "text": "Tentukan bahan yang akan digunakan.",
                    "text_evidence": {"user_confirmed": True},
                },
            },
            {
                "id": "faq0",
                "kind": "faq",
                "value": {
                    "title": "Bagaimana memulai?",
                    "title_evidence": {"user_confirmed": True},
                    "text": "Hubungi studio untuk berdiskusi.",
                    "text_evidence": {"user_confirmed": True},
                },
            },
            {
                "id": "project0",
                "kind": "project",
                "value": {
                    "title": "Cangkir pagi",
                    "title_evidence": {"user_confirmed": True},
                    "text": "Contoh karya keramik.",
                    "text_evidence": {"user_confirmed": True},
                },
            },
        ]
    )
    draft = {
        "contract_version": "request-draft-source-bound-v1",
        "prompt": prompt,
        "genre": "company_profile",
        "style_mode": "plain_css",
        "business_facts": facts,
        "requested_features": [],
        "asset_ids": ["company-shapes"],
        "fictitious": True,
    }
    return draft, tokenizer or _FixtureTokenizer(), load_intake_catalog(ROOT)
