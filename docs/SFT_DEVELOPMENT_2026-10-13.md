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

## Temuan development v1 dan kontrol v2

TRAIN-008 berhenti terencana pada step 800, lalu TRAIN-009 resume dengan config/budget yang sama sampai 2.400. Pada 24 development prompts: step 800 menghasilkan 22 valid / 0 exact; step 2.400 menghasilkan 24 valid / 1 exact. Nama/style/sections/interactions semuanya tepat 24/24; tema hanya tepat 1/24. Final suite belum dibuka. Loss token 0,0068 tidak merangkum ketepatan atribut penting yang hanya sedikit token.

Hipotesis: theme/font/color berada setelah ratusan token section pada target urutan alfabet dan belum dikondisikan dengan baik dari prompt. Kontrol v2 memindahkan style_mode/theme sebelum sections pada top-level serialization. Nested key order, makna seluruh target, semua prompt, family allocation, tokenizer, parent, budget dan hyperparameters dipertahankan. Preparation membuktikan SHA JSONL train/validation/test dan final suite sama; hanya token cache/serialization berubah. Belum menyatakan hipotesis terbukti sebelum generasi v2 diperiksa.

## Hasil kontrol v2 dan masalah penyalinan nama

TRAIN-010 menyelesaikan 2.400 update: development 24/24 valid dan exact, final terkunci 48/48 valid dan exact. Hasil konsisten dengan manfaat serialization baru pada corpus terkontrol ini. Percobaan ini tidak membuktikan sebab tunggal berlaku pada model/data lain. Semua generasi berhenti pada EOS tanpa repair. Final target-token loss 0,00001699, pada corpus yang berbeda dari baseline kode dan reviewed pilot.

RUN-120 mencoba nama Studio Cakrawala yang belum ada dalam lexicon 24 nama corpus. JSON valid, tetapi model menghasilkan Studio Cahaya. Status generated lama pada file itu hanya menyatakan validasi schema, bukan ketepatan nama. Probe ini gagal terhadap kebutuhan pengguna dan dipertahankan. Model v2 telah mempelajari kombinasi nama yang diketahui, belum penyalinan nama terbuka.

## Eksperimen lexical copying v3

RUN-121 menyiapkan revision baru tanpa menimpa v1/v2: 2.400 nama fiktif, masing-masing enam variasi resep/style/menu. Split 1.920/240/240 keluarga, 11.520/1.440/1.440 contoh. String brand utuh tidak beririsan; subword/suku kata dan resep komponen dipakai bersama. Teks utama memuat variasi komposisi kalimat Indonesia. Nama Cakrawala dikecualikan dari corpus. Probe yang sudah dibaca tetap development, bukan benchmark independen.

Budget v3 ditetapkan sebelum training/final baru: 4.800 update, warmup 240, validation/checkpoint 400, batch 4 x accumulation 2, BF16, LR 3e-4 ke 3e-5. Parent tetap pretraining proyek dari bobot acak, BPE tidak berubah. Serialization appearance_before_sections dipertahankan. Final 48 prompt baru dikunci sebelum training, threshold tetap 95% schema / 90% exact. Tidak menggunakan final v2 untuk memilih checkpoint v3.

## Validasi dan ekspor website

Renderer menerjemahkan JSON asli model menjadi HTML, CSS biasa atau Tailwind 4.3.3 lokal, dan JavaScript dari enam interaksi katalog. Tidak mengganti output dengan target. Tailwind dipasang dari npm resmi menggunakan package-lock dan dikompilasi menjadi stylesheet lokal, tanpa CDN saat preview. Form hanya demo validasi lokal, belum mengirim pesan.

Validasi prompt terpisah memeriksa nama di title/navbar/hero/footer, teks utama, theme, komponen, field form/harga contoh, dan target interaksi pada format yang didukung. Jika gagal, raw output tetap disimpan tetapi website ditolak. Validasi tidak memperbaiki output model. Prompt bebas di luar format ini belum didukung.

RUN-118 gagal karena path relatif saat ekspor, folder parsial dipertahankan. RUN-119 berhasil mengekspor 48 contoh v2 ke folder baru. Upaya membuka galeri melalui alat browser ditolak oleh kebijakan protokol file lokal. Tidak menjalankan workaround; tidak ada klaim visual/browser atau interaksi end-to-end dari pemeriksaan file saja.

## Diagnosis subword dan continuation v4

TRAIN-011 selesai 4.800 update, development 24/24 schema valid tetapi exact 20/24. RUN-127 menunjukkan empat kasus salah berasal dari keluarga Kursus Workstaralasa; kesalahan nama merambat dari navbar ke hero/footer/title. RUN-128 mengukur vocabulary penyalinan: token sta (ID 776) nol kemunculan pada title train, sedangkan seluruh token lain nama itu pernah muncul. Ini bukti gap exposure pada subword, bukan alasan menyatakan seluruh JSON sesuai hanya karena loss rendah.

V4 menambahkan latihan copy train-only dari vocabulary BPE yang sebelumnya dilatih pada train pretraining. Kandidat alphabetic ASCII maksimal enam karakter ditempatkan pada nama fiktif, tokenisasi diperiksa untuk exposure token yang dimaksud. Target tetap PageSpec, tidak mengganti tokenizer. Semua train v3 tetap ada; validation/test/final v3 yang belum dibaca dipertahankan identik. Keluarga train tambahan tidak beririsan dengan heldout. Ini memperluas ragam subword, bukan menyisipkan nama atau label dari final.

Continuation memulai dari best validation TRAIN-011 milik proyek sendiri, dengan optimizer baru dan schedule 4.800 update, LR 1e-4 ke 1e-5, warmup 120. Arsitektur 14,19 juta parameter tetap. Initial weights parent SFT sintetis disimpan sebagai curriculum_parent terpisah; pretraining_parent asli tetap phase pretrain dengan SHA/fingerprint yang sama. Jalur ini hanya menerima checkpoint synthetic_curriculum proyek dengan ancestry/tokenizer/corpus/model yang cocok. Gate production reviewed tetap menolak checkpoint sintetis.

Final tidak dibuka saat v3 gagal development. Threshold dan file suite tetap, tidak menurunkan kriteria atau memilih kasus final yang menguntungkan. Counter update v4 adalah tahap baru, bukan optimizer resume v3; jumlah token/waktu tiap tahap dilaporkan terpisah.
