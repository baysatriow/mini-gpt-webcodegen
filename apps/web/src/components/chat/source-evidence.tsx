import type { PromptMessage, SourceEvidence } from "@/lib/api-types";
import { labelMissingField } from "@/lib/intake-copy";

export function SourceEvidenceDisclosure({
  evidence,
  sourceMessages = [],
  summary = "Lihat sumber fakta",
}: {
  evidence: SourceEvidence[];
  sourceMessages?: PromptMessage[];
  summary?: string;
}) {
  if (evidence.length === 0) return null;
  const messageNumbers = new Map(sourceMessages.map((message, index) => [message.id, index]));

  return (
    <details className="mt-3 rounded-xl border border-border bg-white/80 px-3.5 py-3">
      <summary className="cursor-pointer text-xs font-medium text-primary">
        {summary} <span className="text-slate-note">({evidence.length})</span>
      </summary>
      <ul className="mt-3 space-y-2">
        {evidence.map((item, index) => {
          const messageNumber = messageNumbers.get(item.source_message_id);
          const sourceLabel = messageNumber === undefined || messageNumber === 0
            ? "Brief awal"
            : `Balasan ${messageNumber}`;
          return (
            <li key={`${item.source_message_id}-${item.start}-${item.end}-${index}`} className="rounded-lg bg-frost px-3 py-2.5">
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[11px] text-slate-note">
                <span className="font-medium text-harbor-ink">{labelMissingField(item.field)}</span>
                <span>{sourceLabel}</span>
              </div>
              <blockquote className="mt-1.5 whitespace-pre-wrap break-words border-l-2 border-primary/40 pl-2.5 text-sm leading-6 text-harbor-ink">
                {item.quote}
              </blockquote>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
