import type { PageGenre, StyleMode } from "@/lib/api-types";

type IdeaCategory = "food" | "retail" | "service" | "creative" | "learning" | "wellness" | "community";
type IdeaSeed = { id: string; label: string; category: IdeaCategory };

const IDEA_SEEDS = [
  { id: "coffee-shop", label: "Kedai kopi", category: "food" },
  { id: "bakery", label: "Toko roti", category: "food" },
  { id: "tea-house", label: "Kedai teh", category: "food" },
  { id: "ice-cream-shop", label: "Toko es krim", category: "food" },
  { id: "juice-bar", label: "Bar jus", category: "food" },
  { id: "healthy-meals", label: "Katering makanan sehat", category: "food" },
  { id: "catering", label: "Usaha katering", category: "food" },
  { id: "food-truck", label: "Food truck", category: "food" },
  { id: "noodle-house", label: "Kedai mi", category: "food" },
  { id: "burger-kitchen", label: "Dapur burger", category: "food" },
  { id: "seafood-kitchen", label: "Kedai hidangan laut", category: "food" },
  { id: "traditional-snacks", label: "Toko camilan tradisional", category: "food" },
  { id: "artisan-chocolate", label: "Studio cokelat", category: "food" },
  { id: "vegan-kitchen", label: "Dapur makanan nabati", category: "food" },
  { id: "breakfast-cafe", label: "Kafe sarapan", category: "food" },
  { id: "rice-bowl-kitchen", label: "Kedai rice bowl", category: "food" },
  { id: "pizza-kitchen", label: "Dapur pizza", category: "food" },
  { id: "dessert-studio", label: "Studio hidangan penutup", category: "food" },
  { id: "spice-shop", label: "Toko rempah", category: "food" },
  { id: "meal-prep-service", label: "Layanan meal prep", category: "food" },
  { id: "florist", label: "Toko bunga", category: "retail" },
  { id: "bookstore", label: "Toko buku", category: "retail" },
  { id: "thrift-store", label: "Toko pakaian preloved", category: "retail" },
  { id: "ceramics-studio", label: "Studio keramik", category: "creative" },
  { id: "modest-fashion", label: "Butik busana", category: "retail" },
  { id: "sneaker-store", label: "Toko sneakers", category: "retail" },
  { id: "stationery-shop", label: "Toko alat tulis", category: "retail" },
  { id: "skincare-brand", label: "Merek perawatan kulit", category: "retail" },
  { id: "home-decor-store", label: "Toko dekorasi rumah", category: "retail" },
  { id: "furniture-studio", label: "Studio furnitur", category: "retail" },
  { id: "plant-shop", label: "Toko tanaman", category: "retail" },
  { id: "toy-store", label: "Toko mainan", category: "retail" },
  { id: "pet-supplies", label: "Toko perlengkapan hewan", category: "retail" },
  { id: "craft-market", label: "Pasar produk kerajinan", category: "retail" },
  { id: "coffee-roaster", label: "Roastery kopi", category: "food" },
  { id: "jewelry-studio", label: "Studio perhiasan", category: "creative" },
  { id: "gift-shop", label: "Toko hadiah", category: "retail" },
  { id: "eyewear-store", label: "Toko kacamata", category: "retail" },
  { id: "sportswear-store", label: "Toko pakaian olahraga", category: "retail" },
  { id: "organic-grocery", label: "Toko bahan pangan", category: "retail" },
  { id: "barber-shop", label: "Barbershop", category: "service" },
  { id: "hair-salon", label: "Salon rambut", category: "service" },
  { id: "laundry-service", label: "Layanan laundry", category: "service" },
  { id: "home-cleaning", label: "Layanan kebersihan rumah", category: "service" },
  { id: "appliance-repair", label: "Servis peralatan rumah", category: "service" },
  { id: "bicycle-repair", label: "Bengkel sepeda", category: "service" },
  { id: "phone-repair", label: "Servis ponsel", category: "service" },
  { id: "car-detailing", label: "Perawatan kendaraan", category: "service" },
  { id: "moving-service", label: "Jasa pindahan", category: "service" },
  { id: "event-planning", label: "Jasa perencana acara", category: "service" },
  { id: "wedding-photography", label: "Fotografi pernikahan", category: "creative" },
  { id: "portrait-photography", label: "Studio foto potret", category: "creative" },
  { id: "travel-planning", label: "Perencana perjalanan", category: "service" },
  { id: "tutoring-center", label: "Bimbingan belajar", category: "learning" },
  { id: "language-course", label: "Kursus bahasa", category: "learning" },
  { id: "accounting-service", label: "Jasa pembukuan", category: "service" },
  { id: "home-renovation", label: "Jasa renovasi rumah", category: "service" },
  { id: "interior-consulting", label: "Konsultan interior", category: "creative" },
  { id: "garden-care", label: "Jasa perawatan taman", category: "service" },
  { id: "tailoring-service", label: "Jasa jahit", category: "service" },
  { id: "design-studio", label: "Studio desain", category: "creative" },
  { id: "content-studio", label: "Studio konten", category: "creative" },
  { id: "branding-agency", label: "Agensi branding", category: "creative" },
  { id: "web-studio", label: "Studio website", category: "creative" },
  { id: "video-production", label: "Studio produksi video", category: "creative" },
  { id: "animation-studio", label: "Studio animasi", category: "creative" },
  { id: "music-school", label: "Sekolah musik", category: "learning" },
  { id: "art-studio", label: "Studio seni", category: "creative" },
  { id: "architecture-studio", label: "Studio arsitektur", category: "creative" },
  { id: "social-media-studio", label: "Studio media sosial", category: "creative" },
  { id: "seo-studio", label: "Studio optimasi web", category: "creative" },
  { id: "copywriting-studio", label: "Studio penulisan konten", category: "creative" },
  { id: "podcast-production", label: "Studio produksi podcast", category: "creative" },
  { id: "handmade-gifts", label: "Studio hadiah buatan tangan", category: "creative" },
  { id: "graphic-design-studio", label: "Studio desain grafis", category: "creative" },
  { id: "illustration-studio", label: "Studio ilustrasi", category: "creative" },
  { id: "community-media", label: "Media komunitas", category: "community" },
  { id: "product-photography", label: "Studio foto produk", category: "creative" },
  { id: "advertising-studio", label: "Studio periklanan", category: "creative" },
  { id: "creative-workshop", label: "Lokakarya kreatif", category: "learning" },
  { id: "yoga-studio", label: "Studio yoga", category: "wellness" },
  { id: "pilates-studio", label: "Studio pilates", category: "wellness" },
  { id: "fitness-gym", label: "Pusat kebugaran", category: "wellness" },
  { id: "dance-school", label: "Sekolah tari", category: "learning" },
  { id: "martial-arts-studio", label: "Studio bela diri", category: "wellness" },
  { id: "swimming-school", label: "Sekolah renang", category: "learning" },
  { id: "coding-school", label: "Kelas pemrograman", category: "learning" },
  { id: "art-classes", label: "Kelas seni", category: "learning" },
  { id: "music-course", label: "Kursus musik", category: "learning" },
  { id: "child-learning-center", label: "Pusat belajar anak", category: "learning" },
  { id: "language-club", label: "Klub bahasa", category: "community" },
  { id: "community-library", label: "Perpustakaan komunitas", category: "community" },
  { id: "local-museum", label: "Museum lokal", category: "community" },
  { id: "camping-tour", label: "Paket wisata alam", category: "service" },
  { id: "bicycle-tour", label: "Tur sepeda", category: "service" },
  { id: "fitness-coaching", label: "Pendampingan kebugaran", category: "wellness" },
  { id: "meditation-class", label: "Kelas meditasi", category: "wellness" },
  { id: "healthy-cooking-class", label: "Kelas memasak sehat", category: "learning" },
  { id: "sports-club", label: "Klub olahraga", category: "community" },
  { id: "family-playground", label: "Ruang bermain keluarga", category: "community" },
] as const satisfies ReadonlyArray<IdeaSeed>;

export type WebsiteTemplateId = (typeof IDEA_SEEDS)[number]["id"];
export type WebsiteTemplateFact = {
  kind: "project" | "process" | "faq";
  title: string;
  text: string;
};

export type WebsiteTemplate = {
  id: WebsiteTemplateId;
  label: string;
  category: IdeaCategory;
  prompt: string;
  genre: PageGenre;
  styleMode: StyleMode;
  name: string;
  description: string;
  value: string;
  services: Array<{ title: string; text: string }>;
  additionalFacts: WebsiteTemplateFact[];
};

const SERVICES_BY_CATEGORY: Record<IdeaCategory, [string, string, string]> = {
  food: ["Menu pilihan", "Paket pesanan", "Pesanan khusus"],
  retail: ["Koleksi produk", "Paket pilihan", "Pesanan khusus"],
  service: ["Layanan utama", "Paket layanan", "Konsultasi awal"],
  creative: ["Eksplorasi konsep", "Produksi karya", "Pendampingan proyek"],
  learning: ["Kelas pemula", "Kelas lanjutan", "Sesi privat"],
  wellness: ["Sesi reguler", "Kelas pemula", "Pendampingan personal"],
  community: ["Program komunitas", "Kegiatan terjadwal", "Keanggotaan"],
};

const COMPANY_PROFILE_IDS = new Set<string>([
  "accounting-service",
  "event-planning",
  "tutoring-center",
  "language-course",
  "design-studio",
  "branding-agency",
  "web-studio",
  "video-production",
  "architecture-studio",
  "advertising-studio",
  "music-school",
  "community-media",
  "community-library",
  "local-museum",
  "sports-club",
]);

function createTemplate(seed: (typeof IDEA_SEEDS)[number], index: number): WebsiteTemplate {
  const genre: PageGenre = COMPANY_PROFILE_IDS.has(seed.id) ? "company_profile" : "landing_page";
  const styleMode: StyleMode = index % 2 === 0 ? "tailwind" : "plain_css";
  const name = `Contoh ${seed.label}`;
  const serviceNames = SERVICES_BY_CATEGORY[seed.category];
  const services = serviceNames.map((title) => ({
    title,
    text: `Contoh ${title.toLowerCase()} untuk ${seed.label.toLowerCase()} fiktif. Sesuaikan rincian ini dengan penawaran sebenarnya.`,
  }));
  const processFacts: WebsiteTemplateFact[] = [
    { kind: "process", title: "Tentukan kebutuhan", text: "Pilih layanan yang sesuai dengan kebutuhan Anda." },
    { kind: "process", title: "Tinjau pilihan", text: "Periksa pilihan yang tersedia dan sesuaikan dengan kebutuhan Anda." },
    { kind: "process", title: "Konfirmasi rincian", text: "Hubungi tim usaha untuk memastikan detail dan cara pemesanan." },
  ];
  const pageFacts: WebsiteTemplateFact[] = genre === "company_profile"
    ? [
        { kind: "project", title: `Contoh proyek ${seed.label}`, text: "Contoh portofolio fiktif. Ganti dengan proyek yang benar dan boleh ditampilkan." },
        { kind: "project", title: `Contoh karya ${seed.label}`, text: "Contoh karya fiktif. Ganti dengan karya yang benar dan boleh ditampilkan." },
      ]
    : [
        { kind: "faq", title: "Apa saja yang ditawarkan?", text: `Contoh ini memuat ${serviceNames.map((item) => item.toLowerCase()).join(", ")}. Sesuaikan dengan penawaran sebenarnya.` },
        { kind: "faq", title: "Bagaimana cara memulai?", text: "Pilih layanan, lalu hubungi tim usaha untuk mengetahui cara pemesanan." },
        { kind: "faq", title: "Apakah data ini nyata?", text: "Tidak. Nama dan isi template ini adalah contoh fiktif yang bisa Anda ubah." },
      ];

  return {
    id: seed.id,
    label: seed.label,
    category: seed.category,
    prompt: `Buat ${genre === "company_profile" ? "company profile" : "landing page"} untuk ${seed.label.toLowerCase()} fiktif bernama ${name}. Gunakan ${styleMode === "tailwind" ? "Tailwind CSS" : "CSS biasa"}.`,
    genre,
    styleMode,
    name,
    description: `Contoh ${seed.label.toLowerCase()} fiktif. Gunakan halaman ini sebagai titik awal, lalu ganti semua informasi dengan fakta usaha yang benar.`,
    value: `Tampilkan ${serviceNames[0].toLowerCase()} dan informasi utama dengan susunan yang ringkas serta mudah dipahami.`,
    services,
    additionalFacts: [...processFacts, ...pageFacts],
  };
}

export const WEBSITE_TEMPLATES: WebsiteTemplate[] = IDEA_SEEDS.map(createTemplate);

export function isWebsiteTemplateId(value: unknown): value is WebsiteTemplateId {
  return typeof value === "string" && WEBSITE_TEMPLATES.some((template) => template.id === value);
}

export function getWebsiteTemplate(id: WebsiteTemplateId): WebsiteTemplate {
  return WEBSITE_TEMPLATES.find((template) => template.id === id)!;
}
