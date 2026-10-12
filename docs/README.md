# Dokumentasi Proyek

Dokumen di sini menjelaskan ruang lingkup, persyaratan tugas, sumber dataset, environment, dan urutan kerja Mini GPT WebCodeGen.

## Dokumen utama

- [Ruang lingkup dan rancangan pipeline](PROJECT_SCOPE_AND_PIPELINE.md): target, batas, interface modul, evaluasi, risiko, dan tahapan.
- [Rencana implementasi data, model, dan training](superpowers/plans/2026-10-12-pipeline-data-model-training.md): tugas implementasi serta verifikasi yang harus ditinjau sebelum mulai coding.
- [Analisis dataset awal](ANALISIS_DATASET_2026-10-12.md): isi, akses, lisensi, dan keterbatasan Webdev, WebMC, serta WebSight.
- [Perbandingan dataset dan stack](PERBANDINGAN_DATASET_STACK_WEB_2026-10-12.md): hasil audit Vulcan dan kandidat CSS biasa atau Tailwind.
- [Panduan environment](PANDUAN_ENVIRONMENT.md): VENV, PyTorch CUDA, kernel notebook, dan bukti pemeriksaan GPU.
- [Panduan pipeline data](PIPELINE_DATA_GUIDE.md): command akuisisi, preparation, review SFT, tokenizer, dan pemeriksaan integritas.
- [Review pipeline](../reports/REVIEW_PIPELINE_2026-10-12.md): empat temuan, perbaikan, regression tests, dan batas review data.

## Status

Environment, download subset, dan pipeline data tersedia. Model, pipeline training model, checkpoint, dan aplikasi web belum dibuat. Anotasi produksi SFT menunggu review manusia. Raw/processed data dan tokenizer berada di disk lokal. Code, config, manifest, attribution, log, dan ringkasan berukuran kecil dilacak Git.

Sebelum mengambil atau merilis data, periksa lagi revision, lisensi, atribusi, dan ketentuan penggunaan saat itu.
