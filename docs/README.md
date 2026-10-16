# Dokumentasi Proyek

Dokumen di sini menjelaskan ruang lingkup, persyaratan tugas, sumber dataset, environment, dan urutan kerja Mini GPT WebCodeGen.

## Dokumen utama

- [Desain aplikasi chat generator](superpowers/specs/2026-10-15-generator-chat-application-design.md): alur chat, RequestDraft source-bound, batas model, API, preview, dan unduhan.
- [Desain prompt-first dan intake ringkas](superpowers/specs/2026-10-16-prompt-first-intake-design.md): analisis kemampuan model saat ini, ekstraksi fakta terverifikasi, klarifikasi gabungan, dan UI prompt-first.
- [Rencana implementasi prompt-first](superpowers/plans/2026-10-16-prompt-first-intake.md): corpus extractor, checkpoint terpisah, API, UI, gate development, dan log.
- [Roadmap aplikasi generator](superpowers/plans/2026-10-15-generator-app-roadmap.md): urutan paket TRAIN-025, FastAPI, lalu UI Next.js/shadcn.
- [Paket runtime terpilih](../training/selected/fullpage-v5/README.md): provenance kandidat TRAIN-025 step 1.800 dan batas review visualnya.
- [API lokal generator](../apps/api/README.md): setup `.venv`, server satu worker, CORS, rute, dan batas lazy-load model.
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

Environment, pipeline data, Mini GPT dan evaluator tersedia. Generator halaman terpilih TRAIN-025 step 1.800 menerima draft terstruktur yang melewati validasi source-bound. Kandidat ekstraktor brief bebas `REQUEST-EXTRACT-V1` step 1.800 masih menjalani evaluasi pada data synthetic development; gerbang raw dan safety API belum lulus, jadi ekstraksi otomatis belum diaktifkan. Jika kandidat belum tersedia, UI tetap menyimpan brief dan memakai editor manual. Final/test tetap tertutup.

UI prompt-first sekarang memakai satu brief dan satu klarifikasi gabungan, menyajikan bukti sumber untuk pemeriksaan, lalu menunggu persetujuan eksplisit sebelum generation. Build, lint, TypeScript, dan review browser di viewport sekitar 624 x 864 serta 1440 x 900 berhasil pada 17 Oktober 2026. Jalur prompt-first belum diverifikasi end-to-end dengan inference aplikasi. Panduan setup ada di [panduan API lokal](../apps/api/README.md) dan [panduan UI lokal](../apps/web/README.md). Data, BPE, checkpoint, dan output development tetap lokal.

Sebelum mengambil atau merilis data, periksa lagi revision, lisensi, atribusi, dan ketentuan penggunaan saat itu.
