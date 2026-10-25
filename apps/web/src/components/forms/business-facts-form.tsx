"use client";

import { useState, type FormEvent } from "react";
import { ChevronDown, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { CatalogResponse, PageGenre, RequestDraft, StyleMode } from "@/lib/api-types";
import {
  createDraft,
  DraftValidationError,
  getAdditionalFacts,
  getFactValue,
  getStructuredFacts,
  type ConfirmedBusinessFacts,
  type ConfirmedStructuredFact,
} from "@/lib/request-draft";
import { describeMissingFields } from "@/lib/intake-copy";
import { getWebsiteTemplate, type WebsiteTemplateId } from "@/lib/website-templates";

type ServiceFields = { title: string; text: string };
type FormFields = {
  genre: PageGenre;
  styleMode: StyleMode;
  name: string;
  description: string;
  value: string;
  services: ServiceFields[];
  additionalFacts: ConfirmedStructuredFact[];
  requestedFeatureIds: string[];
  assetIds: string[];
  fictitious: "" | "true" | "false";
};

type BusinessFactsFormProps = {
  prompt: string;
  initialDraft: RequestDraft;
  catalog: CatalogResponse | null;
  missingFields: string[];
  onlyMissing?: boolean;
  templateId?: WebsiteTemplateId;
  onSubmit: (draft: RequestDraft) => Promise<void>;
};

const FALLBACK_GENRES = [
  { id: "landing_page", label: "Landing page" },
  { id: "company_profile", label: "Company profile" },
];
const FALLBACK_STYLES = [
  { id: "plain_css", label: "CSS biasa" },
  { id: "tailwind", label: "Tailwind CSS" },
];
const INPUT_CLASS = "mt-1.5 min-h-11 w-full rounded-xl border border-input bg-white px-3.5 py-2.5 text-sm text-harbor-ink placeholder:text-slate-note/70 focus-visible:border-primary";
const TEXTAREA_CLASS = "mt-1.5 min-h-[86px] resize-y rounded-xl border-input bg-white px-3.5 py-2.5 text-sm leading-6 text-harbor-ink placeholder:text-slate-note/70 focus-visible:border-primary";
const DISCLOSURE_CLASS = "group rounded-xl border border-border bg-white";
const DISCLOSURE_SUMMARY_CLASS = "flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 rounded-xl px-3.5 py-3 transition-colors hover:bg-frost/70 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-primary [&::-webkit-details-marker]:hidden";

function defaultAssetForGenre(genre: PageGenre): string {
  return genre === "landing_page" ? "studio-shapes" : "company-shapes";
}

function ensureRequiredServices(services: ServiceFields[]): ServiceFields[] {
  const result = [...services];
  while (result.length < 3) result.push({ title: "", text: "" });
  return result;
}

function ensureRequiredAdditionalFacts(
  facts: ConfirmedStructuredFact[],
  genre: PageGenre,
): ConfirmedStructuredFact[] {
  const required = genre === "landing_page"
    ? { process: 3, faq: 3 }
    : { process: 3, project: 2 };
  const requiredKinds = new Set(Object.keys(required));
  const result = facts.filter((fact) => fact.title.trim() || fact.text.trim() || requiredKinds.has(fact.kind));
  for (const [kind, count] of Object.entries(required) as Array<[ConfirmedStructuredFact["kind"], number]>) {
    const existing = result.filter((fact) => fact.kind === kind).length;
    for (let index = existing; index < count; index += 1) {
      result.push({ kind, title: "", text: "" });
    }
  }
  return result;
}

function fromDraft(draft: RequestDraft): FormFields {
  const genre = draft.genre === "company_profile" ? "company_profile" : "landing_page";
  const services = getStructuredFacts(draft, "service");
  const additionalFacts = ensureRequiredAdditionalFacts(getAdditionalFacts(draft), genre);
  const fictitious = draft.fictitious === true ? "true" : draft.fictitious === false ? "false" : "";
  return {
    genre,
    styleMode: draft.style_mode === "plain_css" ? "plain_css" : "tailwind",
    name: getFactValue(draft, "name"),
    description: getFactValue(draft, "description"),
    value: getFactValue(draft, "value"),
    services: ensureRequiredServices(services),
    additionalFacts,
    requestedFeatureIds: draft.requested_features.map((feature) => feature.capability_id),
    assetIds: [...new Set([defaultAssetForGenre(genre), ...draft.asset_ids])],
    fictitious,
  };
}

function fromTemplate(templateId: WebsiteTemplateId): FormFields {
  const template = getWebsiteTemplate(templateId);
  return {
    genre: template.genre,
    styleMode: template.styleMode,
    name: template.name,
    description: template.description,
    value: template.value,
    services: template.services.map((service) => ({ ...service })),
    additionalFacts: template.additionalFacts.map((fact) => ({ ...fact })),
    requestedFeatureIds: [],
    assetIds: [defaultAssetForGenre(template.genre)],
    fictitious: "true",
  };
}

function hasMissingField(missingFields: string[], keys: string[]): boolean {
  return missingFields.some((field) => keys.includes(field));
}

export function BusinessFactsForm({
  prompt,
  initialDraft,
  catalog,
  missingFields,
  onlyMissing = false,
  templateId,
  onSubmit,
}: BusinessFactsFormProps) {
  const [fields, setFields] = useState<FormFields>(() => templateId ? fromTemplate(templateId) : fromDraft(initialDraft));
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const genres = catalog?.supported_genres.length ? catalog.supported_genres : FALLBACK_GENRES;
  const styles = catalog?.supported_style_modes.length ? catalog.supported_style_modes : FALLBACK_STYLES;
  const assets = catalog?.assets ?? [];
  const missingLabels = describeMissingFields(missingFields);
  function showField(keys: string[]) {
    return !onlyMissing
      || missingFields.length === 0
      || missingFields.includes("business_facts")
      || hasMissingField(missingFields, keys);
  }
  const visibleAdditionalFacts = fields.additionalFacts
    .map((fact, index) => ({ fact, index }))
    .filter(({ fact }) => showField([`business_facts.${fact.kind}`]));
  const showCoreFields = showField([
    "genre",
    "style_mode",
    "business_facts.name",
    "business_facts.description",
    "business_facts.value",
  ]);
  const showServiceFields = showField(["business_facts.service", "business_facts.services"]);
  const showBusinessSettings = showField(["fictitious", "asset_ids", "requested_features"]);
  const completedServices = fields.services.filter((service) => service.title.trim() && service.text.trim()).length;
  const requiredAdditionalFactCounts = fields.genre === "landing_page"
    ? { process: 3, faq: 3 }
    : { process: 3, project: 2 };
  const requiredAdditionalFactCount = Object.values(requiredAdditionalFactCounts).reduce((total, count) => total + count, 0);
  const completedAdditionalFactCount = Object.entries(requiredAdditionalFactCounts).reduce((total, [kind, count]) => {
    const completeCount = fields.additionalFacts.filter(
      (fact) => fact.kind === kind && fact.title.trim() && fact.text.trim(),
    ).length;
    return total + Math.min(count, completeCount);
  }, 0);
  const genreLabel = genres.find((option) => option.id === fields.genre)?.label ?? fields.genre;
  const styleLabel = styles.find((option) => option.id === fields.styleMode)?.label ?? fields.styleMode;
  const settingsSummary = `${fields.fictitious === "" ? "Status usaha belum dipilih" : fields.fictitious === "true" ? "Usaha fiktif" : "Usaha nyata"} · ${fields.assetIds.length} aset`;

  function revealInvalidSection(event: FormEvent<HTMLFormElement>) {
    if (!(event.target instanceof HTMLElement)) return;
    const section = event.target.closest("details");
    if (section instanceof HTMLDetailsElement) section.open = true;
  }

  function updateService(index: number, key: keyof ServiceFields, value: string) {
    setFields((current) => ({
      ...current,
      services: current.services.map((service, serviceIndex) =>
        serviceIndex === index ? { ...service, [key]: value } : service,
      ),
    }));
  }

  function updateAdditionalFact(index: number, patch: Partial<ConfirmedStructuredFact>) {
    setFields((current) => ({
      ...current,
      additionalFacts: current.additionalFacts.map((fact, factIndex) =>
        factIndex === index ? { ...fact, ...patch } : fact,
      ),
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = event.currentTarget;
    if (fields.fictitious === "") {
      setError("Pilih apakah usaha ini fiktif atau nyata.");
      return;
    }
    const confirmed: ConfirmedBusinessFacts = {
      genre: fields.genre,
      styleMode: fields.styleMode,
      name: fields.name,
      description: fields.description,
      value: fields.value,
      services: fields.services,
      additionalFacts: fields.additionalFacts,
      requestedFeatureIds: fields.requestedFeatureIds,
      assetIds: fields.assetIds,
      fictitious: fields.fictitious === "true",
    };
    try {
      const draft = createDraft(prompt, confirmed);
      setIsSubmitting(true);
      await onSubmit(draft);
    } catch (submitError) {
      if (submitError instanceof DraftValidationError) {
        setError(submitError.message);
        form.querySelectorAll("details").forEach((section) => {
          section.open = true;
        });
      } else {
        setError("Draft belum berhasil divalidasi. Periksa koneksi API lokal lalu coba lagi.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function toggleAsset(assetId: string) {
    setFields((current) => {
      const selected = current.assetIds.includes(assetId);
      if (!selected && current.assetIds.length >= 8) return current;
      return {
        ...current,
        assetIds: selected
          ? current.assetIds.filter((id) => id !== assetId)
          : [...current.assetIds, assetId],
      };
    });
  }

  function updateGenre(genre: PageGenre) {
    setFields((current) => ({
      ...current,
      genre,
      additionalFacts: ensureRequiredAdditionalFacts(current.additionalFacts, genre),
      assetIds: [...new Set([
        defaultAssetForGenre(genre),
        ...current.assetIds.filter((assetId) => assetId !== defaultAssetForGenre(current.genre)),
      ])],
    }));
  }

  function toggleRequestedFeature(capabilityId: string) {
    setFields((current) => {
      const selected = current.requestedFeatureIds.includes(capabilityId);
      return {
        ...current,
        requestedFeatureIds: selected
          ? current.requestedFeatureIds.filter((id) => id !== capabilityId)
          : [...current.requestedFeatureIds, capabilityId],
      };
    });
  }

  return (
    <form onSubmit={handleSubmit} onInvalidCapture={revealInvalidSection} className="mt-4 overflow-hidden rounded-2xl border border-border bg-paper shadow-[0_8px_30px_rgba(30,45,69,0.05)]">
      <div className="border-b border-border bg-[#F4F2EC] px-4 py-3.5 sm:px-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-sm font-semibold text-harbor-ink">{templateId ? `Template ${getWebsiteTemplate(templateId).label}` : "Lengkapi fakta halaman"}</p>
            <p className="mt-0.5 text-xs leading-5 text-slate-note">
              {templateId
                ? "Data contoh fiktif sudah terisi. Sesuaikan fakta dengan usaha Anda sebelum melanjutkan."
                : onlyMissing
                ? "Lengkapi bagian yang masih kosong. Fakta yang sudah ditemukan tetap dipertahankan."
                : "Isi detail yang belum tersedia. Tidak ada fakta bisnis yang ditebak dari prompt."}
            </p>
          </div>
          <span className="rounded-full bg-verified/10 px-2.5 py-1 text-[11px] font-medium text-verified">
            {templateId ? "Contoh fiktif" : "Dikonfirmasi saat dikirim"}
          </span>
        </div>
      </div>

      {missingFields.length > 0 ? (
        <div className="flex flex-wrap gap-1.5 border-b border-border px-4 py-3 sm:px-5" aria-label="Field yang perlu dilengkapi">
          {missingLabels.map((field) => (
            <span key={field} className="rounded-full border border-border bg-frost px-2.5 py-1 text-[11px] text-slate-note">
              {field}
            </span>
          ))}
        </div>
      ) : null}

      <div className="space-y-3 px-4 py-4 sm:px-5 sm:py-5">
        {showCoreFields ? <details open className={DISCLOSURE_CLASS}>
          <summary className={DISCLOSURE_SUMMARY_CLASS}>
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-harbor-ink">Usaha dan tampilan</span>
              <span className="mt-0.5 block truncate text-xs text-slate-note">
                {fields.name.trim() || "Nama usaha belum diisi"} · {genreLabel} · {styleLabel}
              </span>
            </span>
            <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-slate-note transition-transform group-open:rotate-180" />
          </summary>
          <div className="grid gap-4 border-t border-border p-3.5 sm:p-4">
        {showField(["genre", "style_mode"]) ? <div className="grid gap-4 sm:grid-cols-2">
          {showField(["genre"]) ? <div>
            <label htmlFor="page-genre" className="text-sm font-medium text-harbor-ink">Jenis halaman</label>
            <select
              id="page-genre"
              value={fields.genre}
              onChange={(event) => updateGenre(event.target.value as PageGenre)}
              className={INPUT_CLASS}
            >
              {genres.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
            </select>
          </div> : null}
          {showField(["style_mode"]) ? <div>
            <label htmlFor="style-mode" className="text-sm font-medium text-harbor-ink">Gaya hasil</label>
            <select
              id="style-mode"
              value={fields.styleMode}
              onChange={(event) => setFields((current) => ({ ...current, styleMode: event.target.value as StyleMode }))}
              className={INPUT_CLASS}
            >
              {styles.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
            </select>
          </div> : null}
        </div> : null}

        {showField(["business_facts.name"]) ? <div>
          <label htmlFor="business-name" className="text-sm font-medium text-harbor-ink">Nama usaha <span className="text-destructive">*</span></label>
          <input
            id="business-name"
            value={fields.name}
            onChange={(event) => setFields((current) => ({ ...current, name: event.target.value }))}
            maxLength={100}
            required
            aria-invalid={hasMissingField(missingFields, ["business_facts.name"])}
            className={INPUT_CLASS}
            placeholder="Contoh: Ruang Tanah"
          />
        </div> : null}

        {showField(["business_facts.description"]) ? <div>
          <label htmlFor="business-description" className="text-sm font-medium text-harbor-ink">Deskripsi usaha <span className="text-destructive">*</span></label>
          <Textarea
            id="business-description"
            value={fields.description}
            onChange={(event) => setFields((current) => ({ ...current, description: event.target.value }))}
            maxLength={3000}
            required
            aria-invalid={hasMissingField(missingFields, ["business_facts.description"])}
            className={TEXTAREA_CLASS}
            placeholder="Jelaskan usaha ini dengan kata-kata Anda."
          />
          <p className="mt-1 text-right text-[11px] tabular-nums text-slate-note">{fields.description.length}/3000</p>
        </div> : null}

        {showField(["business_facts.value"]) ? <div>
          <label htmlFor="business-value" className="text-sm font-medium text-harbor-ink">Nilai utama atau keunggulan <span className="text-destructive">*</span></label>
          <Textarea
            id="business-value"
            value={fields.value}
            onChange={(event) => setFields((current) => ({ ...current, value: event.target.value }))}
            maxLength={1000}
            required
            aria-invalid={hasMissingField(missingFields, ["business_facts.value"])}
            className={TEXTAREA_CLASS}
            placeholder="Apa yang penting atau berbeda dari usaha ini?"
          />
        </div> : null}
          </div>
        </details> : null}

        {showServiceFields ? <details className={DISCLOSURE_CLASS}>
          <summary className={DISCLOSURE_SUMMARY_CLASS}>
            <span>
              <span className="block text-sm font-semibold text-harbor-ink">Layanan</span>
              <span className="mt-0.5 block text-xs text-slate-note">{completedServices} dari {fields.services.length} lengkap</span>
            </span>
            <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-slate-note transition-transform group-open:rotate-180" />
          </summary>
          <div className="border-t border-border p-3.5 sm:p-4">
        <fieldset className="space-y-3">
          <div className="flex items-end justify-between gap-3">
            <div>
              <legend className="text-sm font-medium text-harbor-ink">Layanan <span className="text-destructive">*</span></legend>
              <p className="mt-0.5 text-xs text-slate-note">
                {templateId ? "Contoh layanan sudah terisi. Ganti dengan layanan yang benar sebelum melanjutkan." : "Isi 3 layanan yang benar untuk ditampilkan di halaman."}
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={fields.services.length >= 5}
              onClick={() => setFields((current) => ({ ...current, services: [...current.services, { title: "", text: "" }] }))}
              className="shrink-0 gap-1.5 rounded-lg"
            >
              <Plus aria-hidden="true" className="size-3.5" />
              Tambah layanan
            </Button>
          </div>
          {fields.services.map((service, index) => (
            <div key={`service-${index}`} className="rounded-xl border border-border bg-white p-3.5">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs font-medium text-slate-note">Layanan {index + 1}</p>
                {fields.services.length > 3 ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Hapus layanan ${index + 1}`}
                    onClick={() => setFields((current) => ({ ...current, services: current.services.filter((_, itemIndex) => itemIndex !== index) }))}
                    className="text-slate-note hover:text-destructive"
                  >
                    <Trash2 aria-hidden="true" className="size-3.5" />
                  </Button>
                ) : null}
              </div>
              <label htmlFor={`service-title-${index}`} className="sr-only">Nama layanan {index + 1}</label>
              <input
                id={`service-title-${index}`}
                value={service.title}
                onChange={(event) => updateService(index, "title", event.target.value)}
                maxLength={100}
                required
                className={INPUT_CLASS}
                placeholder="Nama layanan"
              />
              <label htmlFor={`service-text-${index}`} className="sr-only">Deskripsi layanan {index + 1}</label>
              <Textarea
                id={`service-text-${index}`}
                value={service.text}
                onChange={(event) => updateService(index, "text", event.target.value)}
                maxLength={1000}
                required
                className={`${TEXTAREA_CLASS} min-h-[72px]`}
                placeholder="Jelaskan layanan tersebut."
              />
            </div>
          ))}
        </fieldset>
          </div>
        </details> : null}

        {visibleAdditionalFacts.length > 0 ? <details className={DISCLOSURE_CLASS}>
          <summary className={DISCLOSURE_SUMMARY_CLASS}>
            <span>
              <span className="block text-sm font-semibold text-harbor-ink">Isi halaman</span>
              <span className="mt-0.5 block text-xs text-slate-note">{completedAdditionalFactCount} dari {requiredAdditionalFactCount} rincian wajib lengkap</span>
            </span>
            <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-slate-note transition-transform group-open:rotate-180" />
          </summary>
          <div className="border-t border-border p-3.5 sm:p-4">
        <fieldset className="space-y-3">
          <div className="flex items-end justify-between gap-3">
            <div>
              <legend className="text-sm font-medium text-harbor-ink">Rincian untuk halaman <span className="text-destructive">*</span></legend>
              <p className="mt-0.5 text-xs leading-5 text-slate-note">
                {templateId
                  ? "Contoh proses dan rincian halaman sudah terisi. Sesuaikan dengan informasi yang benar sebelum melanjutkan."
                  : fields.genre === "landing_page"
                  ? "Isi 3 langkah proses dan 3 FAQ. Semua rincian harus berasal dari Anda."
                  : "Isi 3 langkah proses dan 2 proyek atau karya. Semua rincian harus berasal dari Anda."}
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={fields.additionalFacts.length >= 12}
              onClick={() => setFields((current) => ({
                ...current,
                additionalFacts: [...current.additionalFacts, {
                  kind: current.genre === "landing_page" ? "faq" : "project",
                  title: "",
                  text: "",
                }],
              }))}
              className="shrink-0 gap-1.5 rounded-lg"
            >
              <Plus aria-hidden="true" className="size-3.5" />
              Tambah fakta
            </Button>
          </div>
          {visibleAdditionalFacts.map(({ fact, index }) => (
            <div key={`fact-${index}`} className="grid gap-2 rounded-xl border border-border bg-white p-3.5 sm:grid-cols-[145px_1fr]">
              <label htmlFor={`fact-kind-${index}`} className="sr-only">Jenis fakta {index + 1}</label>
              <select
                id={`fact-kind-${index}`}
                value={fact.kind}
                onChange={(event) => updateAdditionalFact(index, { kind: event.target.value as ConfirmedStructuredFact["kind"] })}
                className={INPUT_CLASS}
              >
                <option value="project">Proyek</option>
                <option value="process">Proses</option>
                <option value="faq">FAQ</option>
              </select>
              <div className="space-y-2">
                <label htmlFor={`fact-title-${index}`} className="sr-only">Judul fakta {index + 1}</label>
                <input
                  id={`fact-title-${index}`}
                  value={fact.title}
                  onChange={(event) => updateAdditionalFact(index, { title: event.target.value })}
                  maxLength={100}
                  className={INPUT_CLASS}
                  placeholder="Judul"
                />
                <label htmlFor={`fact-text-${index}`} className="sr-only">Isi fakta {index + 1}</label>
                <Textarea
                  id={`fact-text-${index}`}
                  value={fact.text}
                  onChange={(event) => updateAdditionalFact(index, { text: event.target.value })}
                  maxLength={1000}
                  className={`${TEXTAREA_CLASS} min-h-[72px]`}
                  placeholder="Informasi yang benar tentang usaha"
                />
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={`Hapus fakta tambahan ${index + 1}`}
                onClick={() => setFields((current) => ({ ...current, additionalFacts: current.additionalFacts.filter((_, itemIndex) => itemIndex !== index) }))}
                className="justify-self-start text-slate-note hover:text-destructive sm:col-start-1 sm:row-start-2"
              >
                <Trash2 aria-hidden="true" className="size-3.5" />
              </Button>
            </div>
          ))}
        </fieldset>
          </div>
        </details> : null}

        {showBusinessSettings ? <details className={DISCLOSURE_CLASS}>
          <summary className={DISCLOSURE_SUMMARY_CLASS}>
            <span>
              <span className="block text-sm font-semibold text-harbor-ink">Pengaturan tambahan</span>
              <span className="mt-0.5 block text-xs text-slate-note">{settingsSummary}</span>
            </span>
            <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-slate-note transition-transform group-open:rotate-180" />
          </summary>
          <div className="space-y-4 border-t border-border p-3.5 sm:p-4">
        {showField(["fictitious"]) ? <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-harbor-ink">Status usaha <span className="text-destructive">*</span></legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { value: "true", label: "Usaha fiktif atau demo" },
              { value: "false", label: "Usaha nyata" },
            ].map((option) => (
              <label key={option.value} className="flex min-h-11 cursor-pointer items-center gap-2.5 rounded-xl border border-border bg-white px-3.5 text-sm text-harbor-ink hover:border-primary/40">
                <input
                  type="radio"
                  name="business-status"
                  value={option.value}
                  checked={fields.fictitious === option.value}
                  onChange={(event) => setFields((current) => ({ ...current, fictitious: event.target.value as FormFields["fictitious"] }))}
                  required
                  className="accent-primary"
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset> : null}

        {showField(["asset_ids"]) && assets.length > 0 ? (
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-harbor-ink">Aset lokal <span className="font-normal text-slate-note">(ilustrasi sesuai jenis halaman dipilih otomatis)</span></legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {assets.map((asset) => {
                const selected = fields.assetIds.includes(asset.id);
                const requiredAsset = asset.id === defaultAssetForGenre(fields.genre);
                return (
                  <label key={asset.id} className="flex cursor-pointer items-start gap-2.5 rounded-xl border border-border bg-white px-3 py-2.5 text-xs hover:border-primary/40">
                    <input
                      type="checkbox"
                      checked={selected}
                      disabled={requiredAsset || (!selected && fields.assetIds.length >= 8)}
                      onChange={() => toggleAsset(asset.id)}
                      className="mt-0.5 accent-primary"
                    />
                    <span className="min-w-0">
                      <span className="block break-all font-medium text-harbor-ink">{asset.id}</span>
                      <span className="mt-0.5 block leading-5 text-slate-note">{asset.width} × {asset.height} · {asset.license}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        ) : (
          <p className="rounded-xl bg-frost px-3.5 py-3 text-xs leading-5 text-slate-note">
            Katalog aset belum tersedia. Pilihan aset dapat diperiksa setelah API lokal terhubung.
          </p>
        )}

        {showField(["requested_features"]) && catalog?.unsupported_capabilities.length ? (
          <fieldset className="space-y-2 rounded-xl border border-[#E5D6B1] bg-[#FBF8F0] px-3.5 py-3">
            <legend className="px-1 text-xs font-semibold text-harbor-ink">Periksa kebutuhan fitur</legend>
            <p className="text-xs leading-5 text-slate-note">
              Tandai jika prompt meminta salah satu kemampuan berikut. Intake akan menjelaskan batasnya sebelum halaman dibuat.
            </p>
            <div className="space-y-1.5">
              {catalog.unsupported_capabilities.map((item) => (
                <label key={item.id} className="flex cursor-pointer items-start gap-2 text-xs leading-5 text-slate-note">
                  <input
                    type="checkbox"
                    checked={fields.requestedFeatureIds.includes(item.id)}
                    onChange={() => toggleRequestedFeature(item.id)}
                    className="mt-1 accent-primary"
                  />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>
            <p className="pt-1 text-xs leading-5 text-slate-note">{catalog.scope_message}</p>
          </fieldset>
        ) : null}
          </div>
        </details> : null}

        {error ? (
          <p role="alert" className="rounded-lg border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-sm text-destructive">
            {error}
          </p>
        ) : null}

        <div className="flex flex-col-reverse gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-sm text-[11px] leading-5 text-slate-note">
            Nilai yang Anda kirim ditandai sebagai konfirmasi pengguna untuk validasi ini.
          </p>
          <Button type="submit" disabled={isSubmitting} className="shrink-0 gap-2 rounded-xl px-4">
            {isSubmitting ? "Memeriksa fakta…" : onlyMissing ? "Periksa detail" : "Periksa dan tinjau"}
          </Button>
        </div>
      </div>
    </form>
  );
}
