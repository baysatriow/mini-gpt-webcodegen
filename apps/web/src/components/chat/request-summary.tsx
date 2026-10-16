"use client";

import { BadgeCheck, PencilLine, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
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
      <span className={`grid size-8 shrink-0 place-items-center rounded-xl border ${confirmed ? "border-verified/20 bg-verified/10 text-verified" : "border-primary/15 bg-accent text-primary"}`}>
        {confirmed ? <BadgeCheck aria-hidden="true" className="size-4" /> : <ShieldCheck aria-hidden="true" className="size-4" />}
      </span>
      <div className="min-w-0 flex-1 pt-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs font-semibold text-slate-note">Ringkasan rancangan</p>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${confirmed ? "bg-verified/10 text-verified" : "bg-accent text-cobalt-action"}`}>
            {confirmed ? "Disetujui pengguna" : "Siap ditinjau"}
          </span>
        </div>
        <p className="mt-1 text-[15px] leading-7 text-harbor-ink">{message.content}</p>
        <SourceEvidenceDisclosure
          evidence={message.sourceEvidence ?? []}
          sourceMessages={message.sourceMessages}
          summary="Periksa kutipan sumber"
        />

        <div className="mt-3 overflow-hidden rounded-2xl border border-border bg-paper">
          <div className="grid gap-3 border-b border-border bg-[#F8FAFC] p-4 sm:grid-cols-2 sm:px-5">
            <SummaryItem label="Nama usaha" value={name} verified />
            <SummaryItem
              label="Jenis dan gaya"
              value={`${optionLabel(catalog?.supported_genres, draft.genre)} · ${optionLabel(catalog?.supported_style_modes, draft.style_mode)}`}
            />
          </div>
          <div className="space-y-4 p-4 sm:px-5">
            <SummaryItem label="Deskripsi" value={description} verified />
            <div>
              <p className="text-[11px] font-medium text-slate-note">Layanan</p>
              <ul className="mt-1.5 space-y-2">
                {services.map((service, index) => (
                  <li key={`${service.title}-${index}`} className="rounded-lg bg-frost px-3 py-2.5">
                    <p className="text-sm font-medium text-harbor-ink">{service.title}</p>
                    <p className="mt-0.5 text-xs leading-5 text-slate-note">{service.text}</p>
                  </li>
                ))}
              </ul>
            </div>
            {extras.length > 0 ? (
              <div>
                <p className="text-[11px] font-medium text-slate-note">Fakta tambahan</p>
                <ul className="mt-1.5 space-y-1.5">
                  {extras.map((fact, index) => (
                    <li key={`${fact.kind}-${index}`} className="text-sm text-harbor-ink">
                      <span className="font-medium">{fact.title}</span>
                      <span className="text-slate-note"> · {fact.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="grid gap-3 border-t border-border pt-3 sm:grid-cols-2">
              <SummaryItem label="Status usaha" value={draft.fictitious ? "Fiktif atau demo" : "Usaha nyata"} verified />
              <SummaryItem label="Aset lokal" value={selectedAssets.length ? selectedAssets.join(", ") : "Tidak ada aset dipilih"} />
            </div>
          </div>
          <div className="flex flex-col-reverse gap-2 border-t border-border bg-[#FCFDFE] p-3.5 sm:flex-row sm:justify-end sm:px-5">
            {confirmed ? (
              <p className="self-center text-xs font-medium text-verified" role="status">
                Ringkasan dikonfirmasi. Nilai bisnis tetap berasal dari isian Anda.
              </p>
            ) : (
              <>
                <Button type="button" variant="outline" size="sm" onClick={() => onEdit(message)} className="gap-2 rounded-lg">
                  <PencilLine aria-hidden="true" className="size-3.5" />
                  Edit detail
                </Button>
                <Button type="button" size="sm" onClick={() => onConfirm(message)} className="rounded-lg">
                  Generate website
                </Button>
              </>
            )}
          </div>
        </div>
        <p className="mt-2 text-[11px] leading-5 text-slate-note">
          Periksa fakta dan kutipannya bila perlu. Klik Generate website saat siap.
        </p>
      </div>
    </article>
  );
}

function SummaryItem({ label, value, verified = false }: { label: string; value: string; verified?: boolean }) {
  return (
    <div className="min-w-0">
      <p className="flex items-center gap-1.5 text-[11px] font-medium text-slate-note">
        {label}
        {verified ? <BadgeCheck aria-hidden="true" className="size-3 text-verified" /> : null}
      </p>
      <p className="mt-1 break-words text-sm leading-6 text-harbor-ink">{value || "Belum diisi"}</p>
    </div>
  );
}
