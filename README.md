# WebCraft GPT

WebCraft by VibeStack adalah aplikasi generator website WebCraft GPT. Proyek ini melatih Mini GPT dari bobot acak. Aplikasi menerima brief atau template, memvalidasi fakta, menjalankan generator bertahap, lalu menyediakan preview dan unduhan HTML, CSS biasa atau Tailwind, serta JavaScript dari katalog interaksi.

## Status per 1 November 2026

| Bagian | Status dan bukti |
| --- | --- |
| Generator aplikasi | TRAIN-025 step 1800, kontrak source-bound-v1 |
| Arsitektur | 14.579.712 parameter, 6 layer, 6 head, embedding 384, konteks 2048 |
| Identitas model | Hash checkpoint, tokenizer, dan laporan seleksi cocok |
| Pemuatan model | Adapter aplikasi dan paket upload berhasil memuat model di CUDA pada audit 1 November |
| Development | Validator menerima 80/80 request pada laporan seleksi |
| Extractor brief bebas | Belum dipromosikan; selection runtime belum tersedia |
| Kualitas visual | Target 95 persen belum dibuktikan oleh review manusia |
| Evaluasi final FULLPAGE-V5 | Tetap tertutup; hasil final eksperimen lama memakai benchmark terpisah |

Audit pemuatan tidak menjalankan inference baru. Angka 80/80 mengukur kepatuhan kontrak development. Angka itu tidak mengukur daya tarik visual atau kemampuan menghasilkan layout bebas.

## Mulai menggunakan

1. Ikuti [panduan environment](docs/PANDUAN_ENVIRONMENT.md) untuk Python 3.11 dan CUDA proyek.
2. Siapkan [model dan paket upload](docs/MODEL_RUNTIME_AND_UPLOAD.md). Clone Git saja tidak menyertakan bobot atau tokenizer.
3. Jalankan [FastAPI](apps/api/README.md) pada loopback port 8000, satu worker.
4. Jalankan [Next.js](apps/web/README.md) pada port 3000.
5. Pilih template atau lengkapi fakta halaman, tinjau ringkasan, lalu pilih Generate website.

Katalog menyediakan 100 contoh usaha fiktif yang dapat diedit. Saat extractor belum tersedia, editor fakta tetap menjadi jalur input yang dapat digunakan. Model baru dimuat ketika generation diminta; health API tidak memuat bobot.

Untuk mencoba generator langsung melalui terminal, gunakan [panduan generasi](docs/GENERATING_WEBSITES.md).

## Alur aplikasi

~~~mermaid
flowchart TD
    A[Brief atau template] --> B[Draft fakta halaman]
    B --> C[Validasi dan konfirmasi pengguna]
    C --> D[Mini GPT membuat plan]
    D --> E[Mini GPT membuat draft tiap section]
    E --> F[Validasi fakta dan komposisi PageSpec]
    F --> G[Renderer HTML, CSS, JavaScript dan aset]
    G --> H[Preview sandbox dan unduhan]
    G --> I[Metadata proses di Usage]
~~~

Generator memilih rancangan melalui JSON dan ID katalog. Resolver memasukkan fakta yang telah dikonfirmasi. Renderer menyediakan interaksi yang didukung, termasuk menu dan formulir demo. Pengiriman formulir ke layanan bisnis nyata memerlukan integrasi terpisah.

## Struktur repository

| Lokasi | Isi |
| --- | --- |
| apps/web/ | Chat Next.js, shadcn, preview, source viewer, login, dan Usage |
| apps/api/ | Adapter FastAPI, validasi intake, model lazy-load, artefak, dan audit |
| src/ | Library data, Mini GPT, training, evaluasi, komposer, dan renderer |
| qa/ | Entry point eksperimen, pemeriksaan, dan ekspor |
| configs/ | Konfigurasi eksperimen, schema, dan katalog kontrak |
| training/selected/ | Manifest kandidat runtime dan salinan model lokal |
| checkpoints/ | Checkpoint kanonis lokal dengan pointer dan payload .versions |
| data/ | Korpus lokal, tokenizer, manifest, lisensi, dan anotasi |
| assets/ dan tooling/ | Ilustrasi yang diizinkan dan dependency compiler Tailwind |
| outputs/ | Hasil lokal, database Usage, dan paket upload |
| docs/, reports/, notebooks/, logs/ | Panduan, bukti terukur, proses notebook, dan riwayat |
| examples/ | Contoh hasil dan gallery eksperimen historis |
| sampah/ | Karantina file yang dapat dipulihkan |

[Panduan struktur](docs/PROJECT_STRUCTURE.md) menjelaskan batas tiap folder dan aturan perapihan.

## Ruang lingkup

Target keluaran adalah landing page dan company profile satu halaman, dalam bahasa Indonesia. Pilihan style yang didukung adalah CSS biasa dan Tailwind lokal. Model dan renderer bekerja dengan bagian, layout, aset, serta interaksi dari katalog proyek.

Generator belum ditujukan untuk backend bisnis, database aplikasi hasil, situs banyak halaman, React/Vue hasil generasi, atau JavaScript bebas. Frontend WebCraft sendiri memakai Next.js; batas tersebut berlaku pada website yang dihasilkan.

## Data dan evaluasi

Snapshot pipeline awal mencatat 54.996 baris diterima, menjadi 51.211 setelah deduplikasi: 41.639 train, 5.016 validation, dan 4.556 test. Angka ini berasal dari manifest pretraining, bukan jumlah pasangan SFT terbaru. Family assignment, tokenizer, lineage, dan laporan eksperimen mengikat data yang dipakai tiap run.

[Audit struktur dan model](reports/structure/AUDIT_2026-11-01.json) memuat hasil pemeriksaan terbaru. [Manifest runtime](training/selected/fullpage-v5/selection.json) dan [laporan seleksi](reports/training/FULLPAGE-V5_DEVELOPMENT_SELECTION.json) menjadi rujukan identitas kandidat. Evaluasi visual manusia dan evaluasi final harus dilaporkan terpisah dari validasi schema.

## Dokumentasi dan riwayat

Mulai dari [indeks dokumentasi](docs/README.md), [notebook](notebooks/README.md), atau [log training](logs/LOG_TRAINING.md). Interaksi dan pelaksanaan dicatat secara append-only di [log eksperimen](logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md).

[README sebelum penataan](docs/history/README_BEFORE_2026-11-01.md) menyimpan kronologi eksperimen lama. Klaim runtime di sana berlaku pada tahap historisnya. Panduan lama CLI juga disimpan sebagai [riwayat generasi](docs/history/GENERATING_WEBSITES_BEFORE_2026-11-01.md).
