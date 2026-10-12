# Log Training Mini GPT WebCodeGen

Catat setiap percobaan pretraining, penyelarasan instruksi, resume, atau evaluasi training. Run gagal, crash, OOM, dihentikan, atau hasil buruk tetap dicatat. Setiap resume mendapat TRAIN ID baru dan merujuk percobaan asal.

## Status awal

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
