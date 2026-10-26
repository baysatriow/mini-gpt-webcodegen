import { redirect } from "next/navigation";
import { LockKeyhole, ShieldAlert } from "lucide-react";
import { LoginForm } from "@/components/auth/login-form";
import { isAccessConfigured, isAccessRequired } from "@/lib/access-session.mjs";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  if (!isAccessRequired()) redirect("/");

  const configured = isAccessConfigured();
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-5 py-10">
      <section className="w-full max-w-md rounded-3xl border border-border bg-card p-7 shadow-sm sm:p-9">
        <div className="mb-7 flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-2xl bg-primary text-primary-foreground">
            {configured ? <LockKeyhole aria-hidden="true" className="size-5" /> : <ShieldAlert aria-hidden="true" className="size-5" />}
          </span>
          <div>
            <p className="text-sm font-semibold tracking-tight text-foreground">Rancang AI</p>
            <p className="text-xs text-muted-foreground">Akses aplikasi</p>
          </div>
        </div>
        {configured ? (
          <>
            <div className="mb-6 space-y-2">
              <h1 className="text-2xl font-semibold tracking-tight text-foreground">Masuk untuk melanjutkan</h1>
              <p className="text-sm leading-relaxed text-muted-foreground">Aplikasi ini dibagikan secara terbatas. Masukkan kredensial akses untuk membuka ruang kerja.</p>
            </div>
            <LoginForm />
          </>
        ) : (
          <div className="space-y-3" role="alert">
            <h1 className="text-xl font-semibold tracking-tight text-foreground">Akses belum siap</h1>
            <p className="text-sm leading-relaxed text-muted-foreground">Konfigurasi login server belum lengkap. Halaman dan API tetap dikunci sampai konfigurasi diperbaiki.</p>
          </div>
        )}
      </section>
    </main>
  );
}
