import assert from "node:assert/strict";
import test from "node:test";
import { formatSourceCode } from "../src/lib/source-format.ts";

test("formats a single-line generated HTML document for reading", async () => {
  const source = "<!doctype html><html><head><title>Demo</title></head><body><main><h1>Halo</h1><p>Contoh</p></main></body></html>";
  const formatted = await formatSourceCode("index.html", source);

  assert.ok(formatted.split("\n").length > 5);
  assert.match(formatted, /\n  <body>/);
  assert.match(formatted, /<h1>Halo<\/h1>/);
});

test("formats minified CSS and JavaScript into readable lines", async () => {
  const css = ".card{display:grid;gap:1rem;color:#123456}@media(max-width:600px){.card{grid-template-columns:1fr}}";
  const js = "document.querySelectorAll('[data-menu]').forEach(root=>{const button=root.querySelector('[data-menu-button]');button.addEventListener('click',()=>{button.setAttribute('aria-expanded','true')})})";

  const formattedCss = await formatSourceCode("styles.css", css);
  const formattedJs = await formatSourceCode("app.js", js);

  assert.ok(formattedCss.split("\n").length > 3);
  assert.ok(formattedJs.split("\n").length > 3);
  assert.match(formattedJs, /addEventListener/);
});

test("rejects unsupported file names instead of guessing a parser", async () => {
  await assert.rejects(() => formatSourceCode("unknown.txt", "some content"), /Unsupported source file/);
});
