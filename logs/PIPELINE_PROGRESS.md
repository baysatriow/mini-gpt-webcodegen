# Pipeline ledger: docs/superpowers/plans/2026-10-12-pipeline-data-model-training.md

Status terkini 14 Oktober 2026: pipeline V5 source-bound, selector, dan notebook 15 sudah disiapkan. Fresh source-bound run kini hanya dapat memakai ID TRAIN-025. TRAIN-026 hanya dapat melanjutkan checkpoint TRAIN-025 step 1800 dengan hash laporan dan checkpoint yang sesuai. Config beku saat ini SHA-256 `8852971e852e3b4ce6a6b845c24c8629e65d2a5f699d30968c2f3ce61a353186`. RUN-579 lulus 21 training tests. RUN-580 dan RUN-585 lulus 79 full-page tests. Notebook 15 memiliki 22 sel dan belum dieksekusi. Review ulang branch, commit/push, serta preflight GPU/storage segar masih menunggu sebelum TRAIN-025. Target tetap 76/80 dari 80 request development, dengan validation CE sebagai pendukung. Final tetap tertutup. [Log training](LOG_TRAINING.md), [interaksi AI-025](interaksi_llm/AI-025_2026-10-14.md), dan [notebook 15](../notebooks/15_fullpage_v5_source_bound_facts.ipynb). Catatan AI-011, AI-013, dan AI-022 di bawah tetap menjadi riwayat.

Tanggal: 12 Oktober 2026. Planning disetujui oleh pengguna, termasuk download dataset setelah pemeriksaan storage.

## AI-011: Dua output website dan batas model

- RUN-103/105/127/128: prefix sesuai, pilot underfit/hafalan, nama belum disalin konsisten, subword sta tidak ada dalam title train v3.
- TRAIN-007400update fit empat train, validation gagal; TRAIN-008/009 v1 schema24/24exact1/24; TRAIN-010 v2 final48/48exact tetapi Cakrawala menjadi Cahaya.
- TRAIN-011/012 lexical drills, heldout title families, final43/48exact89,58% gagal90%. Kriteria tidak diturunkan, test tidak dipakai memilih checkpoint. Corpus bukan human-reviewed.
- TRAIN-013 weighted name tokens16x/full ordinary validation tidak membaik. Beststep0 identik parent77tensors, freshfinalv5 tidak dibuka. Runtime tetap TRAIN-012best.
- RUN-139/142 dua Cakrawala diterima literalcontract, CSS/menu/form serta Tailwind/serif/hijau/tabs. RUN-141 Senandika salah menjadi Senanka, rejected tanpaHTML. Research --development dicatat quality_gate=false; default dan productionreviewed gate tetap.
- RUN-144 dua snapshot+ZIP di Git, indexhasil statis. RUN-14850filewebsite schema/raw/link/ARIA/JSsyntax/ZIPCRC/hash valid. Browserblocked, tidak ada JSruntime/visual claim.
- RUN-149/150 enam notebook48sel tanpaerror, optionalgenerationFalse. Notebook01-05 snapshot historis,06 terbaru. Source/log/config/hasil dipush tanpa Co-Authored-By.
- Berikutnya: tingkatkan ketepatan nama umum sampai overallgate lulus, evaluasi human/browservisual, baru UIgenerator/preview sandbox. Dua contoh tervalidasi tersedia sekarang, bukan model promptbebas.

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

- Ruling: pertahankan folder scratch review yang diabaikan Git karena pembersihan ditolak pemeriksaan otomatis dengan alasan blocked by policy. Biaya: artifact sementara review tetap di disk lokal; source/data/checkpoint dan hasil push tidak terdampak.

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

## AI-008: Review anotasi Indonesia

- Ruling: laksanakan persiapan review dari tahap anotasi yang sudah disetujui. Alasan: baseline belum menghasilkan PageSpec valid dan produksi reviewed masih 0. Biaya: SFT menunggu data yang ditinjau; aplikasi tetap tahap akhir.
- RUN-081 gagal import package pada script authoring lokal, RUN-082 berhasil setelah pembacaan JSON mandiri.
- RUN-083 mengekspor pilot 12 draft/12 keluarga, enam CSS biasa dan enam Tailwind, empat per partition asal. Queue awal 119 draft/102 keluarga diaudit.
- Seluruh pilot lolos schema/context, maksimum 640 token dari batas 1.024. Dua interaksi berasal dari script sumber, tanpa memasukkan kode script ke PageSpec.
- Ruling: semua tetap draft, reviewer kosong. Alasan: proyeksi layout, terjemahan dan tujuan link belum ditinjau manusia. Biaya: belum ada data SFT produksi meski format benar.
- RUN-084/085 menambah dan menjalankan notebook 04; total empat notebook/30 sel tanpa error, gate loader menolak draft.
- Needs-data: review konkret pada `outputs/annotation_review/pilot-id-v1/packet.html` dan `review.csv`, revisi link/proyeksi, perluas coverage, lalu preparation SFT. Tidak ada TRAIN baru.
- RUN-086: 51 Python, 25 JSON, 39 Markdown, 4 notebook/30 sel tanpa temuan. `git diff --check` bersih; private GitHub dan ignore paket lokal dikonfirmasi. Source notebook lama dipertahankan, notebook kurasi baru menyimpan hasil eksekusi.

## AI-009: Revisi pilot dan kandidat perluasan

- RUN-087/088: v2 12 draft/12 keluarga; empat target/lima prompt direvisi. Semua fragment tersedia dan target <=1.024 token, maksimum 612.
- Ruling: source ID/family/partition dipertahankan; tautan fungsi yang tidak didukung dihapus. Alasan: menghindari janji fitur/section rekaan. Cost: proyeksi lebih sempit, perlu persetujuan manusia.
- RUN-089: katalog train 14 kandidat/14 keluarga. Sinyal yang terdeteksi belum merupakan anotasi, modal/filter belum ditemukan heuristik. Tabs source tidak memiliki fungsi yang dipanggil; accordion native perlu review adaptasi.
- RUN-090/091: notebook 04 v2 berisi perbandingan perubahan/coverage, empat notebook/32 sel tanpa error. Tidak ada TRAIN baru.
- Needs-data: paket v2 dan worksheet tersedia, keputusan/nama reviewer diminta. Reviewed produksi masih 0; perlu review dan perluasan corpus sebelum SFT.
- RUN-092: 52 Python, 28 JSON, 40 Markdown, empat notebook/32 sel valid tanpa temuan. Diff whitespace bersih dan GitHub private dikonfirmasi ulang. Paket/source kandidat tetap lokal.

## AI-010: Reviewed SFT pilot

- Direct human approval "aprove lanjut" untuk seluruh 12 kandidat v2. RUN-093 reviewed copy baru, reviewer teknis user_chat_approval, tanpa mengarang nama/checklist individual. Paket asli immutable.
- RUN-094 12 accepted/0 rejected/0 duplicate, 4 train/4 validation/4 test, tokenizer/cache/family assignment tetap.
- RUN-095 TRAIN-005 smoke3, selesai. RUN-096 TRAIN-006 pilot40, selesai, parent pretrain sama; validation loss7,512 ke3,739, peak allocated1,179GiB, free24,07GiB.
- RUN-097 test JSON target loss3,488/PPL32,729, generasi0/4valid/parseable; empat output token_limit768. Tidak ada repair, tuning dari test atau browser acceptance.
- Ruling: budget40 dan best validation ditetapkan sebelum test. Cost: pilot empat train belum memadai. Perlu perluasan reviewed train berdasarkan katalog proyek; test yang sudah dilihat hanya eksploratif untuk penggunaan berikutnya.
- RUN-098/099 notebook05/profil/grafik; lima notebook38sel tanpa cell error. Snapshot output notebook01-04 dipertahankan, status terbaru pada05.
- Ruling: aplikasi tetap tahap akhir, needs-more-data-and-model-work. Tidak menyalin target test ke train. Kandidat tambahan belum disetujui oleh approval12pilot.
- RUN-100/101: hasil dan log lengkap ditulis; 53 Python / 35 JSON / 42 Markdown / lima notebook dengan 38 sel valid, tanpa temuan format/syntax/link. Private GitHub dan ignore reviewed/raw/checkpoint dikonfirmasi. Dua blank line baru pada log diperbaiki sebelum commit.

## AI-012: Optimasi training GPU

- RUN-156 mengonfirmasi VENV/CUDA/RTX 5070. RUN-157 sampai RUN-160 melakukan empat sweep aktual yang terpisah. Bobot probe dibuang; train-only, tidak membuka final.
- Config terpilih batch 48, BF16, SDPA, fused AdamW, proyeksi token target, dan expandable segments. Batch 64 sedikit lebih cepat tetapi ditolak karena headroom kurang dari 1 GiB. Tidak melakukan perubahan power limit, clock, driver atau arsitektur.
- RUN-161 operator profiler menunjukkan memory-efficient attention CUTLASS dan fused AdamW, bukan klaim FlashAttention.
- RUN-162 TRAIN-014 selesai 800 update, 162,257 detik, 14.365.682 target labels. Throughput update setelah lima step awal 99.200 token target/detik, sekitar 3,43 kali baseline probe. Active GPU mean 93,23%, maksimum 100%, suhu maksimum 67C. Tidak ada exception/OOM/nonfinite.
- Best step 0, 77 tensor identik parent TRAIN-012. Kualitas terpilih tidak membaik. RUN-163 development 24/24 schema valid, 20/24 exact; final v5 tetap tertutup. Runtime website tetap TRAIN-012 dengan overall historical gate gagal 43/48.
- RUN-164 laporan/plot/notebook baru dan selection diagnostic; RUN-165 log training komprehensif; RUN-166 notebook 07 delapan sel tanpa error. Notebook 01 sampai 06 tetap dipertahankan. Peringatan Jupyter ditulis verbatim di RUN log.
- [Laporan GPU](../reports/GPU_TRAINING_OPTIMIZATION_2026-10-13.md), [notebook 07](../notebooks/07_optimasi_gpu_dan_training.ipynb), dan [interaksi AI-012](interaksi_llm/AI-012_2026-10-13.md).
# Status terbaru, AI-013, 13 Oktober 2026

- TRAIN-015 selesai 2.400 update dengan data v6, total40.158train. Data tambahan21.090row sintetis, reviewed manusia tetap12. Validation/test/final v5 dipertahankan byte-identik selama pengembangan.
- Development24/24schema dan24/24exact. Kandidat bestCE dipilih sebelum satu final:48/48schema dan44/48exact91,67%, melewati threshold90%. Empat kesalahan disimpan. Final ini sekarang consumed, bukan bahan pemilihan eksperimen selanjutnya.
- Runtime command terbaru TRAIN-015 best. Gallery44website dan ZIP diekspor dari raw output yang accepted, HTML/CSS/Tailwind/JavaScript lokal. Prompt Senandika yang dahulu gagal kini diterima pada RUN-185.
- Notebook08/09 dijalankan,9+6sel tanpa error; notebook01-07 dipertahankan. TRAIN log memuat budget, ancestry/hash, objective, disk, telemetry, hasil dan batas bukti.
- [Final gate](../reports/FINAL_GATE_2026-10-13.md), [gallery](../examples/generated/AI-013/index.html), [notebook08](../notebooks/08_kualitas_penyalinan_dan_training.ipynb), [notebook09](../notebooks/09_evaluasi_final_dan_output.ipynb).
- Tahap berikutnya: UI input dengan grammar prompt yang didukung, validasi per request, preview sandbox, unduhan, dan browser acceptance saat surface inspection tersedia. Prompt bebas/layout baru belum terbukti. Semua bagian berikut adalah riwayat tahap sebelumnya.

## AI-014: Permintaan halaman lengkap, 2026-10-13

- Scope pilihan pengguna: landing page dan company profile. Analisis selesai, implementasi baru belum dimulai.
- Seluruh train v6 memiliki 3 sampai 5 bagian. Fixture manual 9 bagian valid memerlukan 1.498/1.479 token, melebihi konteks 1.024. RUN-194 gagal validasi fixture, RUN-195 rerun berhasil; keduanya dipertahankan.
- Usulan: plan halaman, isi per bagian, komposer, renderer dengan variasi layout dan aset lokal. Review arah arsitektur berikutnya sesuai brainstorming. [Laporan](../reports/FULL_PAGE_DIRECTION_2026-10-13.md).

## AI-015: Arah disetujui, spesifikasi tertulis tersedia

- Pengguna menyetujui generasi bertahap dan menanyakan konteks 2.048. Target kandidat 2.048 disertai migrasi posisi, output budget terpisah serta profiling sebelum training.
- [Spesifikasi](../docs/superpowers/specs/2026-10-13-full-page-generation-design.md) tersedia untuk review; selanjutnya rencana implementasi setelah review. Belum ada implementasi atau training baru.

## AI-016: Output maksimum 1.536 ditetapkan

- Spesifikasi pipeline baru memakai context2.048 dan output task isi1.536, prefix maksimum512 termasuk penanda. Task plan512. Belum mengubah runtime/checkpoint lama atau menjalankan training.

## AI-017: Rencana implementasi tersedia untuk review

- Spesifikasi dilanjutkan setelah pengguna Gas bro. [Rencana delapan tahap](../docs/superpowers/plans/2026-10-13-full-page-generation.md) tersedia dengan context2.048/output1.536, plan ringkas512 dan migrasi terukur.
- Status: planning selesai dan self-review dilakukan, kode/migration/training baru belum dimulai. Review rencana dan metode eksekusi berikutnya sesuai writing-plans, Native direkomendasikan untuk efisiensi.

## AI-018: implementasi dan training halaman utuh

- Kontrak2.048/plan512/section1.536, migrasi posisi, curriculum320families, composer/renderer/aset lokal dan generator bertahap tersedia.
- TRAIN-016600 dan TRAIN-0172400 selesai. Best39/80, last58/80 development; keduanya gagal95%. Final tetap tertutup.
- Gallery accepted saja, notebook10/11 dan [laporan](../reports/FULL_PAGE_PROGRESS_2026-10-13.md) tersedia; human/browser/UI pending. Artefak lama tetap dipertahankan.

### Delivery AI-018, 14 Oktober 2026

RUN-241 notebook11 selesai8 cells; notebook10 SHA tetap7 cells. RUN-243 bytes ZIP/file972 dan HTML local links99 checked, source/raw/page/notebook/document identity checked. BEST39/80, LAST58/80 development V2; final/human/browser/UI pending. Untuk penerimaan saat ini gunakan gallery V2; gallery awal/ZIP historis tidak dipakai sebagai acceptance terkini. Dua minor review ditunda sebelum final nyata.

## AI-019, eksperimen fullpage-v2, 14 Oktober 2026

- WebMC pinned revision berhasil diunduh dan diperiksa:600 soal pilihan ganda, bukan file training50.000. Tidak dimasukkan ke SFT. Webdev API publik membalas401 dan ketersediaannya belum terkonfirmasi.
- Curriculum v2 train-only dan sampler plan70%/section30% disiapkan. RTX5070 profile memilih batch16, accumulation3, effective48. TRAIN-018 fresh INIT2048 berhenti pada global1800 lalu TRAIN-019 exact resume sampai3600.
- Development 80 prompt menghasilkan46/80 pada1800 dan70/80 pada3600. Baseline LAST TRAIN-01758/80. Step3600 terpilih, peningkatan12 halaman dari baseline tetapi masih kurang6 untuk gate76/80.
- Peta gagal yang disimpan menunjukkan isu berulang di identity/name, plan required fields dan service/fact grounding. Final tetap tertutup, candidate tidak dikunci. Validator ketat tidak diubah.
- Notebook [12](../notebooks/12_perbaikan_fullpage_dan_evaluasi.ipynb) merekam profile, kurva loss, evaluasi dan error map. Training log komprehensif di [LOG_TRAINING.md](../logs/LOG_TRAINING.md); laporan pemilihan di [AI-019_DEVELOPMENT_SELECTION.json](../reports/fullpage/AI-019_DEVELOPMENT_SELECTION.json).
- Berikutnya: brainstorming bounded untuk eksperimen train-only dengan contoh nama literal, kelengkapan field plan, dan konten struktural yang hanya mengacu pada fakta request. Perlu persetujuan desain sebelum perubahan berikutnya. UI, browser, review manusia dan final masih pending.

### Koreksi diagnosis error RUN-277

Pemeriksaan pesan validator mentah mengonfirmasi tiga keluarga mengalami plan identity/style mismatch, satu navbar brand mismatch, dan satu FAQ berisi item yang tidak didukung business fact. CSS biasa dan Tailwind pada keluarga gagal mendapat hasil sama, jadi pola masalahnya ada di konten/model bersama, bukan renderer style. RUN-278 memperjelas kategori ini di notebook12. RUN-275 adalah kesalahan variabel pada wrapper verifikasi setelah notebook berjalan, bukan kegagalan cell; RUN-276 mengonfirmasi keenam code cell tersimpan tanpa error.

## AI-020: Eksperimen fullpage-v3, 14 Oktober 2026

- Kurikulum v3 menambahkan 960 halaman sintetis, 480 alias nama, dan 5.760 task ke train dari 240 keluarga yang sama. Validation/test tetap sama checksum; data belum ditinjau manusia.
- RTX 5070 profile memilih microbatch 8, accumulation 6, effective batch 48. TRAIN-020 mencapai step 1800 dan TRAIN-021 exact-resume mencapai step 3600.
- Pada 80 prompt development, kedua checkpoint memberikan 0 halaman lengkap. Cross entropy masing-masing 0,005813 dan 0,007596, tetapi keduanya gagal kontrak halaman. Baseline TRAIN-019 tetap 70/80; gate 95 persen memerlukan 76/80.
- Error dominan adalah JSON rusak pada role `process`. Jumlah baris role ini tetap 480 pada v2 dan v3, sementara role navigation, services, FAQ, portfolio dan footer ditambah. Ini hipotesis untuk eksperimen berikutnya, bukan bukti sebab-akibat.
- Perbandingan laporan membuktikan sampler baseline dan v3 sama-sama memakai plan 70 persen. Jadi perlakuan v3 adalah distribusi augmentation, bukan perubahan rasio. Koreksi dicatat dalam notebook 13 dan selection report.
- Tidak ada kandidat yang dipromosikan. Final tetap tertutup, tidak ada review browser atau manusia. [Notebook 13](../notebooks/13_fullpage_v3_targeted_training.ipynb), [training log](../logs/LOG_TRAINING.md), [AI-020](../logs/interaksi_llm/AI-020_2026-10-14.md).
- Sebelum training baru, rancangan perlu memprioritaskan contoh section `process` yang valid dan copy title persis, dengan data train-only dan evaluation development beku. Minta review desain sebelum mengubah strategi training.

CodeGraph index lokal tersedia dan telah disinkronkan setelah perubahan source v3 pada RUN-318, RUN-321, dan RUN-323.

Paket v3, notebook, dan rekam eksperimen dipush ke branch `feature/pipeline-data-model-training` pada commit `8be8a53`. Penutupan checklist dan dokumentasi commit menyusul pada `aa29b4d`.

### Diagnosis raw output v3

RUN-331 membandingkan satu target train role `process` dengan keluaran gagal TRAIN-020. Target menulis `id=process` dengan JSON valid, sedangkan model mengeluarkan `{"id":"props":...}` dan berhenti di EOS setelah231 token. Pada v3 role process tetap480 dari17.280 section rows, turun dari3,85 persen menjadi2,78 persen dari v2. Ini hipotesis kemungkinan data dilution, belum bukti kausal. Usulan kontrol berikutnya adalah menambah target process untuk train page yang memiliki role tersebut, dengan prompt v3 dan seluruh setting lain tetap. Eksperimen tersebut kini tercatat di AI-022 dan hasilnya belum mencapai target. Detail di [AI-021](../logs/interaksi_llm/AI-021_2026-10-14.md).

## AI-022: eksperimen fullpage v4, 14 Oktober 2026

- V4 menambahkan960 target section `process` dari keluarga train saja. Train menjadi24.000 rows dan target role process naik480 ke1.440. Validation dan test tetap sama checksum.
- RTX 5070 profile memilih microbatch8 dan accumulation6, effective batch48, untuk mempertahankan konfigurasi eksperimen yang dibekukan. Batch16 hanya2,6 persen lebih cepat pada sampel profile.
- TRAIN-022 mendapat64/80 halaman pada update1.800. Exact resume TRAIN-024 berakhir di update3.600 dan mendapat68/80 halaman. Target95 persen memerlukan76/80, sehingga kandidat belum lolos gate.
- Error utama candidate terbaik adalah plan identity/style mismatch, disusul mismatch fakta merek pada hero/navigation dan teks about. Validator tidak dilonggarkan; tidak ada klaim kausal dari satu eksperimen.
- TRAIN-023 gagal pada storage preflight di update0. Checkpoint resume historis dipindahkan dengan checksum terverifikasi dan junction di lokasi awal; TRAIN-024 melanjutkan dari TRAIN-022/step1800. Semua failure/retry dicatat.
- Notebook14 menjalankan16 sel tanpa error. Data tetap sintetis, human review dan browser visual review belum dilakukan, final benchmark tidak dibuka.
- Laporan ranking: `reports/training/FULLPAGE-V4_DEVELOPMENT_SELECTION.json`. Detail hardware, config, lineage, metrics, errors, dan run IDs ada pada `logs/LOG_TRAINING.md` dan [AI-022](interaksi_llm/AI-022_2026-10-14.md).

### Diagnosis lanjutan TRAIN-024, 14 Oktober 2026

- RUN-380 menelusuri attempt mentah pada 12 halaman gagal. Seluruhnya terkumpul pada enam keluarga nama usaha. Kesalahan berulang berupa ejaan nama yang dipotong atau diganti pada plan, navigation, hero, dan about.
- Pair CSS biasa dan Tailwind sering mendapat hasil teks gagal yang sama. Ini mendukung prioritas perbaikan identity/fact copy model bersama, bukan penyesuaian renderer CSS.
- Pilihan berikutnya untuk review: probe prompt copy eksplisit, penambahan target copy identitas dari keluarga train saja, atau perubahan kontrak agar identitas dan fakta diikat dari request oleh renderer. Belum ada perubahan atau training v5.
- Catatan bukti lengkap: [AI-023](interaksi_llm/AI-023_2026-10-14.md), [training log](LOG_TRAINING.md), RUN-379 dan RUN-380.

## AI-024: Desain source-bound facts dan penanganan prompt, 14 Oktober 2026

- Pengguna memilih perubahan kontrak yang merujuk fakta langsung ke request karena error v4 didominasi penyalinan nama dan fakta.
- Spec baru mempertahankan input request terstruktur di pipeline model. Untuk UI prompt bebas yang akan dibuat kemudian, request tidak jelas atau kurang fakta wajib meminta klarifikasi; request di luar cakupan diberi pesan cakupan; tidak ada output parsial atau file.
- Request valid menghasilkan plan dengan referensi fakta. Resolver/renderer memakai fakta literal dari request. Model tidak menghasilkan JavaScript bebas.
- [Spec untuk review](../docs/superpowers/specs/2026-10-14-fullpage-source-bound-facts-design.md). Tidak ada implementasi atau training baru.

## AI-025: Rencana implementasi source-bound fullpage, 14 Oktober 2026

- Pengguna menyetujui arah spesifikasi dan meminta pekerjaan dilanjutkan. Rencana implementasi ditulis untuk ditinjau sebelum perubahan kode atau training dimulai.
- Rencana menguraikan sepuluh bagian: schema source-bound versioned, resolver/composer, generation dan legacy dispatch, intake/status, target train-only, warm-start TRAIN-024 dengan optimizer baru, development selector, notebook, TRAIN-025 step 1.800, dan resume TRAIN-026 step 3.600.
- Inspeksi menunjukkan runner saat ini hanya menyediakan exact resume. Jalur weights-only initialization yang terpisah direncanakan supaya bobot TRAIN-024 dapat dipakai tanpa membawa optimizer, scheduler, sampler, atau RNG lama.
- Keluarga data dan 80 prompt development tetap beku; test hanya diverifikasi dengan hash bytes dan tidak diparse. Target tetap 76/80 dan final benchmark tetap tertutup.
- [Rencana implementasi](../docs/superpowers/plans/2026-10-14-fullpage-source-bound-facts.md), [spesifikasi](../docs/superpowers/specs/2026-10-14-fullpage-source-bound-facts-design.md), [interaksi AI-025](interaksi_llm/AI-025_2026-10-14.md). Belum ada implementasi, test, perubahan dataset/checkpoint, training, atau evaluasi.

### Source-bound V5 training readiness, 14 Oktober 2026

- Source-bound schema, resolver/composer, staged generator, prompt intake, V5 train/development corpus, warm-start lineage, development selector, and notebook foundation are implemented. The training/evaluation UI is still not built.
- V5 is synthetic and not human-reviewed. It contains 240 train families and 40 development families, 3,360/80 requests, and 33,600/800 task rows. Final and test rows remain outside the V5 training corpus.
- TRAIN-024 is pinned as the only V5 initialization parent: step 3,600, weights-only, SHA-256 `913b1b00aec040a0d51c3607cf7261288e7fe089378850fc66c131400c0f319a`. The source-bound engine loads these weights before creating a fresh optimizer; the legacy INIT-2048 path retains its previous ordering; exact resume tests still pass.
- Historical config SHA-256 `195c314855fddc340f0b1f7a32ce77dae0a436fa55aed0b23b0cbe8d545a8f64` pinned the V5 manifest and engine before later guard revisions. Current config SHA-256 is `6ef910cca039890916fb97217d2c4f934b11e3332c1376021c70797ad06e7842`; prior configs remain archived under `logs/config-archive/`.
- RUN-537 passed all 17 training tests. RUN-538 passed all 71 full-page tests. RUN-529 passed the project `.venv` RTX 5070 CUDA/BF16 check, parent/data lineage, and storage reserve. RUN-535 reverified config lineage after the final engine change; RUN-536 rebuilt the 22-cell notebook.
- Storage preflight measured 17,301,045,248 bytes free against 16,706,895,872 bytes required including the 15 GiB reserve and checkpoint estimate. This is the earlier preflight measurement; repeat it immediately before TRAIN-025.
- Notebook: [15, source-bound V5 training](../notebooks/15_fullpage_v5_source_bound_facts.ipynb). It separates TRAIN-025 weights-only initialization at step 0 to 1,800 from TRAIN-026 exact resume to step 3,600.
- Remaining before training: whole-diff review, commit/push, and immediate storage/GPU preflight. Training has not started. The development selector waits for both real checkpoint reports. The 76/80 gate is unchanged and final data is unopened.

### Implementasi source-bound v1 dimulai

- 14 Oktober 2026: mulai Task 1 pada branch `feature/pipeline-data-model-training` setelah persetujuan pengguna.
- Kontrak test RED tercatat pada RUN-381 karena builder source-bound belum tersedia. Implementasi belum mulai saat pemeriksaan merah dijalankan.
- Historical note: split dataset tetap tertutup dan training belum dimulai. Rujukan AI-026 hanya berlaku untuk tahap implementasi terdahulu dan bukan status keputusan terbaru.

### Source-bound Task 1 verification

- Implemented the two closed source-bound v1 schemas, catalog, PagePlan/SectionDraft validators, and an explicit schema preparation switch.
- RUN-382 passed 6 focused tests. RUN-383 generated both new schemas. RUN-385 proved all four legacy schema hashes are unchanged. RUN-384 was a failed overbroad verification script and is preserved with its correction in RUN-385.
- Training and dataset preparation have not started. Task 1 awaits final diff review and commit.

### Source-bound Task 1 final checks

- Catalog shape validation now returns an error for malformed mapping types instead of raising. SectionDraft asset references are checked against the trusted asset catalog as well as the request and PagePlan.
- RUN-387 recorded the regression failures. RUN-388 passed all 7 focused tests. RUN-389 refreshed the CodeGraph index.
- Task 1 can proceed to final diff review and commit. No dataset, checkpoint, or training artifacts were created.

- RUN-391 completed the staged diff whitespace check with no errors after correcting the two command-output EOF blanks.

### Explicit schema artifact loading

- Source-bound validators now load the checked-in schema files through an explicit `source-bound-v1` mapping and verify the schemas before use.
- RUN-392 recorded the expected RED import failure. RUN-393 passed all 8 focused tests, including generated-file equality.
- Task 1 is ready for CodeGraph refresh and final diff review.

### CodeGraph refresh before Task 1 review

- RUN-394 completed with exit 0 after schema validators were changed to load the versioned artifacts directly.

- RUN-395 confirmed the complete staged Task 1 diff has no whitespace errors.

- RUN-396 normalized three decorative CodeGraph output separators to plain text and confirmed the staged diff remained whitespace-clean.

### Source-bound Task 2 implementation

- Added a resolver that maps validated request fact references to PageSpec properties, and a composer that builds PageSpec 2.0 metadata, theme, and supported interactions from the request and local catalog.
- Contact form fields and hero alternative text are static entries in the source-bound copy catalog. The composer reuses the existing semantic fact checks and fullpage schema validation before returning the complete page.
- RUN-397 recorded the expected import failure before implementation. RUN-405 found that the first negative-test catalog fixture violated its own mapping contract before reaching the intended semantic check. The fixture was corrected without weakening validation; RUN-406 then passed all 15 focused tests across both genres and styles, including repeated service references, escaped HTML-sensitive text, missing references, and unprovided catalog items.
- Task 2 code review and commit are pending. No dataset, checkpoint, training, UI, or backend change has been made in this task.

### Task 2 commit and push

- Task 2 is complete in commit 87182d0b1e43d7aca4ce8bf74d7db20e223511af, pushed to origin/feature/pipeline-data-model-training.
- RUN-406 passed the final 15-test focused source-bound suite. RUN-412 records the commit and push. Task 3 generation dispatch is next.

### Source-bound Task 3 implementation

- Added checkpoint-versioned source-bound prompts and canonical JSON serialization. Checkpoints without `fullpage_contract_version` retain the legacy generator path.
- The v1 path validates request and prompt budgets, requires EOS, retries once, prechecks every planned section prompt before any section generation, resolves only validated catalog and request references, and exports through the existing renderer using a temporary directory promoted only after success.
- Evaluation identity now hashes the source-bound prompts, serializer, validators, resolver, composer, renderer, asset catalog code, versioned schemas, and copy catalog. A focused test protects the legacy and source-bound identity split.
- RUN-421 passed 10 focused generation tests. RUN-422 passed all 25 full-page tests. RUN-423 synchronized CodeGraph. No dataset, checkpoint, training run, UI, or backend changed in Task 3. Real checkpoint generation and browser review remain pending.
- Task 3 code is committed as `efcbd4453dd8b49b11da12176695e852c84e8f5f` (`feat: dispatch source-bound fullpage generation`) and pushed to `origin/feature/pipeline-data-model-training`; RUN-426 and RUN-427 contain the commit and remote verification records.

### Source-bound Task 4 prompt intake

- Added a versioned RequestDraft schema and fixed capability catalog. Intake validates user-confirmed or exact prompt-span evidence for every scalar and nested fact, request limits, catalog references, and required business facts.
- Explicit unsupported capabilities require a matching prompt quote from the catalog. Unsupported genre or style labels are classified as out of scope only when they are explicitly mentioned in the original prompt. Unmentioned draft labels request clarification.
- Generation statuses map to stable user-safe messages. Raw validator and model errors are hidden. Intake does not run an extraction model, modify the original prompt, create a page, or write output files. No `app/` files changed.
- RUN-446 passed 17 focused intake tests. RUN-447 and the final RUN-453 passed all 42 full-page tests. RUN-444 captured a negative-test fixture mismatch and RUN-450 captured and corrected a whitespace issue in the summary log.
- Task 4 is committed as `8bc231700e028b25160465bcf7c1d21e8ac12fb8` (`feat: validate fullpage prompt intake evidence`) and pushed to `origin/feature/pipeline-data-model-training`; RUN-456 and RUN-457 confirm the push.
- Historical note: no dataset, checkpoint, or training artifact had changed at this earlier Task 4 milestone. Task 5 has since been completed with train-family-only V5 targets and frozen validation/final partitions.

### Resume-parent verification follow-up

- RUN-565 reproduced that TRAIN-026 could reach generic resume handling with a non-TRAIN-025 path. The trainer now rejects any other run ID or parent path before reading the checkpoint or creating run artifacts.
- TRAIN-025 report/config identity, step-1800 committed state, checkpoint digest, and full optimizer/scheduler/sampler/RNG state are verified by the trainer. The development selector checks the same parent report and hash recorded in TRAIN-026.
- RUN-566 passed 21 focused regressions. RUN-568 refreshed config SHA-256 to `0ee3332b0a3f19e42efe2ddb2eb6a1dbf69add7e84511323efeffa418bf78244`; RUN-569 rebuilt notebook 15 with 22 cells. RUN-570 passed 20 training tests, and RUN-571 passed 79 full-page tests.
- TRAIN-025 remains unstarted. Await the fresh whole-branch review, commit and push, then repeat the live RTX 5070 and storage preflight. Final data remains sealed.


## TRAIN-025 runtime gate

RUN-589 passed the fresh RTX 5070, CUDA BF16, V5 lineage, TRAIN-024 parent, output-path, and storage checks. Storage headroom above the frozen reserve plus checkpoint estimate is 78,761,984 bytes, so it must be monitored. Commit `eb9d8d6` is pushed. TRAIN-025 launch at the approved 1,800-step boundary is next; training has not started at this entry. Final data remains closed.


## TRAIN-025 status

RUN-589 preflight passed and was pushed. RUN-590 records launch of fresh TRAIN-025 from the verified TRAIN-024 checkpoint with the frozen V5 config, stopping at step 1,800. Monitor storage due to about 75 MiB preflight headroom. TRAIN-026 and evaluations remain pending.


## TRAIN-025 complete, TRAIN-026 waiting on storage

RUN-590 completed TRAIN-025 at step 1,800. Its report and `last.pt` passed exact-resume lineage validation. RUN-591 did not launch TRAIN-026 because free space is 273,317,888 bytes below the frozen reserve plus checkpoint estimate. Free at least this amount, preferably more, then rerun the read-only storage gate before resuming from `checkpoints/TRAIN-025/last.pt`. No development, test, or final evaluation was run. Final remains closed.


## TRAIN-026 resume preflight passed

RUN-592 supersedes the earlier RUN-591 storage snapshot. The training engine's disk check now reports 23.091 GiB free and 7,571,214,336 bytes above the frozen reserve plus checkpoint estimate. TRAIN-025 step-1800 report and checkpoint lineage passed, and TRAIN-026 paths are absent. Resume launch from `checkpoints/TRAIN-025/last.pt` is ready. Development, test, and final evaluations remain closed.


## TRAIN-026 exact resume active

RUN-592 superseded the earlier storage snapshot and passed the fresh preflight. RUN-593 records exact resume from TRAIN-025 step 1,800 to global step 3,600 with the frozen config. Training begins after this record is pushed. Development, test, and final evaluation remain closed during training.
