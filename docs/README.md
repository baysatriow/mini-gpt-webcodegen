# Dokumentasi Proyek

Dokumen di sini menjelaskan ruang lingkup, persyaratan tugas, sumber dataset, environment, dan urutan kerja Mini GPT WebCodeGen.

## Dokumen utama

- [Desain aplikasi chat generator](superpowers/specs/2026-10-15-generator-chat-application-design.md): alur chat, RequestDraft source-bound, batas model, API, preview, dan unduhan.
- [Roadmap aplikasi generator](superpowers/plans/2026-10-15-generator-app-roadmap.md): urutan paket TRAIN-025, FastAPI, lalu UI Next.js/shadcn.
- [Paket runtime terpilih](../training/selected/fullpage-v5/README.md): provenance kandidat TRAIN-025 step 1.800 dan batas review visualnya.
- [Ruang lingkup dan rancangan pipeline](PROJECT_SCOPE_AND_PIPELINE.md): target, batas, interface modul, evaluasi, risiko, dan tahapan.
- [Rencana implementasi data, model, dan training](superpowers/plans/2026-10-12-pipeline-data-model-training.md): tugas implementasi serta verifikasi yang harus ditinjau sebelum mulai coding.
- [Analisis dataset awal](ANALISIS_DATASET_2026-10-12.md): isi, akses, lisensi, dan keterbatasan Webdev, WebMC, serta WebSight.
- [Perbandingan dataset dan stack](PERBANDINGAN_DATASET_STACK_WEB_2026-10-12.md): hasil audit Vulcan dan kandidat CSS biasa atau Tailwind.
- [Panduan environment](PANDUAN_ENVIRONMENT.md): VENV, PyTorch CUDA, kernel notebook, dan bukti pemeriksaan GPU.
- [Panduan pipeline data](PIPELINE_DATA_GUIDE.md): command akuisisi, preparation, review SFT, tokenizer, dan pemeriksaan integritas.
- [Review pipeline](../reports/REVIEW_PIPELINE_2026-10-12.md): empat temuan, perbaikan, regression tests, dan batas review data.
- [Panduan training](TRAINING_GUIDE.md): profiling, smoke/baseline, resume, SFT, failure artifact, dan evaluasi.
- [Optimasi GPU](../reports/GPU_TRAINING_OPTIMIZATION_2026-10-13.md): empat sweep RTX 5070, runtime optimal, training nyata, telemetry, dan batas kualitas.
- [Ringkasan baseline](../reports/PIPELINE_TRAINING_SUMMARY.md): hasil pretraining terukur, grafik, checkpoint dan probe JSON historis.
- [Hasil SFT pilot](../reports/SFT_PILOT_SUMMARY_2026-10-13.md): approval, 40 update, loss target dan generasi 0/4 valid.
- [Pengembangan output](SFT_DEVELOPMENT_2026-10-13.md): diagnosis, curriculum sintetis, serialization, dan penyalinan nama.
- [Panduan generasi website](GENERATING_WEBSITES.md): format prompt, validasi isi, ekspor lokal CSS/Tailwind/JavaScript dan batasnya.
- [Notebook proses](../notebooks/README.md): notebook berurutan, output aktual, dan kernel proyek.
- [Review training](../reports/REVIEW_TRAINING_2026-10-12.md): checkpoint terbaik, transaksi save, lineage parent/SFT/test, verified copy, dan Minor ditunda.

## Status

Environment, pipeline data, Mini GPT dan training/evaluator tersedia. CLI dan dua contoh CSS/Tailwind menghasilkan output diterima validator. Overall model gate belum lulus43/48exact; research per output berbeda dari production readiness. Lihat [hasil terbaru](../reports/OUTPUT_DEVELOPMENT_2026-10-13.md). UI input/preview sandbox tahap akhir. Data/BPE/checkpoint lokal; code, log, laporan dan dua snapshot website di Git.

Sebelum mengambil atau merilis data, periksa lagi revision, lisensi, atribusi, dan ketentuan penggunaan saat itu.
