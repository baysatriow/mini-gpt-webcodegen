function parseDirectives(policy: string): Map<string, string> | null {
  const directives = new Map<string, string>();
  for (const entry of policy.split(";")) {
    const [name, ...values] = entry.trim().split(/\s+/);
    if (!name) continue;
    if (directives.has(name)) return null;
    directives.set(name, values.join(" "));
  }
  return directives;
}

function scriptNonce(directives: Map<string, string>): string | null {
  const match = /(?:^|\s)'nonce-([A-Za-z0-9_-]{24})'(?:\s|$)/.exec(
    directives.get("script-src") ?? "",
  );
  return match?.[1] ?? null;
}

function hasBaseRestrictions(directives: Map<string, string>): boolean {
  const required = {
    "default-src": "'none'",
    "base-uri": "'none'",
    "object-src": "'none'",
    "form-action": "'none'",
  };
  return Object.entries(required).every(([name, value]) => directives.get(name) === value);
}

function hasOnlyAllowedSources(
  directives: Map<string, string>,
  name: string,
  required: string[],
  allowed: string[],
): boolean {
  const values = (directives.get(name) ?? "").split(/\s+/).filter(Boolean);
  return required.every((value) => values.includes(value))
    && values.every((value) => allowed.includes(value));
}

function hasExpectedResponsePolicy(directives: Map<string, string>, nonce: string): boolean {
  const nonceSource = `'nonce-${nonce}'`;
  const fontSources = directives.get("font-src");
  return hasBaseRestrictions(directives)
    && hasOnlyAllowedSources(directives, "connect-src", ["'none'"], ["'none'", "'self'"])
    && hasOnlyAllowedSources(directives, "script-src", [nonceSource], [nonceSource, "'self'"])
    && hasOnlyAllowedSources(directives, "style-src", [nonceSource], [nonceSource, "'self'"])
    && hasOnlyAllowedSources(directives, "img-src", ["data:"], ["data:", "'self'"])
    && (fontSources === undefined || fontSources === "'self'");
}

export function isTrustedPreviewDocument(document: string, responsePolicy: string): boolean {
  const meta = /<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"\s*\/?\s*>/i.exec(document);
  if (!meta) return false;

  const embeddedPolicy = meta[1].replace(/&#(?:0*39|x0*27);/gi, "'");
  const headerDirectives = parseDirectives(responsePolicy);
  const embeddedDirectives = parseDirectives(embeddedPolicy);
  if (!headerDirectives || !embeddedDirectives) return false;

  const nonce = scriptNonce(headerDirectives);
  if (!nonce || scriptNonce(embeddedDirectives) !== nonce) return false;
  if (
    /'unsafe-inline'|'unsafe-eval'/i.test(responsePolicy)
    || /'unsafe-inline'|'unsafe-eval'/i.test(embeddedPolicy)
  ) {
    return false;
  }

  return hasExpectedResponsePolicy(headerDirectives, nonce)
    && hasExpectedResponsePolicy(embeddedDirectives, nonce);
}
