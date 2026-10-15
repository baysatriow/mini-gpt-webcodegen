"""Public, path-free capability and asset catalog for the UI."""

from __future__ import annotations

from apps.api.schemas import AssetMetadata, CapabilityLabel, CatalogOption, CatalogResponse
from apps.api.services.runtime import Runtime, get_runtime


GENRE_LABELS = {
    "landing_page": "Landing page",
    "company_profile": "Company profile",
}
STYLE_LABELS = {
    "plain_css": "CSS biasa",
    "tailwind": "Tailwind CSS",
}


def get_public_catalog(runtime: Runtime | None = None) -> CatalogResponse:
    services = runtime or get_runtime()
    local_catalog = services.get_intake_catalog()
    capabilities = local_catalog["capabilities"]
    assets = local_catalog["assets"]

    return CatalogResponse(
        contract_version=capabilities["contract_version"],
        supported_genres=[
            CatalogOption(id=identifier, label=GENRE_LABELS.get(identifier, identifier))
            for identifier in capabilities["supported_genres"]
        ],
        supported_style_modes=[
            CatalogOption(id=identifier, label=STYLE_LABELS.get(identifier, identifier))
            for identifier in capabilities["supported_style_modes"]
        ],
        scope_message=capabilities["scope_message"],
        unsupported_capabilities=[
            CapabilityLabel(id=item["id"], label=item["label"])
            for item in capabilities["unsupported_capabilities"]
        ],
        assets=[
            AssetMetadata(
                id=identifier,
                width=info["width"],
                height=info["height"],
                origin=info["origin"],
                license=info["license"],
            )
            for identifier, info in assets.items()
        ],
    )
