"use client";

import { useState } from "react";
import { Eye, EyeOff, LockKeyhole, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export function LoginForm() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
        cache: "no-store",
      });
      if (!response.ok) {
        setError(response.status === 503 ? "Akses belum dikonfigurasi dengan lengkap." : "Username atau password salah.");
        return;
      }
      window.location.replace("/");
    } catch {
      setError("Tidak dapat menghubungi server. Coba lagi.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5" aria-describedby="login-guidance">
      <div className="space-y-2">
        <label htmlFor="login-username" className="text-sm font-medium text-foreground">Username</label>
        <input
          id="login-username"
          name="username"
          autoComplete="username"
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
            className="h-11 w-full rounded-lg border border-border bg-background px-3.5 text-sm text-foreground outline-none transition focus-visible:border-primary focus-visible:ring-3 focus-visible:ring-primary/15"
        />
      </div>
      <div className="space-y-2">
        <label htmlFor="login-password" className="text-sm font-medium text-foreground">Password</label>
        <div className="relative">
          <input
            id="login-password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="h-11 w-full rounded-lg border border-border bg-background px-3.5 pr-12 text-sm text-foreground outline-none transition focus-visible:border-primary focus-visible:ring-3 focus-visible:ring-primary/15"
          />
          <button
            type="button"
            onClick={() => setShowPassword((visible) => !visible)}
            aria-label={showPassword ? "Sembunyikan password" : "Tampilkan password"}
            aria-pressed={showPassword}
            className="absolute inset-y-0 right-1 grid w-10 place-items-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {showPassword ? <EyeOff aria-hidden="true" className="size-4" /> : <Eye aria-hidden="true" className="size-4" />}
          </button>
        </div>
      </div>
      <p id="login-guidance" className="text-xs leading-relaxed text-muted-foreground">
        Sesi akses berlaku selama 12 jam pada perangkat ini.
      </p>
      {error ? <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2.5 text-sm text-destructive">{error}</p> : null}
      <Button type="submit" disabled={pending || !username || !password} className="h-11 w-full rounded-lg">
        {pending ? <Sparkles aria-hidden="true" className="size-4 animate-pulse" /> : <LockKeyhole aria-hidden="true" className="size-4" />}
        {pending ? "Memeriksa akses..." : "Masuk"}
      </Button>
    </form>
  );
}
