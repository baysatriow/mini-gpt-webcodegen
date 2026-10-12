# Kode Sumber

`src/` direncanakan untuk pipeline data, Mini GPT, training, evaluasi, dan inferensi setelah planning ditinjau.

- `src/data/`: mengambil, menormalkan, memvalidasi, membagi, menokenisasi, serta memuat data.
- `src/models/`: decoder-only dari bobot acak dengan causal attention dan positional embedding mandiri.
- `src/training/`: objective, optimizer, precision, scheduler, checkpoint, dan metrik.
- `src/evaluation/`: loss/perplexity, pemeriksaan JSON/schema, prompt held-out, dan rubric hasil.
- `src/inference/`: generation, decoding JSON, validasi, dan antarmuka ke aplikasi akhir.
- `src/utils/`: konfigurasi, determinisme, pencatatan, dan reproducibility.

Interface yang disepakati untuk planning ada di [rancangan pipeline](../docs/PROJECT_SCOPE_AND_PIPELINE.md). Implementasi belum dimulai. Framework aplikasi web akan diputuskan pada tahap produk akhir.
