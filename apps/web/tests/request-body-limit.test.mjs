import assert from "node:assert/strict";
import test from "node:test";
import {
  readJsonWithByteLimit,
  RequestBodyTooLargeError,
} from "../src/lib/read-limited-json.mjs";

function streamedRequest(bytes, headers = {}) {
  return new Request("http://127.0.0.1/api/auth/login", {
    method: "POST",
    headers,
    body: new ReadableStream({
      start(controller) {
        controller.enqueue(bytes);
        controller.close();
      },
    }),
    duplex: "half",
  });
}

test("rejects an oversized streamed JSON body when Content-Length is absent", async () => {
  const request = streamedRequest(new Uint8Array(4097));

  assert.equal(request.headers.get("content-length"), null);
  await assert.rejects(
    readJsonWithByteLimit(request, 4096),
    RequestBodyTooLargeError,
  );
});

test("rejects a declared oversized body before parsing it", async () => {
  const request = streamedRequest(new TextEncoder().encode("{}"), {
    "content-length": "4097",
  });

  await assert.rejects(
    readJsonWithByteLimit(request, 4096),
    RequestBodyTooLargeError,
  );
});

test("classifies very large decimal Content-Length values as oversized", async () => {
  const request = streamedRequest(new TextEncoder().encode("{}"), {
    "content-length": "9007199254740992",
  });

  await assert.rejects(
    readJsonWithByteLimit(request, 4096),
    RequestBodyTooLargeError,
  );
});

test("accepts valid JSON exactly at the byte limit", async () => {
  const padding = "x".repeat(4096 - 11);
  const payload = JSON.stringify({ data: padding });
  const bytes = new TextEncoder().encode(payload);
  const request = streamedRequest(bytes);

  assert.equal(bytes.byteLength, 4096);
  assert.deepEqual(await readJsonWithByteLimit(request, 4096), {
    data: padding,
  });
});
