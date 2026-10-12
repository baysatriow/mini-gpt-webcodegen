# Kode Sumber

`src/data/` menyediakan pipeline data yang sudah dapat dijalankan. Mini GPT, training, evaluasi, dan inferensi adalah tahap berikutnya.

- `src/data/`: mengambil, menormalkan, memvalidasi, membagi, menokenisasi, serta memuat data.
- `src/models/`: decoder-only dari bobot acak dengan causal attention dan positional embedding mandiri.
- `src/training/`: objective, optimizer, precision, scheduler, checkpoint, dan metrik.
- `src/evaluation/`: loss/perplexity, pemeriksaan JSON/schema, prompt held-out, dan rubric hasil.
- `src/inference/`: generation, decoding JSON, validasi, dan antarmuka ke aplikasi akhir.
- `src/utils/`: konfigurasi, determinisme, pencatatan, dan reproducibility.

Modul yang tersedia: sources.py (download/provenance), schema.py dan validate.py (PageSpec), normalize.py (kode/anotasi), split.py (group split dan peta keluarga bersama), integrity.py (lineage cache dan SFT), tokenizer.py (BPE baru), dataset.py (label/masking/memory mapping), pipeline.py (orchestrator). Kontrak label next-token sudah digeser dan tidak boleh digeser kembali dalam loss model.

Interface ada di [rancangan pipeline](../docs/PROJECT_SCOPE_AND_PIPELINE.md); petunjuk operasi di [panduan data](../docs/PIPELINE_DATA_GUIDE.md). Framework aplikasi web diputuskan pada tahap produk akhir.
