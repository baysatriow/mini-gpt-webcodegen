# Data Proyek

Folder ini mendokumentasikan sumber, manifest, dan hasil pipeline dataset Mini GPT WebCodeGen.

- File mentah berada di `data/raw/` dan tidak dilacak Git.
- Hasil normalisasi berada di `data/processed/` dan juga tidak dilacak Git.
- Manifest menyimpan URL, revision, tanggal akses, lisensi, atribusi, nama kolom, hash, jumlah baris, filter, dedup, dan split.
- Contoh kanonis menyimpan `example_id`, `prompt`, `target_spec`, `style_mode`, `interactions`, `source_id`, `source_revision`, `license_id`, `group_id`, dan `split`.
- WebSight v0.2 diproses melalui streaming kolom teks tanpa screenshot. Vulcan hanya seed. WebMC tetap benchmark. Webdev belum dapat diverifikasi.
- Jangan campur data sebelum bahasa, schema, lisensi, dan fungsi sumber dicatat.

Lihat [rancangan pipeline](../docs/PROJECT_SCOPE_AND_PIPELINE.md), [analisis dataset](../docs/ANALISIS_DATASET_2026-10-12.md), dan [log eksperimen](../logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md).
