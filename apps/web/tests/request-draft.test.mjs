import assert from "node:assert/strict";
import test from "node:test";
import { createDraft } from "../src/lib/request-draft.ts";


function landingFacts(overrides = {}) {
  return {
    genre: "landing_page",
    styleMode: "tailwind",
    name: "Kedai Contoh",
    description: "Kedai kopi contoh untuk pemeriksaan lokal.",
    value: "Kopi diseduh setelah dipesan.",
    services: [
      { title: "Manual brew", text: "Seduhan kopi manual." },
      { title: "Kopi susu", text: "Kopi susu racikan kedai." },
      { title: "Paket biji", text: "Biji kopi untuk dibawa pulang." },
    ],
    additionalFacts: [
      { kind: "process", title: "Pilih biji", text: "Pilih profil rasa." },
      { kind: "process", title: "Giling kopi", text: "Biji digiling saat dipesan." },
      { kind: "process", title: "Seduh kopi", text: "Kopi diseduh sesuai pilihan." },
      { kind: "faq", title: "Jam buka?", text: "Setiap hari pukul 09.00 sampai 21.00." },
      { kind: "faq", title: "Bisa pesan bawa pulang?", text: "Bisa, pesan di kasir." },
      { kind: "faq", title: "Ada pilihan tanpa susu?", text: "Ada kopi hitam dan teh." },
    ],
    requestedFeatureIds: [],
    assetIds: [],
    fictitious: true,
    ...overrides,
  };
}


test("createDraft rejects a landing page without the trained fact set", () => {
  const facts = landingFacts({ services: [{ title: "Manual brew", text: "Seduhan kopi manual." }] });

  assert.throws(() => createDraft("Buat landing page.", facts), /3 layanan/);
});

test("createDraft includes confirmed value facts and the matching local asset", () => {
  const draft = createDraft("Buat landing page.", landingFacts());

  assert.deepEqual(
    draft.business_facts.map(({ id, kind }) => [id, kind]),
    [
      ["business-name", "name"],
      ["business-description", "description"],
      ["business-value", "value"],
      ["service-1", "service"],
      ["service-2", "service"],
      ["service-3", "service"],
      ["process-1", "process"],
      ["process-2", "process"],
      ["process-3", "process"],
      ["faq-1", "faq"],
      ["faq-2", "faq"],
      ["faq-3", "faq"],
    ],
  );
  assert.deepEqual(draft.asset_ids, ["studio-shapes"]);
  assert.deepEqual(draft.business_facts[2].value, "Kopi diseduh setelah dipesan.");
  assert.deepEqual(draft.business_facts[2].evidence, { user_confirmed: true });
});

test("createDraft requires two company projects instead of landing page FAQs", () => {
  const facts = landingFacts({
    genre: "company_profile",
    additionalFacts: [
      ...landingFacts().additionalFacts.filter((fact) => fact.kind === "process"),
      { kind: "project", title: "Cangkir pagi", text: "Contoh karya keramik." },
      { kind: "project", title: "Vas senja", text: "Contoh vas pesanan." },
    ],
  });

  const draft = createDraft("Buat company profile.", facts);

  assert.deepEqual(draft.asset_ids, ["company-shapes"]);
  assert.equal(draft.business_facts.filter((fact) => fact.kind === "faq").length, 0);
  assert.equal(draft.business_facts.filter((fact) => fact.kind === "project").length, 2);
});
