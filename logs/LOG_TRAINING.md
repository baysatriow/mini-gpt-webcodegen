# Log Training Mini GPT WebCodeGen

Catat setiap percobaan pretraining, penyelarasan instruksi, resume, atau evaluasi training. Run gagal, crash, OOM, dihentikan, atau hasil buruk tetap dicatat. Setiap resume mendapat TRAIN ID baru dan merujuk percobaan asal.

## Status awal

Status awal berikut adalah riwayat. [Pengembangan output AI-011](../reports/OUTPUT_DEVELOPMENT_2026-10-13.md): modelTRAIN-012 gagal final43/48exact; dua research demo Cakrawala diterima per output. TRAIN-013 weighted objective tidak meningkatkan ordinary validation. Ini bukan kesiapan produksi/general prompt.

- Profiling, smoke, dan baseline pretraining Mini GPT telah dijalankan; SFT produksi belum dijalankan.
- Model yang direncanakan mulai dari bobot acak, tanpa bobot model pralatih.
- VENV lokal: CPython 3.11.9, PyTorch 2.14.1+cu130, runtime CUDA 13.0, RTX 5070 sekitar 12 GB VRAM.
- Download 55.000 source selesai. Corpus pretraining 51.211 unik sudah displit, BPE train-only 8.192 dan token cache tersedia; SFT produksi menunggu anotasi reviewed.
- RUN-031 download; RUN-045 preparation final; RUN-046 integrity/GPU batch; RUN-047 reuse. Nomor RUN berikutnya mengikuti ID tertinggi di logs/RUN-*.txt.
- Review data: empat temuan diperbaiki. RUN-050 lulus 37 tests; RUN-051 memverifikasi dan mempertahankan tokenizer/cache; RUN-052 integrity/CUDA batch lulus. SFT wajib mengikuti family partition pretraining dan menunggu review produksi. Temuan/ruling ada pada reports/REVIEW_PIPELINE_2026-10-12.md serta logs/PIPELINE_PROGRESS.md.
- TRAIN-001 profiling, TRAIN-002 smoke, TRAIN-003 baseline hingga step 200, TRAIN-004 resume hingga step 1.200. Planning telah disetujui.
- Token train 19.038.770, vocabulary 8.192, blok data 1.024. Model 6 layer / 6 head / embedding 384 diprofilkan sebelum memilih batch 4 x accumulation 4; baseline memakai BF16, LR 0,0003, dan schedule 1.200 update. Blok data dapat diregenerasi jika konteks berubah.

## Indeks

| TRAIN ID | Tahap | Status | RUN IDs | Commit | Hasil |
| --- | --- | --- | --- | --- | --- |
| TRAIN-001 | GPU profiling, bobot dibuang | Selesai | RUN-056 | HEAD dasar b81cc61, working tree Task 6 | 14.186.496 parameter; batch 1/2/4 finite; batch 4 peak allocated 2.189.641.216 bytes |
| TRAIN-002 | Smoke pretraining BF16 | Selesai, 5 update | RUN-061 | HEAD dasar 24f9e5b, working tree Task 7 | Validation subset loss 9,1021 menjadi 8,7006; bukan baseline kualitas |
| TRAIN-003 | Baseline bagian awal | Berhenti terencana, step 200 | RUN-062 | 8113021 | Validation subset 9,1015 menjadi 2,2209; dilanjutkan TRAIN-004 |
| TRAIN-004 | Resume baseline | Selesai, step 1.200 | RUN-064, RUN-066, RUN-067 | 8113021 | Validation subset 1,1114; full test loss 1,0710 / perplexity 2,9183; probe JSON 0/4 |

## TRAIN-001: Profiling kandidat Mini GPT

- Model: random init, 6 layer / 6 head / embedding 384 / context 1024 / vocab 8192 / tied embeddings / dropout 0,1. Parameter terukur 14.186.496.
- Command: `python qa/profile_minigpt.py --run-id TRAIN-001`, output RUN-056 dan `outputs/metrics/TRAIN-001_profile.json` lokal.
- RTX 5070, PyTorch 2.14.1+cu130, BF16, seed 42, AdamW LR 0,0003, grad clip 1. Empat optimizer update per kandidat pada batch train pertama yang sama; satu warmup, tiga step timing. Bobot kandidat tidak menjadi checkpoint baseline.
- Batch 1: 0,0200 detik/step; allocated 761.374.208 bytes. Batch 2: 0,0272 detik/step; allocated 1.238.009.344 bytes. Batch 4: 0,0524 detik/step, 78.170,8 token/detik; allocated 2.189.641.216 / reserved 2.424.307.712 bytes.
- Semua loss/grad norm finite. Tidak ada OOM. Warning konversi loss Tensor ke scalar direkam; pencatatan berikutnya memakai detach. Angka ini profiling batch berulang, bukan throughput end-to-end baseline.
- Keputusan: microbatch 4 dengan accumulation 4 sebagai titik awal baseline, effective batch 16 blok / 16.384 token maksimum per update. Ukur lagi VRAM/throughput selama run aktual.
- Tidak ada validation/test, generation quality, atau PageSpec evaluation pada profiling ini. Profiling tidak membuktikan model sudah mempelajari dataset.

## TRAIN-002: Smoke training aktual

- Command: `python -m qa.train_minigpt --config configs/training_pretrain.json --run-id TRAIN-002 --max-steps 5 --smoke`.
- Tujuan: memeriksa loop CUDA, optimizer, validation, checkpoint last/best, dan output metrik pada subset kecil. Model tetap 14.186.496 parameter dari bobot acak, seed 42, BF16. Subset 32 train blocks / 8 validation blocks; microbatch 4, accumulation 1 pada smoke.
- Optimizer AdamW LR dasar 0,0003, warmup 60 dari config baseline; run 5 steps berhenti saat warmup. Loss train akhir 8,803996; validation awal 9,102139 dan akhir 8,700616. Semua finite; tidak ada OOM/NaN.
- Config, environment, hash lineage, global step, total token, waktu dan peak VRAM aktual: `reports/training/TRAIN-002.json`. Full config/checkpoint lokal: `checkpoints/TRAIN-002/`; metrics: `outputs/metrics/TRAIN-002.jsonl`; console: `logs/training/TRAIN-002.log`.
- Checkpoint last dan best dipilih lewat validation loss. Target labels dikonsumsi langsung tanpa shift kedua. Tidak ada SFT atau skor website.
- Pengujian engine RUN-060: 47 tests, termasuk loss masking, checksum sebelum load, resume CPU identik bitwise, draft SFT gate, serta failure artifact simulated OOM. Simulasi bukan OOM hardware yang benar-benar terjadi.

## TRAIN-003 dan TRAIN-004: Baseline dan resume aktual

- Command pertama: `python -m qa.train_minigpt --config configs/training_pretrain.json --run-id TRAIN-003 --stop-after 200`. Command resume: `python -m qa.train_minigpt --config configs/training_pretrain.json --run-id TRAIN-004 --resume checkpoints/TRAIN-003/last.pt`.
- Konfigurasi: 14.186.496 parameter, seed 42, BF16, batch 4 / accumulation 4, grad clip 1; AdamW betas 0,9/0,95, weight decay 0,1, LR 0,0003, warmup 60, cosine decay menuju 0,00003. Target 1.200 optimizer update; validation/checkpoint tiap100, 128 validation blocks dipilih seed59 dan dipakai tetap.
- TRAIN-003: wall 47,244 detik, 200 update. TRAIN-004: wall 227,017 detik untuk update201-1200. Total waktu proses 274,261 detik, tidak termasuk profiling/smoke/evaluasi. Stop pertama sengaja untuk memeriksa resume GPU; bukan crash.
- Validation sebelum/sesudah load checkpoint step200 sama persis: 2,220936931669712. Cursor sampler step200 800, lalu step210 840 dan step1200 4.800. Optimizer, scheduler, RNG, total token dan dataset cursor dipulihkan. Identik bitwise terhadap run tanpa jeda diuji pada CPU fixture; perbandingan bitwise penuh dua run GPU tidak dilakukan.
- Train loss akhir 0,933632; validation subset akhir/best 1,111391, perplexity 3,038581. Token valid kumulatif 19.657.265, sekitar 1,03 lintasan token train. Median throughput update 77.932,47 token/detik. Peak TRAIN-004 allocated 2.181.572.096 / reserved 2.357.198.848 bytes. Tidak ada OOM/NaN pada run aktual.
- Config/environment/hash/step/VRAM aktual ada di `reports/training/TRAIN-003.json` dan `reports/training/TRAIN-004.json`. Checkpoint last/best per run masing-masing 170.347.289 bytes, lokal di checkpoints/. Model best TRAIN-004 dipilih berdasarkan validation subset step1200, SHA-256 `9f407be207c9b9090104d48243109a2c333d9609cd89e7584dd8ccd5d5b50486`.
- Metrics setiap step berada di `outputs/metrics/TRAIN-003.jsonl` serta TRAIN-004.jsonl; console `logs/training/TRAIN-003.log` / TRAIN-004.log. RUN console dilacak Git. Grafik loss/LR: `reports/training/BASELINE_LOSS_2026-10-12.png`, 1.200 train updates / 13 validation points unik. Grafik telah diperiksa visual.

### Evaluasi baseline, RUN-066

- Command: `python -m qa.evaluate_minigpt --checkpoint checkpoints/TRAIN-004/best.pt --report-id TRAIN-004`.
- Test partition penuh, 507 batches / 2.074.051 token label valid: mean cross entropy 1,070987, perplexity 2,918259. Mean dihitung berdasarkan token valid; padding -100 dikecualikan. Test tidak dipakai memilih hyperparameter/checkpoint.
- Empat probe buatan Indonesia, mode exploratory_unreviewed, greedy temperature0/seed42, maksimal512 token: parseable JSON 0/4 dan schema valid 0/4. Tiga output berakhir EOS, satu mencapai token limit. Output menyerupai potongan HTML, belum PageSpec JSON. Semua raw output/error disimpan di `reports/training/TRAIN-004_evaluation.json` dan outputs/metrics/ lokal.
- Probe ini bukan benchmark SFT held-out, bukan hasil reviewed manusia, dan tidak dibuka di browser. Manual rubric tetap kosong. Tidak ada klaim layout/interaksi berhasil.
- Interpretasi: model belajar distribusi kode, tetapi belum dilatih mengikuti prompt-ke-PageSpec. Gerbang aplikasi needs-data; kurasi instruksi Indonesia dan SFT harus dilakukan sebelum membangun produk.

## Protokol pencatatan

Sebelum training, simpan config snapshot, ukur distribusi token, hitung parameter, cek ruang disk checkpoint, dan jalankan pemeriksaan bentuk data. Catat command meskipun gagal sebelum update pertama. Jangan melaporkan estimasi sebagai pengukuran.

Log console setiap proses disimpan di `logs/training/TRAIN-NNN.log`. Metrik machine-readable disimpan di `outputs/metrics/TRAIN-NNN.jsonl`, grafik loss di `outputs/metrics/TRAIN-NNN_loss.png`, dan checkpoint/config lokal di `checkpoints/TRAIN-NNN/`. Berkas besar tidak dilacak Git. Log utama mencatat command RUN dan AI ID terkait.

## Template percobaan

Salin template ini untuk setiap TRAIN ID.

### Identitas, tujuan, dan pelaksanaan

- **TRAIN ID dan status:** planned / running / selesai / gagal / dihentikan
- **Tahap:** pretraining / penyelarasan instruksi / resume / evaluasi
- **Tujuan dan hipotesis:**
- **Waktu mulai/selesai Asia/Jakarta dan durasi wall clock:**
- **RUN IDs terkait:**
- **AI IDs, chat share atau ekspor:**
- **Commit, branch, dan status working tree:**
- **Command lengkap dan direktori kerja:**
- **Pelaksana/reviewer dan pembagian anggota:**
- **Alasan stop dan langkah selanjutnya:**

### Lingkungan komputasi

- **Python executable dan versi:**
- **OS/build, versi driver, PyTorch, CUDA runtime:**
- **GPU, compute capability, VRAM total:**
- **CPU dan RAM host:**
- **Package terkait dan versi:**
- **Precision dan status BF16:**
- **Peak VRAM allocated/reserved yang benar-benar terukur:**
- **Seed Python/NumPy/PyTorch/CUDA dan deterministic flags:**
- **Perubahan environment sejak run sebelumnya:**

### Data dan provenance

- **Dataset URL, nama, revision, tanggal akses, license, attribution:**
- **Ketentuan disclosure rilis yang harus dipenuhi:**
- **Path raw/processed, hash file, hash manifest:**
- **Filter, normalisasi, konversi, dan alasan setiap kategori drop:**
- **Jumlah baris sebelum/sesudah kurasi per source, mode style, dan split:**
- **Prompt/target duplikat, near duplicate, group leakage:**
- **Bahasa prompt dan teks website:**
- **Jumlah token train/validation/test setelah tokenizer:**
- **Parser/schema/semantic rejection:**
- **Apakah screenshot atau binary ikut diambil:**

### Tokenizer dan model

- **Tokenizer, versi, vocab size, hash, special tokens:**
- **Aturan serialisasi prompt dan target JSON:**
- **Context length, padding, truncation, target mask:**
- **Layer, attention heads, dimensi embedding, FFN, positional encoding:**
- **Dropout, tie embedding, initialization, jumlah parameter:**
- **Model asal saat resume dan checkpoint parent:**
- **Path tokenizer/model config:**

### Konfigurasi optimizer dan training

- **Objective dan definisi loss:**
- **Epoch, max steps, validation/checkpoint interval:**
- **Batch per device, accumulation, effective batch, token per update:**
- **Optimizer, LR, weight decay, scheduler, warmup:**
- **Gradient clipping, mixed precision, scaler jika ada:**
- **Gradient checkpointing/compile:**
- **Config snapshot path/hash dan resume/RNG state:**

### Hasil training

- **Global step dan epoch tercapai:**
- **Train loss terakhir/terbaik:**
- **Validation loss terakhir/terbaik:**
- **Perplexity dan definisi token yang dihitung:**
- **LR saat run selesai:**
- **Tokens/sec, examples/sec, durasi step:**
- **Peak VRAM allocated/reserved:**
- **Gradient norm dan jumlah NaN/Inf/skipped step:**
- **Checkpoint last/best: path, ukuran, step, alasan pemilihan:**
- **Path log console, JSONL metric, grafik, config:**
- **Perubahan dari baseline dan interpretasi:**

### Evaluasi kualitas keluaran

- **Test set revision/hash dan bukti tidak dipakai saat tuning:**
- **Jumlah prompt dan prompt file:**
- **JSON parseable: jumlah dan persentase:**
- **Schema-valid: jumlah dan persentase:**
- **Style mode valid dan interaksi di katalog:**
- **Kesesuaian isi terhadap prompt, rubric dan reviewer:**
- **Browser, viewport, layout, aksesibilitas, interaksi yang diuji:**
- **Masalah/keluaran buruk:**
- **Path spesifikasi, render, screenshot, dan contoh terbaik:**

Token loss/perplexity tidak cukup untuk menyatakan halaman berguna. Catat validitas format, kesesuaian prompt, inspeksi visual, dan interaksi JavaScript secara terpisah. Jangan klaim halaman berhasil dirender bila belum dibuka di browser.

### Debugging dan keputusan tim

- **Pesan error lengkap:**
- **Prompt perbaikan ke LLM:**
- **Analisis akar masalah oleh kelompok:**
- **Solusi yang diterapkan, diubah, atau ditolak:**
- **Command dan hasil verifikasi:**
- **Pelajaran yang diambil:**
- **Keputusan eksperimen berikutnya:**

## Rencana pengelolaan checkpoint

Checkpoint resume menyertakan model, optimizer, scheduler, global step, config, tokenizer hash, RNG state, dan data manifest hash. Simpan `last` untuk melanjutkan training dan `best` berdasarkan metrik validation yang ditentukan sebelum run. Jangan memilih checkpoint berdasarkan test set. Setiap save/load/resume dicatat.

## AI-007: review, verified copy, dan notebook

Tidak ada TRAIN baru atau update produksi. Training aktual tetap TRAIN-001 sampai TRAIN-004.

- Review b81cc61..dd26110: 5 Important diperbaiki satu pass; 1 Minor deferred. Reviewer memeriksa 12 tests; implementer menjalankan suite penuh setelah fix.
- RUN-071 red: best step tidak sesuai loss, checksum rusak saat sidecar gagal, validator lineage belum ada. RUN-072 green 55 tests. RUN-074 red helper legacy binding; RUN-075 green 58 tests dengan ResourceWarning sebagai error.
- Format baru: immutable payload/manifest dan satu pointer commit. Best mencatat generation/step/loss/checksum. Last mempertahankan best historis, juga saat validation lebih sering daripada checkpoint save. Fault injection meliputi payload, manifest, commit, dan last save; bukan power-loss hardware.
- Lineage mencakup revision corpus, assignment family, checksum teks/token semua partition, tokenizer, reviewed manifest SFT, dan ancestry parent. Parent harus pretraining dengan update, bukan smoke. Evaluasi produksi memerlukan membership artifact test verified.
- RUN-076: verified copy baseline step 1.200, model tensors identik bitwise, optimizer updates 0. SHA sumber `9f407be207c9b9090104d48243109a2c333d9609cd89e7584dd8ccd5d5b50486`; SHA payload copy `49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c`.
- Fingerprint pretraining `fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a`. Hash copy berubah karena metadata; bobot tidak berubah. Free disk setelah migration 27.204.759.552 bytes, sekitar 25,34 GiB, di atas reserve 15 GiB.
- RUN-077: copy dievaluasi melalui gate baru, test loss 1,0709870979895217 / perplexity 2,9182586860057063 / 2.074.051 label / 507 batches, sama dengan RUN-066. Probe JSON/schema 0/4. Tidak ada tuning atau training baru.
- Notebook menyimpan output actual kernel proyek. RUN-070 berhenti pada syntax notebook 03; RUN-073 ketiganya lulus setelah koreksi. Default tidak melatih ulang; smoke harus diaktifkan eksplisit dan membuat RUN/TRAIN baru.
- Minor deferred: schema alternatif hanya dihash; validator memakai schema proyek. Config aktual cocok. Jangan mengklaim custom schema telah digunakan.
- Gerbang tetap needs-data: reviewed produksi 0 dari 119 draft. Review manusia, SFT, dan evaluasi PageSpec diperlukan sebelum aplikasi.

Rincian: [review](../reports/REVIEW_TRAINING_2026-10-12.md), [migration](../reports/training/TRAIN-004_lineage_migration.json), [evaluasi copy](../reports/training/TRAIN-004-VERIFIED_evaluation.json), [notebook](../notebooks/README.md).

- Verifikasi akhir AI-007: RUN-078 tiga notebook, 23 sel kode tanpa error; RUN-079 syntax/JSON/Markdown links/nbformat tanpa temuan; RUN-080 58/58 tests lulus. Tidak ada training produksi tambahan.

## AI-008: Persiapan anotasi sebelum SFT

Tahap data, **bukan TRAIN baru**. Jumlah update produksi dan checkpoint tetap baseline TRAIN-004/verified copy. Tidak ada optimizer update pada sesi ini.

- Parent yang disiapkan untuk SFT: `checkpoints/TRAIN-004-VERIFIED/best.pt`, step 1.200, dengan fingerprint corpus/tokenizer/partition yang sudah diverifikasi.
- Queue awal 119 draft/102 keluarga: 94 train, 11 validation, 14 test; semuanya hero sederhana, belum siap sebagai pasangan instruksi Indonesia.
- Pilot `data/annotations/pilot_drafts_id_v1.jsonl`: 12 draft/12 keluarga, 4 train, 4 validation, 4 test. Enam `plain_css`, enam `tailwind`. Dua contoh per kombinasi style/partition asal, tanpa reshuffle.
- Semua prompt/target pilot ditulis ulang dalam bahasa Indonesia oleh LLM, revision `llm-pilot-id-v1`. Reviewer dan persetujuan manusia kosong. Jangan menyebut ini data reviewed.
- Target mencakup contact_form, navbar, hero, feature_grid, text_section dan footer; interaksi form_validate dan menu_toggle berasal dari source JavaScript Vulcan.
- RUN-083 memverifikasi source text/provenance/family assignment, schema dan `encode_sft`: 12/12 lolos format, semua <=1.024 token, maksimum 640. Tidak memotong JSON atau melatih tokenizer ulang. Lolos format tidak berarti proyeksi semantik/tautan sudah disetujui.
- Tokenizer SHA tetap `f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7`; family assignment SHA `b827fdf80f0a20577a674a2ef4b70159da92a472e2535d5458c410c0398ab55b`.
- Paket review lokal memuat sumber, prompt, target, catatan perubahan, checklist kosong serta hash output. Gambar/CDN/script sumber tidak dijalankan.
- RUN-085 notebook 04 memeriksa mask prompt/target dan membuktikan loader menolak draft. Keempat notebook selesai 30 sel kode tanpa error. Tidak ada metrik SFT, generasi model baru atau hasil browser pada tahap ini.
- Keterbatasan: corpus kecil, belum semua section/interaksi, perubahan layout perlu penilaian manusia, empat kandidat memiliki isu kontrak/tujuan tautan. Review dan perluasan data diperlukan sebelum SFT.

Rincian: [panduan review](../docs/ANNOTATION_REVIEW_GUIDE.md), [laporan pilot](../reports/data/ANNOTATION_REVIEW_PILOT_ID_V1.json), [interaksi AI-008](interaksi_llm/AI-008_2026-10-12.md).

## AI-009: Revisi data dan coverage sebelum SFT

Tidak ada TRAIN baru atau optimizer update. Baseline TRAIN-004 dan parent `TRAIN-004-VERIFIED` tetap.

- RUN-087/088 menyiapkan pilot v2: 12 draft/12 keluarga, empat target dan lima prompt berubah. Partition 4 train/4 validation/4 test dan style 6/6 dipertahankan. Reviewed produksi 0, reviewer kosong.
- Schema/context valid 12/12, maksimum 612 token. Fragment tidak tersedia empat pada v1 menjadi nol pada v2. Audit ini memeriksa keberadaan section, bukan semantik label/browser.
- Tokenizer dan assignment hashes sama dengan v1. Corpus pretraining, token cache dan checkpoint tidak diubah.
- RUN-089 katalog dari train: 41.639 baris dibaca/38.666 HTML, 14 kandidat/14 keluarga tersimpan. Coverage heuristik menemukan bahan testimonial/pricing dan kandidat accordion/tabs, belum modal/filter. Kandidat tabs tidak memiliki fungsi openTab yang dipanggil source; belum layak dianggap interaksi bekerja. Accordion native memerlukan adaptasi yang ditinjau.
- RUN-090/091 memperbarui dan mengeksekusi notebook kurasi: empat notebook, 32 sel kode tanpa error. Status reviewed/production tetap nol; loader tetap menolak draft.
- Tidak ada hasil SFT/visual baru. Review manusia, corpus instruksi lebih luas dan accepted/rejected preparation diperlukan sebelum profiling/training SFT.

Rincian: [pilot v2](../reports/data/ANNOTATION_REVIEW_PILOT_ID_V2.json), [revisi](../reports/data/ANNOTATION_PILOT_REVISIONS_V2.json), [coverage kandidat](../reports/data/ANNOTATION_CANDIDATE_COVERAGE_V1.json), [AI-009](interaksi_llm/AI-009_2026-10-13.md).

## AI-010: Approval, preparation dan SFT pilot nyata

Persetujuan langsung pengguna "aprove lanjut" untuk seluruh 12 kandidat v2, bukan kandidat perluasan. RUN-093 memverifikasi checksum paket, membuat reviewed copy/path worksheet baru, tanpa menimpa draft asli. `reviewer=user_chat_approval`, revision `human-approved-pilot-v2-20261013`; nama pribadi/checklist individual tidak diberikan dan tidak direka. SHA reviewed JSONL `cc1d349231786be7a286ed8ed250405556781cc8d445f236d3bb4a05535dcb38`.

RUN-094 preparation: 12 accepted / 0 rejected / 0 duplicate, 12 family, 4/4/4. Tokenizer/cache/corpus dan assignment pretraining dipertahankan. BPE SHA `f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7`, assignment SHA `b827fdf80f0a20577a674a2ef4b70159da92a472e2535d5458c410c0398ab55b`. Source: WebSight CC-BY-4.0 dan Vulcan MIT, revision/atribusi ditahan pada data/lineage. Test tidak menjadi train.

Model dari random weights proyek: 14.186.496 parameter, 6 layer/6 head/embedding384/context1024/vocab8192/dropout0,1. Label sudah shifted next-token; prompt/padding -100, JSON/EOS aktif. Oversize ditolak utuh. VENV Python3.11.9/PyTorch2.14.1+cu130/CUDA13.0/RTX5070/BF16 live verified. Parent smoke dan pilot sama, pretrain step1200 `TRAIN-004-VERIFIED`; optimizer/schedule baru, bukan resume atau bobot pretrained eksternal.

Preflight HEAD `09dd290eb3aa08b98f4a75c60c300f64e1d528e3`. Config/evaluator pilot baru merupakan perubahan lokal belum committed saat run, seperti tercatat pada RUN. Setelah sesi ini config/code/results dilacak satu commit agar kondisi kerja reviewable. Source-config SHA dan expanded-config SHA berbeda karena trainer menambahkan model/lineage/override; keduanya direkam pada report.

### TRAIN-005: smoke SFT

- RUN: RUN-095; status **completed**, update 3; last_committed_step 3.
- Waktu aktual Asia/Jakarta: 2026-10-13T05:27:36.969360+07:00 sampai 2026-10-13T05:27:45.624715+07:00; wall 8.655439 detik. Timestamp UTC asli pada laporan; tanggal client sesi 13 Oktober 2026.
- Tujuan: memastikan batch target-mask/gradient/checkpoint berjalan pada GPU.
- Optimizer AdamW: seed 42, batch 2 x accumulation 1, LR 0.0001 ke 1e-05, cosine/warmup 4, betas [0.9, 0.95], weight decay 0.1, grad clip 1.0.
- Validation interval 1, validation batches 2, checkpoint interval 1, log interval 1; full validation empat contoh / 1.404 target labels / dua batch.
- Initial validation loss 7.511530427851, PPL 1829.010570663550; final validation loss 5.349697884671, PPL 210.544679482009; final train loss 5.380970453199.
- Valid target train tokens 2,034; microbatch accumulation smoke satu, hanya tiga update, bukan benchmark kemampuan.
- Peak GPU allocated 1,205,175,808 bytes (1.122407 GiB), reserved 1,325,400,064 bytes (1.234375 GiB). Tidak ada OOM/nonfinite pada run ini; hasil bukan jaminan semua config muat.
- Free disk setelah run 26,520,719,360 bytes (24.699345 GiB), reserve config 16,106,127,360 bytes.
- Parent `checkpoints/TRAIN-004-VERIFIED/best.pt`, SHA `49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c`. Kedua run independen dari parent sama; pilot tidak dimulai dari smoke.
- Source config SHA `fed5201907570e90bc23ef7f185d743e1e824921bd159c0a20bc348f3c1f8c8c`; expanded config SHA `981d9dd77a895aba84e4307003c381a674b2e9a3924fb96b6fc64a27b0a24821`.
- SFT train SHA `e909dbb3e89f3346d934d535c413d4cea305fe122835b00a8c368e9a6c81f67d`, validation SHA `4fbc318e136ff6eafc91d8002f69089125a76a8f5f96d551d10427aa6ec57b95`.
- Best validation step 3, loss 5.349697884671, payload SHA `5775435063dda891dcfaa68f2be2d96c4ef31aea665f8e11e53c1e6311f82117`; final/last payload SHA `82d2e387f0b36d29a414175544973def50082c176600ffedc3ed4546fbd6e21d`. Best dipilih validation, bukan test.
- Artifact lokal: `checkpoints/TRAIN-005/best.pt`, `last.pt`, `.versions/`, `outputs/metrics/TRAIN-005.jsonl`, `logs/training/TRAIN-005.log`; report tracked [report TRAIN-005](../reports/training/TRAIN-005.json). Error lengkap: tidak ada exception yang menggagalkan run; stdout tetap pada log RUN.

### TRAIN-006: SFT pilot reviewed

- RUN: RUN-096; status **completed**, update 40; last_committed_step 40.
- Waktu aktual Asia/Jakarta: 2026-10-13T05:28:24.765079+07:00 sampai 2026-10-13T05:28:36.481796+07:00; wall 11.717124 detik. Timestamp UTC asli pada laporan; tanggal client sesi 13 Oktober 2026.
- Tujuan: percobaan proses penyelarasan kecil dengan budget 40 update sebelum test.
- Optimizer AdamW: seed 42, batch 2 x accumulation 2, LR 0.0001 ke 1e-05, cosine/warmup 4, betas [0.9, 0.95], weight decay 0.1, grad clip 1.0.
- Validation interval 10, validation batches 2, checkpoint interval 10, log interval 5; full validation empat contoh / 1.404 target labels / dua batch.
- Initial validation loss 7.511530427851, PPL 1829.010570663550; final validation loss 3.739241901626, PPL 42.066087841179; final train loss 2.533279713012.
- Valid target train tokens 56,040; 1.401 target labels per update; empat contoh diulang 40 passes, sekitar 160 presentasi, bukan 160 contoh unik.
- Peak GPU allocated 1,266,312,704 bytes (1.179346 GiB), reserved 1,392,508,928 bytes (1.296875 GiB). Tidak ada OOM/nonfinite pada run ini; hasil bukan jaminan semua config muat.
- Free disk setelah run 25,839,218,688 bytes (24.064648 GiB), reserve config 16,106,127,360 bytes.
- Parent `checkpoints/TRAIN-004-VERIFIED/best.pt`, SHA `49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c`. Kedua run independen dari parent sama; pilot tidak dimulai dari smoke.
- Source config SHA `fed5201907570e90bc23ef7f185d743e1e824921bd159c0a20bc348f3c1f8c8c`; expanded config SHA `121c2fd14282faa3995820139384420db225735463685b179a1f4e327c3a07e8`.
- SFT train SHA `e909dbb3e89f3346d934d535c413d4cea305fe122835b00a8c368e9a6c81f67d`, validation SHA `4fbc318e136ff6eafc91d8002f69089125a76a8f5f96d551d10427aa6ec57b95`.
- Best validation step 40, loss 3.739241901626, payload SHA `74705520f6f6c543dc8d9908057769fdf81f478159efb44b6e3966ca847c5540`; final/last payload SHA `a2a76fb7b0f110778b08cdf54b9dce75c0398ed0a1abcc57bf5addadfcca326a`. Best dipilih validation, bukan test.
- Artifact lokal: `checkpoints/TRAIN-006/best.pt`, `last.pt`, `.versions/`, `outputs/metrics/TRAIN-006.jsonl`, `logs/training/TRAIN-006.log`; report tracked [report TRAIN-006](../reports/training/TRAIN-006.json). Error lengkap: tidak ada exception yang menggagalkan run; stdout tetap pada log RUN.

### RUN-097: Evaluasi held-out SFT pilot TRAIN-006

- Checkpoint best step40 berdasarkan validation, budget/schedule ditetapkan sebelum melihat test. `qa/evaluate_sft_pilot.py` menolak report overwrite, smoke checkpoint, prompt di luar artifact test reviewed dan schema selain proyek.
- Actual SFT test 4 contoh/4 family, batch2, labels1531, batches2. Loss **3.48825924385614**, perplexity **32.72892501203196**; target JSON masked loss, bukan pretraining corpus loss.
- Decoding greedy temperature0/max_new_tokens768/seed42/context1024, precisionBF16. Generation mode production adalah gate ancestry/membership, belum aplikasi siap.
- JSON parseable **0/4**, schema valid **0/4**, semua stop_reason token_limit dan generated_tokens768, tidak ada EOS. Parse error setiap contoh: `Expecting value: line 1 column 1 (char 0)`.
- Raw output tidak di-repair; tidak ada hasil render/browser/visual/manual acceptance. Cuplikan raw tersimpan pada notebook05; full local `outputs/metrics/TRAIN-006_sft_outputs.json`.
- Test SHA `8f469daab1a040b6c60b35ef1f64664b89ea38f9c9329acb0ae11014cb64c873`; evaluation config SHA `e2ecc362304bcd85e85693e6ba097089b0ccd0df9aa7aeb91830f8303351342b`.
- [Report test](../reports/training/TRAIN-006_sft_evaluation.json). Status evaluasi selesai meskipun kualitas generasi gagal. Tidak ada tuning/retry training dari hasil test.

### Analisis dan keputusan

Train hanya navbar/hero/text_section/contact_form dengan menu_toggle/form_validate. Feature_grid/footer/testimonial/pricing belum ada di train pilot; coverage gabungan tidak berarti train mencakup semuanya. Empat contoh dan pengulangan kuat membatasi kesimpulan. Penurunan teacher-forced loss belum menjamin generasi autoregresif valid. Tidak menyimpulkan satu penyebab kegagalan sudah dibuktikan.

Perlu perluasan train berdasarkan katalog proyek yang sudah ditetapkan dan review manusia, dengan partition keluarga tetap. Jangan menyalin target test ke train atau menyesuaikan parameter dari test. Setelah test pilot dibaca, reuse hanya eksploratif; evaluasi final membutuhkan holdout yang belum dipakai untuk pengembangan. Budget/data run berikutnya belum ditentukan. Gerbang aplikasi **needs-more-data-and-model-work**, software tahap akhir.

RUN-098 menulis notebook05/grafik/profil dari log aktual. RUN-099 lima notebook, 7+10+6+9+6=38 sel kode tanpa error. Source notebook01-04 sama; output snapshot historis dipulihkan sesudah rerun, status terbaru pada notebook05. Grafik diperiksa secara visual. Warning kernel Windows/TCP tetap tercatat; bukan error sel. Tidak menjalankan suite unit tambahan pada sesi ini.

[Ringkasan terbaru](../reports/SFT_PILOT_SUMMARY_2026-10-13.md), [ekspor interaksi AI-010](interaksi_llm/AI-010_2026-10-13.md).

RUN-100 mendokumentasikan hasil; RUN-101 syntax/format/link memeriksa 53 Python, 35 JSON, 42 Markdown dan lima notebook / 38 sel tanpa temuan. GitHub private dan ignore artifact lokal dikonfirmasi. Blank line tambahan pada akhir dua log diperbaiki sebelum commit; isi riwayat RUN tetap dipertahankan.

## AI-011: Diagnosis fit dan perluasan latihan

RUN-103 memeriksa train/validation dari TRAIN-006 saja. Prefix training/generation identik, target awal `{` belum dipilih konsisten. Selisih logits prefix/penuh maksimum 0,03125 pada BF16 dicatat; tidak ada dugaan mismatch format yang terbukti.

RUN-104 / **TRAIN-007**: config kandidat `training_sft.json` asli, 400 update dari parent TRAIN-004-VERIFIED yang sama, optimizer/schedule baru, seed 42, BF16, context 1.024, batch 2 x accumulation 4, warmup 20, LR 1e-4 ke 1e-5, betas 0,9/0,95, decay 0,1, clipping 1. Initial validation target loss 7,511530; best validation 3,547173 step 50; final validation 4,248309 / PPL 69,986935; final train loss 0,003838. Empat train diulang kuat, 1.120.800 target labels termasuk pengulangan.

RUN-105 memakai **last** step 400 untuk diagnosis hafalan, bukan memilih model final. Empat train JSON valid dengan EOS, teacher-forced token accuracy sempurna. Validation bukan target fit train; raw/metadata ada di [diagnostic](../reports/training/TRAIN-007-LAST-DEV_diagnostic.json). Tidak membaca ulang pilot test. Kesimpulan: mampu mempelajari format, corpus empat train membatasi transfer. Tidak mengklaim generalisasi.

Report [TRAIN-007](../reports/training/TRAIN-007.json) mencatat config/lineage/hashes/waktu/GPU/storage secara penuh; log command RUN-104, metrics/checkpoint lokal terpisah. Parent, corpus reviewed 4/4/4, tokenizer dan assignment sama dengan AI-010.

RUN-106 curriculum sintetis terpisah: 13.824 programmatic_contract, split 11.040 / 1.392 / 1.392, keluarga nama 230 / 29 / 29. Delapan section/enam interaction tercakup, maksimum 856 token, semua schema valid. Tidak mengubah review manusia atau corpus HF. Final 48 prompt dikunci sebelum training, kriteria schema >=95% / exact target >=90%, tanpa repair. Config 2.400 update dengan parent pretraining proyek; hasil berikutnya dicatat setelah eksekusi.

RUN-107 pemeriksaan source: 57 Python / 40 JSON / 44 Markdown / lima notebook / 38 sel, tanpa temuan format/syntax/link. Bukan hasil eksekusi training curriculum atau suite unit baru. [Interaksi AI-011](interaksi_llm/AI-011_2026-10-13.md).

### TRAIN-008: actual curriculum record

- Status **stopped_at_limit**, step 800, last_committed_step 800; resume parent None.
- Mulai 2026-10-13T08:24:14.337151+07:00, selesai 2026-10-13T08:25:52.229307+07:00, trainer wall 97.893404 detik. Tanggal client sesi 13 Oktober 2026.
- Data review kind: programmatic_contract, human_reviewed false; bukan reviewed production SFT. Corpus data/processed/curriculum/v1; jumlah train 11040, validation subset 128. Split/nested-template limitations pada manifest.
- Model proyek 14,186,496 parameter; {'vocab_size': 8192, 'block_size': 1024, 'n_layer': 6, 'n_head': 6, 'n_embd': 384, 'dropout': 0.1, 'tie_embeddings': True, 'initialization': 'random normal mean 0 std 0.02; no pretrained weights'}; BF16/CUDA. Environment aktual {'python': '3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]', 'executable': 'F:\\Generative_AI\\Vibe_Coding_Proyek_1\\.venv\\Scripts\\python.exe', 'torch': '2.14.1+cu130', 'cuda': '13.0', 'gpu': 'NVIDIA GeForce RTX 5070', 'platform': 'Windows-10-10.0.26200-SP0'}.
- Batch 4 x accumulation 2; seed 42; budget 2400; warmup 120; LR 0.0003 ke 3e-05; AdamW betas [0.9, 0.95], decay 0.1, clipping 1.0. Validation/checkpoint setiap 200/200; validation_batches 32.
- Initial validation {'loss': 7.61002983327008, 'perplexity': 2018.3383104505665, 'valid_tokens': 54345, 'batches': 32}; final validation {'loss': 0.012233271885295506, 'perplexity': 1.0123084044154458, 'valid_tokens': 54345, 'batches': 32}; final train loss 0.013945644965165755; best validation loss 0.012233271885295506, step 800.
- Total target train labels 2,703,845, termasuk pengulangan dan **kumulatif saat resume**. Jangan menjumlahkan total parent+child. Prompt/padding -100, JSON/EOS aktif, label next-token sudah digeser.
- Peak allocated 2,176,525,824 bytes (2.027048 GiB), reserved 2,367,684,608 (2.205078 GiB). Free disk 24,452,829,184 bytes (22.773472 GiB), reserve 16,106,127,360 bytes. Tidak ada OOM/nonfinite pada status sukses run ini.
- Parent project-pretrain SHA `49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c`, recorded pretrain step 1200. Resume SHA `None`. New optimizer hanya saat initialize, resume memulihkan optimizer/scheduler/RNG/cursor.
- Tokenizer SHA `f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7`; pretrain fingerprint `fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a`; synthetic manifest SHA `f84ca6307e0c89f36c76006739bb41e38701c654051041854d5314a2ba8825db`; source config SHA `1552872afc504fdfa196317afd017204bae184ab5517c9e4822a4b8c110a9bfb`; expanded config SHA `b8eb487ea5d268e4b20218ba88685b771aa390310e80390a2618762ec89f2009`.
- Data SHA {'train': 'd7fe1365ab927c75e879aa7fe31a8522e447625055ed79afd1411c0b0ea1b5c4', 'validation': '3677bc1956cb404f8b7ad3eff20d4fd0e9108cc41afe4f0f30285876c52b117c'}; validation indices SHA `56286c1c502a98de233b6f1605299b750c9455901ce781cf5ac9ae7935c51ffd`.
- Best payload SHA `959a5b5a5344714123896bd57c810f3d9ad63f0b7f3223a7bc1c68b61ec8c17f`; final/last SHA `2995101e0f981a5b796f28aa5c800b5821a62559fa4798e9fc4bc97b1845b7cc`. Best berdasarkan validation saja, bukan train atau final test.
- Run Git HEAD `5209976e73450c39e2b3101521a5b793e3021749`; kondisi source/config lokal bila belum committed dijelaskan pada AI-011. Report lengkap [report TRAIN-008](../reports/training/TRAIN-008.json); local `outputs/metrics/TRAIN-008.jsonl`, `logs/training/TRAIN-008.log`, `checkpoints/TRAIN-008/`.

### TRAIN-009: actual curriculum record

- Status **completed**, step 2400, last_committed_step 2400; resume parent checkpoints\TRAIN-008\last.pt.
- Mulai 2026-10-13T08:27:37.070341+07:00, selesai 2026-10-13T08:30:50.352650+07:00, trainer wall 193.285490 detik. Tanggal client sesi 13 Oktober 2026.
- Data review kind: programmatic_contract, human_reviewed false; bukan reviewed production SFT. Corpus data/processed/curriculum/v1; jumlah train 11040, validation subset 128. Split/nested-template limitations pada manifest.
- Model proyek 14,186,496 parameter; {'vocab_size': 8192, 'block_size': 1024, 'n_layer': 6, 'n_head': 6, 'n_embd': 384, 'dropout': 0.1, 'tie_embeddings': True, 'initialization': 'random normal mean 0 std 0.02; no pretrained weights'}; BF16/CUDA. Environment aktual {'python': '3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]', 'executable': 'F:\\Generative_AI\\Vibe_Coding_Proyek_1\\.venv\\Scripts\\python.exe', 'torch': '2.14.1+cu130', 'cuda': '13.0', 'gpu': 'NVIDIA GeForce RTX 5070', 'platform': 'Windows-10-10.0.26200-SP0'}.
- Batch 4 x accumulation 2; seed 42; budget 2400; warmup 120; LR 0.0003 ke 3e-05; AdamW betas [0.9, 0.95], decay 0.1, clipping 1.0. Validation/checkpoint setiap 200/200; validation_batches 32.
- Initial validation {'loss': 0.012233271885295506, 'perplexity': 1.0123084044154458, 'valid_tokens': 54345, 'batches': 32}; final validation {'loss': 0.006715163022858292, 'perplexity': 1.006737760283181, 'valid_tokens': 54345, 'batches': 32}; final train loss 0.006660966859082176; best validation loss 0.006715163022858292, step 2400.
- Total target train labels 8,098,973, termasuk pengulangan dan **kumulatif saat resume**. Jangan menjumlahkan total parent+child. Prompt/padding -100, JSON/EOS aktif, label next-token sudah digeser.
- Peak allocated 2,181,572,096 bytes (2.031747 GiB), reserved 2,342,518,784 (2.181641 GiB). Free disk 23,769,993,216 bytes (22.137531 GiB), reserve 16,106,127,360 bytes. Tidak ada OOM/nonfinite pada status sukses run ini.
- Parent project-pretrain SHA `49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c`, recorded pretrain step 1200. Resume SHA `2995101e0f981a5b796f28aa5c800b5821a62559fa4798e9fc4bc97b1845b7cc`. New optimizer hanya saat initialize, resume memulihkan optimizer/scheduler/RNG/cursor.
- Tokenizer SHA `f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7`; pretrain fingerprint `fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a`; synthetic manifest SHA `f84ca6307e0c89f36c76006739bb41e38701c654051041854d5314a2ba8825db`; source config SHA `1552872afc504fdfa196317afd017204bae184ab5517c9e4822a4b8c110a9bfb`; expanded config SHA `b8eb487ea5d268e4b20218ba88685b771aa390310e80390a2618762ec89f2009`.
- Data SHA {'train': 'd7fe1365ab927c75e879aa7fe31a8522e447625055ed79afd1411c0b0ea1b5c4', 'validation': '3677bc1956cb404f8b7ad3eff20d4fd0e9108cc41afe4f0f30285876c52b117c'}; validation indices SHA `56286c1c502a98de233b6f1605299b750c9455901ce781cf5ac9ae7935c51ffd`.
- Best payload SHA `cfff2bc2d3a8d71a9d0c00c81248d66da018b9148a9a7a468add1777ff63114a`; final/last SHA `3bb559d3d1cc777028a7268c74c492c8ea03f15ce7e70227f736fdc959198e8c`. Best berdasarkan validation saja, bukan train atau final test.
- Run Git HEAD `5209976e73450c39e2b3101521a5b793e3021749`; kondisi source/config lokal bila belum committed dijelaskan pada AI-011. Report lengkap [report TRAIN-009](../reports/training/TRAIN-009.json); local `outputs/metrics/TRAIN-009.jsonl`, `logs/training/TRAIN-009.log`, `checkpoints/TRAIN-009/`.

### TRAIN-010: actual curriculum record

- Status **completed**, step 2400, last_committed_step 2400; resume parent None.
- Mulai 2026-10-13T08:35:27.425902+07:00, selesai 2026-10-13T08:40:14.485099+07:00, trainer wall 287.063823 detik. Tanggal client sesi 13 Oktober 2026.
- Data review kind: programmatic_contract, human_reviewed false; bukan reviewed production SFT. Corpus data/processed/curriculum/v2; jumlah train 11040, validation subset 128. Split/nested-template limitations pada manifest.
- Model proyek 14,186,496 parameter; {'vocab_size': 8192, 'block_size': 1024, 'n_layer': 6, 'n_head': 6, 'n_embd': 384, 'dropout': 0.1, 'tie_embeddings': True, 'initialization': 'random normal mean 0 std 0.02; no pretrained weights'}; BF16/CUDA. Environment aktual {'python': '3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]', 'executable': 'F:\\Generative_AI\\Vibe_Coding_Proyek_1\\.venv\\Scripts\\python.exe', 'torch': '2.14.1+cu130', 'cuda': '13.0', 'gpu': 'NVIDIA GeForce RTX 5070', 'platform': 'Windows-10-10.0.26200-SP0'}.
- Batch 4 x accumulation 2; seed 42; budget 2400; warmup 120; LR 0.0003 ke 3e-05; AdamW betas [0.9, 0.95], decay 0.1, clipping 1.0. Validation/checkpoint setiap 200/200; validation_batches 32.
- Initial validation {'loss': 7.595766971288757, 'perplexity': 1989.7553516443652, 'valid_tokens': 54345, 'batches': 32}; final validation {'loss': 1.6208545980298625e-05, 'perplexity': 1.0000162086773394, 'valid_tokens': 54345, 'batches': 32}; final train loss 0.00012622822070579585; best validation loss 1.6208545980298625e-05, step 2400.
- Total target train labels 8,098,973, termasuk pengulangan dan **kumulatif saat resume**. Jangan menjumlahkan total parent+child. Prompt/padding -100, JSON/EOS aktif, label next-token sudah digeser.
- Peak allocated 2,176,525,824 bytes (2.027048 GiB), reserved 2,367,684,608 (2.205078 GiB). Free disk 22,952,054,784 bytes (21.375767 GiB), reserve 16,106,127,360 bytes. Tidak ada OOM/nonfinite pada status sukses run ini.
- Parent project-pretrain SHA `49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c`, recorded pretrain step 1200. Resume SHA `None`. New optimizer hanya saat initialize, resume memulihkan optimizer/scheduler/RNG/cursor.
- Tokenizer SHA `f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7`; pretrain fingerprint `fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a`; synthetic manifest SHA `bfb4c2cbf1a8f353dec379ede7a7c4eb39c3414b32183e29f6eb6b0602418aa2`; source config SHA `ea645d8b6f9a1bb444fdb7f7729b55f40b6c48f6d13a8df1587ddb7303942a79`; expanded config SHA `06f6c64c52f526424d583e263d6b69a81c2b89886bea91658d1836cc7abc6c21`.
- Data SHA {'train': 'd7fe1365ab927c75e879aa7fe31a8522e447625055ed79afd1411c0b0ea1b5c4', 'validation': '3677bc1956cb404f8b7ad3eff20d4fd0e9108cc41afe4f0f30285876c52b117c'}; validation indices SHA `56286c1c502a98de233b6f1605299b750c9455901ce781cf5ac9ae7935c51ffd`.
- Best payload SHA `fc082d0cfece6e4227a4b9f2b4cba0a006af1e5f4d18891b72676ffd72c5faf7`; final/last SHA `13986f0344fa58367e405c3ad69053f17a36e23f9b70a2855f317ac3a90a3c5c`. Best berdasarkan validation saja, bukan train atau final test.
- Run Git HEAD `5209976e73450c39e2b3101521a5b793e3021749`; kondisi source/config lokal bila belum committed dijelaskan pada AI-011. Report lengkap [report TRAIN-010](../reports/training/TRAIN-010.json); local `outputs/metrics/TRAIN-010.jsonl`, `logs/training/TRAIN-010.log`, `checkpoints/TRAIN-010/`.

### TRAIN-011: actual curriculum record

- Status **completed**, step 4800, last_committed_step 4800; resume parent None.
- Mulai 2026-10-13T09:05:02.455070+07:00, selesai 2026-10-13T09:14:09.291953+07:00, trainer wall 546.842718 detik. Tanggal client sesi 13 Oktober 2026.
- Data review kind: programmatic_contract, human_reviewed false; bukan reviewed production SFT. Corpus data/processed/curriculum/v3; jumlah train 11520, validation subset 128. Split/nested-template limitations pada manifest.
- Model proyek 14,186,496 parameter; {'vocab_size': 8192, 'block_size': 1024, 'n_layer': 6, 'n_head': 6, 'n_embd': 384, 'dropout': 0.1, 'tie_embeddings': True, 'initialization': 'random normal mean 0 std 0.02; no pretrained weights'}; BF16/CUDA. Environment aktual {'python': '3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]', 'executable': 'F:\\Generative_AI\\Vibe_Coding_Proyek_1\\.venv\\Scripts\\python.exe', 'torch': '2.14.1+cu130', 'cuda': '13.0', 'gpu': 'NVIDIA GeForce RTX 5070', 'platform': 'Windows-10-10.0.26200-SP0'}.
- Batch 4 x accumulation 2; seed 42; budget 4800; warmup 240; LR 0.0003 ke 3e-05; AdamW betas [0.9, 0.95], decay 0.1, clipping 1.0. Validation/checkpoint setiap 400/400; validation_batches 32.
- Initial validation {'loss': 7.5773243363358525, 'perplexity': 1953.3953378696876, 'valid_tokens': 56973, 'batches': 32}; final validation {'loss': 0.006050640093847748, 'perplexity': 1.006068982191771, 'valid_tokens': 56973, 'batches': 32}; final train loss 0.00017382848282911206; best validation loss 0.006050640093847748, step 4800.
- Total target train labels 16,745,351, termasuk pengulangan dan **kumulatif saat resume**. Jangan menjumlahkan total parent+child. Prompt/padding -100, JSON/EOS aktif, label next-token sudah digeser.
- Peak allocated 2,176,525,824 bytes (2.027048 GiB), reserved 2,367,684,608 (2.205078 GiB). Free disk 22,102,052,864 bytes (20.584141 GiB), reserve 16,106,127,360 bytes. Tidak ada OOM/nonfinite pada status sukses run ini.
- Parent project-pretrain SHA `49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c`, recorded pretrain step 1200. Resume SHA `None`. New optimizer hanya saat initialize, resume memulihkan optimizer/scheduler/RNG/cursor.
- Tokenizer SHA `f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7`; pretrain fingerprint `fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a`; synthetic manifest SHA `f1086c3c0522fefe789cd8a254e69f7d085080959f4895dd5bfb96f9f7ba2166`; source config SHA `c92ba46c7d638293d7c8895e5a40e56681f05073ee8e5970178d1960dec4fd31`; expanded config SHA `8ff19d13fa1f0687b8c5f97f6e4193bd0b58cff46bd6a6c1aa1fc823b340f8ed`.
- Data SHA {'train': '4edc5ff2687c37625280d44c6cbc12c62ba5763a23d7f6448cff95a1b75498a4', 'validation': '945bde9e48d4e4e274a63e519d13357b201e1c1fa9835af427cb0758031d2800'}; validation indices SHA `b379ba2b400a1419faaa24e292abc375a7315a7fb406e491dc35081e3063c980`.
- Best payload SHA `7f4eb2c39bd8c55697663a3c7bb854312e7f242030499397b9a3ac00d44d1e15`; final/last SHA `257be5fa1e0dc349b90de64b005464655c2dc8a4331de18a407f0fc16d429a34`. Best berdasarkan validation saja, bukan train atau final test.
- Run Git HEAD `5209976e73450c39e2b3101521a5b793e3021749`; kondisi source/config lokal bila belum committed dijelaskan pada AI-011. Report lengkap [report TRAIN-011](../reports/training/TRAIN-011.json); local `outputs/metrics/TRAIN-011.jsonl`, `logs/training/TRAIN-011.log`, `checkpoints/TRAIN-011/`.

### TRAIN-012: actual curriculum record

- Status **completed**, step 4800, last_committed_step 4800; resume parent None.
- Mulai 2026-10-13T09:22:37.370706+07:00, selesai 2026-10-13T09:31:42.379336+07:00, trainer wall 545.015247 detik. Tanggal client sesi 13 Oktober 2026.
- Data review kind: programmatic_contract, human_reviewed false; bukan reviewed production SFT. Corpus data/processed/curriculum/v4; jumlah train 19068, validation subset 128. Split/nested-template limitations pada manifest.
- Model proyek 14,186,496 parameter; {'vocab_size': 8192, 'block_size': 1024, 'n_layer': 6, 'n_head': 6, 'n_embd': 384, 'dropout': 0.1, 'tie_embeddings': True, 'initialization': 'random normal mean 0 std 0.02; no pretrained weights'}; BF16/CUDA. Environment aktual {'python': '3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]', 'executable': 'F:\\Generative_AI\\Vibe_Coding_Proyek_1\\.venv\\Scripts\\python.exe', 'torch': '2.14.1+cu130', 'cuda': '13.0', 'gpu': 'NVIDIA GeForce RTX 5070', 'platform': 'Windows-10-10.0.26200-SP0'}.
- Batch 4 x accumulation 2; seed 42; budget 4800; warmup 120; LR 0.0001 ke 1e-05; AdamW betas [0.9, 0.95], decay 0.1, clipping 1.0. Validation/checkpoint setiap 400/400; validation_batches 32.
- Initial validation {'loss': 0.006050640093847748, 'perplexity': 1.006068982191771, 'valid_tokens': 56973, 'batches': 32}; final validation {'loss': 0.005902343875809186, 'perplexity': 1.005919797028697, 'valid_tokens': 56973, 'batches': 32}; final train loss 0.02376972221466432; best validation loss 0.005362110107760764, step 3600.
- Total target train labels 14,392,192, termasuk pengulangan dan **kumulatif saat resume**. Jangan menjumlahkan total parent+child. Prompt/padding -100, JSON/EOS aktif, label next-token sudah digeser.
- Peak allocated 2,176,525,824 bytes (2.027048 GiB), reserved 2,367,684,608 (2.205078 GiB). Free disk 21,210,828,800 bytes (19.754124 GiB), reserve 16,106,127,360 bytes. Tidak ada OOM/nonfinite pada status sukses run ini.
- Initial weights SHA `7f4eb2c39bd8c55697663a3c7bb854312e7f242030499397b9a3ac00d44d1e15`, project-pretrain ancestor SHA `49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c`, recorded pretrain step 1200. Curriculum parent {'checkpoint_sha256': '7f4eb2c39bd8c55697663a3c7bb854312e7f242030499397b9a3ac00d44d1e15', 'global_step': 4800, 'synthetic_manifest_sha256': 'f1086c3c0522fefe789cd8a254e69f7d085080959f4895dd5bfb96f9f7ba2166', 'run_id': 'TRAIN-011'}. Resume SHA `None`. New optimizer saat initialize/continuation, resume memulihkan optimizer/scheduler/RNG/cursor. Continuation tahap baru mereset update counter tetapi mempertahankan ancestry, bukan resume optimizer lama.
- Tokenizer SHA `f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7`; pretrain fingerprint `fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a`; synthetic manifest SHA `4875ed584633d9ee59d121e7b9d89e277fe37ec5f249cf4e1b3f189c81fd4673`; source config SHA `28bce4aca9297dffe3f2243b4031808a3c5466966089209e989a033d71aedfb1`; expanded config SHA `1a14a78cb814c772264e9250b75891a2343a2d14e64c7c550962259f8b5ab69e`.
- Data SHA {'train': '418dc7e18c4bf932ea8d89a3b5b2771eec440f5ec68186337ec6f90f32374538', 'validation': '945bde9e48d4e4e274a63e519d13357b201e1c1fa9835af427cb0758031d2800'}; validation indices SHA `b379ba2b400a1419faaa24e292abc375a7315a7fb406e491dc35081e3063c980`.
- Best payload SHA `791a365463710f73dbfbba767bd8bd17f5b4442e8f6137a92ec8c5888d1a2ed3`; final/last SHA `81405fa346420381b76d7b195c1cc4881346f4ea622a3bac7584e9dc55e1651d`. Best berdasarkan validation saja, bukan train atau final test.
- Run Git HEAD `5209976e73450c39e2b3101521a5b793e3021749`; kondisi source/config lokal bila belum committed dijelaskan pada AI-011. Report lengkap [report TRAIN-012](../reports/training/TRAIN-012.json); local `outputs/metrics/TRAIN-012.jsonl`, `logs/training/TRAIN-012.log`, `checkpoints/TRAIN-012/`.

### TRAIN-013: actual curriculum record

- Status **completed**, step 3600, last_committed_step 3600; resume parent None.
- Mulai 2026-10-13T09:45:00.782979+07:00, selesai 2026-10-13T09:52:14.998374+07:00, trainer wall 434.220064 detik. Tanggal client sesi 13 Oktober 2026.
- Data review kind: programmatic_contract, human_reviewed false; bukan reviewed production SFT. Corpus data/processed/curriculum/v5; jumlah train 19068, validation subset 1440. Split/nested-template limitations pada manifest.
- Model proyek 14,186,496 parameter; {'vocab_size': 8192, 'block_size': 1024, 'n_layer': 6, 'n_head': 6, 'n_embd': 384, 'dropout': 0.1, 'tie_embeddings': True, 'initialization': 'random normal mean 0 std 0.02; no pretrained weights'}; BF16/CUDA. Environment aktual {'python': '3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]', 'executable': 'F:\\Generative_AI\\Vibe_Coding_Proyek_1\\.venv\\Scripts\\python.exe', 'torch': '2.14.1+cu130', 'cuda': '13.0', 'gpu': 'NVIDIA GeForce RTX 5070', 'platform': 'Windows-10-10.0.26200-SP0'}.
- Batch 4 x accumulation 2; seed 42; budget 3600; warmup 90; LR 0.0001 ke 1e-05; AdamW betas [0.9, 0.95], decay 0.1, clipping 1.0. Validation/checkpoint setiap 600/600; validation_batches 360.
- Initial validation {'loss': 0.005658693556845027, 'perplexity': 1.0056747342053285, 'valid_tokens': 623706, 'batches': 360}; final validation {'loss': 0.007606502481371312, 'perplexity': 1.007635505411688, 'valid_tokens': 623706, 'batches': 360}; final train loss 0.3668931201967368; best validation loss 0.005658693556845027, step 0.
- Total target train labels 10,781,936, termasuk pengulangan dan **kumulatif saat resume**. Jangan menjumlahkan total parent+child. Prompt/padding -100, JSON/EOS aktif, label next-token sudah digeser.
- Peak allocated 2,247,337,472 bytes (2.092996 GiB), reserved 2,501,902,336 (2.330078 GiB). Free disk 20,558,270,464 bytes (19.146381 GiB), reserve 16,106,127,360 bytes. Tidak ada OOM/nonfinite pada status sukses run ini.
- Initial weights SHA `791a365463710f73dbfbba767bd8bd17f5b4442e8f6137a92ec8c5888d1a2ed3`, project-pretrain ancestor SHA `49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c`, recorded pretrain step 1200. Curriculum parent {'checkpoint_sha256': '791a365463710f73dbfbba767bd8bd17f5b4442e8f6137a92ec8c5888d1a2ed3', 'global_step': 3600, 'synthetic_manifest_sha256': '4875ed584633d9ee59d121e7b9d89e277fe37ec5f249cf4e1b3f189c81fd4673', 'run_id': 'TRAIN-012'}. Resume SHA `None`. New optimizer saat initialize/continuation, resume memulihkan optimizer/scheduler/RNG/cursor. Continuation tahap baru mereset update counter tetapi mempertahankan ancestry, bukan resume optimizer lama.
- Tokenizer SHA `f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7`; pretrain fingerprint `fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a`; synthetic manifest SHA `cb0537774dd785111329fc79a083a8ddbd3150ae60b5f40e57a0f6ce8e936394`; source config SHA `56d5816bd061274b256beb8263cdb4282c80a0d46e89d4c107c5759a48df000f`; expanded config SHA `42ff1ab6e918fc81decb4013464b4cb588cc800b9e3338e8797a3583df592b9e`.
- Data SHA {'train': '418dc7e18c4bf932ea8d89a3b5b2771eec440f5ec68186337ec6f90f32374538', 'validation': '945bde9e48d4e4e274a63e519d13357b201e1c1fa9835af427cb0758031d2800'}; validation indices SHA `9bc32cb1719357ec7de7e859d9c67f3f0bdb69cb6deca4043f46d59d6b552c07`.
- Best payload SHA `e44030d363afcc0c70b305ead82ba8bf1510ef53761e913e79b2697a4d81d28a`; final/last SHA `fb4330b37f5198700d7d4ead95f7df264b02242dc3d82089e6a3dbfbaa338aac`. Best berdasarkan validation saja, bukan train atau final test.
- Run Git HEAD `0b2de4a6377a87069f2a684253554715217a5187`; kondisi source/config lokal bila belum committed dijelaskan pada AI-011. Report lengkap [report TRAIN-013](../reports/training/TRAIN-013.json); local `outputs/metrics/TRAIN-013.jsonl`, `logs/training/TRAIN-013.log`, `checkpoints/TRAIN-013/`.

### TRAIN-014: GPU optimized training actual record

- Permintaan pengguna AI-012: maksimalkan performa GPU untuk training. Batch dipilih dari empat sweep aktual, bukan asumsi VRAM besar. [Laporan GPU](../reports/GPU_TRAINING_OPTIMIZATION_2026-10-13.md).
- Status completed, step 800, last committed 800; mulai 2026-10-13T10:31:03.997817+07:00, selesai 2026-10-13T10:33:46.253395+07:00, wall 162.257257detik. Tidak ada exception/OOM/nonfinite pada run ini.
- Environment aktual {'python': '3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]', 'executable': 'F:\\Generative_AI\\Vibe_Coding_Proyek_1\\.venv\\Scripts\\python.exe', 'torch': '2.14.1+cu130', 'cuda': '13.0', 'gpu': 'NVIDIA GeForce RTX 5070', 'platform': 'Windows-10-10.0.26200-SP0'}. Model 14,186,496parameter dengan config {'vocab_size': 8192, 'block_size': 1024, 'n_layer': 6, 'n_head': 6, 'n_embd': 384, 'dropout': 0.1, 'tie_embeddings': True, 'initialization': 'random normal mean 0 std 0.02; no pretrained weights'}. Tidak ada pretrained LLM eksternal atau perubahan arsitektur.
- Data data/processed/curriculum/v5, origin synthetic_curriculum, human_reviewed False; train 19068rows, fullvalidation 1440rows. Train/validation sama dengan v4; finalv5 belum dibuka. Synthetic recipe sharing tetap menjadi keterbatasan.
- Batch 48 x accumulation 1, seed 42, BF16, budget 800, warmup 40, LR 2e-05ke2e-06, AdamWbetas[0.9, 0.95], decay0.1, clip1.0. Validation/checkpoint tiap 160/160; validation_batches30.
- Runtime performance {'attention_backend': 'sdpa', 'fused_adamw': True, 'pin_memory': True, 'tf32': True, 'supervised_only_logits': True, 'allocator_config': 'expandable_segments:True', 'gpu_telemetry': True, 'selected_by': 'reports/training/GPU-PERF-004.json'}. Allocator process expandable_segments:True. SDPA actual profiler mencatat CUTLASS memory-efficient attention, bukan klaim FlashAttention. Tidak melakukan overclock/power-limit/driver changes. Model forward fullcontext tetap; lm_head/CE training hanya active labels, prompt/pad-100, JSON/EOSaktif, labels already shifted. Objective ordinary CE, tanpa name16x.
- Initial validation {'loss': 0.005657631831054099, 'perplexity': 1.0056736664550927, 'valid_tokens': 623706, 'batches': 30}; final validation {'loss': 0.0057741252896185225, 'perplexity': 1.0057908276828111, 'valid_tokens': 623706, 'batches': 30}; best loss 0.005657631831054099step0, final train loss 0.03567990046656613. Validation backend SDPA; evaluator development defaultmanual terpisah. Beda numerik runtime dicatat.
- 14,365,682 supervised target labels termasuk pengulangan. Setelah lima update awal dikeluarkan, 795update, 143.921213detik update, throughput 99199.671targettokens/sec, sekitar3.4322x baseline probe. Bukan equal-budget quality comparison atau wall speedup seluruh pipeline.
- Active-update telemetry {'sample_count': 256, 'utilization_pct': {'mean': 93.23046875, 'max': 100.0, 'min': 1.0}, 'memory_used_mib': {'mean': 8669.87109375, 'max': 8691.0, 'min': 8421.0}, 'power_w': {'mean': 194.998828125, 'max': 201.96, 'min': 114.99}, 'temperature_c': {'mean': 61.36328125, 'max': 67.0, 'min': 52.0}, 'sm_clock_mhz': {'mean': 2922.8984375, 'max': 2940.0, 'min': 2917.0}}. Classification query timestamp terhadap intervalupdate; persentase sampling nvidia-smi bisa mencakup lag/window aktivitas. All-phase telemetry termasuk validation/checkpoint/startup ada pada report. Maximum100% tidak berarti selalu100%.
- Peak allocated 7,037,730,304bytes/6.5544GiB, reserved 7,163,871,232/6.6719GiB. Memori nvidia-smi termasuk desktop/proses lain dan tidak identik dengan allocated/reserved. Free disk 20,155,940,864bytes/18.7717GiB, reserve 16,106,127,360bytes.
- Initial parent SHA `791a365463710f73dbfbba767bd8bd17f5b4442e8f6137a92ec8c5888d1a2ed3`, curriculum parent {'checkpoint_sha256': '791a365463710f73dbfbba767bd8bd17f5b4442e8f6137a92ec8c5888d1a2ed3', 'global_step': 3600, 'synthetic_manifest_sha256': '4875ed584633d9ee59d121e7b9d89e277fe37ec5f249cf4e1b3f189c81fd4673', 'run_id': 'TRAIN-012'}, original pretraining parent {'checkpoint_sha256': '49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c', 'phase': 'pretrain', 'global_step': 1200, 'pretrain_fingerprint': {'version': 1, 'tokenizer_sha256': 'f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7', 'assignment_sha256': 'b827fdf80f0a20577a674a2ef4b70159da92a472e2535d5458c410c0398ab55b', 'source_revisions': [{'id': 'vulcan', 'revision': '19d2a482c78554e59feca0ce2b50fb7835e90c6f', 'license': 'mit', 'rows': 5000}, {'id': 'websight_v01', 'revision': 'b11f8172f89c992b56ac702319e02c428cca4a4e', 'license': 'cc-by-4.0', 'rows': 20000}, {'id': 'websight_v02', 'revision': 'b11f8172f89c992b56ac702319e02c428cca4a4e', 'license': 'cc-by-4.0', 'rows': 30000}], 'partition_sha256': {'train': '9de281a574a839157549c3334cee4d61a6ef90ccccd81905f04ce89e79ae098b', 'validation': '4116003f72270f9631ffa42b4d37c403d7adf4a82b4c749194a3dddd51b95bfd', 'test': 'ecca06285b5c4f67b12146e2a3824ea793a7b2a2797416ab9560f1c30456d9f5'}, 'token_cache_sha256': {'train': '44eb1d883865917f5cafc448ac60592c002d9526de7e2579deca9ad50655e0c8', 'validation': '5461629ba4b9bff9ec640a9b64ccb21466d2dacb96a948cea33629526f74d80e', 'test': 'cb3fe10b32e993e6b4e835d7068d62638df35e5fd75739e10dd9d08db41acf4a'}, 'sha256': 'fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a'}}. Continuation memulai optimizer/schedule/cursor stage baru; bukan resume optimizer lama. Resume parent None, SHANone.
- Tokenizer SHA `f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7`, pretrain fingerprint SHA `fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a`, synthetic manifest SHA `cb0537774dd785111329fc79a083a8ddbd3150ae60b5f40e57a0f6ce8e936394`, data SHA {'train': '418dc7e18c4bf932ea8d89a3b5b2771eec440f5ec68186337ec6f90f32374538', 'validation': '945bde9e48d4e4e274a63e519d13357b201e1c1fa9835af427cb0758031d2800'}, validationindices SHA `9bc32cb1719357ec7de7e859d9c67f3f0bdb69cb6deca4043f46d59d6b552c07`.
- Sourceconfig SHA `95f83046d898e069d48e0460f0ecff1dd6cc967dcfc2c61160d9cb4ad8cac04e`, expandedconfig SHA `b86e51d727b00a323b8d44424ec596cc10eb84f05b886312d161f815905856e4`, best SHA `0c7a4dae3ecc2b4801846727a91928e4ad3166a837cf1c16d158ccf288aaebfe`, last SHA `4c392a2ce1af98915bdf82d2f73c1291bf4316cfd77d42e63c7323e888efd347`. Git HEAD saat run `d876a9a227747ef751389f7ebf0c1e661885325b`, perubahan runtime lokal AI-012 dicommit setelah pengukuran/eksekusi selesai.
- Selected model tensors identical to parent: True, jumlah 77. **Throughput meningkat, kualitas terpilih belum membaik**. Runtime contoh tetap TRAIN-012best, gate keseluruhan historis43/48gagal. Tidak memakai final baru untuk mencari kelulusan.
- Artifacts [training report](../reports/training/TRAIN-014.json), [performance](../reports/training/TRAIN-014_gpu_performance.json), [development](../reports/training/TRAIN-014-DEV_curriculum_evaluation.json), [notebook07](../notebooks/07_optimasi_gpu_dan_training.ipynb), local outputs/metrics/TRAIN-014.jsonl dan TRAIN-014_gpu.jsonl, logs/training/TRAIN-014.log, checkpoints/TRAIN-014/.

### TRAIN-015: Varied lexical copying actual record

- AI-013 continuation sesuai persetujuan pengguna; status completed, committed step 2400. Mulai 2026-10-13T19:07:23.960828+07:00, selesai 2026-10-13T19:15:25.390693+07:00, wall 481.435741detik. Tidak ada training exception/OOM/nonfinite tercatat.
- Environment {'python': '3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]', 'executable': 'F:\\Generative_AI\\Vibe_Coding_Proyek_1\\.venv\\Scripts\\python.exe', 'torch': '2.14.1+cu130', 'cuda': '13.0', 'gpu': 'NVIDIA GeForce RTX 5070', 'platform': 'Windows-10-10.0.26200-SP0'}; model 14186496parameter, config {'vocab_size': 8192, 'block_size': 1024, 'n_layer': 6, 'n_head': 6, 'n_embd': 384, 'dropout': 0.1, 'tie_embeddings': True, 'initialization': 'random normal mean 0 std 0.02; no pretrained weights'}. Bobot berasal dari proyek, original pretraining parent {'checkpoint_sha256': '49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c', 'phase': 'pretrain', 'global_step': 1200, 'pretrain_fingerprint': {'version': 1, 'tokenizer_sha256': 'f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7', 'assignment_sha256': 'b827fdf80f0a20577a674a2ef4b70159da92a472e2535d5458c410c0398ab55b', 'source_revisions': [{'id': 'vulcan', 'revision': '19d2a482c78554e59feca0ce2b50fb7835e90c6f', 'license': 'mit', 'rows': 5000}, {'id': 'websight_v01', 'revision': 'b11f8172f89c992b56ac702319e02c428cca4a4e', 'license': 'cc-by-4.0', 'rows': 20000}, {'id': 'websight_v02', 'revision': 'b11f8172f89c992b56ac702319e02c428cca4a4e', 'license': 'cc-by-4.0', 'rows': 30000}], 'partition_sha256': {'train': '9de281a574a839157549c3334cee4d61a6ef90ccccd81905f04ce89e79ae098b', 'validation': '4116003f72270f9631ffa42b4d37c403d7adf4a82b4c749194a3dddd51b95bfd', 'test': 'ecca06285b5c4f67b12146e2a3824ea793a7b2a2797416ab9560f1c30456d9f5'}, 'token_cache_sha256': {'train': '44eb1d883865917f5cafc448ac60592c002d9526de7e2579deca9ad50655e0c8', 'validation': '5461629ba4b9bff9ec640a9b64ccb21466d2dacb96a948cea33629526f74d80e', 'test': 'cb3fe10b32e993e6b4e835d7068d62638df35e5fd75739e10dd9d08db41acf4a'}, 'sha256': 'fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a'}}; curriculum parent {'checkpoint_sha256': '791a365463710f73dbfbba767bd8bd17f5b4442e8f6137a92ec8c5888d1a2ed3', 'global_step': 3600, 'synthetic_manifest_sha256': '4875ed584633d9ee59d121e7b9d89e277fe37ec5f249cf4e1b3f189c81fd4673', 'run_id': 'TRAIN-012'}.
- Dataset data/processed/curriculum/v6, counts {'train': {'rows': 40158, 'families': 16239}, 'validation': {'rows': 1440, 'families': 240}, 'test': {'rows': 1440, 'families': 240}}; tambah 21090train-only rows. 1327/3903piece mendapat targeted contexts; 20679varian dilewati. Validation/test/final byte-identik v5, final belum dievaluasi. Origin synthetic_curriculum, human_reviewed False, bukan production reviewed.
- Batch 48 x accumulation 1; budget 2400, seed 42, warmup 120, LR 5e-05 ke 5e-06; betas [0.9, 0.95], decay 0.1, clip 1.0. Validation/checkpoint interval 400/400, batches 30, full 1440rows.
- Objective ordinary CE dengan prompt/pad-100 dan JSON/EOS aktif, labels already shifted. Performance {'attention_backend': 'sdpa', 'fused_adamw': True, 'pin_memory': True, 'tf32': True, 'supervised_only_logits': True, 'allocator_config': 'expandable_segments:True', 'gpu_telemetry': True, 'selected_by': 'reports/training/GPU-PERF-004.json', 'confirmed_on_v6_by': 'reports/training/GPU-PERF-005.json'}, allocator expandable_segments:True. Probe GPU-PERF-005 selesai sebelum training, bobot probe dibuang. Continuation baru optimizer/schedule/cursor; resume parent None, resume SHA None.
- Initial validation {'loss': 0.005657631831054099, 'perplexity': 1.0056736664550927, 'valid_tokens': 623706, 'batches': 30}; final {'loss': 0.0012606918653733105, 'perplexity': 1.0012614868714138, 'valid_tokens': 623706, 'batches': 30}; best CE 0.0012606918653733105step2400; final train loss 0.025576640820549845. 46345118target labels kumulatif termasuk pengulangan. Setelah lima update awal: 2395update, 101568.856targettokens/sec.
- Development best 24/24schema, 24/24exact, CE0.0012593359404379288; last 24/24schema, 24/24exact, CE0.0012593359404379288. Semua raw/model/hash tersimpan. Final belum diuji; runtime tetap TRAIN-012. Tidak menyatakan arbitrary-prompt/browser/production readiness.
- Active telemetry 804samples, {'utilization_pct': {'mean': 92.02611940298507, 'max': 100.0}, 'temperature_c': {'mean': 63.365671641791046, 'max': 68.0}, 'power_w': {'mean': 193.38189054726368, 'max': 202.28}, 'memory_used_mib': {'mean': 10406.951492537313, 'max': 10977.0}}; all-phase telemetry {'sample_count': 848, 'interval_seconds': 0.5, 'raw_path': 'F:\\Generative_AI\\Vibe_Coding_Proyek_1\\outputs\\metrics\\TRAIN-015_gpu.jsonl', 'errors': [], 'memory_scope': 'nvidia-smi memory includes other desktop applications', 'utilization_pct': {'mean': 90.33372641509433, 'max': 100.0, 'min': 1.0}, 'memory_used_mib': {'mean': 10338.69575471698, 'max': 10977.0, 'min': 2716.0}, 'power_w': {'mean': 191.74408018867925, 'max': 214.42, 'min': 36.88}, 'temperature_c': {'mean': 63.12971698113208, 'max': 68.0, 'min': 42.0}, 'sm_clock_mhz': {'mean': 2913.3620283018868, 'max': 2947.0, 'min': 870.0}}. Timestamp query dibanding interval update; bukan klaim utilisasi selalu100%. Peak allocated 7166819328bytes, reserved 8046772224bytes; nvidia-smi mencakup desktop. Free disk 19039686656bytes, reserve 16106127360bytes.
- Tokenizer SHA `f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7`, synthetic manifest SHA `0fb20da53b4e498cbcbadb7aa6296685a319ae323f68cc96e36f1659ba20d08c`, pretrain fingerprint `fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a`, data SHA {'train': '7d0d9f247436ca413f93fcde7b22337de88a29c64150c41998a172058388d2fd', 'validation': '945bde9e48d4e4e274a63e519d13357b201e1c1fa9835af427cb0758031d2800'}, validationindices SHA `9bc32cb1719357ec7de7e859d9c67f3f0bdb69cb6deca4043f46d59d6b552c07`.
- Initial checkpoint SHA `791a365463710f73dbfbba767bd8bd17f5b4442e8f6137a92ec8c5888d1a2ed3`, sourceconfig SHA `cc9c35fe57cf3ac7e41eaf60207dbb8287f6aedf42647fb9792af22138a79c95`, expandedconfig SHA `a53c5b776af8225471b1ad5aea32ca28c7afbc01ff87557375c2573f152093cc`, best SHA `3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638`, last SHA `07ca1d7cbe4fe41501a230126e86ede9af94609bed4c135e525ad8518233ae1d`. Git HEAD saat training `4b38fe1f8ec1e94a1c77e663cfe0138356c5ebe9`; perubahan AI-013 dicommit setelah seluruh pengukuran.
- [Report training](../reports/training/TRAIN-015.json), [summary](../reports/training/TRAIN-015_copy_experiment.json), [hasil kualitas](../reports/COPYING_QUALITY_2026-10-13.md), [notebook08](../notebooks/08_kualitas_penyalinan_dan_training.ipynb). Raw lokal outputs/metrics/TRAIN-015.jsonl dan TRAIN-015_gpu.jsonl, checkpoints/TRAIN-015/, logs/training/TRAIN-015.log.

#### TRAIN-015: Satu evaluasi final setelah kandidat dikunci

- Final 48/48schema, 44/48exact (91.67%), link 48, semuaEOS True; tokenmetrics {'loss': 0.0029893913076406266, 'perplexity': 1.0029938639935947, 'valid_tokens': 624225, 'batches': 360}. Gate True, runtime TRAIN-015/best.
- CheckpointSHA `3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638`, suiteSHA `3535c7c954fedefcf46911c059fc94171fdb689d2bd8982cbf4e20580c3858b5`, rawSHA `aa37e57dc7abed220b9b9f76ab73cb9a2d614f10b646de380146a0fb00bed456`, selectionSHA `c87edd00d5521dce19e953e3f43eaccd8c23828fb734b6bfaaaf5e519b1e82b5`. Kandidat dipilih sebelum final; tidak melakukan reselection/retraining dari hasil ini. Final sekarang consumed.
- 44website diekspor dari raw accepted jika gate lulus. Bukan aplikasi UI atau browser acceptance. [Gerbang final](../reports/FINAL_GATE_2026-10-13.md), [notebook09](../notebooks/09_evaluasi_final_dan_output.ipynb).
#### AI-013: Integritas bukti saat disimpan ke Git

- RUN-190 gagal memeriksa hash laporan TRAIN-015 yang staged karena newline normalization/index lama. Atribut byte-preserving hanya ditambahkan pada laporan baru fase ini; index baru direfresh. Laporan/model lama tidak ditulis ulang.
- RUN-191 lulus: enam hash frozen selection/training/development/final/policy/data-manifest cocok dengan byte yang disimpan Git. Gallery44website/308fileZIP tetap cocok dengan metadata, local resources/fragments tersedia. Audit ini statis, bukan browser atau eksekusi interaksi JS.
- RUN-185 prompt development Senandika yang pernah salah kini accepted dengan TRAIN-015best/evidence final cocok, EOS424token. Ini bukan tambahan skor final dan tidak menjadi data train pada fase ini.

#### AI-014: Analisis kebutuhan sebelum training halaman lengkap

- Tidak ada TRAIN-016 atau perubahan checkpoint dalam tahap ini. RUN-193 membaca distribusi train v6; RUN-194 gagal pada fixture manual; RUN-195 berhasil memperbaiki fixture tanpa mengubah kode produksi.
- Dua fixture 9 bagian memerlukan 1.498/1.479 total token. Ini analisis panjang, bukan generation atau metrik model. Reviewed manusia tetap 12; final TRAIN-015 sudah consumed.
- [Usulan arah](../reports/FULL_PAGE_DIRECTION_2026-10-13.md): plan dan task isi bagian, family split baru, development/final baru, notebook serta profiling sebelum menentukan budget training. Free storage sekitar 17,73 GiB dengan reserve 15 GiB.

#### AI-015: Desain konteks 2.048, bukan training baru

- RUN-200 adalah perhitungan analitis token/parameter, tanpa alokasi model GPU atau training. Model baru memerlukan position extension dan weights-only warm start dari model proyek dengan optimizer baru; exact resume lama tidak dipakai untuk config yang berbeda.
- Kandidat konteks 2.048, budget output plan512/section1.024; opsional full-page1.600 jika eksperimen development khusus disiapkan. Prefix dan budget diperiksa bersama, tanpa pemotongan JSON.
- [Spesifikasi](../docs/superpowers/specs/2026-10-13-full-page-generation-design.md) memuat profil batch4/8/12/16, length buckets/padding trim, budget disk, pilot data, final baru dan notebook. Angka batch/update belum hasil pengukuran dan tidak dinyatakan sebagai optimum.
- Tidak ada TRAIN-016, checkpoint baru, data baru atau reviewed manusia baru pada tahap penulisan spesifikasi.

#### AI-016: Revisi budget keluaran sebelum implementasi

- Keputusan pengguna: context2.048/output maksimum1.536; plan tetap512. Dengan output penuh, prefix dan penanda maksimum512. Menggantikan usulan full-page1.600 dan section1.024 pada desain AI-015.
- Tidak ada training/checkpoint/profil GPU baru. Spesifikasi dan perhitungan budget diperbarui, bukan konfigurasi runtime historis. [Spesifikasi](../docs/superpowers/specs/2026-10-13-full-page-generation-design.md).

#### AI-017: Rencana migrasi/data/training, belum eksekusi

- Rencana memakai context2.048/output section1.536/plan512. RUN-203 mengukur fixture plan ringkas366/367 token, bukan output model. Posisi tambahan belum dilatih.
- [Rencana implementasi](../docs/superpowers/plans/2026-10-13-full-page-generation.md) memuat migrasi weights-only, curriculum baru, loader/sampler exact-resume, profil batch4/8/12/16, pilot600 dan proposal training utama2.400 yang dikunci setelah diagnosis pilot sebelum run. Angka tersebut rencana, bukan hasil.
- Generator disiapkan sebelum pilot, benchmark final baru belum dijalankan. Tidak ada TRAIN-016, migrasi checkpoint, data baru atau test suite pada tahap penulisan rencana. RUN-204/205 review dokumen/interfaces selesai.

#### INIT-2048-001: Migrasi posisi, belum training

- RUN-209/210 menghasilkan initializationweights-only konteks2.048 dari TRAIN-015best. CheckpointSHA27a68c6a66bdb60fb9a729c9fd718e6eaa10d1b4d7e5f8789576339048ab9372; parameter14.579.712. Baris1.024lama/tensor lainidentik dan prefixlogits selisih0.0.
- Optimizer/scheduler lama tidakdireuse. Posisi1.024baru randomnormal0/std0.02 seed42, belum dilatih. Load dan ancestrymatch diperiksa, modelconfigmismatch ditolak. Freebytes18.971.791.360 setelahmigrasi, reserve15GiB dipertahankan.
- [Migration report](../reports/training/INIT-2048-001.json), [load inspection](../reports/training/INIT-2048-001_LOAD_INSPECTION.json). Ini bukan run training atau klaim halaman lengkap.

## TRAIN-016, fullpage pilot, mulai
Budget600 updates, context2048, plan512/section1536, batch16/accum3, effective48, BF16 SDPA fused AdamW, seed42. Konfigurasi configs/fullpage/pilot.json immutable, data fullpage-v1 pilot40 train/10 development families, human_reviewed=False. Parent INIT-2048-001 sha27a68c6a66bdb60fb9a729c9fd718e6eaa10d1b4d7e5f8789576339048ab9372. Profil FULLPAGE-GPU-001/002. Final belum dibuka; angka kualitas menunggu report aktual.

### TRAIN-016 hasil
Completed600,124.5807516detik, beststep600/CE0.1509130906. Checkpoint best5386787f5a93b2be7911f3ef1c36a23a80e907f752d359ccf2ba900326b54f87. Generation pilot0/20. Per-task dan GPU/disk detail terdapat pada reports/training/TRAIN-016*.json serta reports/fullpage/TRAIN-016_PILOT.json. Final tertutup. INIT-independent main2400 akan memakai configs/fullpage/training-v2.json; best weights-only, last full optimizer/scheduler/RNG/sampler.

## TRAIN-017, selesai
Configs/fullpage/training-v2.json, INIT2048 parent,2400 updates,458.4783864detik. Beststep1200 sha a0e8137d08ec081a129d6bb977b159b84d31613dcc8e444cc8ea0fe6735074ff, bestCE0.0352996924; lastCE0.0377850258. GPU mean88.48/max99%, temperaturemax69C. Per-task CE dan label panjang: reports/training/TRAIN-017_TASK_LOSS.json. Full/selected projection logits identik pada diagnosis. Ordinary CE belum menjadi kualitas halaman; generation development80 best/last sedangdijalankan, final tertutup. Semua checkpoint historis dipertahankan.

## TRAIN-016/017, ringkasan komprehensif dan koreksi acceptance, 14 Oktober 2026

### TRAIN-016

- **status:** `"completed"`.
- **started_at_utc:** `"2026-10-13T14:22:02.076755+00:00"`.
- **global_step:** `600`.
- **wall_seconds:** `124.5807515999768`.
- **initial_validation:** `{"loss": 6.259770864771965, "perplexity": 523.0990659510674, "valid_tokens": 59640, "batches": 15}`.
- **final_validation:** `{"loss": 0.15091309064510763, "perplexity": 1.1628955871845912, "valid_tokens": 59640, "batches": 15}`.
- **best_validation_loss:** `0.15091309064510763`.
- **total_train_tokens:** `7462133`.
- **final_train_loss:** `0.17651811833712314`.
- **peak_allocated_bytes:** `3726565376`.
- **free_bytes_after:** `18254815232`.
- **best_checkpoint_sha256:** `"5386787f5a93b2be7911f3ef1c36a23a80e907f752d359ccf2ba900326b54f87"`.
- **gpu_telemetry:** `{"sample_count": 222, "interval_seconds": 0.5, "raw_path": "F:\\Generative_AI\\Vibe_Coding_Proyek_1\\outputs\\metrics\\TRAIN-016_gpu.jsonl", "errors": [], "memory_scope": "nvidia-smi memory includes other desktop applications", "utilization_pct": {"mean": 82.14864864864865, "max": 99.0, "min": 0.0}, "memory_used_mib": {"mean": 6960.747747747748, "max": 7139.0, "min": 3212.0}, "power_w": {"mean": 181.13981981981982, "max": 200.49, "min": 28.67}, "temperature_c": {"mean": 60.17567567567568, "max": 65.0, "min": 44.0}, "sm_clock_mhz": {"mean": 2906.698198198198, "max": 2955.0, "min": 1057.0}}`.
- **Konfigurasi beku:**

```json
{
  "mode": "sft",
  "scope": "pilot",
  "data_origin": "fullpage_curriculum",
  "human_reviewed": false,
  "dataset_dir": "data/processed/fullpage/v1",
  "seed": 42,
  "block_size": 2048,
  "tokenizer": "data/tokenizer/tokenizer.json",
  "model_config_path": "configs/model_fullpage_2048.json",
  "model_config": {
    "vocab_size": 8192,
    "block_size": 2048,
    "n_layer": 6,
    "n_head": 6,
    "n_embd": 384,
    "dropout": 0.1,
    "tie_embeddings": true,
    "initialization": "random normal mean 0 std 0.02; no pretrained weights"
  },
  "device": "cuda",
  "precision": "bf16",
  "batch_size": 16,
  "gradient_accumulation": 3,
  "max_steps": 600,
  "warmup_steps": 60,
  "learning_rate": 5e-05,
  "min_learning_rate": 5e-06,
  "betas": [
    0.9,
    0.95
  ],
  "weight_decay": 0.1,
  "grad_clip": 1,
  "validation_interval": 100,
  "validation_batches": null,
  "checkpoint_interval": 100,
  "log_interval": 100,
  "reserve_free_bytes": 16106127360,
  "initial_checkpoint": "checkpoints/INIT-2048-001/initial.pt",
  "initial_checkpoint_sha256": "27a68c6a66bdb60fb9a729c9fd718e6eaa10d1b4d7e5f8789576339048ab9372",
  "performance": {
    "attention_backend": "sdpa",
    "fused_adamw": true,
    "pin_memory": true,
    "tf32": true,
    "supervised_only_logits": true,
    "validation_supervised_only_logits": true,
    "allocator_config": "expandable_segments:True",
    "gpu_telemetry": true,
    "selected_by": "reports/training/FULLPAGE-GPU-002.json"
  },
  "selection_rule": "Fixed budget, best full ordinary development CE. Generation development gate required before final. Main initializes independently from INIT2048, not pilot selection.",
  "lineage": {
    "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
    "fullpage_manifest_sha256": "86f4b41126478f87018271cb655da062d00119176df978ad9b2886976535b348",
    "initialization_parent": {
      "migration_kind": "position_extension",
      "source_checkpoint_sha256": "3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638",
      "source_config_sha256": "9e72eec8798e47f90f17b77a6d99e10037d0273503e5bb104f8b284ad5fb3d98",
      "source_lineage": {
        "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
        "pretrain_fingerprint": {
          "version": 1,
          "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
          "assignment_sha256": "b827fdf80f0a20577a674a2ef4b70159da92a472e2535d5458c410c0398ab55b",
          "source_revisions": [
            {
              "id": "vulcan",
              "revision": "19d2a482c78554e59feca0ce2b50fb7835e90c6f",
              "license": "mit",
              "rows": 5000
            },
            {
              "id": "websight_v01",
              "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
              "license": "cc-by-4.0",
              "rows": 20000
            },
            {
              "id": "websight_v02",
              "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
              "license": "cc-by-4.0",
              "rows": 30000
            }
          ],
          "partition_sha256": {
            "train": "9de281a574a839157549c3334cee4d61a6ef90ccccd81905f04ce89e79ae098b",
            "validation": "4116003f72270f9631ffa42b4d37c403d7adf4a82b4c749194a3dddd51b95bfd",
            "test": "ecca06285b5c4f67b12146e2a3824ea793a7b2a2797416ab9560f1c30456d9f5"
          },
          "token_cache_sha256": {
            "train": "44eb1d883865917f5cafc448ac60592c002d9526de7e2579deca9ad50655e0c8",
            "validation": "5461629ba4b9bff9ec640a9b64ccb21466d2dacb96a948cea33629526f74d80e",
            "test": "cb3fe10b32e993e6b4e835d7068d62638df35e5fd75739e10dd9d08db41acf4a"
          },
          "sha256": "fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a"
        },
        "synthetic_manifest_sha256": "0fb20da53b4e498cbcbadb7aa6296685a319ae323f68cc96e36f1659ba20d08c",
        "data_sha256": {
          "train": "7d0d9f247436ca413f93fcde7b22337de88a29c64150c41998a172058388d2fd",
          "validation": "945bde9e48d4e4e274a63e519d13357b201e1c1fa9835af427cb0758031d2800"
        },
        "validation_indices_sha256": "9bc32cb1719357ec7de7e859d9c67f3f0bdb69cb6deca4043f46d59d6b552c07",
        "train_blocks_or_examples": 40158,
        "validation_blocks_or_examples": 1440,
        "smoke": false,
        "human_reviewed": false,
        "pretraining_parent": {
          "checkpoint_sha256": "49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c",
          "phase": "pretrain",
          "global_step": 1200,
          "pretrain_fingerprint": {
            "version": 1,
            "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
            "assignment_sha256": "b827fdf80f0a20577a674a2ef4b70159da92a472e2535d5458c410c0398ab55b",
            "source_revisions": [
              {
                "id": "vulcan",
                "revision": "19d2a482c78554e59feca0ce2b50fb7835e90c6f",
                "license": "mit",
                "rows": 5000
              },
              {
                "id": "websight_v01",
                "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
                "license": "cc-by-4.0",
                "rows": 20000
              },
              {
                "id": "websight_v02",
                "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
                "license": "cc-by-4.0",
                "rows": 30000
              }
            ],
            "partition_sha256": {
              "train": "9de281a574a839157549c3334cee4d61a6ef90ccccd81905f04ce89e79ae098b",
              "validation": "4116003f72270f9631ffa42b4d37c403d7adf4a82b4c749194a3dddd51b95bfd",
              "test": "ecca06285b5c4f67b12146e2a3824ea793a7b2a2797416ab9560f1c30456d9f5"
            },
            "token_cache_sha256": {
              "train": "44eb1d883865917f5cafc448ac60592c002d9526de7e2579deca9ad50655e0c8",
              "validation": "5461629ba4b9bff9ec640a9b64ccb21466d2dacb96a948cea33629526f74d80e",
              "test": "cb3fe10b32e993e6b4e835d7068d62638df35e5fd75739e10dd9d08db41acf4a"
            },
            "sha256": "fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a"
          }
        },
        "curriculum_parent": {
          "checkpoint_sha256": "791a365463710f73dbfbba767bd8bd17f5b4442e8f6137a92ec8c5888d1a2ed3",
          "global_step": 3600,
          "synthetic_manifest_sha256": "4875ed584633d9ee59d121e7b9d89e277fe37ec5f249cf4e1b3f189c81fd4673",
          "run_id": "TRAIN-012"
        }
      },
      "pretrain_fingerprint": {
        "version": 1,
        "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
        "assignment_sha256": "b827fdf80f0a20577a674a2ef4b70159da92a472e2535d5458c410c0398ab55b",
        "source_revisions": [
          {
            "id": "vulcan",
            "revision": "19d2a482c78554e59feca0ce2b50fb7835e90c6f",
            "license": "mit",
            "rows": 5000
          },
          {
            "id": "websight_v01",
            "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
            "license": "cc-by-4.0",
            "rows": 20000
          },
          {
            "id": "websight_v02",
            "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
            "license": "cc-by-4.0",
            "rows": 30000
          }
        ],
        "partition_sha256": {
          "train": "9de281a574a839157549c3334cee4d61a6ef90ccccd81905f04ce89e79ae098b",
          "validation": "4116003f72270f9631ffa42b4d37c403d7adf4a82b4c749194a3dddd51b95bfd",
          "test": "ecca06285b5c4f67b12146e2a3824ea793a7b2a2797416ab9560f1c30456d9f5"
        },
        "token_cache_sha256": {
          "train": "44eb1d883865917f5cafc448ac60592c002d9526de7e2579deca9ad50655e0c8",
          "validation": "5461629ba4b9bff9ec640a9b64ccb21466d2dacb96a948cea33629526f74d80e",
          "test": "cb3fe10b32e993e6b4e835d7068d62638df35e5fd75739e10dd9d08db41acf4a"
        },
        "sha256": "fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a"
      },
      "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
      "source_positions": 1024,
      "target_positions": 2048,
      "new_position_seed": 42,
      "new_position_distribution": "normal mean0 std0.02",
      "human_reviewed": false
    },
    "schema_sha256": {
      "page.schema.json": "eac9c31ba0e46d64f176d428862b217b9dc7246c35b5f7b499c407a29515cf3f",
      "plan.schema.json": "cf8ef56b884ae9b3d15e03698a5cffff9a6fc29c0f311f32050a1e627c4f5e35",
      "request.schema.json": "243dba40b54c02055397af96824f24e06e1a03b0d5e09ca7c7d0385f46e55fd1",
      "section.schema.json": "099bb0a51e0420c9b46dbf2787368798f8f89346e66c309ac139a5e0b1d48c3f"
    },
    "source_sha256": {
      "src/training/engine.py": "1b72c225492530d6831f70b5cbfab62a62ade4bbaa56b2b2a9eade0e79d9a26b",
      "src/models/minigpt.py": "bfa75a3f29ce9cfa2ee4256fd06c6deb08ba1803b94c5fdc7bf273e31f152ccd",
      "src/fullpage/dataset.py": "5d7e6fdf1c9de27df381a7e137fec4a057d2a34c5e519afc799e84043650b385",
      "src/fullpage/prompts.py": "4926508d444b79ec4f60f78e05e3aec204651223d945d148b51f4f044a9333c4"
    },
    "profile_sha256": "7e03cff933c279470a143f514adce566f17ea2ac7e3ce5edc5b471bf496840dc"
  }
}
```

- Sumber lengkap: `reports/training/TRAIN-016.json`, `TRAIN-016_TASK_LOSS.json`, `outputs/metrics/TRAIN-016.jsonl`, `TRAIN-016_gpu.jsonl`. Run completed; tidak ada retraining pada koreksi acceptance. Best ordinary CE, last diagnosis; fullpage best weights-only, exact resume last.

### TRAIN-017

- **status:** `"completed"`.
- **started_at_utc:** `"2026-10-13T14:27:27.903178+00:00"`.
- **global_step:** `2400`.
- **wall_seconds:** `458.47838640003465`.
- **initial_validation:** `{"loss": 6.266232563831536, "perplexity": 526.4901188763001, "valid_tokens": 238822, "batches": 60}`.
- **final_validation:** `{"loss": 0.0377850257676812, "perplexity": 1.0385079564293256, "valid_tokens": 238822, "batches": 60}`.
- **best_validation_loss:** `0.03529969240542512`.
- **total_train_tokens:** `29930463`.
- **final_train_loss:** `0.0006886889110274247`.
- **peak_allocated_bytes:** `3732061184`.
- **free_bytes_after:** `17784012800`.
- **best_checkpoint_sha256:** `"a0e8137d08ec081a129d6bb977b159b84d31613dcc8e444cc8ea0fe6735074ff"`.
- **gpu_telemetry:** `{"sample_count": 818, "interval_seconds": 0.5, "raw_path": "F:\\Generative_AI\\Vibe_Coding_Proyek_1\\outputs\\metrics\\TRAIN-017_gpu.jsonl", "errors": [], "memory_scope": "nvidia-smi memory includes other desktop applications", "utilization_pct": {"mean": 88.47555012224939, "max": 99.0, "min": 1.0}, "memory_used_mib": {"mean": 6949.783618581907, "max": 7042.0, "min": 3157.0}, "power_w": {"mean": 194.1331784841076, "max": 212.03, "min": 20.34}, "temperature_c": {"mean": 64.22860635696821, "max": 69.0, "min": 41.0}, "sm_clock_mhz": {"mean": 2909.3581907090465, "max": 2947.0, "min": 780.0}}`.
- **Konfigurasi beku:**

```json
{
  "mode": "sft",
  "scope": "main",
  "data_origin": "fullpage_curriculum",
  "human_reviewed": false,
  "dataset_dir": "data/processed/fullpage/v1",
  "seed": 42,
  "block_size": 2048,
  "tokenizer": "data/tokenizer/tokenizer.json",
  "model_config_path": "configs/model_fullpage_2048.json",
  "model_config": {
    "vocab_size": 8192,
    "block_size": 2048,
    "n_layer": 6,
    "n_head": 6,
    "n_embd": 384,
    "dropout": 0.1,
    "tie_embeddings": true,
    "initialization": "random normal mean 0 std 0.02; no pretrained weights"
  },
  "device": "cuda",
  "precision": "bf16",
  "batch_size": 16,
  "gradient_accumulation": 3,
  "max_steps": 2400,
  "warmup_steps": 120,
  "learning_rate": 5e-05,
  "min_learning_rate": 5e-06,
  "betas": [
    0.9,
    0.95
  ],
  "weight_decay": 0.1,
  "grad_clip": 1,
  "validation_interval": 400,
  "validation_batches": null,
  "checkpoint_interval": 400,
  "log_interval": 100,
  "reserve_free_bytes": 16106127360,
  "initial_checkpoint": "checkpoints/INIT-2048-001/initial.pt",
  "initial_checkpoint_sha256": "27a68c6a66bdb60fb9a729c9fd718e6eaa10d1b4d7e5f8789576339048ab9372",
  "performance": {
    "attention_backend": "sdpa",
    "fused_adamw": true,
    "pin_memory": true,
    "tf32": true,
    "supervised_only_logits": true,
    "validation_supervised_only_logits": true,
    "allocator_config": "expandable_segments:True",
    "gpu_telemetry": true,
    "selected_by": "reports/training/FULLPAGE-GPU-002.json",
    "best_weights_only": true
  },
  "selection_rule": "Fixed budget, best full ordinary development CE. Generation development gate required before final. Main initializes independently from INIT2048, not pilot selection.",
  "lineage": {
    "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
    "fullpage_manifest_sha256": "86f4b41126478f87018271cb655da062d00119176df978ad9b2886976535b348",
    "initialization_parent": {
      "migration_kind": "position_extension",
      "source_checkpoint_sha256": "3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638",
      "source_config_sha256": "9e72eec8798e47f90f17b77a6d99e10037d0273503e5bb104f8b284ad5fb3d98",
      "source_lineage": {
        "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
        "pretrain_fingerprint": {
          "version": 1,
          "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
          "assignment_sha256": "b827fdf80f0a20577a674a2ef4b70159da92a472e2535d5458c410c0398ab55b",
          "source_revisions": [
            {
              "id": "vulcan",
              "revision": "19d2a482c78554e59feca0ce2b50fb7835e90c6f",
              "license": "mit",
              "rows": 5000
            },
            {
              "id": "websight_v01",
              "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
              "license": "cc-by-4.0",
              "rows": 20000
            },
            {
              "id": "websight_v02",
              "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
              "license": "cc-by-4.0",
              "rows": 30000
            }
          ],
          "partition_sha256": {
            "train": "9de281a574a839157549c3334cee4d61a6ef90ccccd81905f04ce89e79ae098b",
            "validation": "4116003f72270f9631ffa42b4d37c403d7adf4a82b4c749194a3dddd51b95bfd",
            "test": "ecca06285b5c4f67b12146e2a3824ea793a7b2a2797416ab9560f1c30456d9f5"
          },
          "token_cache_sha256": {
            "train": "44eb1d883865917f5cafc448ac60592c002d9526de7e2579deca9ad50655e0c8",
            "validation": "5461629ba4b9bff9ec640a9b64ccb21466d2dacb96a948cea33629526f74d80e",
            "test": "cb3fe10b32e993e6b4e835d7068d62638df35e5fd75739e10dd9d08db41acf4a"
          },
          "sha256": "fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a"
        },
        "synthetic_manifest_sha256": "0fb20da53b4e498cbcbadb7aa6296685a319ae323f68cc96e36f1659ba20d08c",
        "data_sha256": {
          "train": "7d0d9f247436ca413f93fcde7b22337de88a29c64150c41998a172058388d2fd",
          "validation": "945bde9e48d4e4e274a63e519d13357b201e1c1fa9835af427cb0758031d2800"
        },
        "validation_indices_sha256": "9bc32cb1719357ec7de7e859d9c67f3f0bdb69cb6deca4043f46d59d6b552c07",
        "train_blocks_or_examples": 40158,
        "validation_blocks_or_examples": 1440,
        "smoke": false,
        "human_reviewed": false,
        "pretraining_parent": {
          "checkpoint_sha256": "49e03ebb37f01619de9dc93a55f6828367d84fd34380986bfa15597d9583831c",
          "phase": "pretrain",
          "global_step": 1200,
          "pretrain_fingerprint": {
            "version": 1,
            "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
            "assignment_sha256": "b827fdf80f0a20577a674a2ef4b70159da92a472e2535d5458c410c0398ab55b",
            "source_revisions": [
              {
                "id": "vulcan",
                "revision": "19d2a482c78554e59feca0ce2b50fb7835e90c6f",
                "license": "mit",
                "rows": 5000
              },
              {
                "id": "websight_v01",
                "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
                "license": "cc-by-4.0",
                "rows": 20000
              },
              {
                "id": "websight_v02",
                "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
                "license": "cc-by-4.0",
                "rows": 30000
              }
            ],
            "partition_sha256": {
              "train": "9de281a574a839157549c3334cee4d61a6ef90ccccd81905f04ce89e79ae098b",
              "validation": "4116003f72270f9631ffa42b4d37c403d7adf4a82b4c749194a3dddd51b95bfd",
              "test": "ecca06285b5c4f67b12146e2a3824ea793a7b2a2797416ab9560f1c30456d9f5"
            },
            "token_cache_sha256": {
              "train": "44eb1d883865917f5cafc448ac60592c002d9526de7e2579deca9ad50655e0c8",
              "validation": "5461629ba4b9bff9ec640a9b64ccb21466d2dacb96a948cea33629526f74d80e",
              "test": "cb3fe10b32e993e6b4e835d7068d62638df35e5fd75739e10dd9d08db41acf4a"
            },
            "sha256": "fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a"
          }
        },
        "curriculum_parent": {
          "checkpoint_sha256": "791a365463710f73dbfbba767bd8bd17f5b4442e8f6137a92ec8c5888d1a2ed3",
          "global_step": 3600,
          "synthetic_manifest_sha256": "4875ed584633d9ee59d121e7b9d89e277fe37ec5f249cf4e1b3f189c81fd4673",
          "run_id": "TRAIN-012"
        }
      },
      "pretrain_fingerprint": {
        "version": 1,
        "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
        "assignment_sha256": "b827fdf80f0a20577a674a2ef4b70159da92a472e2535d5458c410c0398ab55b",
        "source_revisions": [
          {
            "id": "vulcan",
            "revision": "19d2a482c78554e59feca0ce2b50fb7835e90c6f",
            "license": "mit",
            "rows": 5000
          },
          {
            "id": "websight_v01",
            "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
            "license": "cc-by-4.0",
            "rows": 20000
          },
          {
            "id": "websight_v02",
            "revision": "b11f8172f89c992b56ac702319e02c428cca4a4e",
            "license": "cc-by-4.0",
            "rows": 30000
          }
        ],
        "partition_sha256": {
          "train": "9de281a574a839157549c3334cee4d61a6ef90ccccd81905f04ce89e79ae098b",
          "validation": "4116003f72270f9631ffa42b4d37c403d7adf4a82b4c749194a3dddd51b95bfd",
          "test": "ecca06285b5c4f67b12146e2a3824ea793a7b2a2797416ab9560f1c30456d9f5"
        },
        "token_cache_sha256": {
          "train": "44eb1d883865917f5cafc448ac60592c002d9526de7e2579deca9ad50655e0c8",
          "validation": "5461629ba4b9bff9ec640a9b64ccb21466d2dacb96a948cea33629526f74d80e",
          "test": "cb3fe10b32e993e6b4e835d7068d62638df35e5fd75739e10dd9d08db41acf4a"
        },
        "sha256": "fd6e3b5a20b3214cfd9e6cc769f7c011d3209235731edb793b917e60ca8a371a"
      },
      "tokenizer_sha256": "f7d5410d5963b3504bc09a4f6bf29e695cb8c6ba64041bfe1596a13cecb210d7",
      "source_positions": 1024,
      "target_positions": 2048,
      "new_position_seed": 42,
      "new_position_distribution": "normal mean0 std0.02",
      "human_reviewed": false
    },
    "schema_sha256": {
      "page.schema.json": "eac9c31ba0e46d64f176d428862b217b9dc7246c35b5f7b499c407a29515cf3f",
      "plan.schema.json": "cf8ef56b884ae9b3d15e03698a5cffff9a6fc29c0f311f32050a1e627c4f5e35",
      "request.schema.json": "243dba40b54c02055397af96824f24e06e1a03b0d5e09ca7c7d0385f46e55fd1",
      "section.schema.json": "099bb0a51e0420c9b46dbf2787368798f8f89346e66c309ac139a5e0b1d48c3f"
    },
    "source_sha256": {
      "src/training/engine.py": "a4b1e3a80afb470486f55f3d7031e32eb1b0130e1697049aea263287bea8007c",
      "src/models/minigpt.py": "bfa75a3f29ce9cfa2ee4256fd06c6deb08ba1803b94c5fdc7bf273e31f152ccd",
      "src/fullpage/dataset.py": "5d7e6fdf1c9de27df381a7e137fec4a057d2a34c5e519afc799e84043650b385",
      "src/fullpage/prompts.py": "4926508d444b79ec4f60f78e05e3aec204651223d945d148b51f4f044a9333c4"
    },
    "profile_sha256": "7e03cff933c279470a143f514adce566f17ea2ac7e3ce5edc5b471bf496840dc"
  }
}
```

- Sumber lengkap: `reports/training/TRAIN-017.json`, `TRAIN-017_TASK_LOSS.json`, `outputs/metrics/TRAIN-017.jsonl`, `TRAIN-017_gpu.jsonl`. Run completed; tidak ada retraining pada koreksi acceptance. Best ordinary CE, last diagnosis; fullpage best weights-only, exact resume last.

### Generation dan keputusan

- Pilot TRAIN-0160/20. MAIN historical BEST41/80 dan LAST58/80 pada RUN-230/231 bukan bukti semua fakta sudah benar.
- Review menemukan dua hero BEST terpotong. RUN-236/237 validasi ulang tanpa generation: BEST39/80 (48.75%), first attempt33; LAST58/80 (72.50%), first attempt51.
- Required role coverage accepted BEST39/80, LAST58/80; fact/link/asset checks100% untuk accepted V2. Ini bukan verifikasi semua klaim bahasa alami atau visual.
- Plan budget512, section1536, context2048, greedy, EOS wajib, maksimal satu retry. Failures awal dan raw attempts tetap tersimpan, tidak diisi renderer/target fallback.
- Denominator80, gate95% minimal76. Kedua checkpoint gagal; best tidak dikunci, last tidak dipromosikan, final80 belum dibuka, runtime historis tetap. Human review/browser390/1440/UI pending.
- Data sintetis240/40/40 families, train5760/val960/final800 task rows, family/style lineage tetap; human_reviewed=False. Desain/generalization di luar empat sektor belum terbukti.
- Report V2 memuat original report SHA, raw inputs/outputs hashes, corrected validator hashes, historical metrics dan revoked IDs. Gallery V2/ZIP diverifikasi pada RUN-238/239. Notebook10/11 menunjukkan proses aktual dan training opt-in.

## TRAIN-018/019, fullpage-v2 plan focused experiment, 14 Oktober 2026

### Tujuan dan data beku

- Tujuan yang disetujui pengguna: menaikkan validasi halaman utuh menuju95%, dengan gate sekurangnya76/80 prompt development. Hasil merupakan eksperimen terkontrol, bukan jaminan mencapai target.
- Inisialisasi fresh dari INIT2048, SHA-256 `27a68c6a66bdb60fb9a729c9fd718e6eaa10d1b4d7e5f8789576339048ab9372`. Model dan optimizer lama TRAIN-017 tidak digunakan sebagai parent.
- Data `data/processed/fullpage/v2`, manifest SHA-256 `b26f1714fa186081dec30c6f7c8ace478287601e0fc2bb318ae6f3601dbfd86d`. Isinya17.280 training task dari240 keluarga train dan2.400 variasi request; keluarga independen tidak bertambah. Rasio sampling plan70% dan section30% menghasilkan757 batch plan dari1.080 batch pada epoch terukur. Input maksimum1852 token, atau1853 jika token EOS dihitung.
- Seluruh empat file validation/final di v2 hash-identik dengan v1. Validasi mempunyai80 request. File final tidak diparse atau dipakai untuk pemilihan.
- Human reviewed=False; contoh baru dibuat dari keluarga train. WebMC600MC tidak dipakai untuk training.

### Perangkat, konfigurasi, dan resume

- VENV proyek, torch2.14.1+cu130, CUDA13, NVIDIA GeForce RTX5070. Profile `FULLPAGE-GPU-003` memakai tugas representatif v2 dengan rasio plan70%. Batch4/8/12/16 stabil; batch16 dengan accumulation3 dipilih, effective batch48, throughput profile55.059 token/detik dan peak allocated3,50GiB. Batch16 juga stabil di konteks2048.
- Konfigurasi aktif `configs/fullpage/training-improvement-v2-r1.json`, SHA-256 `d6476a9ee322255f8d0863074543946bd6fd80692cb87370dd8c795fa8d2936f`. Budget total3600 update global, warmup180, learning rate5e-5→5e-6, validasi dan checkpoint tiap600 update, BF16, SDPA, fused AdamW, TF32.
- `TRAIN-018` dimulai fresh dari step0 sampai step1800 lalu disimpan sebagai checkpoint penuh `checkpoints/TRAIN-018/last.pt`, SHA-256 `160009de6d7b653ba392ca692a7b96fd1788a1659ca04dc9b34149d5dfe99c70`. Snapshot generasi weights-only `checkpoints/TRAIN-018/generation-1800.pt`, SHA-256 `f36e1a8ec238f860e800dbf6a6556b8d52afc4ec9e739524de251cc7a14c80a2`.
- `TRAIN-019` melanjutkan optimizer, scheduler, sampler cursor5400, RNG, konfigurasi dan data identik. Resume parent SHA cocok dengan checkpoint TRAIN-018. Berakhir pada global step3600, status completed. Checkpoint penuh last SHA-256 `c96e58d74b7fb63d400f037290d6bbdf9267edff2ac46238528028732ac2c2b6`; snapshot generasi weights-only `checkpoints/TRAIN-019/generation-3600.pt`, SHA-256 `4b3290fb62fc993f412c22db186c2e2e5383a1ef965214bbbfde75331155bf0a`.
- Checkpoint dan output berada pada fase storage `fullpage-improvement-v2`. Reserve disk15GiB dijaga, free disk setelah run15,54GiB. Estimasi fase resume diperbarui sebelum training; guard free disk setiap checkpoint tetap aktif.

### Hasil optimisasi

| Titik global | Status run | Validation CE | Runtime bagian | GPU utilitas rata-rata | Peak VRAM allocated | Halaman development valid |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| INIT, step0 | TRAIN-018 awal | 6,266233 | | | | |
| 1.800 | TRAIN-018 berhenti sementara | 0,012056 | 566,68 detik | 92,19% | 3,51GiB | 46/80 (57,5%) |
| 3.600 | TRAIN-019 selesai | 0,007519 | 547,81 detik | 91,97% | 3,51GiB | 70/80 (87,5%) |

- Akumulasi training29.307.745 target token pada fase TRAIN-018; total sampai global step3600 ialah58.725.809 target token. Suhu GPU maksimum70C dan71C pada tiap run; pemakaian GPU mencapai100%. Total wall time training tercatat1.114,49 detik di luar evaluasi generasi.
- Evaluasi memakai80 request validation identik, validator sama dan maksimal retry yang sama. Required roles70/80 dan first attempt valid70/80 di step3600. Retry tidak menyelamatkan halaman yang gagal.
- Ranking beku memilih step3600 di atas step1800: kelulusan70 lebih besar dari46, lalu cakupan role, first attempt, ordinary CE, dan step lebih awal sebagai tie-break. Laporan `reports/fullpage/AI-019_DEVELOPMENT_SELECTION.json` menyatakan `needs_additional_improvement`; candidate tidak dikunci.
- Baseline LAST TRAIN-017 yang direvalidasi58/80. Step3600 bertambah12 halaman, tetapi masih kurang6 halaman untuk ambang76. Target95% belum tercapai.
- Sepuluh output gagal berasal dari lima keluarga request yang masing-masing dicoba pada CSS biasa dan Tailwind. Rekap error attempt: plan12, nav4, faq4; kategori tercatat identity/name12, field/schema6, unprovided structured item4, fact/content4. Angka kategori menghitung error per attempt, bukan keluarga unik.
- Final consumption tidak terjadi. Klaim visual browser, review manusia, integrasi UI dan deployment masih pending. Cross entropy tidak menggantikan evaluasi halaman utuh.

### Artefak dan run

- Profile `reports/training/FULLPAGE-GPU-003.json`; konfigurasi aktif di atas; ringkasan `reports/training/TRAIN-018.json` dan `TRAIN-019.json`; development `reports/fullpage/TRAIN-018_DEVELOPMENT.json` dan `TRAIN-019_DEVELOPMENT.json`; selection `reports/fullpage/AI-019_DEVELOPMENT_SELECTION.json`.
- Notebook12 merekam data, profil, training, kurva validasi dan perbandingan halaman: [12_perbaikan_fullpage_dan_evaluasi.ipynb](../notebooks/12_perbaikan_fullpage_dan_evaluasi.ipynb). Eksekusi tersimpan dan keenam code cell selesai.
- RUN-262 TRAIN-018, RUN-263 snapshot1800, RUN-264 exact resume preflight, RUN-265 TRAIN-019, RUN-266 snapshot3600, RUN-267/268 development, RUN-269/270 diagnosis kegagalan, RUN-271 selection, RUN-272 audit metrik, RUN-274 notebook.
- Persiapan dan konfigurasi di-commit serta di-push sebelum training pada `c829f02`. Semua percobaan gagal, termasuk pencarian yang tidak valid dan penolakan overwrite config, tetap ada pada canonical RUN ledger.
- Koreksi diagnosis: klasifikasi fact/content dari RUN-270 bersifat kasar. RUN-277 membaca pesan validator mentah pada lima keluarga gagal. Tiga mengalami plan identity/style mismatch, satu navbar brand fact mismatch, dan satu FAQ mengalami required fact item mismatch serta unprovided structured item. RUN-275 mencatat bug kecil pada wrapper verifikasi notebook, RUN-276 memverifikasi semua code cells tersimpan tanpa error, dan RUN-278 memperjelas failure grouping pada notebook.

## TRAIN-020/021, fullpage v3 targeted identity and facts, 14 Oktober 2026

### Tujuan, data, dan kontrak

- Tujuan eksperimen: memperbaiki hasil baseline TRAIN-019 yang mencapai 70/80 halaman development, dengan gate 95 persen atau minimal 76/80. V3 menguji instruksi copy identitas secara tepat dan penggunaan fakta yang tersedia.
- `src/fullpage/prompts.py` memperkuat instruksi plan dan section. Validator, schema, renderer dan retry tidak diubah. Context tetap 2.048 token, output plan 512 token, output section 1.536 token.
- V3 dibuat dari keluarga train yang sama. Penambahan terdiri atas 960 halaman sintetis, 480 alias nama, 240 keluarga, 960 task plan, 4.800 task section, total 5.760 task tambahan. Task train keseluruhan 23.040. Manifest v3 SHA-256 `823d09401a92093d2e6dc463753074e9775d9591ce044185c3442adb07eeb8a6`.
- Validation dan test v3 tetap checksum-identik dengan v2. Development tetap 80 request. File final disalin tanpa diparse dan tidak digunakan untuk evaluasi maupun seleksi. Data sintetis belum ditinjau manusia.
- Klarifikasi sampler: laporan baseline TRAIN-019 menunjukkan `plan_batch_probability=0.7`, sama dengan v3. Perlakuan v3 adalah augmentation dan distribusi contoh role, bukan perubahan rasio sampler. Perbandingan awal yang memakai lokasi laporan keliru tetap dipertahankan; koreksi berbasis laporan resmi dicatat pada RUN-315 dan laporan selection.

### Profil perangkat dan konfigurasi

- Profil dilakukan langsung pada NVIDIA GeForce RTX 5070. Batch 4, 8, 12, dan 16 stabil dengan effective batch 48. Batch 8 plus akumulasi 6 dipilih karena throughput terukur tertinggi, 53.546 target token per detik, peak reserved 2.292.187.136 byte, dengan sisa memori perangkat 9.224.323.072 byte pada sampel profil.
- Config `configs/fullpage/training-improvement-v3.json`: 3.600 update, warmup 180, learning rate awal 5e-5 dan minimum 5e-6, BF16, SDPA, fused AdamW, TF32, microbatch 8, accumulation 6, validasi dan checkpoint tiap 600 update. Fresh init memakai `checkpoints/INIT-2048-001/initial.pt`, SHA-256 `27a68c6a66bdb60fb9a729c9fd718e6eaa10d1b4d7e5f8789576339048ab9372`.

### Hasil training

| Run | Global update | Status | Wall time | Target token kumulatif | Validation CE akhir | Peak reserved | Snapshot generasi SHA-256 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| TRAIN-020 | 1.800 | stopped_at_limit | 568,70 detik | 29.424.126 | 0,005813 | 2.292.187.136 byte | `0204941c5700d2f757c8a92537a2ffa7059d8e0ee4189338096a8991594032cf` |
| TRAIN-021 | 3.600 | completed | 557,89 detik | 58.756.012 | 0,007596 | 2.313.158.656 byte | `74ada927f75cb46ad6b4bc21ca2f3c5e725f76aee0d1e83902e832b1ba4e39a3` |

TRAIN-021 melanjutkan checkpoint lengkap TRAIN-020 secara persis, termasuk state optimizer, scheduler, sampler, dan RNG. Snapshot generasi weights-only terpisah dari checkpoint resume. Checkpoint akhir, parent lineage, konfigurasi, manifest, tokenizer, prompt dan renderer diikat oleh laporan run/evaluasi.

### Hasil generation development

| Kandidat | Halaman lengkap | First attempt lengkap | Required roles | Validation CE | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline TRAIN-019 step 3600 | 70/80 | Lihat laporan baseline | 70/80 | 0,007519 | Belum mencapai 76/80 |
| TRAIN-020 step 1800 | 0/80 | 0/80 | 0/80 | 0,005813 | Gagal |
| TRAIN-021 step 3600 | 0/80 | 0/80 | 0/80 | 0,007596 | Gagal |

- TRAIN-020 mencatat 64 halaman dengan invalid JSON/contract; audit attempt mengaitkan error utama pada role `process`: 128 percobaan yang mengenai 64 halaman. Plan identity mismatch muncul 15 kali pada 8 halaman. Plan schema juga menghasilkan field `columns` yang tidak dikenal dan descriptor yang tidak cocok.
- TRAIN-021 mencatat 72 halaman dengan invalid JSON/contract; role `process` mengalami 144 percobaan pada 72 halaman. Plan identity mismatch 15 percobaan pada 8 halaman; mismatch brand section juga muncul.
- Model gate false pada kedua kandidat. Selection berbasis jumlah halaman memilih TRAIN-020 hanya sebagai kandidat observasi terbaik, bukan checkpoint yang layak dipromosikan. Perbedaan CE tidak membuatnya lolos acceptance.
- Komposisi role menunjukkan `process` berjumlah 480 contoh pada v2 dan v3. V3 menambah navigation 480 hingga total 1.440, services 960 hingga total 1.440, FAQ 480 hingga total 720, portfolio 480 hingga total 720 dan footer 960 hingga total 3.360. Perbandingan ini belum membuktikan kausalitas atas error process.
- Final tetap belum dibuka. Browser review false, human review false. Belum ada klaim kualitas visual, produksi, atau generalisasi prompt nyata.

### Artefak dan bukti

- Notebook [13](../notebooks/13_fullpage_v3_targeted_training.ipynb) dibuat dan dieksekusi, 20 sel, tidak mengizinkan error sel. Ia membaca laporan tersimpan dan tidak menjalankan ulang training.
- Dataset summary `reports/data/FULLPAGE_CURRICULUM_V3.json`; GPU profile `reports/training/FULLPAGE-GPU-004.json`; config `configs/fullpage/training-improvement-v3.json`.
- Training/evaluasi `reports/training/TRAIN-020.json`, `TRAIN-021.json`, `TRAIN-020_DEVELOPMENT.json`, `TRAIN-021_DEVELOPMENT.json`; pemilihan `reports/training/AI-020_DEVELOPMENT_SELECTION.json`.
- RUN-295 persiapan data; RUN-297 profile; RUN-298 freeze config; RUN-300 train 1800; RUN-301 snapshot; RUN-302 evaluasi 1800; RUN-308 exact resume; RUN-309 snapshot; RUN-310 evaluasi 3600; RUN-315 koreksi rasio sampler; RUN-316 distribusi role; RUN-317 mismatch identitas; RUN-320 selection; RUN-325 notebook.
- Debugging tercatat tanpa menghapus run gagal: RUN-282 compile error diperbaiki RUN-284; RUN-287 masalah utilitas hash dituntaskan dengan verifikasi RUN-288/289; RUN-290 context overflow ditangani dengan instruksi fakta yang lebih ringkas; RUN-303 salah tingkat folder dikoreksi oleh audit RUN-306/311; RUN-312 salah lokasi laporan rasio dikoreksi setelah audit RUN-313/315.

Status: pipeline dan rekam training tersedia, tetapi target 95 persen belum tercapai. Sebelum eksperimen training lain, gunakan error utama pada `process` dan title copy untuk menyusun rancangan train-only yang bisa direview. Pertahankan semua partisi, validator strict, reserve storage, dan final benchmark tertutup.

### Diagnosis tambahan setelah notebook v3

RUN-331 membandingkan satu target training role `process` dengan satu raw output TRAIN-020. Target memuat `"id":"process"` yang valid. Output model dimulai dengan `{"id":"props":...` dan berhenti pada EOS setelah231 token dari budget1.536, sehingga contoh itu bukan kegagalan token limit. Error parser terjadi di kolom14.

Distribusi train RUN-316: v2 memiliki480 dari12.480 section rows untuk process, atau3,85 persen. V3 tetap480 process dari17.280 section rows, atau2,78 persen, turun sekitar27,8 persen sebagai porsi relatif. Ini mendukung hipotesis data dilution, tetapi belum membuktikan sebab-akibat.

Rancangan berikutnya yang perlu direview adalah melengkapi target process hanya untuk train page yang mempunyai descriptor process, sambil menahan prompt v3, renderer, validator, sampler0,7, budget token, dan training setting lain tetap. Belum ada implementasi atau training v4. RUN-330 adalah kesalahan syntax pada perintah audit awal; RUN-331 mengulang pemeriksaan dan berhasil.

## TRAIN-022/024, fullpage v4 process-role augmentation, 14 Oktober 2026

### Tujuan dan perubahan data

- Eksperimen menguji hipotesis bahwa lebih banyak target `process` pada train dapat mengurangi kegagalan isi section. Tidak ada prompt, renderer, schema, validator, atau retry yang diubah.
- Data v4 diturunkan dari v3. Sebanyak 960 target section `process` ditambahkan hanya untuk halaman keluarga train yang memang mempunyai descriptor process. Jumlah row train naik dari 23.040 menjadi 24.000. Row target `process` naik dari 480 menjadi 1.440. Jumlah `page_plan` tetap 5.760, sedangkan `section_content` naik dari 17.280 menjadi 18.240.
- Validation dan test tetap checksum-identik. Hash file development requests tetap `2091d047ee3692dcba1fbdb9b81e4c20e56b85e1ff46ad54b5eacd906c9d6836`. Manifest v4 SHA-256 `aae2de8cfceb16110eb93b0668447fcda7237fdfabaa7e0c2a22ce2c3d41cf15`; parent v3 SHA-256 `823d09401a92093d2e6dc463753074e9775d9591ce044185c3442adb07eeb8a6`.
- Semua train examples tetap sintetis dan belum ditinjau manusia. File final tidak dibuka dan tidak digunakan.

### Hardware, profile, dan konfigurasi

- Perangkat: NVIDIA GeForce RTX 5070. Batch 4, 8, 12, dan 16 stabil pada profile representative dengan effective batch 48.
- Throughput terukur: batch 4 49.414 token/detik, batch 8 51.562, batch 12 52.848, batch 16 52.889. Batch 16 hanya 2,6 persen di atas batch 8, dengan peak reserved 4.183.818.240 byte dibanding 2.292.187.136 byte. Konfigurasi tetap microbatch 8 dan accumulation 6 untuk mengisolasi perubahan data dan mempertahankan setting yang disetujui. Pemilihan tersebut bukan klaim batch tercepat.
- Konfigurasi `configs/fullpage/training-improvement-v4.json`, SHA-256 `91bc688b5c34befc33e41749f7dbb0b4513f60c513377c94a35bdd31ef5a6487`: 3.600 update, plan batch probability0,7, batch8, accumulation6, effective batch48, BF16, CUDA, konteks2.048 token, section output maksimal1.536 token, validation/checkpoint tiap600 update. Setting training lain mengikuti konfigurasi v3 yang dibekukan.

### Training dan resume

| Run | Global update | Status | Wall time | Token target kumulatif | Validation CE akhir | Peak allocated | Peak reserved |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| TRAIN-022 | 1.800 | stopped_at_limit | 565,07 detik | 29.555.524 | 0,006403 | 2.118.478.336 byte | 2.292.187.136 byte |
| TRAIN-024 | 3.600 | completed | 588,15 detik | 59.052.905 | 0,007639 | 2.118.917.120 byte | 2.271.215.616 byte |

- TRAIN-022 dimulai dari INIT-2048-001 dan checkpoint last lengkap dipertahankan untuk resume. Snapshot evaluation weights-only SHA-256 `567cd73aac8d3d0eee10be54ea897e6d1d994a084150527fc107b125d3a374c0`.
- TRAIN-024 memulihkan optimizer, scheduler, sampler, RNG, dan konfigurasi persis dari TRAIN-022/step1800. Resume parent SHA-256 `edd14b5d4988f0c513d2754b4a790d663155f7f09712827b21668ab4d148a729`. Snapshot evaluation weights-only SHA-256 `913b1b00aec040a0d51c3607cf7261288e7fe089378850fc66c131400c0f319a`.
- Rata-rata GPU utilization telemetry sekitar90,79 persen pada TRAIN-022 dan90,62 persen pada TRAIN-024. Suhu maksimum masing-masing70C dan69C. Tidak ada telemetry error.
- Validation CE pada update0,600,1200,1800: 6,266233; 0,121490; 0,009746; 0,006403. Saat resume, CE pada1800,2400,3000,3600: 0,006403; 0,006491; 0,007504; 0,007639. Generation quality tetap menjadi kriteria pemilihan utama.

### Insiden penyimpanan dan pemulihan

- Percobaan resume pertama sebagai TRAIN-023 gagal sebelum weight update karena guard penyimpanan membutuhkan ruang untuk checkpoint sambil mempertahankan cadangan15GiB. Error penuh ada di RUN-357. Tidak ada weight update pada TRAIN-023.
- RUN-360 berhenti sebelum pemindahan karena shell tidak memiliki Get-FileHash. RUN-361 memindahkan TRAIN-002, TRAIN-003, TRAIN-004, dan TRAIN-004-VERIFIED ke `C:\Generative_AI_Checkpoint_Archive\Vibe_Coding_Proyek_1\checkpoints`, lalu berhenti saat menemukan TRAIN-005 telah berupa junction. Hash file setelah perpindahan cocok dan junction dipertahankan di path lama.
- TRAIN-005, TRAIN-006, dan TRAIN-007 ternyata sudah mengarah ke arsip E:, sehingga tidak dipindahkan. RUN-363 mencatat temuan itu. TRAIN-008 kemudian dipindahkan dengan checksum terverifikasi pada RUN-365. Total lima folder yang benar-benar dipindahkan adalah1.873.865.524 byte.
- RUN-366 memverifikasi ulang checkpoint TRAIN-022 dan konfigurasi. Ruang F: sebesar18.281.406.464 byte, dengan headroom1.341.235.200 byte di atas estimasi kebutuhan model dan reserve. Karena RUN-023 sudah menyimpan kegagalan awal, resume berikut memakai ID baru TRAIN-024.

### Evaluasi halaman development

| Kandidat | Landing page CSS | Landing page Tailwind | Company profile CSS | Company profile Tailwind | Total | First attempt | Validation CE | Gate 76/80 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| TRAIN-022, step1800 | 18/20 | 18/20 | 14/20 | 14/20 | 64/80, 80% | 62/80 | 0,006403 | Gagal |
| TRAIN-024, step3600 | 19/20 | 19/20 | 15/20 | 15/20 | 68/80, 85% | 68/80 | 0,007639 | Gagal |

- TRAIN-024 dipilih sebagai hasil v4 terbaik berdasarkan jumlah halaman lengkap, naik4 halaman dari TRAIN-022. Target 76/80 belum tercapai, kurang8 halaman. Tidak ada candidate v4 yang lolos model gate atau dipromosikan.
- TRAIN-024 merekam12 halaman gagal akhir. Semua68 halaman yang diterima sudah lolos pada attempt pertama; retry tidak menyelamatkan sisa halaman. Gagal akhir tersebar pada enam keluarga prompt, masing-masing dengan dua style renderer.
- Error mentah yang dominan: plan request identity/style mismatch,16 attempts pada9 halaman; hero brand fact mismatch,4 attempts pada2 halaman; navigation brand fact mismatch,4 attempts pada2 halaman; required fact text mismatch di about,2 attempts pada1 halaman. Angka attempt tidak sama dengan jumlah halaman unik.
- Historical baseline TRAIN-019 tetap70/80 pada request development yang sama. Baseline ini hanya referensi historis dari eksperimen lain, bukan kandidat v4 yang setara untuk ranking.
- Perubahan dari64 ke68 halaman pada dua checkpoint v4 sama-sama memakai data v4 dan tidak mengisolasi efek data terhadap v3 melalui beberapa seed. Hasil ini tidak membuktikan kausalitas penambahan row process.

### Artefak, notebook, dan bukti

- Dataset dan laporan preparation: `data/processed/fullpage/v4/`, `reports/fullpage/FULLPAGE-V4_DATA_PREPARATION.json`.
- Config: `configs/fullpage/training-improvement-v4.json`. GPU profile: `reports/training/FULLPAGE-GPU-005.json` dan `FULLPAGE-GPU-005-CONTROLLED-B8.json`.
- Training summaries: `reports/training/TRAIN-022.json`, `reports/training/TRAIN-024.json`; loss/performance metrics: `outputs/metrics/TRAIN-022.jsonl`, `outputs/metrics/TRAIN-024.jsonl`.
- Evaluasi: `reports/fullpage/TRAIN-022_DEVELOPMENT_STEP1800.json` dan `reports/fullpage/TRAIN-024_DEVELOPMENT_STEP3600.json`.
- Laporan lineage dan ranking: `reports/training/FULLPAGE-V4_DEVELOPMENT_SELECTION.json`. Snapshot tersimpan di `checkpoints/FULLPAGE-V4/`.
- Notebook [14](../notebooks/14_fullpage_v4_process_role_training.ipynb) memiliki16 sel dan berhasil dieksekusi dengan error cell dilarang. Notebook membaca artefak yang telah ada, tidak menjalankan ulang training atau evaluasi.
- RUN utama: RUN-346 preparation; RUN-347/350 profile; RUN-351/352 config; RUN-353 training step1800; RUN-355 evaluation; RUN-357 storage preflight failure; RUN-361/365 checkpoint archive; RUN-366 resume preflight; RUN-367 resume training; RUN-368 snapshot; RUN-369 evaluation; RUN-374 selection; RUN-378 notebook. CodeGraph disinkronkan pada RUN-373 dan RUN-377.
- Output utama tetap synthetic contract evaluation. Browser visual review, human review, deployment, dan final benchmark tidak dilakukan.

Kesimpulan: v4 memperbaiki kelulusan dari80 persen ke85 persen antara step1800 dan3600, tetapi belum mencapai95 persen. Error yang dominan pada candidate terbaik kini adalah konsistensi identity/style di plan serta penyalinan fakta merek. Gunakan pola ini untuk merancang eksperimen train-only berikutnya dengan validator strict dan final benchmark tetap tertutup.

## V5 source-bound experiment: preflight passed, training not started

Tujuan V5 adalah mengurangi kesalahan penyalinan identitas dengan meminta model menghasilkan referensi fakta, lalu mengisi nilai literal dari request melalui resolver dan renderer. Dataset tetap sintetis dan belum human-reviewed, sehingga hasil tidak dianggap sebagai kesiapan produksi.

| TRAIN ID | Tahap | Status | Config | Parent | Target |
| --- | --- | --- | --- | --- | --- |
| TRAIN-025 | Source-bound SFT tahap pertama | Planned, fresh preflight required | `configs/fullpage/training-improvement-v5.json`, SHA-256 `8852971e852e3b4ce6a6b845c24c8629e65d2a5f699d30968c2f3ce61a353186` | TRAIN-024 step 3600, weights-only | 1800 updates |
| TRAIN-026 | Exact resume source-bound SFT | Planned | Sama persis dengan TRAIN-025 | `TRAIN-025/last.pt`, exact resume state | 3600 total updates |

- Data: V5 manifest SHA-256 `90c2dc71c4d91ff9a36a3fbd1bd36bd329c127b711c69556df4c0f58381d6dd2`, 240 train families, 40 development families, 3,360/80 requests, and 33,600/800 task rows. Maximum combined prompt/target context is 1,622/1,569 tokens. No test or final rows are included in V5.
- Model start: Load only the exact TRAIN-024 weights-only snapshot, SHA-256 `913b1b00aec040a0d51c3607cf7261288e7fe089378850fc66c131400c0f319a`. Optimizer, scheduler, sampler, and RNG begin fresh. TRAIN-026 must resume TRAIN-025 exact state.
- Frozen configuration: microbatch 8, accumulation 6, effective batch 48, BF16, CUDA, SDPA, fused AdamW, plan probability 0.7, context 2,048, PagePlan output budget 896, section output budget 1,536, 3,600 update budget, snapshots/evaluation at 1,800 and 3,600.
- Hardware preflight RUN-529 passed on the project `.venv` with Python 3.11.9, PyTorch 2.14.1+cu130, CUDA 13.0, and an actual finite BF16 tensor operation on RTX 5070. V5 source lineage and parent identity verified. Free disk was 17,301,045,248 bytes; reserve plus checkpoint estimate was 16,706,895,872 bytes, leaving 594,149,376 bytes above the 15 GiB reserve.
- Other desktop/Jupyter GPU processes observed during preflight were left untouched. GPU memory showed 10,957 MiB free during the project tensor check.
- Validation plan: compare development generation at steps 1,800 and 3,600 using complete pages and exact fact/reference checks first, validation cross entropy second. Required model gate is at least 76/80. If neither checkpoint passes, report the measured shortfall and do not claim the 95 percent target.
- Final/held-out boundary: final records remain unopened. Only the 80 frozen V4 development requests may be used for selection. No final benchmark or human/browser review is implied.
- Current state: Training has not started. RUN-579 passed all 21 training tests. RUN-580 and RUN-585 passed all 79 full-page tests, including a post-config-refresh check. The fresh-run guard permits source-bound initialization only as TRAIN-025 and requires TRAIN-026 to resume exact TRAIN-025 state. The first training update still waits on whole-branch review, commit/push, and a fresh reserve/GPU preflight.

### Config lineage refresh before TRAIN-025

- After RUN-533, code review restored the original optimizer-then-weight-load order for legacy initializers while preserving the V5 weight-load-before-fresh-optimizer path.
- RUN-534 regenerated the config against the updated engine. RUN-535 verified the new config and retained the previous unused configuration under `logs/config-archive/`.
- Historical config SHA-256: `60e90d27bd8aa0fcb6cc08e71bbdda98e7c6f6ca156fc737a2176052df5108ee`. RUN-549 verified its engine and lineage source pins, V5 manifest, and TRAIN-024 parent before the independent frozen-settings guard.
- The prior config hashes `b6d25313cbfceeeb6471a7191b2bc13abd0ae99ae05fc3894cfb9e20d03cddb3` and `195c314855fddc340f0b1f7a32ce77dae0a436fa55aed0b23b0cbe8d545a8f64` were not used by training and are preserved under `logs/config-archive/`.
- RUN-537 passed 17 training tests and RUN-538 passed 71 full-page tests before the final parent guard. RUN-545 passed six focused guard checks. RUN-550 rebuilt notebook 15 with 22 cells, without running training or evaluation cells. RUN-551 passed all 18 training tests and RUN-552 passed all 72 full-page tests after the parent guard. These results are historical; the latest suites are RUN-563 and RUN-564.

### Independent frozen-settings guard follow-up

- The next whole-branch review found that the selector compared candidate reports against the current config without independently pinning all approved experiment settings. A changed plan probability, batch size, learning rate, TF32 setting, or selection rule could otherwise pass through both trainer and selector.
- Added an independent source-bound settings map for the full training config, parent identity, generation budgets, performance options, selection rule, and the RTX 5070 profile checksum. Both full lineage verification and direct `run_training` calls enforce it before dataset or checkpoint use. The selector shares full lineage verification.
- RUN-555 reproduced five accepted setting mutations. RUN-556 showed that direct training tried to open the temporary parent before rejecting changed settings. RUN-557 passed 14 lineage tests and RUN-558 passed 7 engine tests after the fix.
- RUN-561 archived config SHA-256 `60e90d27bd8aa0fcb6cc08e71bbdda98e7c6f6ca156fc737a2176052df5108ee` and created current config SHA-256 `6ef910cca039890916fb97217d2c4f934b11e3332c1376021c70797ad06e7842`. RUN-562 rebuilt notebook 15 with 22 cells.
- RUN-563 passed all 19 training tests. RUN-564 passed all 73 full-page tests. A second whole-branch review is still required before commit and push. Training remains unstarted; the previous disk/GPU preflight is historical and must be repeated before TRAIN-025.

- Whole-branch review found that removing the TRAIN-024 checkpoint fields could bypass fresh source-bound initialization. RUN-541 reproduced the gap in four lineage mutations and the engine guard. The tiny CPU fixture advanced four steps only inside its temporary test directory; no project training artifact was created. The regression fixture now stops at step zero. RUN-545 passed six focused checks after the lineage and engine guards were added.
- AI-024 records the selected code change and rationale. Fresh training still has not started. RUN-547 through RUN-550 refreshed the config and notebook after the engine change.

### Diagnosis raw output development setelah v4

- RUN-379 gagal karena diagnosis awal mencari `request.json` satu tingkat terlalu tinggi dari folder attempt. Kegagalan tercatat dan tidak dihapus. RUN-380 membaca struktur artifact yang benar, exit 0.
- Pada TRAIN-024, 12 halaman gagal terdiri dari enam keluarga nama usaha, masing-masing dengan style CSS biasa dan Tailwind. Output kedua style sering memperlihatkan kesalahan isi yang sama, sehingga bukti ini mengarah ke copy dan grounding model bersama, bukan masalah stylesheet.
- Contoh raw: `Kafe Bayalaya` menjadi `Kafe Baya` di navigasi; `Toko Yadilala` menjadi `Toko Yadila` di plan atau teks about; `Studio Mapurana` menjadi `Studio Studiominurana` atau `Studio Studioarcurana`; `Kursus Raramapu` menjadi `Kursus Rarau`; `Studio Pusanupu` menjadi `Studio Pusanu` di plan atau hero; `Toko Laditaya` menjadi `Toko Ladirefa` di plan.
- Pada beberapa pasangan style, retry memperbaiki judul plan tetapi kesalahan nama tetap muncul di section berikutnya. Retry yang ada sudah menyebut exact request identity, tetapi tidak menghapus semua kesalahan.
- Source facts dan nama tersedia di request. Kontrak plan dan section meminta model mengeluarkan beberapa fakta itu lagi, lalu validator menolak jika teks berbeda. Tidak ada perbaikan otomatis yang diterapkan.
- Diagnosis hanya membaca raw output TRAIN-024 dan request development yang telah digunakan untuk selection. Tidak ada data development yang ditambahkan ke train, tidak ada perubahan prompt, renderer, schema, validator, bobot, atau checkpoint. Final tetap tertutup.
- RUN-379 dan RUN-380 serta output lengkapnya tercatat di `LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md` dan `logs/RUN-*.txt`. Analisis interaksi dicatat di [AI-023](interaksi_llm/AI-023_2026-10-14.md).
- Rancangan lanjutan masih menunggu review. Bandingkan probe prompt copy eksplisit, curriculum copy identitas train-only, dan desain kontrak source-bound yang menghindari model menyalin ulang fakta identitas. Pertahankan gate 76/80, validator strict, split keluarga, serta final tertutup.

### Source-bound resume lineage guard

- Review branch menemukan resume TRAIN-026 belum diwajibkan berasal dari `checkpoints/TRAIN-025/last.pt` step 1800. Guard trainer sekarang membatasi run ID dan path, memverifikasi laporan TRAIN-025, konfigurasi beku, checksum checkpoint, dan state optimizer, scheduler, sampler, serta RNG sebelum membuat artifact run.
- Selektor kini memeriksa `resume_parent` dan `resume_parent_sha256` TRAIN-026 terhadap laporan dan checkpoint TRAIN-025 yang benar.
- RUN-565 mereproduksi celah sebelum perbaikan. RUN-566 lulus 21 regresi terarah. RUN-568 memperbarui config ke SHA-256 `0ee3332b0a3f19e42efe2ddb2eb6a1dbf69add7e84511323efeffa418bf78244`; RUN-569 membangun ulang notebook dengan 22 sel.
- RUN-570 lulus seluruh 20 training tests dan RUN-571 lulus seluruh 79 full-page tests. Semua tes memakai fixture terisolasi. TRAIN-025 belum berjalan, review branch terbaru, commit/push, dan preflight GPU/storage baru masih harus selesai lebih dahulu. Final tetap tertutup.
- RUN-572 mencatat audit punctuation yang masih menemukan dua status line di log CodeGraph lama. RUN-573 mengonfirmasi hasil bersih setelah kedua baris dinormalisasi.

### Fresh-run TRAIN-026 guard

- Review branch berikutnya menemukan bahwa pemanggil masih dapat memulai fresh run dengan ID TRAIN-026 dari TRAIN-024. Walaupun selector kemudian menolak lineage yang hilang, trainer seharusnya menolak konfigurasi itu sebelum membaca parent atau menyiapkan artifact.
- Engine kini hanya menerima fresh source-bound run sebagai TRAIN-025. TRAIN-026 tetap hanya dapat berjalan dengan exact resume dari checkpoint TRAIN-025 step 1.800. Fixture warm-start memakai ID TRAIN-025 yang canonical.
- RUN-576 mereproduksi celah. RUN-577 menemukan fixture warm-start ber-ID noncanonical; RUN-578 lulus 9 tes engine. RUN-579 lulus 21 tes training, RUN-580 lulus 79 tes full-page, dan RUN-585 mengulangi 79 tes setelah config dan notebook dibangun ulang.
- RUN-583 memperbarui config beku ke SHA-256 `8852971e852e3b4ce6a6b845c24c8629e65d2a5f699d30968c2f3ce61a353186`. RUN-584 membangun ulang notebook 15 dengan 22 sel tanpa menjalankan cell training atau evaluasi.
- TRAIN-025 belum berjalan. Review branch baru, commit/push, dan preflight GPU/storage segar tetap wajib sebelum training. Final tetap tertutup.


### TRAIN-025 runtime preflight and branch delivery

- The whole-branch review completed with no actionable findings. Commit `eb9d8d6` added the source-bound V5 training pipeline and was pushed to `origin/feature/pipeline-data-model-training`.
- RUN-589 performed a fresh, read-only preflight after push. PyTorch 2.14.1+cu130 on CUDA 13.0 detected the RTX 5070, and a CUDA BF16 operation completed with finite output. The frozen V5 config and TRAIN-024 step-3600 parent lineage passed verification. The TRAIN-025 output paths were absent.
- Disk free space was 17,301,737,472 bytes. The frozen 15 GiB reserve plus estimated checkpoint allowance required 17,222,975,488 bytes, leaving 78,761,984 bytes of headroom. This passes the engine gate with a narrow margin, so disk space must be monitored during training.
- The GPU snapshot reported 0 percent utilization, 3,367 / 12,227 MiB used, and 41 C. Other desktop processes were left untouched. Final and test data remain sealed.
- Preflight passed. TRAIN-025 launch is the next action, using the frozen V5 config and the approved stop at step 1,800. No training update has occurred yet at this log entry.


### TRAIN-025 training launch

- RUN-590 records the approved fresh run from the verified TRAIN-024 parent, using frozen config SHA-256 `8852971e852e3b4ce6a6b845c24c8629e65d2a5f699d30968c2f3ce61a353186` and stopping at step 1,800.
- RUN-589 passed the fresh GPU and storage preflight. Its headroom was about 75 MiB, so monitor free storage during the run.
- At this log entry, TRAIN-025 launch is pending. TRAIN-026 and all development/final evaluation remain closed.
