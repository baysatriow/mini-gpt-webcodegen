# Data Proyek

Folder ini mendokumentasikan sumber, manifest, dan hasil pipeline dataset Mini GPT WebCodeGen.

- File mentah berada di `data/raw/` dan tidak dilacak Git.
- Hasil normalisasi berada di `data/processed/` dan juga tidak dilacak Git.
- Manifest menyimpan URL, revision, tanggal akses, lisensi, atribusi, nama kolom, hash, jumlah baris, filter, dedup, dan split.
- Record pretraining menyimpan text, code_language, source revision/license, transformation, group_id, dan split. Contoh SFT menyimpan PageExample dengan prompt dan target_spec; style_mode/interactions berasal dari target_spec.
- Data raw terdiri dari subset 20.000 WebSight v0.1, 30.000 WebSight v0.2, dan 5.000 Vulcan. Download selesai dan checksum direkam di manifests/.
- Byte-level BPE dan token cache terdapat di tokenizer/ dan processed/ lokal. Anotasi draft untuk tinjauan berada di annotations/ lokal.
- WebSight v0.2 diproses melalui streaming kolom teks tanpa screenshot. Vulcan hanya seed. WebMC tetap benchmark. Webdev belum dapat diverifikasi.
- Jangan campur data sebelum bahasa, schema, lisensi, dan fungsi sumber dicatat.

Lihat [rancangan pipeline](../docs/PROJECT_SCOPE_AND_PIPELINE.md), [analisis dataset](../docs/ANALISIS_DATASET_2026-10-12.md), dan [log eksperimen](../logs/LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md).
