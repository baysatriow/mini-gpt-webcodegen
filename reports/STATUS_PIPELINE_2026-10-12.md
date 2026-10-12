# Status Pipeline Data, 12 Oktober 2026

Pipeline data telah diimplementasikan dan dijalankan pada VENV proyek. Model Mini GPT belum dibuat atau dilatih.

## Download dan storage

| Source | Baris | Raw MiB | Lisensi |
| --- | ---: | ---: | --- |
| websight_v01 | 20,000 | 38.84 | cc-by-4.0 |
| websight_v02 | 30,000 | 69.47 | cc-by-4.0 |
| vulcan | 5,000 | 9.26 | mit |

Total raw: 55,000 baris, 123,276,847 bytes (117.57 MiB). Storage preflight F 26,92 GiB; setelah preparation sekitar 26.45 GiB bebas. Raw budget 1 GiB dan reserve disk 15 GiB.

Manifest pinned, raw SHA-256, dan license card disimpan. Download ulang RUN-047 hanya memverifikasi dan memakai ulang file selesai. Tidak ada screenshot/aset eksternal yang diambil.

## Kurasi dan split

Preprocessing menerima 54,996 contoh dan menolak 4 dokumen HTML rusak. Sebanyak 3,785 exact duplicate dihapus, menyisakan 51,211 record dari 41,434 group.

| Split | Baris | Group | Token | Blok 1.024 |
| --- | ---: | ---: | ---: | ---: |
| train | 41,639 | 33,147 | 19,038,770 | 18,593 |
| validation | 5,016 | 4,143 | 2,266,877 | 2,214 |
| test | 4,556 | 4,144 | 2,074,052 | 2,026 |

Group ID dan exact hash antar split tidak beririsan. Family grouping merupakan heuristik struktur kode, belum bukti bebas kebocoran semantik. Rasio 80/10/10 dihitung pada group.

Peta keluarga ke partition disimpan dengan checksum dan digunakan kembali oleh SFT. Source family dihitung dari raw code, terpisah dari group anotasi yang bisa diedit. Penggabungan manual antar partition dan source family yang tidak ada pada corpus pretraining ditolak.

## Tokenizer dan data loader

Byte-level BPE vocabulary 8.192 dilatih dari train split saja. Hash tokenizer dan hash input train diverifikasi. Tidak menggunakan vocabulary atau bobot model pralatih.

| Split | P50 token/dokumen | P95 | Max | Melebihi blok |
| --- | ---: | ---: | ---: | ---: |
| train | 437 | 751 | 1,631 | 89 |
| validation | 440 | 680 | 1,511 | 15 |
| test | 443 | 674 | 1,461 | 11 |

Dokumen pretraining panjang dipack menjadi blok, tanpa membuang ekor. Token cache uint32 dibaca melalui memory mapping. Label next-token sudah digeser satu posisi; SFT memask prompt/padding dan menolak target JSON yang terlalu panjang.

## Bukti dan batas

- RUN-044: 30 unit tests lulus, termasuk schema, disk budget, incomplete/corrupt source, kurasi reviewed, group split, BPE, dan SFT masking.
- RUN-045: preparation final dengan classifier CSS/JS yang diperbaiki; hasil RUN-037/RUN-040/RUN-043 adalah percobaan terdahulu, tidak dipakai sebagai hasil final.
- RUN-046: integritas seluruh raw/split/cache, tokenizer lineage, dan transfer batch [2,1024] ke NVIDIA GeForce RTX 5070 lulus. Transfer ini bukan training Mini GPT.
- RUN-047: pemakaian ulang download selesai berhasil.
- RUN-048: regression setelah review gagal pada perilaku lama. RUN-050: seluruh 37 tests lulus, termasuk SFT yang mengikuti partition pretraining, lineage tokenizer/cache, dan validasi SFT complete pada fixture.
- RUN-051: preparation ulang mempertahankan corpus/split yang sama; tokenizer, profile, dan cache diverifikasi lalu dipakai ulang. Status complete, action reused.
- RUN-052: pemeriksaan aktual checksum raw/split/peta keluarga/tokenizer/cache dan transfer batch CUDA kembali lulus. F masih 26,45 GiB bebas.
- Queue review: 119 anotasi draft, 0 anotasi produksi reviewed. SFT produksi berstatus awaiting_review.
- Code sumber tidak dibuka/dirender untuk validasi browser pada tahap ini. Deteksi bahasa dan parse HTML adalah filter dasar, belum pemeriksaan penuh syntax CSS/JavaScript.

## Langkah berikutnya

Implementasi Mini GPT dari bobot acak dan profiling RTX 5070. Pretraining memakai split yang tersedia; penyelarasan prompt-ke-PageSpec memerlukan review anotasi Indonesia oleh kelompok.

Lihat [panduan pipeline](../docs/PIPELINE_DATA_GUIDE.md), [review dan perbaikan](REVIEW_PIPELINE_2026-10-12.md), [summary](../data/manifests/pipeline_summary.json), [validasi](../data/manifests/validation_summary.json), dan [log training](../logs/LOG_TRAINING.md).
