import { Sparkles } from "lucide-react";

export default function Home() {
  return (
    <main className="flex min-h-svh items-center justify-center px-6 py-12">
      <section className="w-full max-w-3xl">
        <div className="mb-8 flex items-center gap-3 text-sm font-semibold text-slate-note">
          <span className="grid size-10 place-items-center rounded-2xl bg-primary text-white">
            <Sparkles aria-hidden="true" className="size-5" />
          </span>
          Rancang
          <span className="ml-auto rounded-full border border-border bg-paper px-3 py-1 text-xs font-medium">
            Pipeline lokal
          </span>
        </div>
        <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-harbor-ink sm:text-4xl">
          Ubah ide menjadi halaman web, langkah demi langkah.
        </h1>
        <p className="mt-4 max-w-xl text-base leading-7 text-slate-note">
          Rancang mengumpulkan fakta melalui percakapan, meminta Anda meninjau
          ringkasan, lalu menyiapkan halaman untuk dilihat dan diunduh.
        </p>
        <div className="mt-8 flex items-center gap-2 rounded-2xl border border-border bg-paper px-4 py-3 text-sm text-slate-note">
          <span className="size-2 rounded-full bg-verified" aria-hidden="true" />
          Antarmuka percakapan lokal sedang disusun.
        </div>
      </section>
    </main>
  );
}
