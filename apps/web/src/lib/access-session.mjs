import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";

export const SESSION_COOKIE_NAME = "rancang_session";
export const SESSION_MAX_AGE_SECONDS = 12 * 60 * 60;
const MIN_SESSION_SECRET_LENGTH = 32;
const MIN_PASSWORD_LENGTH = 16;

export function isAccessRequired(env = process.env) {
  return env.APP_ACCESS_REQUIRED === "true";
}

export function isAccessConfigured(env = process.env) {
  if (!isAccessRequired(env)) return true;
  return (
    typeof env.APP_ACCESS_USERNAME === "string" &&
    env.APP_ACCESS_USERNAME.length > 0 &&
    typeof env.APP_ACCESS_PASSWORD === "string" &&
    env.APP_ACCESS_PASSWORD.length >= MIN_PASSWORD_LENGTH &&
    typeof env.APP_SESSION_SECRET === "string" &&
    env.APP_SESSION_SECRET.length >= MIN_SESSION_SECRET_LENGTH
  );
}

export function constantTimeStringEqual(left, right) {
  if (typeof left !== "string" || typeof right !== "string") return false;
  const leftDigest = createHash("sha256").update(left).digest();
  const rightDigest = createHash("sha256").update(right).digest();
  return timingSafeEqual(leftDigest, rightDigest);
}

export function isSameHostOrigin(origin, host) {
  if (typeof origin !== "string" || typeof host !== "string" || !host.trim()) return false;
  try {
    const parsed = new URL(origin);
    return (
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      !parsed.username &&
      !parsed.password &&
      parsed.host.toLowerCase() === host.trim().toLowerCase() &&
      parsed.pathname === "/" &&
      !parsed.search &&
      !parsed.hash
    );
  } catch {
    return false;
  }
}

export function createSessionToken(secret, nowMs = Date.now()) {
  if (typeof secret !== "string" || secret.length < MIN_SESSION_SECRET_LENGTH) {
    throw new Error("Session secret is not configured");
  }
  const issuedAt = Math.floor(nowMs / 1000);
  const expiresAt = issuedAt + SESSION_MAX_AGE_SECONDS;
  const nonce = randomBytes(16).toString("base64url");
  const payload = `v1.${issuedAt}.${expiresAt}.${nonce}`;
  const signature = createHmac("sha256", secret).update(payload).digest("base64url");
  return `${payload}.${signature}`;
}

export function verifySessionToken(token, secret, nowMs = Date.now()) {
  if (
    typeof token !== "string" ||
    token.length > 256 ||
    typeof secret !== "string" ||
    secret.length < MIN_SESSION_SECRET_LENGTH
  ) {
    return false;
  }
  const parts = token.split(".");
  if (parts.length !== 5 || parts[0] !== "v1") return false;
  const [, issuedText, expiresText, nonce, suppliedSignature] = parts;
  if (!/^\d{1,12}$/.test(issuedText) || !/^\d{1,12}$/.test(expiresText)) return false;
  if (!/^[A-Za-z0-9_-]{22}$/.test(nonce) || !/^[A-Za-z0-9_-]{43}$/.test(suppliedSignature)) return false;

  const issuedAt = Number(issuedText);
  const expiresAt = Number(expiresText);
  const now = Math.floor(nowMs / 1000);
  if (
    !Number.isSafeInteger(issuedAt) ||
    !Number.isSafeInteger(expiresAt) ||
    issuedAt > now + 60 ||
    expiresAt <= now ||
    expiresAt <= issuedAt ||
    expiresAt - issuedAt > SESSION_MAX_AGE_SECONDS
  ) {
    return false;
  }

  const payload = `${parts[0]}.${issuedText}.${expiresText}.${nonce}`;
  const expected = createHmac("sha256", secret).update(payload).digest();
  const supplied = Buffer.from(suppliedSignature, "base64url");
  return supplied.length === expected.length && timingSafeEqual(supplied, expected);
}
