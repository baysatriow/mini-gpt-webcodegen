/** TypeScript mirror of the local FastAPI JSON contract. */

export type PageGenre = "landing_page" | "company_profile";
export type StyleMode = "plain_css" | "tailwind";
export type IntakeStatus =
  | "needs_clarification"
  | "unsupported_request"
  | "input_too_long"
  | "ready";
export type GenerationStatus = "completed" | "generation_failed" | "input_too_long";
export type SourceFilename = "index.html" | "styles.css" | "app.js";

export type SourceSpanEvidence = {
  source_span: { start: number; end: number };
};

export type CapabilitySourceSpanEvidence = {
  source_span: { start: number; end: number; quote: string };
};

export type UserConfirmedEvidence = { user_confirmed: true };
export type FactEvidence = SourceSpanEvidence | UserConfirmedEvidence;
export type CapabilityEvidence = CapabilitySourceSpanEvidence | UserConfirmedEvidence;

export type ScalarBusinessFact = {
  id: string;
  kind: "name" | "description" | "value";
  value: string;
  evidence: FactEvidence;
};

export type StructuredBusinessFact = {
  id: string;
  kind: "service" | "project" | "process" | "faq";
  value: {
    title: string;
    title_evidence: FactEvidence;
    text: string;
    text_evidence: FactEvidence;
  };
};

export type BusinessFact = ScalarBusinessFact | StructuredBusinessFact;

/** Additional capability fields stay open to mirror the API's dictionary schema. */
export type RequestedFeature = {
  capability_id: string;
  evidence: CapabilityEvidence;
  [key: string]: unknown;
};

export type RequestDraft = {
  contract_version?: string | null;
  prompt?: string | null;
  genre?: PageGenre | string | null;
  style_mode?: StyleMode | string | null;
  business_facts: BusinessFact[];
  requested_features: RequestedFeature[];
  asset_ids: string[];
  fictitious?: boolean | null;
};

export type IntakeEnvelope = {
  prompt: string;
  draft: RequestDraft;
};

export type IntakeResponse = {
  status: IntakeStatus;
  message: string;
  missing_fields: string[];
  request: Record<string, unknown> | null;
};

export type ApiErrorResponse = {
  code: string;
  message: string;
  missing_fields: string[];
};

export type CatalogOption = { id: string; label: string };
export type CapabilityLabel = { id: string; label: string };
export type AssetMetadata = {
  id: string;
  width: number;
  height: number;
  origin: string;
  license: string;
};

export type CatalogResponse = {
  contract_version: "capability-catalog-v1";
  supported_genres: CatalogOption[];
  supported_style_modes: CatalogOption[];
  scope_message: string;
  unsupported_capabilities: CapabilityLabel[];
  assets: AssetMetadata[];
};

export type HealthResponse = {
  status: "ok";
  contract_version: string;
  model_loaded: boolean;
};

export type GenerationRequest = IntakeEnvelope;

export type GenerationResponse = {
  status: GenerationStatus;
  generation_id: string | null;
  message: string;
  missing_fields: string[];
  section_count: number | null;
  preview_url: string | null;
  download_url: string | null;
  files: SourceFilename[];
};

export type GenerationSummary = GenerationResponse & {
  genre: string | null;
  style_mode: string | null;
  business_name: string | null;
  created_at: string | null;
};

export type SourceResponse = {
  "index.html": string;
  "styles.css": string;
  "app.js": string;
};
