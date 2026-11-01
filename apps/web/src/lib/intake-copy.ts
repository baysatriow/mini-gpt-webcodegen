import type { IntakeStatus } from "@/lib/api-types";

export const INTAKE_STATUS_LABEL: Record<IntakeStatus, string> = {
  needs_clarification: "Perlu dilengkapi",
  unsupported_request: "Di luar cakupan",
  input_too_long: "Melewati batas input",
  ready: "Siap ditinjau",
};

const MISSING_FIELD_LABELS: Record<string, string> = {
  prompt: "Deskripsi permintaan",
  request_draft: "Rancangan permintaan",
  genre: "Jenis halaman",
  style_mode: "Gaya CSS",
  "business_facts.name": "Nama usaha",
  "business_facts.description": "Deskripsi usaha",
  "business_facts.value": "Nilai utama atau keunggulan usaha",
  "business_facts.service": "Tiga layanan usaha",
  "business_facts.process": "Tiga langkah proses usaha",
  "business_facts.faq": "Tiga FAQ untuk landing page",
  "business_facts.project": "Dua proyek atau karya untuk company profile",
  "business_facts.services": "Setidaknya satu layanan",
  "business_facts": "Fakta usaha",
  "asset_ids": "Pilihan aset lokal",
  "requested_features": "Fitur yang diminta",
  fictitious: "Status usaha fiktif atau nyata",
};

export function labelMissingField(field: string): string {
  if (MISSING_FIELD_LABELS[field]) return MISSING_FIELD_LABELS[field];
  if (field.startsWith("business_facts.")) return "Fakta usaha tambahan";
  if (field.startsWith("requested_features.")) return "Fitur yang diminta";
  return "Informasi tambahan";
}

export function describeMissingFields(fields: string[]): string[] {
  return [...new Set(fields.map(labelMissingField))];
}

export function intakeActionLabel(status: IntakeStatus): string {
  switch (status) {
    case "needs_clarification":
      return "Lengkapi informasi di bawah ini.";
    case "unsupported_request":
      return "Sederhanakan permintaan agar sesuai dengan kemampuan generator lokal.";
    case "input_too_long":
      return "Ringkas prompt atau fakta tanpa menghilangkan informasi penting.";
    case "ready":
      return "Periksa ringkasan sebelum menyetujui pembuatan halaman.";
  }
}
