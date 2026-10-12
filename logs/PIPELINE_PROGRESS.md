# Pipeline ledger: docs/superpowers/plans/2026-10-12-pipeline-data-model-training.md

Tanggal: 12 Oktober 2026. Planning disetujui oleh pengguna, termasuk download dataset setelah pemeriksaan storage.

- Scope sesi: Task 1 sampai Task 5, pipeline data. Task 6 sampai Task 9 termasuk model dan training, dilaksanakan pada tahap berikutnya.
- Storage preflight: drive F memiliki 26,92 GiB bebas. Batas raw download 1 GiB; cadangan minimal 15 GiB; jangan ambil seluruh korpus WebSight 317 GB.
- Ruling: implementasi pada feature branch di checkout proyek yang sama sesuai plan yang disetujui. VENV dan data lokal tetap digunakan; worktree tambahan tidak dibuat agar lokasi environment dan dataset tetap konsisten. Risiko: branch harus di-switch bila ingin melihat main.
- Ruling: `columns` dipasang pada loader Parquet selain `select_columns`, karena dropping kolom setelah load tidak menjamin projection saat transfer. Mengikuti dokumentasi resmi HF Datasets.
- Ruling: data HTML untuk pretraining dipisahkan dari PageSpec untuk SFT. Anotasi otomatis tetap draft; tidak mengaku mendapat review manusia. Risiko: SFT produksi menunggu kurasi kelompok.
- Pre-flight interface: PageExample menjadi record kanonis; style_mode dan interactions dibaca dari target_spec, tanpa dua field yang bisa berbeda. Validator terdapat di schema.py, adapter validate.py menyediakan kontrak desain.
- Pre-flight interface: source row IDs memakai revision/config/hash ditambah indeks sampling, lalu anotasi menunjuk ID yang sama. Split berdasarkan fingerprint struktur HTML atau group anotasi, tokenizer hanya train.
- Probe metadata pertama gagal karena DatasetCardData bukan dict iterable. Koreksi memakai to_dict; revision dan lisensi kedua repo berhasil diperiksa.

## Progres

- Task 1: complete. RUN-022 gagal karena modul belum ada; RUN-023 lulus 4 tests schema dan aturan interaksi.
- Task 2: complete. RUN-029 lulus 10 tests; RUN-030 smoke 20 baris per source berhasil. RUN-031 menjalankan download penuh.
- Task 3: complete. RUN-027 red; RUN-032 lulus 16 tests keseluruhan. Draft tidak masuk SFT, source JS tetap string untuk pretraining.
- Task 4: complete. RUN-033 red; RUN-034 lulus 20 tests keseluruhan, group split repeatable dan dedup metadata-independent.
- Task 5: pending.

- Debugging: RUN-026 WebSight berhasil tetapi Vulcan gagal karena requests tidak terpasang. Regression RUN-028 gagal untuk sebab yang sama; adapter urllib pada RUN-029 lulus, live retry RUN-030 berhasil.

- Download selesai RUN-031: 20.000 v0.1, 30.000 v0.2, 5.000 Vulcan. Total raw 123.276.847 bytes. Manifest complete per source, free disk 28.776.210.432 bytes setelah download.
