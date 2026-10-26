# API lokal generator

FastAPI menghubungkan chat web ke intake source-bound, generator halaman lokal, dan artefak renderer yang diterima. API ini berjalan pada environment `.venv` proyek yang sudah berisi PyTorch CUDA.

## Pasang dependency API

Dari root repository, jalankan sekali:

```powershell
.\.venv\Scripts\python.exe -m pip install -r apps/api/requirements-api.txt
```

File dependency API hanya memuat pin FastAPI dan Uvicorn. Perintah ini memakai `.venv` yang sudah ada; jangan memasang ulang PyTorch atau mengganti build CUDA proyek.

## Jalankan API

Dari root repository, jalankan satu worker agar lock generation dan model GPU hanya dimiliki satu proses:

```powershell
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Tekan `Ctrl+C` untuk menghentikan server. API hanya menerima bind loopback. Default CORS mengizinkan tepat `http://localhost:3000` dan `http://127.0.0.1:3000`, tanpa wildcard. Contoh nilai environment ada di `.env.example`; aplikasi membaca environment proses, bukan file tersebut secara otomatis.

## Dokumentasi dan rute

- Referensi interaktif: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- OpenAPI JSON: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

| Method | Path | Kegunaan |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Status API, ketersediaan extractor, dan status muat kedua model |
| `GET` | `/api/v1/catalog` | Katalog jenis halaman, gaya, kemampuan, dan aset |
| `POST` | `/api/v1/intake/extract` | Ekstraksi brief bebas menjadi draft bersumber dan satu klarifikasi gabungan |
| `POST` | `/api/v1/intake/validate` | Klarifikasi dan validasi tanpa menjalankan generation |
| `POST` | `/api/v1/generations` | Validasi ulang, lalu membuat satu halaman dengan model lokal |
| `GET` | `/api/v1/generations/{generation_id}` | Ringkasan status yang aman |
| `GET` | `/api/v1/generations/{generation_id}/preview/{relative_path}` | Preview HTML dan berkas yang dirujuknya |
| `GET` | `/api/v1/generations/{generation_id}/source` | Tiga berkas source hasil renderer |
| `GET` | `/api/v1/generations/{generation_id}/download.zip` | Source, spesifikasi halaman, atribusi aset, dan aset terpakai |
| `GET` | `/api/v1/usages/summary?window=24h` | KPI audit dan sampel GPU selama generation |
| `GET` | `/api/v1/usages/gpu/current` | Snapshot `nvidia-smi`, tanpa memuat model |
| `GET` | `/api/v1/usages?cursor=&limit=25&window=7d` | Riwayat audit berhalaman |
| `GET` | `/api/v1/usages/{usage_id}` | Detail status, timeline aman, dan maksimal 300 sampel GPU |

Health dan katalog tidak memuat bobot. Endpoint `intake/extract` menerima sampai 16 pesan dengan total maksimal 4.000 karakter, lalu menjalankan extractor hanya jika paket checkpoint sudah melewati gate development. Ekstraksi memakai 16 scope berurutan di dalam satu giliran API dan berbagi lock inferensi dengan generator. Endpoint ini tidak membuat berkas website. Bila extractor belum dipromosikan, gagal, atau brief melewati budget tokenizer, API mengembalikan error terkontrol agar UI memakai editor manual.

Setiap nilai draft harus muncul persis pada pesan sumber yang dirujuk. Respons menyertakan rentang karakter Python dan UTF-16, konflik yang perlu dikonfirmasi, fitur di luar cakupan, serta daftar fakta yang masih kurang. Klarifikasi yang belum lengkap dikembalikan sekaligus. Saat draft siap, API mengirim token bertanda tangan yang mengikat penilaian fitur ke brief yang sama. Endpoint validasi dan generation tetap menjalankan `prepare_intake()` serta pemeriksaan sumber sebelum menerima draft.

Extractor dilatih dari keluarga training saja. Synthetic development dipakai untuk gate raw extraction dan replay safety API. `qa/select_request_extract_v1.py` hanya menghasilkan paket `training/selected/request-extract-v1` bila semua ambang development lulus. Runtime memverifikasi manifest/checkpoint dan memuat extractor secara lazy di bawah inference lock bersama generator; health tidak memuat model. Jika paket belum lolos verifikasi atau belum ada, extraction mengembalikan respons fail-closed dan UI mempertahankan brief untuk editor manual. Test/final tidak dipakai untuk training atau pemilihan.

Generation menyimpan berkas di `outputs/webapp/generations`, yang diabaikan Git. Preview, source, dan ZIP hanya tersedia jika laporan renderer berstatus `accepted` dan hash berkas cocok. Route preview memakai CSP ketat, content type tetap, dan cache `no-store`. Data prompt dan artefak tetap lokal.

## Audit Usage

Satu middleware mencatat setiap `POST /api/v1/generations` sebelum validasi schema. Respons menyertakan `X-Usage-ID`, termasuk ketika request ditolak. Outcome audit berasal dari status route dan hasil generator, sehingga HTTP 200 dengan `generation_failed` tidak dihitung sebagai sukses. Penyimpanan audit yang tidak siap menghentikan request sebelum generator berjalan.

Database dan sampel per-run berada di `outputs/webapp/usages`; folder itu diabaikan Git. SQLite menggunakan WAL, koneksi pendek, retention 90 hari, dan file lock nonblocking agar hanya satu proses API menggunakan database. Request yang masih berjalan saat proses berhenti ditandai `interrupted` setelah instance lama tidak lagi memegang lock.

`nvidia-smi` diambil selama generation pada interval satu detik. Nilai tersebut mencakup seluruh perangkat dan dapat memasukkan beban aplikasi desktop. Snapshot GPU saat ini hanya mengambil satu pembacaan dan tidak memuat model. Memori alokasi/reservasi PyTorch ditampilkan sebagai baseline, peak, dan delta proses yang terpisah. Jika alat GPU atau CUDA tidak tersedia, nilai metrik tetap `null` dan audit request tetap tersimpan.

Usage menyimpan ID, waktu, durasi, outcome, tahap, kode kegagalan allowlist, jumlah token/attempt/bagian jika dilaporkan, nama checkpoint aman, dan metrik telemetri. Isi prompt, fakta bisnis, source, output halaman, exception mentah, stack trace, dan path absolut tidak disimpan atau dikembalikan oleh API Usage. Riwayat menggunakan cursor stabil berdasarkan waktu mulai dan ID.

## Tailwind untuk halaman hasil

Jika `style_mode` bernilai `tailwind`, renderer memakai compiler yang dipatok di `tooling/tailwind`. Jalankan `npm ci` dari folder tersebut hanya bila `tooling/tailwind/node_modules` belum tersedia. Lockfile harus tetap digunakan.

## Status implementasi

Route extraction, kontrak Pydantic, resolver bukti, token validasi ulang, dan status model di health sudah ditambahkan. Kompilasi statis Python dan pembuatan skema OpenAPI berhasil. Candidate `REQUEST-EXTRACT-V1` step 1.800 sedang dievaluasi pada development. Raw gate belum selesai dan replay API safety gate menunggu hasil raw; extractor belum dipromosikan dan endpoint tetap fail-closed sampai kedua gate lulus.

Frontend prompt-first lulus TypeScript, lint, production build, dan review visual sesi kosong pada viewport sekitar 624 x 864 dan 1440 x 900 pada 17 Oktober 2026. Pemeriksaan tersebut tidak mengirim prompt ke endpoint extraction atau generation. Jalur prompt-first belum diverifikasi end-to-end. Final/test tetap tertutup.
