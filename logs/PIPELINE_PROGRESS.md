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

## Tahap model dan training, AI-006

- Pengguna mengizinkan kelanjutan setelah laporan tahap data. Tasks 6-9 dimulai dari b81cc61, checkout feature yang sama.
- Task 6: in_progress. RUN-053 preflight VENV/RTX 5070/BF16 lulus, F sekitar 26,45 GiB bebas.
- Task 6: complete. RUN-054 red missing module; RUN-055 green 41 tests termasuk causal-prefix, CPU gradient, context rejection, dan CUDA BF16. RUN-056 profile 14.186.496 parameter, batch 4 peak allocated 2,04 GiB; bobot profile dibuang.
- Pre-flight Tasks 5/6/7: dataset memberi input/labels [B,T], label sudah next-token; model memberi logits [B,T,V]. Engine memakai cross entropy langsung, tanpa shift kedua. Tidak ada konflik.
- Pre-flight Tasks 7/8: validation memakai target-mask yang sama dan agregasi berdasarkan jumlah token valid. Test partition baru dipakai setelah pemilihan checkpoint/hyperparameter berdasarkan validation.
- Ruling: jalankan smoke dan baseline pretraining yang dibatasi config setelah profiling, bukan SFT atas draft. Alasan: produksi reviewed masih 0. Biaya: kemampuan prompt-ke-PageSpec belum dapat dinyatakan siap meskipun pretraining berjalan.
- Task 7: complete. RUN-057/RUN-059 red; RUN-060 green 47 tests. Resume CPU dengan dropout/AdamW/scheduler/next-batch identik bitwise terhadap run tanpa jeda. Simulated OOM dan loss NaN menolak update; checkpoint terakhir konsisten dipertahankan.
- TRAIN-002 / RUN-061 smoke CUDA BF16 5 updates selesai. Last/best/config/metric/console dan report tersimpan, subset 32 train dan 8 validation blocks. Bukan baseline kualitas.
- Ruling: baseline config 1.200 update, batch 4 x accumulation 4, LR 0,0003 dengan warmup 60 dan cosine minimum 0,00003. Validation memakai 128 blok dipilih seed 59 dari partition validation. Alasan: sekitar satu lintasan token corpus sebagai baseline terbatas, cukup untuk memeriksa pembelajaran aktual. Risiko: belum optimum dan belum cukup untuk PageSpec instruction following.
- Baseline TRAIN-003 berhenti terencana pada step 200 (RUN-062): validation subset loss 9,1015 menjadi 2,2209, checkpoint cursor 800. TRAIN-004 (RUN-064) melanjutkan checkpoint yang sama hingga target 1.200 untuk membuktikan resume pada GPU aktual. Tidak mereset optimizer/scheduler/seed data.
- Task 8: complete. RUN-063 red; RUN-065/RUN-068 green 49 tests keseluruhan. RUN-066 mengukur full test token loss 1,070987 / perplexity 2,918259 pada 2.074.051 label valid; checkpoint dipilih lewat validation subset sebelum membuka test.
- TRAIN-004 selesai step 1.200, train loss akhir 0,933632 / validation subset 1,111391, total 19.657.265 token valid kumulatif. Peak allocated 2.181.572.096 bytes; resume step200 validasi sama, cursor lanjut hingga4800. RUN-067 kurva aktual 1.200 train points / 13 validation points tersimpan dan diperiksa visual.
- Generation probe eksploratif 4 prompt Indonesia: JSON parseable 0/4, schema valid 0/4; bukan evaluasi SFT held-out karena reviewed produksi 0. Tidak ada browser atau skor visual.
- Ruling: laporan gerbang aplikasi needs-data. Alasan: pretraining membaik pada kode, tetapi belum ada SFT reviewed dan probe JSON gagal. Biaya: produk preview/unduhan belum bisa dilanjutkan sebelum data instruksi dikurasi dan kemampuan PageSpec diuji.
- Task 9: complete untuk laporan gerbang, bukan klaim model/aplikasi siap. Laporan claims/artifact, grafik, checkpoint hash, license/attribution, dan batas bukti tersedia di reports/PIPELINE_TRAINING_SUMMARY.md serta docs/TRAINING_GUIDE.md. Pemeriksaan AST44 Python / JSON22 / Markdown30 (tautan dan tanpa em dash) lulus.
- Task 9 Step 4 Ruling: sampaikan gerbang needs-data kepada pengguna dan pertahankan aplikasi sebagai tahap berikutnya setelah kualitas model ditinjau. Belum meminta izin implementasi aplikasi karena probe PageSpec belum valid dan pengguna mengarahkan software di akhir. Biaya: pekerjaan aplikasi tetap menunggu kurasi/SFT; tidak ada persetujuan aplikasi yang diasumsikan.

## AI-007: notebook dan review akhir training

- Pengguna meminta notebook dan melanjutkan setelah jeda. Tiga notebook dibuat dengan VENV/kernel proyek. RUN-073 semua sel berhasil; tidak menambah training produksi.
- Review b81cc61..dd26110: 0 Critical, 5 Important, 1 Minor. Lima Important masuk satu fix pass. Notebook di luar frozen range reviewer dan diperiksa melalui eksekusi actual.
- Final: fixed resume best dan transaksi checkpoint, RUN-071 RED ke RUN-072 GREEN. Regression menjaga best yang dirujuk last saat save last gagal.
- Final: fixed parent SFT, membership test prompt, dan fingerprint evaluasi, RUN-071 RED ke RUN-072 GREEN. Fixture preparation/SFT RUN-074/075 membuktikan assignment tetap dan menolak spoofed test prompt.
- Final: fixed binding legacy, RUN-074 RED ke RUN-075 GREEN. Suite 58/58, reviewed hanya fixture.
- Final: minor (deferred): schema alternatif dihash tetapi validator memakai schema proyek; config actual cocok.
- Ruling: verified copy baseline sebelum preparation SFT. Alasan: legacy belum merekam fingerprint baru. Biaya: sekitar 163 MiB tambahan dan SHA payload baru meski bobot sama.
- RUN-076 verified copy, bobot identik, optimizer updates 0. RUN-077 gate baru menerima corpus actual; metrik dan probe sama dengan baseline asli.
- Ruling: pertahankan needs-data dan aplikasi sebagai tahap akhir. Biaya: software menunggu kurasi/SFT dan review kualitas, karena reviewed produksi 0 dan JSON probe gagal.
- Ruling: pertahankan feature branch dan push sesuai instruksi pengguna. Merge/PR belum diminta. Biaya: main belum memuat pipeline hingga integrasi dipilih.

- Verifikasi final: RUN-078 notebook 23 sel tanpa error; RUN-079 50 Python / 24 JSON / 37 Markdown / 3 notebook tanpa temuan; RUN-080 suite 58/58. Repository GitHub dikonfirmasi private. Feature branch tetap dipush tanpa coauthor trailer.
