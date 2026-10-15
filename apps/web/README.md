# Aplikasi web lokal

Frontend percakapan untuk generator landing page dan company profile. UI akan meminta fakta yang belum tersedia, memvalidasi draft lewat FastAPI, lalu menunggu konfirmasi sebelum generation.

## Konfigurasi lokal

Salin `.env.example` menjadi `.env.local` jika alamat API berbeda. Nilai bawaan menunjuk ke FastAPI lokal di `http://127.0.0.1:8000`.

```powershell
npm ci
npm run dev
```

Dokumentasi setup lengkap dan batas fitur akan dilengkapi setelah seluruh layar aplikasi tersusun. Membuka frontend tidak menjalankan generation.
