"use client";

import { BadgeCheck, PencilLine, ShieldCheck, Sparkles } from "lucide-react";
import { SourceEvidenceDisclosure } from "@/components/chat/source-evidence";
import type { CatalogResponse, RequestDraft } from "@/lib/api-types";
import type { RequestSummaryMessage } from "@/lib/chat-state";
import { getAdditionalFacts, getFactValue, getStructuredFacts } from "@/lib/request-draft";

type RequestSummaryProps = {
  message: RequestSummaryMessage;
  catalog: CatalogResponse | null;
  onEdit: (message: RequestSummaryMessage) => void;
  onConfirm: (message: RequestSummaryMessage) => void;
};

function optionLabel(options: CatalogResponse["supported_genres"] | undefined, value: string | null | undefined) {
  if (!value) return "Belum dipilih";
  return options?.find((option) => option.id === value)?.label ?? value;
}

export function RequestSummary({ message, catalog, onEdit, onConfirm }: RequestSummaryProps) {
  const draft: RequestDraft = message.draft;
  const name = getFactValue(draft, "name");
  const description = getFactValue(draft, "description");
  const services = getStructuredFacts(draft, "service");
  const extras = getAdditionalFacts(draft);
  const selectedAssets = draft.asset_ids
    .map((id) => catalog?.assets.find((asset) => asset.id === id)?.id ?? id)
    .filter(Boolean);
  const confirmed = message.state === "confirmed";

  return (
    <article className="flex items-start gap-3" aria-label="Ringkasan rancangan">
      <span
        className={`grid size-8 shrink-0 place-items-center rounded-xl border ${
          confirmed
            ? "border-emerald-200 bg-emerald-50 text-emerald-600"
            : "border-border bg-accent text-accent-foreground"
        }`}
      >
        {confirmed ? <BadgeCheck aria-hidden="true" className="size-4" /> : <ShieldCheck aria-hidden="true" className="size-4" />}
      </span>

      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          <p className="text-xs font-semibold text-foreground">Blueprint Rancangan</p>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium border ${
              confirmed
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : "bg-accent text-accent-foreground border-border"
            }`}
          >
            {confirmed ? "Disetujui" : "Siap Ditinjau"}
          </span>
        </div>

        <p className="text-sm leading-relaxed text-muted-foreground">{message.content}</p>

        <SourceEvidenceDisclosure
          evidence={message.sourceEvidence ?? []}
          sourceMessages={message.sourceMessages}
          summary="Periksa kutipan sumber & bukti fakta"
        />

        {/* Blueprint Card */}
        <div className="mt-3 overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
          {/* Header Specs */}
          <div className="grid gap-3 border-b border-border bg-slate-50/80 p-3.5 sm:grid-cols-2 sm:px-4">
            <SummaryItem label="Nama Usaha" value={name} verified />
            <SummaryItem
              label="Jenis & Gaya Desain"
              value={`${optionLabel(catalog?.supported_genres, draft.genre)} Â· ${optionLabel(catalog?.supported_style_modes, draft.style_mode)}`}
            />
          </div>

          <div className="space-y-3 p-3.5 sm:px-4">
            <SummaryItem label="Deskripsi Usaha" value={description} verified />

            <div>
              <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                Layanan Utama (Wajib 3)
              </p>
              <ul className="mt-2 space-y-2">
                {services.map((service, index) => (
                  <li key={`${service.title}-${index}`} className="flex items-start gap-2.5 rounded-xl border border-slate-100 bg-slate-50/70 p-3">
                    <span className="grid size-5 shrink-0 place-items-center rounded-full bg-secondary text-[10px] font-semibold text-secondary-foreground">
                      {index + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-foreground">{service.title || "Layanan"}</p>
                      <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{service.text}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {extras.length > 0 ? (
              <div>
                <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Fakta Tambahan (Proses & FAQ/Proyek)
                </p>
                <ul className="mt-2 space-y-1.5">
                  {extras.map((fact, index) => (
                    <li key={`${fact.kind}-${index}`} className="text-xs text-foreground bg-slate-50/50 rounded-lg p-2 border border-slate-100">
                      <span className="font-semibold text-primary">[{fact.kind.toUpperCase()}] {fact.title}</span>
                      <span className="text-muted-foreground"> â€” {fact.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="grid gap-3 border-t border-border pt-3 sm:grid-cols-2">
              <SummaryItem label="Status Bisnis" value={draft.fictitious ? "Fiktif / Contoh Demo" : "Bisnis Nyata"} verified />
              <SummaryItem label="Aset Ilustrasi" value={selectedAssets.length ? selectedAssets.join(", ") : "Aset standar"} />
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex flex-col-reverse gap-2 border-t border-border bg-slate-50/50 p-2.5 sm:flex-row sm:justify-end sm:items-center sm:px-4">
            {confirmed ? (
              <p className="self-center text-xs font-medium text-emerald-600" role="status">
                Blueprint dikonfirmasi. Siap membuat halaman web.
              </p>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => onEdit(message)}
                  className="inline-flex items-center gap-2 rounded-xl text-xs font-semibold h-9 px-3.5 border border-slate-200/90 bg-white hover:bg-slate-50 hover:border-slate-300 shadow-2xs active:scale-95 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-slate-700"
                >
                  <PencilLine aria-hidden="true" className="size-3.5" />
                  Edit Detail
                </button>
                <button
                  type="button"
                  onClick={() => onConfirm(message)}
                  className="inline-flex items-center gap-2 rounded-lg text-xs font-semibold h-9 px-4 bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.98] transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <Sparkles aria-hidden="true" className="size-3.5" />
                  Generate Website Sekarang
                </button>
              </>
            )}
          </div>
        </div>

        <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
          Periksa fakta di atas. Klik &ldquo;Generate Website&rdquo; untuk memulai pembuatan halaman.
        </p>
      </div>
    </article>
  );
}

function SummaryItem({ label, value, verified = false }: { label: string; value: string; verified?: boolean }) {
  return (
    <div className="min-w-0">
      <p className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
        {label}
        {verified ? <BadgeCheck aria-hidden="true" className="size-3.5 text-emerald-600" /> : null}
      </p>
      <p className="mt-0.5 break-words text-xs sm:text-sm font-medium leading-relaxed text-foreground">
        {value || "Belum diisi"}
      </p>
    </div>
  );
}
