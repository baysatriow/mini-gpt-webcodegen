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
- [Panduan training](TRAINING_GUIDE.md): profiling, smoke/baseline, resume, SFT, failure artifact, dan evaluasi.
- [Ringkasan baseline](../reports/PIPELINE_TRAINING_SUMMARY.md): hasil pretraining terukur, grafik, checkpoint dan probe JSON historis.
- [Hasil SFT pilot](../reports/SFT_PILOT_SUMMARY_2026-10-13.md): approval, 40 update, loss target dan generasi 0/4 valid.
- [Notebook proses](../notebooks/README.md): lima notebook, output aktual, dan kernel proyek.
- [Review training](../reports/REVIEW_TRAINING_2026-10-12.md): checkpoint terbaik, transaksi save, lineage parent/SFT/test, verified copy, dan Minor ditunda.

## Status

Environment, download subset, pipeline data, Mini GPT, loop training, checkpoint/resume, dan evaluator tersedia. Pretraining baseline dan SFT pilot reviewed selesai; generasi test pilot belum menjadi PageSpec valid. Gerbang needs-more-data-and-model-work, aplikasi web tahap akhir. Raw/processed data, tokenizer dan checkpoint berada di disk lokal. Code, config, manifest, attribution, log, grafik dan summary kecil dilacak Git.

Sebelum mengambil atau merilis data, periksa lagi revision, lisensi, atribusi, dan ketentuan penggunaan saat itu.
