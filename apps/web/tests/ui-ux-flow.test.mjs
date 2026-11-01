import assert from "node:assert/strict";
import test from "node:test";
import {
  chatReducer,
  createChatSession,
  createMessage,
  initialChatState,
} from "../src/lib/chat-state.ts";
import {
  WEBSITE_TEMPLATES,
  getWebsiteTemplate,
} from "../src/lib/website-templates.ts";
import {
  describeMissingFields,
  labelMissingField,
  INTAKE_STATUS_LABEL,
} from "../src/lib/intake-copy.ts";

test("WEBSITE_TEMPLATES catalog contains 100 templates with valid structures and categories", () => {
  assert.equal(WEBSITE_TEMPLATES.length, 100, "Must contain exactly 100 template ideas");

  const categories = new Set(["food", "retail", "service", "creative", "learning", "wellness", "community"]);
  for (const template of WEBSITE_TEMPLATES) {
    assert.ok(template.id, "Template must have an id");
    assert.ok(template.label, "Template must have a label");
    assert.ok(categories.has(template.category), `Invalid category: ${template.category}`);
    assert.ok(["landing_page", "company_profile"].includes(template.genre), "Genre must be landing_page or company_profile");

    const retrieved = getWebsiteTemplate(template.id);
    assert.equal(retrieved.id, template.id);
    assert.ok(retrieved.name, "Template must have a name");
    assert.equal(retrieved.services.length, 3, "Template must have 3 services");
    assert.ok(retrieved.additionalFacts.length >= 5, "Template must have at least 5 additional facts (process, faq/project)");
  }
});

test("chatReducer manages session creation, message appending, and state transitions", () => {
  let state = initialChatState;
  const session = createChatSession("Proyek Kedai Kopi");

  // Action: new session
  state = chatReducer(state, { type: "new_session", session });
  assert.equal(state.sessions.length, 1);
  assert.equal(state.activeSessionId, session.id);

  // Action: append user message
  const userMsg = createMessage({
    type: "user",
    content: "Buat landing page kedai kopi minimalis.",
  });
  state = chatReducer(state, {
    type: "append_message",
    sessionId: session.id,
    message: userMsg,
  });
  assert.equal(state.sessions[0].messages.length, 1);
  assert.equal(state.sessions[0].messages[0].content, "Buat landing page kedai kopi minimalis.");

  // Action: append generation status message
  const genMsg = createMessage({
    type: "generation_status",
    content: "Website berhasil digenerate.",
    status: "completed",
    generationId: "550e8400-e29b-41d4-a716-446655440000",
  });
  state = chatReducer(state, {
    type: "append_message",
    sessionId: session.id,
    message: genMsg,
  });
  assert.equal(state.sessions[0].messages.length, 2);
  assert.equal(state.sessions[0].messages[1].type, "generation_status");

  // Action: delete session
  state = chatReducer(state, { type: "delete_session", sessionId: session.id });
  assert.equal(state.sessions.length, 0);
  assert.equal(state.activeSessionId, null);
});

test("intake-copy describes missing business fields and status labels accurately in Indonesian", () => {
  assert.equal(labelMissingField("business_facts.name"), "Nama usaha");
  assert.equal(labelMissingField("business_facts.description"), "Deskripsi usaha");
  assert.equal(labelMissingField("business_facts.service"), "Tiga layanan usaha");
  assert.equal(labelMissingField("genre"), "Jenis halaman");

  const missing = describeMissingFields(["business_facts.name", "genre"]);
  assert.deepEqual(missing, ["Nama usaha", "Jenis halaman"]);

  assert.equal(INTAKE_STATUS_LABEL.needs_clarification, "Perlu dilengkapi");
  assert.equal(INTAKE_STATUS_LABEL.ready, "Siap ditinjau");
  assert.equal(INTAKE_STATUS_LABEL.unsupported_request, "Di luar cakupan");
  assert.equal(INTAKE_STATUS_LABEL.input_too_long, "Melewati batas input");
});

test("generation id validation pattern matches standard UUID format", () => {
  const GENERATION_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  assert.equal(GENERATION_ID_PATTERN.test("550e8400-e29b-41d4-a716-446655440000"), true);
  assert.equal(GENERATION_ID_PATTERN.test("invalid-uuid"), false);
  assert.equal(GENERATION_ID_PATTERN.test("../etc/passwd"), false);
});
