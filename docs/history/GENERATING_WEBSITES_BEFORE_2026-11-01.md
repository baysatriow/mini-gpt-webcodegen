# Arsip sebelum penataan 1 November 2026

Snapshot historis dari docs/GENERATING_WEBSITES.md. Status terkini ada di [README utama](../../README.md). Tautan relatif disesuaikan dengan lokasi arsip.

# Menghasilkan website dari model proyek

Alur executable tersedia melalui CLI: prompt Indonesia -> Mini GPT proyek -> PageSpec JSON mentah -> schema/link/kontrak prompt -> renderer -> folder website. Antarmuka aplikasi generator akan dibuat pada tahap akhir. Laporan terkini: [gerbang final AI-013](../../reports/FINAL_GATE_2026-10-13.md). Runtime terbaru TRAIN-015 best dan command terdapat pada bagian AI-013 di akhir panduan. Bagian awal berikut adalah riwayat AI-011.

## Persiapan

Gunakan `.venv` proyek dengan CUDA/RTX 5070. Raw data, BPE dan checkpoint tetap lokal; clone repo saja tidak menyediakan bobot terlatih. Untuk Tailwind, pasang dependency terkunci:

```powershell
npm ci --prefix tooling/tailwind
```

Compiler mengikuti [panduan resmi Tailwind CLI](https://tailwindcss.com/docs/installation/tailwind-cli). Versi terkunci 4.3.3. HTML dipindai saat build, stylesheet disimpan lokal. CSS biasa tidak membutuhkan dependency Node.

## Format prompt yang didukung

Contoh lengkap: [Studio Cakrawala](../../examples/prompts/studio_cakrawala.txt). Nyatakan nama, CSS biasa/Tailwind, satu aksen yang dilatih, font, teks utama, komponen dan interaksi secara eksplisit. Format kalimat sengaja dibatasi agar kemampuan model kecil dapat diperiksa.

```text
Buat website Indonesia bernama Studio Cakrawala menggunakan CSS biasa. Aksen #2563eb, latar putih, teks #111827 dan font sans. Tampilkan navbar Beranda, hero centered dengan judul nama situs, dan footer nama situs. Teks utama: Temukan layanan pilihan kami. Gunakan menu responsif. Tambahkan dua kartu layanan: Desain dan Konsultasi. Tambahkan form Hubungi Kami, kolom Nama, Email dan Pesan, tombol Kirim, serta validasi form.
```

| Opsi | Kontrak yang dilatih |
| --- | --- |
| Style | CSS biasa, Tailwind |
| Font | sans, serif, mono |
| Aksen | #2563eb, #10b981, #f59e0b, #8b5cf6, #ef4444, #06b6d4 |
| Latar/teks | Putih, #111827 |
| Komponen | navbar, hero, profil teks, kartu layanan, paket harga, testimoni contoh, form kontak, footer |
| Interaksi | menu responsif, accordion, tabs, filter, modal, validasi form |
| Harga/testimonial | Contoh fiktif eksplisit dari kontrak, bukan informasi bisnis nyata |

Layout utama centered, ID section dan pola isi kartu/form mengikuti kontrak katalog. Kalimat/nama lain dapat gagal; validator akan menolak ketidakcocokan yang terdeteksi. Validator ini tidak menilai fakta bisnis, kualitas desain atau bahasa bebas secara umum.

## Menjalankan generasi

Gunakan checkpoint dengan laporan final sintetis yang lulus dan SHA yang cocok. Isi TRAIN_ID dengan ID checkpoint yang dipilih di laporan terkini. Gunakan folder baru setiap run agar raw output terdahulu tetap tersimpan.

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label generate_website -- .\.venv\Scripts\python.exe -m qa.generate_website --checkpoint checkpoints/TRAIN_ID/best.pt --evidence reports/training/TRAIN_ID-FINAL_curriculum_evaluation.json --prompt-file examples/prompts/studio_cakrawala.txt --output outputs/generated_websites/my-first-website
```

Checkpoint dipilih berdasarkan validation loss. Final menguji gate sebelum training, bukan untuk memperbaiki checkpoint. Gate production human-reviewed tetap menolak checkpoint sintetis; rute demo CLI menyatakan provenance tersebut.

### Contoh aktual dalam mode development

TRAIN-012 belum melewati overall quality gate43/48. Untuk penelitian, flag eksplisit `--development` mengizinkan generasi dengan checkpoint yang sudah dievaluasi dan SHA cocok. **Validasi per output tetap wajib**, termasuk nama/props/teks/tema/interaksi. Output salah tetap ditolak, tidak dirender. Flag ini tidak mengubah skor atau status gagal eksperimen, dan tidak memberi persetujuan produksi.

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label research_website -- .\.venv\Scripts\python.exe -m qa.generate_website --checkpoint checkpoints/TRAIN-012/best.pt --evidence reports/training/TRAIN-012-FINAL_curriculum_evaluation.json --development --prompt-file examples/prompts/studio_cakrawala.txt --output outputs/generated_websites/new-cakrawala-run
```

[Dua snapshot yang diterima](../../examples/generated/AI-011/index.html) bisa dibuka tanpa checkpoint. Keduanya menggunakan nama yang tidak ada sebagai title utuh train. Ini demonstrasi yang dipilih, bukan benchmark generalisasi baru; kegagalan Senandika ikut dicatat.

## Membaca output

- `generation.json`: status accepted/rejected, SHA model/prompt/evidence, schema errors, kontrak yang diperiksa dan stop reason.
- `raw_output.txt`: keluaran model asli tanpa repair, termasuk bila ditolak.
- `prompt.txt`: input run yang sebenarnya.
- Jika diterima: `page_spec.json`, `index.html`, `styles.css`, `app.js`.
- Exit 2 berarti ditolak. Jangan menyatakan JSON valid sebagai keberhasilan bila isi berbeda dari permintaan.

Buka index.html secara lokal untuk preview. Form memvalidasi contoh di perangkat tanpa mengirim data. Semua isi model di-escape sebelum menjadi HTML. JavaScript dibentuk renderer dari katalog, bukan script bebas dari model.

## Mengulangi training curriculum

Setiap revision dataset yang sudah ada dipertahankan. Preparation memakai seed tetap dan menolak menimpa folder. Reproduksi revision v3 dari mesin baru:

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label prepare_curriculum -- .\.venv\Scripts\python.exe -m src.data.curriculum --revision v3 --serialization appearance_before_sections
.\.venv\Scripts\python.exe qa/run_logged.py --label train_curriculum -- .\.venv\Scripts\python.exe -m qa.train_curriculum --config configs/training_curriculum_v3.json --initialize-from checkpoints/TRAIN-004-VERIFIED/best.pt
```

Parent pretraining dan tokenizer HF harus direproduksi/disediakan terlebih dahulu sesuai [panduan training](../TRAINING_GUIDE.md). Hasil penuh run aktual ada pada [log training](../../logs/LOG_TRAINING.md). Jangan menganggap perintah reproduksi sebagai hasil training baru yang sudah dijalankan.
# Runtime terbaru, AI-013

TRAIN-015 best telah dipilih sebelum evaluasi final dan memenuhi gerbang kontrak terkontrol: 48/48 JSON valid, 44/48 sesuai persis. [Laporan final](../../reports/FINAL_GATE_2026-10-13.md), [gallery](../../examples/generated/AI-013/index.html), dan [ZIP](../../examples/generated/AI-013/websites.zip). Ini belum kemampuan prompt bebas atau bukti browser. Empat output dengan nama salah tidak diekspor.

CLI memerlukan checkpoint dan evidence secara eksplisit. Gunakan keduanya dari run yang sama. Contoh berikut menulis folder baru dan tetap memvalidasi setiap output, walaupun gerbang model secara keseluruhan lulus:

```powershell
.\.venv\Scripts\python.exe -m qa.run_logged --label generate_selected_model -- .venv/Scripts/python.exe -m qa.generate_website --checkpoint checkpoints/TRAIN-015/best.pt --evidence reports/training/TRAIN-015-FINAL_curriculum_evaluation.json --prompt-file outputs/generated_websites/kafe-senandika-v1/prompt.txt --output outputs/generated_websites/senandika-new-request
```

Prompt tersebut adalah contoh development yang pernah gagal. RUN-185 mengukur prompt yang sama tanpa `--development` dan hasilnya accepted pada folder `outputs/generated_websites/kafe-senandika-v2`. Model tidak memperbaiki JSON atau mengganti nama sesudah decoding. Jika output gagal kontrak, CLI menyimpan prompt/raw/error dan tidak menghasilkan HTML.

Bagian berikut merekam runtime serta keterbatasan sebelum TRAIN-015. Notebook 08 mencatat fase development dan notebook 09 mencatat final yang sudah selesai. Final v5/v6 ini sudah terpakai; eksperimen baru membutuhkan holdout independen.
