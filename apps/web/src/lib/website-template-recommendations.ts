import type { WebsiteTemplate } from "./website-templates";

export const WEBSITE_TEMPLATE_CATEGORIES = [
  { id: "all", label: "Semua" },
  { id: "food", label: "Kuliner" },
  { id: "creative", label: "Kreatif" },
  { id: "retail", label: "Retail" },
  { id: "service", label: "Layanan" },
  { id: "learning", label: "Belajar" },
  { id: "wellness", label: "Kebugaran" },
  { id: "community", label: "Komunitas" },
] as const;

export type WebsiteTemplateCategoryFilter = (typeof WEBSITE_TEMPLATE_CATEGORIES)[number]["id"];

function seededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

export function sampleWebsiteTemplates(
  templates: readonly WebsiteTemplate[],
  category: WebsiteTemplateCategoryFilter,
  seed: number,
  count = 4,
): WebsiteTemplate[] {
  const pool = category === "all"
    ? [...templates]
    : templates.filter((template) => template.category === category);
  const random = seededRandom(seed);

  for (let index = pool.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(random() * (index + 1));
    [pool[index], pool[randomIndex]] = [pool[randomIndex], pool[index]];
  }

  return pool.slice(0, Math.max(0, Math.floor(count)));
}
