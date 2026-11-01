export class RequestBodyTooLargeError extends Error {
  constructor() {
    super("Request body exceeds the configured byte limit");
    this.name = "RequestBodyTooLargeError";
  }
}

export async function readJsonWithByteLimit(request, maxBytes) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 0) {
    throw new RangeError("maxBytes must be a non-negative safe integer");
  }

  const contentLength = request.headers.get("content-length");
  if (contentLength !== null) {
    if (!/^\d+$/.test(contentLength)) {
      throw new SyntaxError("Invalid Content-Length header");
    }

    const declaredBytes = Number(contentLength);
    if (!Number.isSafeInteger(declaredBytes)) {
      throw new RequestBodyTooLargeError();
    }
    if (declaredBytes > maxBytes) {
      throw new RequestBodyTooLargeError();
    }
  }

  if (!request.body) {
    throw new SyntaxError("Request body is missing");
  }

  const reader = request.body.getReader();
  const chunks = [];
  let totalBytes = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      totalBytes += value.byteLength;
      if (totalBytes > maxBytes) {
        try {
          await reader.cancel();
        } catch {
          // The request may already be closing while the byte limit is reached.
        }
        throw new RequestBodyTooLargeError();
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }

  const bytes = new Uint8Array(totalBytes);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }

  const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  return JSON.parse(text);
}
