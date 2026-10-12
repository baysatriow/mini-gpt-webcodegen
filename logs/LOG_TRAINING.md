# Log Training Mini GPT WebCodeGen

Catat setiap percobaan pretraining, penyelarasan instruksi, resume, atau evaluasi training. Run gagal, crash, OOM, dihentikan, atau hasil buruk tetap dicatat. Setiap resume mendapat TRAIN ID baru dan merujuk percobaan asal.

## Status awal

- Training Mini GPT belum dijalankan.
- Model yang direncanakan mulai dari bobot acak, tanpa bobot model pralatih.
- VENV lokal: CPython 3.11.9, PyTorch 2.14.1+cu130, runtime CUDA 13.0, RTX 5070 sekitar 12 GB VRAM.
- Download 55.000 source selesai. Corpus pretraining 51.211 unik sudah displit, BPE train-only 8.192 dan token cache tersedia; SFT produksi menunggu anotasi reviewed.
- RUN-031 download; RUN-045 preparation final; RUN-046 integrity/GPU batch; RUN-047 reuse. Nomor RUN berikutnya mengikuti ID tertinggi di logs/RUN-*.txt.
- Review data: empat temuan diperbaiki. RUN-050 lulus 37 tests; RUN-051 memverifikasi dan mempertahankan tokenizer/cache; RUN-052 integrity/CUDA batch lulus. SFT wajib mengikuti family partition pretraining dan menunggu review produksi. Temuan/ruling ada pada reports/REVIEW_PIPELINE_2026-10-12.md serta logs/PIPELINE_PROGRESS.md.
- TRAIN-001 adalah slot pertama yang menunggu Mini GPT dan profiling GPU. Planning telah disetujui.
- Token train 19.038.770, vocabulary 8.192, blok data 1.024. Dimensi model, batch, LR, scheduler, precision dan total step dipilih setelah profiling GPU; blok data dapat diregenerasi jika berubah.

## Indeks

| TRAIN ID | Tahap | Status | RUN IDs | Commit | Hasil |
| --- | --- | --- | --- | --- | --- |
| TRAIN-001 | GPU profiling, bobot dibuang | Selesai | RUN-056 | HEAD dasar b81cc61, working tree Task 6 | 14.186.496 parameter; batch 1/2/4 finite; batch 4 peak allocated 2.189.641.216 bytes |

## TRAIN-001: Profiling kandidat Mini GPT

- Model: random init, 6 layer / 6 head / embedding 384 / context 1024 / vocab 8192 / tied embeddings / dropout 0,1. Parameter terukur 14.186.496.
- Command: `python qa/profile_minigpt.py --run-id TRAIN-001`, output RUN-056 dan `outputs/metrics/TRAIN-001_profile.json` lokal.
- RTX 5070, PyTorch 2.14.1+cu130, BF16, seed 42, AdamW LR 0,0003, grad clip 1. Empat optimizer update per kandidat pada batch train pertama yang sama; satu warmup, tiga step timing. Bobot kandidat tidak menjadi checkpoint baseline.
- Batch 1: 0,0200 detik/step; allocated 761.374.208 bytes. Batch 2: 0,0272 detik/step; allocated 1.238.009.344 bytes. Batch 4: 0,0524 detik/step, 78.170,8 token/detik; allocated 2.189.641.216 / reserved 2.424.307.712 bytes.
- Semua loss/grad norm finite. Tidak ada OOM. Warning konversi loss Tensor ke scalar direkam; pencatatan berikutnya memakai detach. Angka ini profiling batch berulang, bukan throughput end-to-end baseline.
- Keputusan: microbatch 4 dengan accumulation 4 sebagai titik awal baseline, effective batch 16 blok / 16.384 token maksimum per update. Ukur lagi VRAM/throughput selama run aktual.
- Tidak ada validation/test, generation quality, atau PageSpec evaluation pada profiling ini. Profiling tidak membuktikan model sudah mempelajari dataset.

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
