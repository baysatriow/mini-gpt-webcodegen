import assert from "node:assert/strict";
import test from "node:test";
import { isTrustedPreviewDocument } from "../src/lib/preview-security.ts";

const nonce = "previewNonce_12345678901";
const policy = [
  "default-src 'none'",
  "base-uri 'none'",
  "object-src 'none'",
  "form-action 'none'",
  "connect-src 'none'",
  `script-src 'nonce-${nonce}'`,
  `style-src 'nonce-${nonce}'`,
  "img-src data:",
].join("; ");

function documentWithPolicy(contentPolicy = policy) {
  return `<html><head><meta http-equiv="Content-Security-Policy" content="${contentPolicy}"></head><body></body></html>`;
}

test("accepts proxy-added same-origin sources while enforcing the strict embedded policy", () => {
  const normalizedHeader = policy
    .replaceAll("; ", " ;  ")
    .replace("connect-src 'none'", "connect-src 'none' 'self'")
    .replace(`script-src 'nonce-${nonce}'`, `script-src 'nonce-${nonce}' 'self'`)
    .replace(`style-src 'nonce-${nonce}'`, `style-src 'nonce-${nonce}' 'self'`)
    .replace("img-src data:", "img-src data: 'self'")
    + " ; font-src 'self'";
  assert.equal(isTrustedPreviewDocument(documentWithPolicy(), normalizedHeader), true);
});

test("accepts an entity-escaped meta policy normalized by the browser response layer", () => {
  const normalized = policy
    .replace("connect-src 'none'", "connect-src 'none' 'self'")
    .replace(`style-src 'nonce-${nonce}'`, `style-src 'nonce-${nonce}' 'self'`)
    .replace("img-src data:", "img-src data: 'self'")
    + "; font-src 'self'";
  const escapedMeta = normalized.replaceAll("'", "&#39;");
  const forbiddenScriptOrigin = normalized.replace(
    `script-src 'nonce-${nonce}'`,
    `script-src 'nonce-${nonce}' https://untrusted.example`,
  );

  assert.equal(isTrustedPreviewDocument(documentWithPolicy(escapedMeta), normalized), true);
  assert.equal(isTrustedPreviewDocument(documentWithPolicy(forbiddenScriptOrigin), forbiddenScriptOrigin), false);
});

test("rejects a preview whose embedded policy nonce differs from the response header", () => {
  const changed = policy.replace(nonce, "differentNonce_123456789012");
  assert.equal(isTrustedPreviewDocument(documentWithPolicy(changed), policy), false);
});

test("rejects previews that weaken or omit required CSP directives", () => {
  const weakened = policy.replace("script-src 'nonce-", "script-src 'unsafe-inline' 'nonce-");
  const missing = policy.replace("connect-src 'none'; ", "");
  assert.equal(isTrustedPreviewDocument(documentWithPolicy(weakened), weakened), false);
  assert.equal(isTrustedPreviewDocument(documentWithPolicy(missing), missing), false);
  assert.equal(isTrustedPreviewDocument("<html><head></head><body></body></html>", policy), false);
});
