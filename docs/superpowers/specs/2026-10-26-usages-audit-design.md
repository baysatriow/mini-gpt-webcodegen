# Desain Usage dan Audit Generation

Status: spesifikasi implementasi dari permintaan langsung pengguna
Tanggal: 26 Oktober 2026

## Tujuan

Menambahkan halaman **Usage** untuk memperlihatkan dua hal yang dipilih pengguna: ringkasan pemakaian GPU dan riwayat audit setiap permintaan generation. Pengguna harus dapat membedakan request yang berhenti sebelum inference dari inference yang berjalan lalu gagal, serta mengetahui kapan generator berhasil membuat halaman.

Fitur ini memakai telemetry lokal. Ia tidak mengubah training, checkpoint terpilih, kontrak PageSpec, strategi generation bertahap, validator, renderer, preview, atau format unduhan.

## Temuan source dan UI saat rancangan dibuat

- FastAPI berjalan satu worker pada `127.0.0.1:8000`; UI Next.js berjalan pada port `3000`.
- API generation saat ini membuat `generation_id` setelah intake dinyatakan siap. Request yang ditolak oleh schema, lock, intake, atau inisialisasi model belum selalu mempunyai catatan bersama.
- Laporan generator telah menyediakan durasi, total token, status, serta attempt bertahap dengan retry. String error tidak boleh langsung dipublikasikan sebagai metrik karena dapat memuat konten request.
- `src/training/performance.py` sudah menyediakan `GpuMonitor` berbasis `nvidia-smi` dengan interval 0,5 detik. Statistik `nvidia-smi` bersifat untuk seluruh perangkat dan dapat mencakup aplikasi desktop lain.
- API health saat ini tidak memuat bobot dan melaporkan `generator_loaded=true`, `extractor_available=false`, `extractor_loaded=false`. Halaman lokal yang diperiksa masih menampilkan error layanan pada draft lama. Keadaan ini tidak membuktikan generation baru berhasil.
- Source working tree memuat revisi UI yang meringkas composer, sidebar, kartu fakta, pesan, ringkasan, status, preview, dan tab source. Halaman browser yang diperiksa masih menyajikan bundle lama dari `next start`; perubahan source belum mendapat review visual dari build terbaru.

## Sasaran pengguna

Pengguna tunggal aplikasi lokal ingin melihat apakah generation berjalan, bagaimana hasilnya, kapan dan pada tahap mana kegagalan terjadi, serta berapa pemakaian GPU yang terukur selama proses.

## Alur

```text
Browser mengirim POST /api/v1/generations
    -> middleware membuat usage_id dan menyimpan status received
    -> validasi schema, lock, intake, model, inference, validasi output, render, persist
    -> setiap tahap memperbarui status dan metrik tanpa menyimpan isi brief
    -> selesai atau gagal: usage record ditutup dengan outcome dan waktu
    -> halaman /usage membaca summary, status GPU, riwayat, dan detail
```

Catatan dibuat sedini mungkin agar kegagalan sebelum pembuatan `generation_id` tetap tercatat. Middleware membuat `UsageRecorder` pada `request.state` sebelum validasi FastAPI dan menambahkan `X-Usage-ID` pada respons. Router generation menandai tahap dan kode aman, lalu menyelesaikan catatan secara eksplisit pada setiap hasil. Middleware menjadi fallback untuk schema-invalid, exception tidak terduga, dan request terputus. Jika database audit tidak dapat menyimpan awal request, generation tidak dimulai dan API mengembalikan error audit-storage yang aman.

## Data yang dicatat

Simpan data minimum yang diperlukan untuk audit teknis:

- `usage_id` UUID untuk setiap request generation, termasuk request yang ditolak sebelum inference.
- `generation_id` nullable jika artefak generation sudah dialokasikan.
- waktu mulai dan selesai UTC, durasi total, status HTTP, tahap terakhir, outcome, dan kode kegagalan dari allowlist.
- status transport HTTP dicatat terpisah dari outcome aplikasi. `generation_failed` dapat berpasangan dengan HTTP 200, sementara `input_too_long` dapat muncul sebagai HTTP 413 atau status hasil report.
- apakah inference mulai, jumlah token input/output jika tersedia, jumlah retry/attempt, jumlah bagian halaman, dan status hasil renderer.
- identitas versi model/checkpoint terpilih yang aman ditampilkan. Tidak menyimpan path absolut atau bobot.
- nama perangkat, utilisasi, pemakaian memori perangkat, daya, suhu, dan clock yang tersedia selama generation. Sampel `nvidia-smi` bersifat seluruh perangkat, bukan atribusi eksklusif proses aplikasi.
- baseline serta peak alokasi/reservasi VRAM proses PyTorch jika tersedia; delta terhadap baseline ditampilkan terpisah dari memori total perangkat.
- ringkasan per tahap dan sample GPU per-run yang diperlukan untuk detail audit.

Jangan menyimpan prompt, pesan klarifikasi, nama usaha, fakta bisnis, token ekstraksi, HTML/CSS/JavaScript hasil, output mentah model, isi exception, stack trace, atau environment variable. Error yang tampil adalah kategori stabil seperti `input_rejected`, `service_busy`, `model_unavailable`, `cuda_out_of_memory`, `output_invalid`, `render_failed`, `storage_failed`, atau `internal_error`.

## Status dan tahap

Status record: `running`, `completed`, `rejected`, `failed`, dan `interrupted`. Tahap: `request_received`, `request_validation`, `intake_validation`, `model_load`, `inference`, `output_validation`, `render_export`, `persist_result`, dan `completed`.

Dashboard melaporkan secara terpisah:

- total request masuk;
- inference dimulai;
- halaman selesai;
- request ditolak sebelum inference;
- inference gagal setelah dimulai;
- proses yang terputus saat server berhenti;
- rasio keberhasilan semua request dan rasio keberhasilan khusus request yang mencapai inference, dengan denominator tertulis.

Kegagalan generator yang dikembalikan sebagai HTTP 200 tetap diklasifikasikan menurut `GenerationResponse.status` dan laporan generator, bukan berdasarkan status HTTP saja. Request schema-invalid menjadi `rejected`; router menandai kode alasan lock, intake, model, inference, output, render, atau persist secara eksplisit.

## Penyimpanan lokal

- Database: `outputs/webapp/usages/usage.sqlite3`.
- Sample telemetry per-run: `outputs/webapp/usages/samples/<usage_id>.jsonl`.
- Keduanya lokal, diabaikan Git, dan tidak dicampur ke artefak website.
- SQLite memakai koneksi pendek per operasi, WAL, busy timeout, registri instance server, heartbeat 15 detik, dan file lock proses lintas platform. Satu instance API per direktori Usage ditegakkan; proses kedua yang menemukan lock aktif gagal startup dengan pesan aman.
- Startup memperoleh file lock nonblocking sebelum pemulihan. Setelah lock berhasil didapat, record `running` dari instance sebelumnya tidak lagi memiliki proses hidup dan ditandai `interrupted`; instance aktif tidak disentuh. Ini memungkinkan restart segera tanpa menunggu heartbeat timeout.
- Retensi awal 90 hari. Pembersihan berjalan saat startup dan paling banyak sekali sehari pada request Usage. Sampel dihapus sebelum baris database; detail hanya membuka file sampel jika record masih ada di SQLite. Pembersihan orphan dibatasi ke folder `samples` dan ID UUID valid.
- Jika sample GPU tidak tersedia, request tetap dicatat dan UI menunjukkan metrik sebagai tidak tersedia, bukan nol.

## API

Tambahkan router versioned di `/api/v1/usages`:

| Method | Path | Fungsi |
| --- | --- | --- |
| `GET` | `/summary?window=24h` | KPI audit, outcome, durasi, token, dan agregat GPU untuk jendela waktu yang diizinkan |
| `GET` | `/gpu/current` | Snapshot perangkat dari `nvidia-smi` dengan cache singkat; tidak memuat model atau menjalankan inference |
| `GET` | `/?cursor=<opaque>&limit=25&window=7d` | Daftar audit berhalaman dengan filter rentang waktu, status, tahap, serta `limit` 1 sampai 100 |
| `GET` | `/{usage_id}` | Detail aman satu run, timeline tahap, ringkasan dan sample GPU yang telah dibatasi |

Endpoint auth Next.js untuk Quick Tunnel: `POST /api/auth/login` menerima username/password JSON dan mengatur sesi cookie; `POST /api/auth/logout` menghapus sesi. `APP_ACCESS_REQUIRED`, `APP_ACCESS_USERNAME`, `APP_ACCESS_PASSWORD`, dan `APP_SESSION_SECRET` adalah konfigurasi runtime. Bila akses diwajibkan dan ada nilai yang hilang atau secret kurang dari 32 karakter, semua route aplikasi/API ditolak dengan 503. Auth dinonaktifkan pada proses lokal tanpa `APP_ACCESS_REQUIRED=true`.

Urutan route statis harus dideklarasikan sebelum route `/{usage_id}`. Semua response memiliki kontrak Pydantic tertutup, waktu UTC, nilai metrik nullable, dan pesan error tanpa path lokal atau stack trace. Daftar memakai urutan stabil `started_at DESC, usage_id DESC`, cursor opaque, dan index yang mendukung pengurutan/filter. Endpoint baru tidak membaca atau mengubah artefak test/final.

Middleware hanya mencatat `POST /api/v1/generations`, tidak membaca body, dan tidak mencatat request intake biasa, health check, preview, atau download. Detail request schema gagal diambil dari kode status, bukan dengan merekam payload.

## UI/UX

- Tambahkan tautan **Usage** dari navigasi utama/riwayat ke route `/usage`, dengan jalan kembali yang jelas ke percakapan. Pertahankan guidance composer yang terhubung melalui `aria-describedby` saat UI diubah.
- Bagian atas menampilkan status GPU terkini, timestamp snapshot, memori terpakai/total, utilisasi, daya, suhu, serta status unavailable bila alat telemetry gagal.
- Tampilkan catatan bahwa metrik perangkat `nvidia-smi` dapat mencakup aplikasi lain; peak VRAM proses ditampilkan sebagai metrik terpisah.
- KPI memakai rentang waktu yang mudah dipilih: 24 jam, 7 hari, 30 hari.
- Grafik historis hanya merangkum sampel GPU selama generation. Tampilkan jumlah run, jumlah sampel, dan cakupan data; jika tidak ada sampel, tampilkan kosong, bukan nol atau klaim pemantauan kontinu.
- Ringkasan GPU memisahkan memori perangkat dari memori proses PyTorch. Peak proses ditampilkan sebagai delta atas baseline sejak model siap.
- Tabel riwayat menampilkan waktu, status, tahap akhir, durasi, token, retry, perangkat/peak VRAM, kode kegagalan, dan ID singkat. Tidak ada prompt atau source.
- Detail sebuah baris membuka timeline tahap dan grafik kecil sample GPU untuk run tersebut.
- Status loading, error, perangkat tidak tersedia, data kosong, dan pagination memiliki tampilan tersendiri. Polling GPU berhenti ketika halaman tidak terlihat.
- Gunakan SVG/CSS yang sudah tersedia, tanpa dependensi chart baru.
- Halaman responsif dan bisa dipakai dengan keyboard; label status tidak mengandalkan warna saja.

## Privasi dan batas paparan

Usage API tidak mengembalikan prompt, nama bisnis, konten output, raw exception, atau path filesystem. Riwayat dan telemetri tetap pada mesin yang menjalankan API. Quick Tunnel menjangkau Next.js dan seluruh endpoint API melalui rewrite; CORS bukan autentikasi. Sebelum tunnel aktif, login aplikasi kustom melindungi semua halaman dan `/api/*` dengan cookie sesi HttpOnly, Secure saat HTTPS, SameSite=Lax, dan tanda tangan HMAC. Kredensial dan secret sesi hanya dibaca dari environment lokal yang diabaikan Git. Aset statis dan endpoint login dikecualikan. Konfigurasi auth yang tidak lengkap harus menutup akses. Login menyediakan toggle tampil/sembunyikan password, sesuai preferensi pengguna.

## Batas scope

Termasuk: audit request generation, ringkasan penggunaan GPU, current snapshot, filter/list/detail, timeline, dan UI `/usage`.

Tidak termasuk: audit training per langkah, remote telemetry, analytics pihak ketiga, akun multi-pengguna, penyimpanan prompt/source, perubahan bobot, pemuatan extractor, perubahan pipeline generation, deployment hosting permanen, dan eksperimen inference otomatis. Login kustom hanya membatasi Quick Tunnel sementara dan bukan sistem akun.

## Kriteria penerimaan

1. Setiap POST generation yang mencapai API memperoleh satu `usage_id`, termasuk request schema-invalid dan request yang ditolak sebelum inference.
2. Hasil success, `generation_failed`, dan penolakan pra-inference menghasilkan klasifikasi yang konsisten walau status HTTP sama.
3. Detail Usage tidak mengandung teks prompt, fakta usaha, source, exception mentah, atau path absolut.
4. Summary, list, detail, dan current GPU mempunyai skema dan filter yang terdokumentasi; current GPU dan halaman Usage tidak memicu model load/inference.
5. Kegagalan `nvidia-smi` atau CUDA menghasilkan status telemetry unavailable tanpa menggagalkan pembacaan audit.
6. Timeline membedakan pre-inference, inference, output validation, rendering, penyimpanan, dan server restart.
7. Ringkasan dan detail memiliki empty/loading/error states serta tampilan responsif.
8. Revisi UI/UX yang sudah ada tampil pada build terbaru dan tidak menghilangkan keyboard/accessible descriptions pada composer.
9. Pemeriksaan API/UI dan build lokal selesai sebelum deployment. Deployment yang dimaksud adalah aplikasi lokal melalui Cloudflare Quick Tunnel sementara, bukan hosting permanen.
10. Tanpa cookie, API memperoleh 401 JSON dan halaman UI diarahkan ke login; login valid membuka sesi dan logout menghapusnya. Kredensial tidak masuk query string atau respons API.
11. Statistik GPU historis menjelaskan cakupan sampel generation dan menunjukkan kosong/null ketika tidak tersedia.

## Keputusan pengguna

Pengguna meminta fitur Usage sebagai audit generation, termasuk pemakaian VGA dan riwayat inference berhasil atau gagal. Saat diminta memilih prioritas tampilan, pengguna memilih ringkasan GPU sekaligus ringkasan riwayat dan kegagalan. Pengguna juga meminta review UI/UX terbaru, implementasi rencana Usage, lalu deployment setelah seluruhnya siap.
