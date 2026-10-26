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
});

test("Usage dashboard explains unavailable telemetry and renders readable outcome labels", () => {
  const source = read("../src/components/usage/usage-dashboard.tsx");
  assert.match(source, /Telemetri GPU belum tersedia/);
  assert.match(source, /Tidak ada data GPU selama proses generate/);
  assert.match(source, /function outcomeLabel/);
  assert.match(source, /aria-label/);
  assert.match(source, /Kembali ke chat/);
});

test("Usage metric values wrap on narrow screens instead of truncating", () => {
  const source = read("../src/components/usage/usage-dashboard.tsx");
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
