import type {
  BusinessFact,
  PageGenre,
  RequestDraft,
  StyleMode,
} from "@/lib/api-types";

export const SOURCE_DRAFT_CONTRACT = "request-draft-source-bound-v1";

export type ConfirmedStructuredFact = {
  kind: "project" | "process" | "faq";
  title: string;
  text: string;
};

export type ConfirmedBusinessFacts = {
  genre: PageGenre;
  styleMode: StyleMode;
  name: string;
  description: string;
  services: Array<{ title: string; text: string }>;
  additionalFacts: ConfirmedStructuredFact[];
  assetIds: string[];
  fictitious: boolean;
};

export class DraftValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DraftValidationError";
  }
}

export function createDraft(prompt: string, facts: ConfirmedBusinessFacts): RequestDraft {
  const cleanPrompt = prompt.trim();
  const name = facts.name.trim();
  const description = facts.description.trim();
  const services = facts.services.map((service) => ({
    title: service.title.trim(),
    text: service.text.trim(),
  }));
  const additionalFacts = facts.additionalFacts.map((fact) => ({
    ...fact,
    title: fact.title.trim(),
    text: fact.text.trim(),
  }));

  if (!cleanPrompt) throw new DraftValidationError("Prompt belum diisi.");
  if (!name) throw new DraftValidationError("Nama usaha perlu diisi.");
  if (!description) throw new DraftValidationError("Deskripsi usaha perlu diisi.");
  if (services.some((service) => !service.title || !service.text)) {
    throw new DraftValidationError("Lengkapi nama dan deskripsi tiap layanan, atau hapus baris yang kosong.");
  }
  if (services.length === 0) throw new DraftValidationError("Tambahkan setidaknya satu layanan dengan nama dan deskripsi.");
  if (additionalFacts.some((fact) => Boolean(fact.title) !== Boolean(fact.text))) {
    throw new DraftValidationError("Lengkapi judul dan isi setiap fakta tambahan, atau hapus fakta yang belum lengkap.");
  }

  const businessFacts: BusinessFact[] = [
    {
      id: "business-name",
      kind: "name",
      value: name,
      evidence: { user_confirmed: true },
    },
    {
      id: "business-description",
      kind: "description",
      value: description,
      evidence: { user_confirmed: true },
    },
    ...services.map((service, index) => ({
      id: `service-${index + 1}`,
      kind: "service" as const,
      value: {
        title: service.title,
        title_evidence: { user_confirmed: true as const },
        text: service.text,
        text_evidence: { user_confirmed: true as const },
      },
    })),
    ...additionalFacts
      .filter((fact) => fact.title && fact.text)
      .map((fact, index) => ({
        id: `${fact.kind}-${index + 1}`,
        kind: fact.kind,
        value: {
          title: fact.title,
          title_evidence: { user_confirmed: true as const },
          text: fact.text,
          text_evidence: { user_confirmed: true as const },
        },
      })),
  ];

  if (businessFacts.length > 24) {
    throw new DraftValidationError("Jumlah fakta terlalu banyak. Hapus beberapa fakta tambahan.");
  }
  const assetIds = [...new Set(facts.assetIds)];
  if (assetIds.length > 8) throw new DraftValidationError("Pilih maksimal delapan aset lokal.");

  return {
    contract_version: SOURCE_DRAFT_CONTRACT,
    prompt: cleanPrompt,
    genre: facts.genre,
    style_mode: facts.styleMode,
    business_facts: businessFacts,
    // The public API catalog currently publishes no selectable supported capability IDs.
    // Keep this empty rather than inventing IDs; intake validates prompt scope server-side.
    requested_features: [],
    asset_ids: assetIds,
    fictitious: facts.fictitious,
  };
}

export function getFactValue(draft: RequestDraft, kind: "name" | "description"): string {
  const fact = draft.business_facts.find((item) => item.kind === kind);
  return fact && "value" in fact && typeof fact.value === "string" ? fact.value : "";
}

export function getStructuredFacts(draft: RequestDraft, kind: "service" | "project" | "process" | "faq") {
  return draft.business_facts.flatMap((fact) => {
    if (fact.kind !== kind || !("value" in fact) || typeof fact.value !== "object" || fact.value === null) {
      return [];
    }
    const value = fact.value as { title?: unknown; text?: unknown };
    return typeof value.title === "string" && typeof value.text === "string"
      ? [{ title: value.title, text: value.text }]
      : [];
  });
}

export function getAdditionalFacts(draft: RequestDraft): ConfirmedStructuredFact[] {
  return (['project', 'process', 'faq'] as const).flatMap((kind) =>
    getStructuredFacts(draft, kind).map((fact) => ({ kind, ...fact })),
  );
}
