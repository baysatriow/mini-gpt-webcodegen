# Model runtime dan paket upload

Kandidat yang dipakai aplikasi adalah TRAIN-025 step 1800. Audit 1 November 2026 memverifikasi checkpoint, tokenizer, laporan seleksi, dan pemuatan model di CUDA.

## Identitas kandidat

| Atribut | Nilai |
| --- | --- |
| Kontrak | source-bound-v1 |
| Parameter unik | 14.579.712 |
| Layer / head / embedding | 6 / 6 / 384 |
| Vocabulary / konteks | 8192 / 2048 token |
| Checkpoint payload SHA-256 | c1a450149eb8f860cc42595bba283e0f9e915a436f38f967516bc5107bd1c446 |
| Tokenizer SHA-256 | f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7 |
| Validator development | 80/80 request diterima |
| Final FULLPAGE-V5 | Tetap tertutup |

Bobot berasal dari arsitektur Mini GPT proyek dengan inisialisasi acak dan riwayat training proyek. Model menghasilkan rancangan melalui JSON dan katalog; renderer menyusun HTML/CSS/JavaScript.

## Lokasi pada komputer ini

Root proyek: F:/Generative_AI/Vibe_Coding_Proyek_1.

| Kebutuhan | Path relatif root |
| --- | --- |
| Paket upload terbaru beserta panduan | outputs/releases/fullpage-v5-TRAIN-025-step1800-v2.zip |
| Isi paket lokal | outputs/releases/fullpage-v5-TRAIN-025-step1800/ |
| Pointer model aplikasi | training/selected/fullpage-v5/model/TRAIN-025-step1800.pt |
| Payload bobot | training/selected/fullpage-v5/model/.versions/TRAIN-025-step1800-0df0cc6e34b24f3d8423ef5aed195b9d.pt |
| Manifest payload | File .json dengan nama dasar yang sama di .versions |
| Tokenizer | data/tokenizer/tokenizer.json |
| Identitas selection | training/selected/fullpage-v5/selection.json |
| Laporan pemilihan | reports/training/FULLPAGE-V5_DEVELOPMENT_SELECTION.json |
| Output development tersalin | training/selected/fullpage-v5/development-output/ |

Pointer terluar berukuran 213 byte dan menunjuk payload asli sekitar 58 MB dalam folder tersembunyi .versions. Salin pointer, payload, dan manifest bersama. ZIP terbaru menyertakan ketiganya serta tokenizer, kode runtime, schema, aset dan contoh request.

## Mengunggah paket

Unggah ZIP v2 jika tujuan Anda membagikan model agar dapat dijalankan dengan kode proyek. Pengguna sekarang telah mengizinkan persiapan paket untuk upload; audit ini hanya menyiapkan file lokal. Pilih tujuan dan pengaturan akses saat Anda mengunggahnya.

Paket berisi runtime PyTorch custom. Pemuatan memakai FullPageGenerator dan loader checkpoint proyek; adapter Transformers.from_pretrained belum tersedia. Korpus mentah, data final/test, kredensial aplikasi, environment .venv, serta dependency node_modules tidak disertakan.

File UPLOAD_MANIFEST.json di dalam paket mencatat hash tiap file dan perintah CLI. Checksum ZIP terbaru tercatat di [audit struktur](../reports/structure/AUDIT_2026-11-01.json). Paket awal tanpa panduan tetap tersimpan sebagai ZIP tanpa akhiran v2 untuk jejak audit.

## Menjalankan paket

Ekstrak ZIP dengan struktur folder lengkap. Pada Windows, jalankan dari root paket:

~~~powershell
py -3.11 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-gpu.txt
./.venv/Scripts/python.exe -m pip install -r requirements.txt
~~~

requirements-gpu.txt mengunci build PyTorch CUDA proyek. Perangkat dan driver tujuan harus cocok dengan build tersebut. Environment yang sudah cocok dapat dipakai tanpa memasang ulang dependency.

Untuk keluaran Tailwind:

~~~powershell
npm ci --prefix tooling/tailwind
~~~

Contoh CSS biasa:

~~~powershell
./.venv/Scripts/python.exe -m qa.generate_fullpage --request examples/requests/demo.json --checkpoint training/selected/fullpage-v5/model/TRAIN-025-step1800.pt --output outputs/demo
~~~

Runtime saat ini membutuhkan CUDA. Audit memuat model dari root paket pada CUDA dan memeriksa integritas ZIP. Inference baru belum dijalankan saat audit dokumentasi.

## Kualitas dan kemampuan

Kandidat terpilih memenuhi gerbang kontrak development. Hasil 80/80 mengukur kontrak development, bukan skor visual atau kemampuan menghasilkan situs bebas. Dataset, kontrak input, katalog renderer, dan komposer menentukan ruang variasinya.

Extractor brief bebas adalah kandidat terpisah dan belum memiliki selection runtime yang dipromosikan. Paket ini menyediakan generator beserta contoh request terstruktur. Pada aplikasi, template dan editor fakta dapat digunakan untuk menyiapkan input.
