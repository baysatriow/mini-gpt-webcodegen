# WebCraft GPT by VibeStack

Frontend Next.js untuk membuat landing page atau company profile dari satu brief. Layar awal menyediakan 100 ide contoh fiktif dan menampilkan tiga ide sekaligus; tombol **Acak ide** menggantinya. Memilih ide mengisi form fakta otomatis, dan semua data tetap dapat diedit sebelum validasi. Brief bebas tetap menggunakan extractor dan editor manual bila extractor belum tersedia. Pengguna memeriksa fakta dan kutipan sumber, lalu memilih **Generate website**. UI hanya menampilkan preview, source, dan unduhan setelah API mengembalikan status `completed`.

## Menjalankan secara lokal

Pastikan FastAPI sudah disiapkan dan berjalan pada `http://127.0.0.1:8000`. Ikuti [panduan API lokal](../api/README.md) untuk dependency dan perintah server. Referensi API tersedia di [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Next.js meneruskan `/api/v1/*` ke FastAPI melalui rewrite server, sehingga browser dan tunnel cukup mengakses origin Next.js.

Dari folder `apps/web`, salin konfigurasi contoh saat pertama kali menyiapkan frontend:

```powershell
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Buat `.env.local` dari `.env.example`, lalu jalankan frontend. Buka [http://localhost:3000](http://localhost:3000). `API_SERVER_ORIGIN` menentukan origin FastAPI yang dipakai rewrite Next.js dan secara default menunjuk ke `http://127.0.0.1:8000`. Biarkan `NEXT_PUBLIC_API_BASE_URL` kosong agar panggilan dari browser memakai origin yang sama, termasuk saat frontend dibagikan lewat tunnel.

## Usage dan audit proses

Halaman [Usage](http://localhost:3000/usage) menampilkan snapshot GPU saat ini, ringkasan hasil generate, cakupan sampel, dan daftar audit. Pilih 24 jam, 7 hari, atau 30 hari. Setiap baris dapat dibuka untuk melihat urutan tahapan, sampel GPU, dan ringkasan memori PyTorch.

Snapshot GPU diperbarui ketika halaman terlihat. Riwayat `nvidia-smi` hanya merekam sampel selama generation berjalan, dengan cakupan seluruh perangkat. Untuk itu, beban aplikasi lain juga dapat muncul pada metrik perangkat. Tidak ada sampel berarti data tidak tersedia, bukan nilai nol. Metrik alokasi dan reservasi PyTorch ditampilkan terpisah.

Audit menyimpan metadata operasional seperti ID, waktu, durasi, status, tahap, kode kendala, jumlah token atau bagian jika tersedia, dan telemetri. Prompt, fakta bisnis, source, hasil website, exception mentah, kredensial, dan path lokal tidak disimpan oleh fitur Usage. Database berada di `outputs/webapp/usages`, di luar Git, dengan retensi 90 hari. Katalog dan halaman Usage tidak memuat model atau menjalankan inference.

## Login saat dibagikan lewat Quick Tunnel

Autentikasi lokal tidak aktif secara default. Sebelum membuka tunnel, isi `apps/web/.env.local` dengan konfigurasi server berikut:

```dotenv
APP_ACCESS_REQUIRED=true
APP_ACCESS_USERNAME=nama-pengguna
APP_ACCESS_PASSWORD=password-acak-minimal-16-karakter
APP_SESSION_SECRET=secret-acak-minimal-32-karakter
```

Gunakan password dan secret yang berbeda. File `.env.local` diabaikan Git, jangan menyalin nilainya ke dokumentasi atau commit. Login buatan aplikasi mendukung tampilkan/sembunyikan password, memeriksa origin request, dan memberi cookie sesi HttpOnly selama 12 jam. Tombol **Keluar** ada di sidebar dan halaman Usage. Cookie memakai atribut `Secure` saat diakses lewat HTTPS.

Quick Tunnel hanya boleh mengarah ke Next.js pada `http://127.0.0.1:3000`. Jangan membuka port FastAPI `8000` ke tunnel. Sebelum tunnel aktif, periksa bahwa halaman tanpa sesi diarahkan ke `/login` dan endpoint `/api/v1/*` mengembalikan `401`. Quick Tunnel menghasilkan URL sementara yang dapat berubah ketika proses tunnel dimulai ulang.

## Batas runtime

- Membuka UI hanya mengambil katalog lokal dan tidak menjalankan model.
- Memilih salah satu template adalah pilihan eksplisit untuk memakai data contoh fiktif. Pemilihan dan pengacakan ide berlangsung di browser tanpa memanggil extractor atau membuat halaman.
- Mengirim brief memanggil `POST /api/v1/intake/extract` jika extractor telah melewati gate dan dipilih. Extractor tidak membuat halaman; setiap fakta yang diterima harus memiliki bukti pada pesan sumber.
- Jika extractor belum dipromosikan, tidak tersedia, atau menolak input, brief tetap tersimpan dan UI mengarahkan pengguna ke editor manual. Tidak ada fakta usaha yang boleh direka untuk mengisi kekurangan.
- Semua fakta wajib tetap dibutuhkan. Satu jawaban klarifikasi mengisi kekurangan yang dirangkum; jika masih belum lengkap, editor hanya menampilkan bagian yang tersisa.
- Pengguna memeriksa ringkasan dan bukti sumber sebelum **Generate website**. Hanya tindakan ini yang memulai generation melalui FastAPI.
- Form intake menampilkan pilihan fitur di luar cakupan dari katalog. API juga mencocokkan istilah yang tercantum dalam katalog dengan prompt; pencocokan ini memakai frasa tetap, bukan pemahaman semantik umum.
- Brief dibatasi 4.000 karakter dan tidak dipotong diam-diam.
- Chat dan referensi generation disimpan di `localStorage` browser. Source hasil tidak disimpan di riwayat browser.
- Tab kode mengambil `index.html`, `styles.css`, dan `app.js` dari endpoint allowlist API hanya untuk generation yang diterima.
- Preview memeriksa status HTTP endpoint lokal sebelum membuka iframe sandbox. Tombol coba lagi mengulangi pemeriksaan dan preview tanpa generation baru. Ukuran desktop memakai lebar 1280 piksel dan ukuran mobile 390 piksel.
- UI tidak meminta model menulis atau menjalankan JavaScript bebas.

Spesifikasi produk ada di [desain aplikasi chat generator](../../docs/superpowers/specs/2026-10-15-generator-chat-application-design.md) dan [desain intake prompt-first](../../docs/superpowers/specs/2026-10-16-prompt-first-intake-design.md). Build, lint, TypeScript, serta review visual sesi kosong di viewport sekitar 624 x 864 dan 1440 x 900 lulus pada 17 Oktober 2026. Jalur prompt-first belum diverifikasi end-to-end dengan inference aplikasi.
