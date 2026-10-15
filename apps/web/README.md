# Aplikasi web lokal

Frontend Next.js untuk meminta landing page atau company profile melalui chat, melengkapi fakta secara eksplisit, menyetujui ringkasan, lalu meninjau hasil FastAPI. UI hanya menampilkan preview, source, dan unduhan setelah API mengembalikan status `completed`.

## Menjalankan secara lokal

Pastikan FastAPI sudah disiapkan dan berjalan pada `http://127.0.0.1:8000`. Ikuti [panduan API lokal](../api/README.md) untuk dependency dan perintah server. Referensi API tersedia di [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Dari folder `apps/web`, salin konfigurasi contoh saat pertama kali menyiapkan frontend:

```powershell
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Buka [http://localhost:3000](http://localhost:3000). `NEXT_PUBLIC_API_BASE_URL` pada `.env.local` menentukan origin FastAPI; nilai contoh memakai `http://127.0.0.1:8000`. Jika API berjalan pada origin lain, ubah nilai ini dan pastikan origin frontend tersebut diizinkan oleh konfigurasi CORS API.

## Batas runtime

- Membuka UI hanya mengambil katalog lokal dan tidak menjalankan model.
- Prompt menjalankan validasi intake. Inference baru diminta setelah ringkasan lengkap dan pengguna memilih **Setujui dan buat halaman**.
- Form intake menampilkan pilihan fitur di luar cakupan dari katalog. API juga mencocokkan istilah yang tercantum dalam katalog dengan prompt; pencocokan ini memakai frasa tetap, bukan pemahaman semantik umum.
- Chat dan referensi generation disimpan di `localStorage` browser. Source hasil tidak disimpan di riwayat browser.
- Tab kode mengambil `index.html`, `styles.css`, dan `app.js` dari endpoint allowlist API hanya untuk generation yang diterima.
- Preview memeriksa status HTTP endpoint lokal sebelum membuka iframe sandbox. Tombol coba lagi mengulangi pemeriksaan dan preview tanpa generation baru. Ukuran desktop memakai lebar 1280 piksel dan ukuran mobile 390 piksel.
- UI tidak meminta model menulis atau menjalankan JavaScript bebas.

Spesifikasi produk ada di [desain aplikasi chat generator](../../docs/superpowers/specs/2026-10-15-generator-chat-application-design.md). Kode UI belum dijalankan di browser dan belum menjalani review visual atau verifikasi end-to-end.
