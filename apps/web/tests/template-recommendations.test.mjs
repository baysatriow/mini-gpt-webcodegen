import assert from "node:assert/strict";
import test from "node:test";
import { WEBSITE_TEMPLATES } from "../src/lib/website-templates.ts";

async function loadRecommendations() {
  return import("../src/lib/website-template-recommendations.ts").catch(() => null);
}

test("rerolling recommendations produces four unique choices and changes the sample", async () => {
  const recommendations = await loadRecommendations();
  assert.equal(typeof recommendations?.sampleWebsiteTemplates, "function");
  if (!recommendations) return;

  const first = recommendations.sampleWebsiteTemplates(WEBSITE_TEMPLATES, "all", 4).map((template) => template.id);
  const second = recommendations.sampleWebsiteTemplates(WEBSITE_TEMPLATES, "all", 5).map((template) => template.id);

  assert.equal(first.length, 4);
  assert.equal(new Set(first).size, 4);
  assert.notDeepEqual(second, first);
});

test("every template category, including community, can be selected", async () => {
  const recommendations = await loadRecommendations();
  assert.equal(typeof recommendations?.sampleWebsiteTemplates, "function");
  if (!recommendations) return;

  const community = recommendations.sampleWebsiteTemplates(WEBSITE_TEMPLATES, "community", 11);
  assert.equal(community.length, 4);
  assert.ok(community.every((template) => template.category === "community"));
});

test("clipboard helper reports success only after the text is copied", async () => {
  const clipboard = await import("../src/lib/clipboard.ts").catch(() => null);
  assert.equal(typeof clipboard?.copyTextToClipboard, "function");
  if (!clipboard) return;

  let copiedText = "";
  const copied = await clipboard.copyTextToClipboard("<h1>Rancang</h1>", {
    writeText: async (text) => {
      copiedText = text;
    },
  });

  assert.equal(copied, true);
  assert.equal(copiedText, "<h1>Rancang</h1>");
});

test("clipboard helper reports a denied clipboard write", async () => {
  const clipboard = await import("../src/lib/clipboard.ts").catch(() => null);
  assert.equal(typeof clipboard?.copyTextToClipboard, "function");
  if (!clipboard) return;

  const copied = await clipboard.copyTextToClipboard("Rancang AI", {
    writeText: async () => {
      throw new Error("Clipboard permission denied");
    },
  });

  assert.equal(copied, false);
});
