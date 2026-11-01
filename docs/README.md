# Dokumentasi Mini GPT WebCodeGen

Gunakan panduan aktif di bawah untuk menjalankan proyek. Laporan bertanggal dan notebook menyimpan hasil eksperimen pada tahap masing-masing.

## Menjalankan aplikasi dan model

| Kebutuhan | Panduan |
| --- | --- |
| Memahami keadaan proyek | [README utama](../README.md) |
| Memahami folder dan batas modul | [Struktur proyek](PROJECT_STRUCTURE.md) |
| Menyiapkan Python dan CUDA | [Environment](PANDUAN_ENVIRONMENT.md) |
| Menemukan bobot dan menyiapkan upload | [Model runtime dan upload](MODEL_RUNTIME_AND_UPLOAD.md) |
| Menjalankan generator lewat CLI | [Generasi website](GENERATING_WEBSITES.md) |
| Menjalankan chat, preview, dan login | [Frontend](../apps/web/README.md) |
| Menjalankan FastAPI dan Usage | [API](../apps/api/README.md) |
| Memeriksa kandidat terpilih | [Paket FULLPAGE-V5](../training/selected/fullpage-v5/README.md) |

## Pipeline dan bukti

- [Rancangan pipeline](PROJECT_SCOPE_AND_PIPELINE.md) merekam ruang lingkup dan tahap awal.
- [Pipeline data](PIPELINE_DATA_GUIDE.md), [kurasi anotasi](ANNOTATION_REVIEW_GUIDE.md), dan [training](TRAINING_GUIDE.md) menjelaskan prosedur eksperimen.
- [Analisis dataset](ANALISIS_DATASET_2026-10-12.md) dan [perbandingan stack](PERBANDINGAN_DATASET_STACK_WEB_2026-10-12.md) mencatat hasil audit sumber pada tanggalnya.
- [Notebook proses](../notebooks/README.md) menyusun urutan pekerjaan.
- [Laporan seleksi FULLPAGE-V5](../reports/training/FULLPAGE-V5_DEVELOPMENT_SELECTION.json) memilih TRAIN-025 step 1800 dari hasil development.
- [Audit 1 November](../reports/structure/AUDIT_2026-11-01.json) memverifikasi model, tokenizer, struktur, dan paket upload.
- [Log training](../logs/LOG_TRAINING.md) dan [log eksperimen](../logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md) mempertahankan riwayat pelaksanaan.

## Desain aplikasi

[Desain chat](superpowers/specs/2026-10-15-generator-chat-application-design.md), [desain intake](superpowers/specs/2026-10-16-prompt-first-intake-design.md), dan [roadmap](superpowers/plans/2026-10-15-generator-app-roadmap.md) mencatat keputusan arsitektur. Status implementasi terkini diringkas di README utama dan panduan aplikasi.

Extractor otomatis belum memiliki selection runtime yang dipromosikan pada audit 1 November. Pengguna dapat memilih contoh fiktif dan mengisi editor fakta. Generator terpilih menerima fakta yang lolos validasi. Target visual 95 persen masih memerlukan review manusia; final FULLPAGE-V5 tetap tertutup.

## Arsip dokumentasi

[README historis](history/README_BEFORE_2026-11-01.md) dan [panduan CLI historis](history/GENERATING_WEBSITES_BEFORE_2026-11-01.md) menyimpan isi sebelum penataan. Angka dan pernyataan runtime di arsip harus dibaca bersama tanggal eksperimennya. Snapshot final eksperimen lama tidak menjadi hasil final FULLPAGE-V5.
