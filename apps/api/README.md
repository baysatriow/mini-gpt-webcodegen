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
| `GET` | `/api/v1/health` | Status API dan apakah generator sudah dimuat |
| `GET` | `/api/v1/catalog` | Katalog jenis halaman, gaya, kemampuan, dan aset |
| `POST` | `/api/v1/intake/validate` | Klarifikasi dan validasi tanpa menjalankan generation |
| `POST` | `/api/v1/generations` | Validasi ulang, lalu membuat satu halaman dengan model lokal |
| `GET` | `/api/v1/generations/{generation_id}` | Ringkasan status yang aman |
| `GET` | `/api/v1/generations/{generation_id}/preview/{relative_path}` | Preview HTML dan berkas yang dirujuknya |
| `GET` | `/api/v1/generations/{generation_id}/source` | Tiga berkas source hasil renderer |
| `GET` | `/api/v1/generations/{generation_id}/download.zip` | Source, spesifikasi halaman, atribusi aset, dan aset terpakai |

Health, katalog, dan intake tidak memuat bobot. Model dimuat secara lazy saat permintaan generation yang lolos intake dijalankan. Endpoint generation menjalankan inference GPU secara sinkron; responsnya JSON biasa dan tidak mengklaim progres streaming.

Generation menyimpan berkas di `outputs/webapp/generations`, yang diabaikan Git. Preview, source, dan ZIP hanya tersedia jika laporan renderer berstatus `accepted` dan hash berkas cocok. Route preview memakai CSP ketat, content type tetap, dan cache `no-store`. Data prompt dan artefak tetap lokal.

## Tailwind untuk halaman hasil

Jika `style_mode` bernilai `tailwind`, renderer memakai compiler yang dipatok di `tooling/tailwind`. Jalankan `npm ci` dari folder tersebut hanya bila `tooling/tailwind/node_modules` belum tersedia. Lockfile harus tetap digunakan.

## Status implementasi

Source API, kontrak JSON, dan rute telah ditambahkan. Dependency API belum dipasang, server belum dijalankan, dan tidak ada test, build, atau inference yang dijalankan selama tahap ini. Model hanya akan dipanggil ketika endpoint generation digunakan.
