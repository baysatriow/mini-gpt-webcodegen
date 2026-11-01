import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

test("Usage client is same-origin, typed, and never caches audit data", () => {
  const source = read("../src/lib/usage-client.ts");
  assert.match(source, /\/api\/v1\/usages/);
  assert.match(source, /cache:\s*["']no-store["']/);
  assert.match(source, /export type UsageRecord/);
  assert.match(source, /export function getUsageDetail/);
  assert.match(source, /filters\.q\.trim\(\)\.slice\(0, 200\)/);
});

test("Usage dashboard explains unavailable telemetry and renders readable outcome labels", () => {
  const dashboard = read("../src/components/usage/usage-dashboard.tsx");
  const components = read("../src/components/usage/usage-components.tsx");
  const source = `${dashboard}\n${components}`;
  assert.match(source, /Telemetri GPU belum tersedia/);
  assert.match(source, /Tidak ada data GPU selama proses generate/);
  assert.match(source, /function outcomeLabel/);
  assert.match(source, /aria-label/);
  assert.match(source, /Kembali ke chat/);
});

test("Usage dashboard localizes the legacy GPU scope message", () => {
  const dashboard = read("../src/components/usage/usage-dashboard.tsx");
  assert.match(dashboard, /Device-wide nvidia-smi samples collected during generation only/);
  assert.match(dashboard, /Sampel nvidia-smi mencatat penggunaan seluruh GPU hanya selama proses generate\./);
});

test("Usage metric values wrap on narrow screens instead of truncating", () => {
  const source = read("../src/components/usage/usage-components.tsx");
  assert.match(source, /whitespace-normal break-words leading-snug text-sm font-medium text-foreground/);
  assert.doesNotMatch(source, /truncate text-sm font-medium text-foreground">\{value\}/);
});

test("chat navigation and composer guidance remain accessible", () => {
  const sidebar = read("../src/components/chat/history-sidebar.tsx");
  const composer = read("../src/components/chat/composer.tsx");
  assert.match(sidebar, /href=["']\/usage["']/);
  assert.match(composer, /aria-describedby=/);
  assert.match(composer, /id=["']composer-guidance["']/);
  assert.match(composer, /id=["']composer-character-count["']/);
});

test("Usage inspection renders accepted source as inert text and shares navigation", () => {
  const dashboard = read("../src/components/usage/usage-dashboard.tsx");
  const components = read("../src/components/usage/usage-components.tsx");
  const sidebar = read("../src/components/chat/history-sidebar.tsx");
  assert.match(dashboard, /<HistorySidebar \{\.\.\.historyProps\}/);
  assert.match(dashboard, /activeSection: "usage"/);
  assert.match(components, /<code>\{source\}<\/code>/);
  assert.doesNotMatch(components, /dangerouslySetInnerHTML|<iframe/i);
  assert.match(components, /getSource\(generationId\)/);
  assert.match(components, /Fakta yang dikonfirmasi/);
  assert.match(components, /const STAGE_GROUPS/);
  assert.match(components, /const confirmedFacts = Array\.isArray\(detail\.confirmed_facts\)/);
  assert.match(components, /API FastAPI belum mengembalikan detail input/);
  assert.match(sidebar, /aria-current=\{activeSection === "usage" \? "page" : undefined\}/);
});

test("reselecting a Usage run reloads its detail even when its ID is unchanged", () => {
  const dashboard = read("../src/components/usage/usage-dashboard.tsx");
  const selectRecord = dashboard.match(/function selectRecord\(record: UsageRecord\) \{[\s\S]*?\n  \}/);
  assert.ok(selectRecord, "selectRecord handler should exist");
  assert.match(selectRecord[0], /setDetailVersion\(\(value\) => value \+ 1\)/);
});
