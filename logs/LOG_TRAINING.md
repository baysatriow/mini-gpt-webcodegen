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
