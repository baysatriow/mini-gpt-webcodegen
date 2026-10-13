# Progress halaman utuh, 14 Oktober 2026

## Hasil utama

Pipeline bertahap sudah menghasilkan halaman lengkap sembilan bagian pada sebagian request development. Model belum memenuhi gerbang95%; status **needs_more_model_work**. Final baru80 halaman tetap tertutup. Runtime v1/AI-013 dan artefak historis dipertahankan. UI aplikasi belum dikerjakan.

| Tahap | Update | Durasi | Ordinary CE terbaik | Complete generation |
| --- | ---: | ---: | ---: | ---: |
| TRAIN-016 pilot | 600 | 124.58 detik | 0.150913 | 0/20 development |
| TRAIN-017 best | 2400 total, best step1200 | 458.48 detik total | 0.035300 | 39/80 (48.75%) |
| TRAIN-017 last | 2400 | run yang sama | 0.037785 | 58/80 (72.50%) |

Best dipilih dengan ordinary CE sesuai aturan yang dibekukan. Last dilaporkan sebagai diagnosis; tidak dipromosikan sebagai kandidat final. First-attempt complete best=33, last=51; sesudah maksimal satu retry=39/58. Semua ekspor accepted lolos fakta terstruktur, required roles, CTA/fragment dan aset. Ini belum membuktikan kualitas browser atau penilaian manusia.

## Teknologi dan flow aktual

Request JSON berisi prompt, genre, style, business facts dan asset IDs. Model menghasilkan plan ringkas enam elemen per descriptor, kemudian menghasilkan isi masing-masing bagian. Validator menolak struktur/fakta yang salah. Komposer tidak mengisi konten yang gagal. Renderer mengekspor HTML, CSS biasa atau Tailwind lokal, SVG milik proyek dan JavaScript dari katalog. Formulir hanya memvalidasi lokal.

Context2048; plan output512; section output1536, prefix maksimal512 termasuk tiga penanda. EOS dapat mengakhiri keluaran lebih dini. Tidak ada truncation atau target fallback. Model14.579.712 parameter,6layer/6head/embed384, tokenizer proyek8192; tambahan posisi diperiksa dan dilatih, tanpa pretrained LLM eksternal.

## Data dan batas klaim

Curriculum baru240/40/40 families, dua genre dan dua style per family. Train5760, development960, final800 task rows. Semua sintetis, human_reviewed=False;12 anotasi human-reviewed historis tidak berubah. Shared component text dan template berulang secara sengaja. Empat sektor demo: studio, kafe, kursus, toko.

960 train rows termasuk retry mempunyai supervised labels setelah posisi1024. Sidecar6720 prompt/target hashes train/development tersedia. Final dibekukan sebelum training; target final tidak dipakai untuk fitting atau selection.

Urutan target tertentu ditahan antar split, tetapi request tidak meminta urutan tersebut secara eksplisit. Gerbang menerima urutan yang memenuhi role/fakta. Hasil ini bukan bukti generalisasi layout/order baru atau semua prompt bebas.

## RTX5070 dan storage

Profil batch4/8/12/16 dilakukan pada panjang2048 dan task sebenarnya. Batch16/accum3 dipilih, effective48, BF16/SDPA/fused AdamW, supervised-only projection. Throughput profil representative72030 target token/s; profil pendek dan campuran task berbeda mempunyai noise.

TRAIN-017 memakai 29,930,463 label target. GPU telemetry seluruh run: mean utilization88.48%, max99%, suhu max69C. Peak allocated3.48GiB. Disk free sesudah run16.56GiB. Best weights-only; exact resume memakai last dengan optimizer/scheduler/RNG/sampler. Reserve15GiB dan phase budget1.5GiB diperiksa sebelum checkpoint writes; tidak menghapus checkpoint/data lama.

## Mapping delapan tahap

| Tahap | Bukti | Status |
| --- | --- | --- |
| Kontrak dan token budget | RUN-206/207/208 | Implemented, fixture diagnosis |
| Migrasi positional embedding | RUN-209/210 | Identical old tensors dan short-prefix logits |
| Curriculum dan loader | RUN-211/212/226 | Frozen families, EOS/masking/sampler checked |
| Composer/renderer/aset | RUN-213 | Empat fixture manual, browser pending |
| Generator bertahap | RUN-214/215/230/231 | Raw attempts, retry, failure; sebagian halaman lengkap |
| Profil dan training | RUN-216/217/220/225/229 | Pilot dan main selesai |
| Gate dan final | RUN-230/231 | Development gagal95%; final tidak dijalankan |
| Notebook dan delivery | Notebook10/11, log dan gallery | Output aktual, human/browser pending |

## Artefak

- [Gallery best39](../examples/generated/AI-018-best-v2/index.html), [ZIP best](../examples/generated/AI-018-best-v2/websites.zip).
- [Gallery last58, diagnosis](../examples/generated/AI-018-last-v2/index.html), [ZIP last](../examples/generated/AI-018-last-v2/websites.zip).
- [Notebook10](../notebooks/10_fullpage_data_context_dan_gpu.ipynb), [notebook11](../notebooks/11_fullpage_training_dan_generation.ipynb).
- [Best development](fullpage/TRAIN-017_DEVELOPMENT_BEST_V2.json), [last development](fullpage/TRAIN-017_DEVELOPMENT_LAST_V2.json), [log training](../logs/LOG_TRAINING.md).

## Koreksi review dan hasil historis

Review menemukan nama hero Studio Pusanu untuk request Studio Pusanupu pada dua halaman BEST. RUN-234 mereproduksi celah nama, fakta tambahan dan konsumsi final. RUN-235 memeriksa koreksi menggunakan output asli serta claim sementara tanpa membaca final. RUN-236/237 memvalidasi ulang raw accepted: best turun41 menjadi39, last tetap58. Tidak ada model generation, target fallback atau perubahan output asli. Report V2 menjadi sumber acceptance saat ini.

Fakta layanan/proyek/tim/proses/FAQ/testimoni/harga hanya boleh berasal dari facts yang dirujuk. fictitious=True adalah pengungkapan demo; fakta demo tetap harus diberikan di request. Teks pemasaran umum masih diperbolehkan dan tidak dinilai sebagai verifikasi semua klaim bahasa alami. Guard final menyimpan identitas sebelum membaca request final, dengan hanya matching resume; final sebenarnya belum diklaim/dibuka.

Gallery awal dan ZIP lama adalah snapshot sebelum koreksi. Index awal dipertahankan dengan nama index_pre_review.html; index saat ini menampilkan notice superseded. Manifest awal hanya mengikat ZIP historis. Gallery V2 mempunyai manifest/ZIP baru dan revalidation.json per halaman, sementara result.json asli tetap historis.

Dua minor ditunda: binding scope/development request identity pada candidate lock, dan retry error-category yang membutuhkan contoh curriculum baru. Lihat laporan review [AI-018_REVIEW_AND_RULINGS.md](fullpage/AI-018_REVIEW_AND_RULINGS.md). Final dan aktivasi runtime tetap ditutup karena gate belum95%.

## Pekerjaan berikutnya

Perlu eksperimen train-only untuk kesalahan tuple plan, referensi media dan field isi bagian; tetap gunakan final yang belum dibuka. Perjelas layout/urutan yang diminta di request pada revisi data baru. Setiap budget/data/selection revision dibekukan sebelum run dan wajib tetap muat disk, tanpa memperlonggar validator atau mengisi keluaran gagal.

Review manusia dan browser390/1440 belum selesai. Tidak ada rating yang dibuat atas nama manusia. Unit test suite tidak ditambahkan/dijalankan sesuai instruksi sesi; bukti yang dilaporkan berupa diagnosis pipeline, profiling, training dan generation aktual.
