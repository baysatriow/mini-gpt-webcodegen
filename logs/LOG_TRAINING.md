# Log Training Mini GPT WebCodeGen

Catat setiap percobaan pretraining, penyelarasan instruksi, resume, atau evaluasi training. Run gagal, crash, OOM, dihentikan, atau hasil buruk tetap dicatat. Setiap resume mendapat TRAIN ID baru dan merujuk percobaan asal.

## Status awal

- Training Mini GPT belum dijalankan.
- Model yang direncanakan mulai dari bobot acak, tanpa bobot model pralatih.
- VENV lokal: CPython 3.11.9, PyTorch 2.14.1+cu130, runtime CUDA 13.0, RTX 5070 sekitar 12 GB VRAM.
- Dataset proyek belum dikurasi, dinormalisasi, atau dikonversi ke target JSON.
- RUN-017 mencatat preflight repository dan RUN-018 memverifikasi commit/push planning. RUN-019 menjadi nomor run berikutnya untuk pipeline atau eksperimen.
- TRAIN-001 adalah slot pertama yang menunggu pipeline data dan planning.
- Ukuran model, jumlah token, tokenizer vocabulary, panjang konteks, batch, LR, scheduler, dan total step belum ditentukan.

## Indeks

| TRAIN ID | Tahap | Status | RUN IDs | Commit | Hasil |
| --- | --- | --- | --- | --- | --- |
| TRAIN-001 | Menunggu data dan planning | Belum dijalankan | Belum ada | Belum ada | Belum ada model, command, atau metrik |

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
