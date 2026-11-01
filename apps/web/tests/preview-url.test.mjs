import assert from "node:assert/strict";
import test from "node:test";
import { getShareablePreviewUrl } from "../src/lib/shareable-preview-url.ts";

test("copied preview paths remain usable on the current local or tunnel origin", () => {
  const path = "/api/v1/generations/example/preview/index.html";
  for (const origin of ["http://127.0.0.1:3000", "https://demo.trycloudflare.com"]) {
    assert.equal(getShareablePreviewUrl(path, `${origin}/usage`), `${origin}${path}`);
  }
});

test("absolute preview URLs retain their configured origin and escaped path", () => {
  const url = "https://preview.example/api/result%20one/index.html";
  assert.equal(getShareablePreviewUrl(url, "https://app.example/"), url);
});

test("non-web preview URLs cannot be copied as shareable site links", () => {
  for (const src of ["javascript:alert(1)", "data:text/html,example", "file:///example.html"]) {
    assert.throws(() => getShareablePreviewUrl(src, "https://app.example/"));
  }
});
