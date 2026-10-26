import assert from "node:assert/strict";
import test from "node:test";
import {
  createSessionToken,
  isAccessConfigured,
  isAccessRequired,
  isSameHostOrigin,
  verifySessionToken,
} from "../src/lib/access-session.mjs";

const secret = "test-session-secret-with-more-than-thirty-two-characters";
const now = Date.UTC(2026, 9, 26, 5, 0, 0);

test("signed sessions accept valid tokens and reject expiry, tampering, and malformed values", () => {
  const token = createSessionToken(secret, now);
  assert.equal(verifySessionToken(token, secret, now + 1), true);
  assert.equal(verifySessionToken(token, secret, now + 12 * 60 * 60 * 1000 + 1), false);
  assert.equal(verifySessionToken(`${token}x`, secret, now + 1), false);
  assert.equal(verifySessionToken("not-a-token", secret, now + 1), false);
  assert.equal(verifySessionToken(undefined, secret, now + 1), false);
});

test("access is open only when not explicitly required and required configuration is complete", () => {
  assert.equal(isAccessRequired({}), false);
  assert.equal(isAccessRequired({ APP_ACCESS_REQUIRED: "true" }), true);
  assert.equal(isAccessConfigured({ APP_ACCESS_REQUIRED: "false" }), true);
  assert.equal(isAccessConfigured({ APP_ACCESS_REQUIRED: "true" }), false);
  assert.equal(
    isAccessConfigured({
      APP_ACCESS_REQUIRED: "true",
      APP_ACCESS_USERNAME: "demo",
      APP_ACCESS_PASSWORD: "short",
      APP_SESSION_SECRET: secret,
    }),
    false,
  );
  assert.equal(
    isAccessConfigured({
      APP_ACCESS_REQUIRED: "true",
      APP_ACCESS_USERNAME: "demo",
      APP_ACCESS_PASSWORD: "long-enough-password-value",
      APP_SESSION_SECRET: secret,
    }),
    true,
  );
});

test("login origin must match the request host exactly", () => {
  assert.equal(isSameHostOrigin("https://demo.example", "demo.example"), true);
  assert.equal(isSameHostOrigin("http://localhost:3000", "localhost:3000"), true);
  assert.equal(isSameHostOrigin("https://evil.example", "demo.example"), false);
  assert.equal(isSameHostOrigin("null", "demo.example"), false);
  assert.equal(isSameHostOrigin(undefined, "demo.example"), false);
  assert.equal(isSameHostOrigin("https://demo.example/path", "demo.example"), false);
});
