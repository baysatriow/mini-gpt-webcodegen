# Penyelarasan Mini GPT untuk menghasilkan PageSpec

Tujuan pengguna: lanjutkan pengembangan sampai keluaran yang diharapkan tersedia. Tahap ini melanjutkan pipeline yang sudah disetujui, memakai model proyek dan format PageSpec yang sama. Aplikasi tetap tahap akhir. Tidak mengganti model dengan pretrained LLM.

## Diagnosis dan hipotesis

RUN-103 memeriksa train/validation saja: prefix training/generation identik, namun model 40 update sering memprediksi underscore sebelum JSON. RUN-104 memakai budget SFT 400 update yang sudah ada. Train loss mendekati nol, validation memburuk: empat contoh terlalu mudah dihafal. RUN-105 memeriksa last checkpoint untuk diagnosis fit, bukan memilih checkpoint final dari train/test.

## Pendekatan eksperimen berikutnya

Tambahkan latihan sintetis berbasis kontrak komponen: prompt Indonesia menyebut nama, style, warna, font, teks, komponen dan interaksi. Target dibuat deterministik dan divalidasi schema/mask/context. Isi bisnis dan testimoni bersifat fiktif. Labelnya `programmatic_contract`, tidak ada klaim human-reviewed. Jalur ini terpisah dari 12 reviewed annotations dan manifest/checkpoint historis HF; gate produksi reviewed tidak dilonggarkan.

Corpus berisi 288 nama fiktif, 12 resep komponen, dua style dan dua pilihan menu. Nama dibagi menjadi keluarga train/validation/test yang tidak beririsan. Resep komponen dipakai bersama antar partition: eksperimen mengukur transfer ke kombinasi nama baru, bukan generalisasi layout-template baru. Tidak memindahkan contoh test pilot lama ke train.

Training memakai engine, model, BPE dan parent pretraining proyek yang sama. Config tetap 2.400 update, batch 4 x accumulation 2, BF16, LR 3e-4 ke 3e-5. Model/optimizer dapat stop/resume pada budget tersebut. Best dipilih dari validation token loss. Pemeriksaan generasi development boleh mengarahkan eksperimen berikutnya; final suite 48 prompt dikunci saat preparation, sebelum training.

## Kriteria keberhasilan eksperimen

- Keluaran autoregresif mentah, tanpa repair atau memaksa token pembuka.
- Schema valid minimal 95% dan target kontrak tepat minimal 90% pada suite final sintetis.
- Tautan section harus tersedia; EOS/context/token limit dilaporkan.
- Hasil train, development, final sintetis dan human-reviewed pilot dibedakan.
- Klaim kemampuan dibatasi pada katalog PageSpec dan pola prompt yang dilatih. Prompt bebas, kualitas visual/browser dan aplikasi belum dibuktikan oleh skor ini.

## Artifact dan log

`src/data/curriculum.py`, `qa/train_curriculum.py` dan `qa/evaluate_curriculum.py` menyediakan rute eksperimen; data/cache/checkpoint lokal, manifest/laporan kecil di Git. Setiap eksekusi melalui RUN logger, setiap training memakai TRAIN baru. Notebook tahap lanjut menampilkan diagnosis, distribusi, kurva, prompt, raw output dan kesimpulan. Commit/push tanpa Co-Authored-By.
