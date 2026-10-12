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
- Task 5: complete. RUN-035 red; RUN-044 lulus 30 tests; RUN-045 preparation final; RUN-046 checksum/lineage/memorymap/CUDA batch lulus; RUN-047 reuse berhasil.

- Debugging: RUN-026 WebSight berhasil tetapi Vulcan gagal karena requests tidak terpasang. Regression RUN-028 gagal untuk sebab yang sama; adapter urllib pada RUN-029 lulus, live retry RUN-030 berhasil.

- Download selesai RUN-031: 20.000 v0.1, 30.000 v0.2, 5.000 Vulcan. Total raw 123.276.847 bytes. Manifest complete per source, free disk 28.776.210.432 bytes setelah download.

- Ruling: source CSS/JavaScript standalone tetap menjadi corpus kode, bukan dibuang karena tidak memiliki html/body. Group CSS mengabaikan nilai tema; language classification bersifat heuristic. Risiko: syntax/semantic quality belum dibuktikan dengan parser/browser penuh.
- Koreksi corpus: RUN-037/RUN-040 menyaring 3.204 record; inspeksi menemukan 3.200 CSS-only Vulcan dan empat HTML rusak. Regression RUN-041 gagal; RUN-042 menangkap var() CSS yang salah dibaca sebagai deklarasi JS. RUN-044 lulus setelah regex deklarasi diperbaiki. RUN-043 adalah percobaan lama; hasil final hanya RUN-045.
- Final data: accepted 54.996, rejected 4, duplicate 3.785, unique 51.211. Split train 41.639 / validation 5.016 / test 4.556. Group overlap dan exact-hash overlap kosong.
- BPE train-only 8.192; train tokens 19.038.770. Dataset queue 119 draft, reviewed 0. Tidak ada training model atau browser rendering.

## Review dan penutupan tahap data

- Satu reviewer independen pada range 7956be4..4160879 menemukan 4 Important, 0 Critical, 0 Minor. Semua Important diterima; tidak ada temuan yang ditunda. Detail: reports/REVIEW_PIPELINE_2026-10-12.md.
- Ruling: source family pretraining menjadi acuan SFT; group manual hanya boleh menggabungkan source dari partition yang sama. Alasan: seed yang sama pada subset berbeda tidak menjamin isolasi lintas fase. Biaya: kelompok harus memilih anotasi pada train/validation/test sumber; subset bisa memiliki rasio baris berbeda.
- Perbaikan satu pass: nullable HTML attributes, immutable source linkage/family, persisted split allocation, verified tokenizer/cache reuse, serta checker SFT berdasarkan status.
- RUN-048 red; RUN-049/RUN-050 green 37 tests. RUN-050 memakai ResourceWarning sebagai error. Fixture reviewed hanya untuk tests.
- RUN-051 mempertahankan split dan token artifacts dengan hash yang sama; action reused. RUN-052 integritas seluruh data aktual dan CUDA batch lulus. Free F 26,45 GiB.
- Ruling: branch feature tetap dipush sesuai instruksi pengguna; tidak digabung ke main karena Tasks 6-9 belum diimplementasikan. Workspace review plan tetap lokal untuk tahap berikutnya. Risiko: konsumen main belum mendapat kode tahap data hingga integrasi dipilih.
- Tahap data Tasks 1-5 complete. Model dan training Tasks 6-9 belum dimulai. SFT produksi awaiting_review; bukan model siap menghasilkan website.
