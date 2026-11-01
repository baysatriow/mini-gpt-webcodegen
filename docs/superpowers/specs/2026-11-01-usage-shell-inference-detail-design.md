# Spesifikasi Rework Usage, Shell, dan Detail Inference

Status: draf untuk persetujuan pengguna

Tanggal: 1 November 2026

Produk: WebCraft by VibeStack

Sasaran pengguna: pemilik dan tim VibeStack

## 1. Tujuan

Membuat Usage sebagai meja audit untuk satu proses generation. Pengguna dapat menelusuri input yang dikirim, fakta usaha yang dikonfirmasi, tahap proses, hasil, source yang diterima renderer, dan telemetry GPU yang benar-benar tercatat.

Rework mencakup shell navigasi bersama agar sidebar tetap tersedia di Usage, serta detail inference per run. Alur chat, validasi, inference, rendering, preview, unduhan, dan login tetap memakai kontrak yang ada.

Spesifikasi ini melanjutkan keputusan dalam 2026-10-26-usages-audit-design.md. Bagian penyimpanan prompt dan fakta terkonfirmasi mengganti keputusan lama yang melarang penyimpanannya. Ketentuan telemetry, autentikasi, dan retensi 90 hari tetap berlaku selama tidak bertentangan dengan spesifikasi ini.

## 2. Keputusan yang sudah disetujui

- Rework visual memakai comp-first.
- Comp yang dipilih adalah Meja Perbandingan, option 1 dari 3, pada apps/web/.impeccable/mocks/usage-meja-perbandingan.png.
- Arah visual mengikuti challenger reference yang sudah disetujui: kertas hangat, panel putih, aksi hijau pine, aksen terracotta, garis tipis, dan tipografi sans yang mudah dibaca.
- Sidebar bersama tetap tersedia pada Chat dan Usage. Pada layar kecil, sidebar dibuka melalui navigation drawer.
- Prompt dan fakta bisnis yang telah dikonfirmasi disimpan secara lokal selama 90 hari.
- Token extractor tidak disimpan.
- Source HTML, CSS, dan JavaScript tidak disalin ke database Usage. Source hanya dibaca dari endpoint artefak generation yang sudah ada dan diterima renderer.
- Data Usage tetap lokal dan mengikuti kebijakan akses aplikasi yang ada. Tidak ada endpoint publik baru.
- Kode hasil ditampilkan sebagai teks mentah yang tidak dieksekusi di halaman Usage.

## 3. Bukti source dan kondisi saat spesifikasi dibuat

- Route /usage saat ini merender UsageDashboard sendiri, di luar ChatShell. Karena itu navigasi sidebar Chat tidak ikut tampil di Usage.
- HistorySidebar saat ini menerima daftar sesi dan callback dari ChatShell. Riwayat percakapan disimpan di localStorage browser.
- UsageDashboard saat ini menampilkan ringkasan GPU, snapshot GPU saat ini, daftar audit, filter periode/status/tahap, pagination, event, dan sample GPU. Detail dibuka inline pada baris.
- UsageDetailResponse saat ini hanya mengembalikan record, events, dan samples. Prompt dan fakta belum menjadi bagian dari kontrak Usage.
- Middleware audit membuat record sebelum validasi body, tanpa membaca request body. Ia tetap menjadi sumber pencatatan aman untuk request yang ditolak sebelum mencapai handler bertipe.
- GenerationRequest berisi prompt, draft, dan extraction_token opsional. Draft memuat business_facts dan fitur lainnya. Hanya prompt dan fakta terkonfirmasi yang dibutuhkan oleh spesifikasi ini.
- Database SQLite memakai allowlist kolom ketat, WAL, dan retensi 90 hari. Pembuatan tabel saat ini belum cukup untuk menambah kolom ke database lama, sehingga perubahan skema memerlukan migrasi aditif yang idempotent.
- GET /api/v1/generations/{generation_id}/source mengembalikan tiga file renderer yang diterima: index.html, styles.css, dan app.js. Endpoint sudah memasang Cache-Control no-store dan menolak artefak yang tidak diterima.
- Comp Meja Perbandingan berukuran 1586 x 992. Pengukuran comp tersimpan di .impeccable/build/spec.json dengan warnings kosong dan uncoveredInkCells kosong. Nama usaha, ID, jumlah run, durasi, status, nilai GPU, dan kode yang tampak di comp adalah contoh sintetis, bukan data aplikasi.

## 4. Ruang lingkup

### Termasuk

- Menampilkan sidebar bersama pada Chat dan Usage tanpa memutus navigasi percakapan.
- Mengganti halaman Usage menjadi workspace daftar run dan detail terpilih.
- Menampilkan prompt dan fakta terkonfirmasi pada detail Usage.
- Menampilkan tahapan run dalam satu rail ringkas dan menyediakan rincian event.
- Menampilkan source HTML, CSS, dan JavaScript yang diterima renderer, beserta salin, unduh per file, dan unduh ZIP melalui endpoint yang tersedia.
- Mempertahankan ringkasan dan snapshot GPU yang sudah ada serta memperjelas perbedaan data global, snapshot saat ini, dan sample per run.
- Menambahkan pencarian server-side pada prompt dan fakta terkonfirmasi.
- Menambah migrasi SQLite aditif untuk prompt dan fakta terkonfirmasi.
- Menyediakan keadaan loading, kosong, gagal, unavailable, dan data lama tanpa detail input.

### Tidak termasuk

- Perubahan model, checkpoint, training, extractor, prompt generation, kontrak PageSpec, renderer, preview, atau logika unduhan.
- Menjalankan inference saat membuka Usage, berpindah halaman, mencari, atau membaca source.
- Menyimpan extraction_token, exception mentah, stack trace, path absolut, atau source code di database Usage.
- Menjalankan source dalam iframe atau preview dari halaman Usage.
- Mengirim prompt, fakta, atau telemetry ke layanan eksternal.
- Mengubah login menjadi sistem akun multi-pengguna.
- Mengubah akses, isi, atau aturan retensi data test dan final.

## 5. Struktur layar dan interaksi

### 5.1 Shell bersama

- Gunakan satu sidebar WebCraft by VibeStack pada Chat dan Usage.
- Sidebar memuat identitas produk, tombol Chat Baru, riwayat percakapan, tautan Penggunaan, dan Keluar jika autentikasi aplikasi diwajibkan.
- Pada Chat, aksi riwayat harus mempertahankan perilaku saat ini: membuat sesi, memilih sesi, menghapus sesi, dan memperbarui sesi lokal.
- Pada Usage, tautan riwayat membuka percakapan yang dipilih tanpa membuat atau menjalankan generation. Usage menjadi item navigasi aktif.
- Sidebar desktop memiliki lebar tetap sekitar 244 sampai 260 CSS px. Pada lebar tablet dan ponsel, sidebar menjadi drawer yang dapat dibuka dari tombol navigasi dengan label aksesibel.
- Chat tidak dipindahkan ke komponen yang mengubah reducer atau format localStorage kecuali diperlukan untuk berbagi shell. Jika state harus dipindah, format penyimpanan dan semua interaksi Chat tetap kompatibel.
- Retensi 90 hari berlaku untuk database Usage. Penyimpanan riwayat Chat yang sudah ada di localStorage adalah mekanisme terpisah dan tidak diubah dalam scope ini. Usage tidak membuat salinan prompt atau source ke localStorage.

### 5.2 Workspace Usage desktop

Pada lebar desktop yang cukup, halaman menggunakan tiga area:

1. Sidebar bersama.
2. Daftar run dengan judul, pencarian, filter, status, waktu, dan durasi.
3. Detail run terpilih.

Detail mengikuti comp yang disetujui:

- Header berisi judul run, ID singkat, waktu, status, dan aksi salin ID.
- Panel bukti berisi prompt dan fakta terkonfirmasi.
- Satu rail vertikal dengan lima tahap yang dikelompokkan dari event internal.
- Panel source berisi tab index.html, styles.css, dan app.js, serta aksi raw, salin, unduh file, dan unduh ZIP.
- Ringkasan GPU terletak di bawah detail dan secara eksplisit bertanda metrik milik run terpilih.

KPI periode dan snapshot GPU saat ini tetap tersedia pada bagian ringkasan halaman. Gunakan bentuk kompak agar tidak mengambil ruang dari daftar dan detail. Jangan memasukkan nilai biaya atau waktu antrean dari comp karena API saat ini tidak menyediakannya.

### 5.3 Daftar run

- Muat 25 record per halaman dengan cursor yang sudah digunakan API.
- Setiap item menampilkan judul ringkas dari prompt, waktu lokal yang jelas, status, durasi jika tersedia, dan tahap akhir atau kode kegagalan yang aman.
- Judul item dibentuk dari prompt dengan whitespace diringkas dan panjang maksimum 80 karakter. Jika prompt tidak tersedia, tampilkan label aman seperti Request ditolak sebelum input terbaca.
- Sediakan pencarian prompt dan fakta, filter periode 24 jam, 7 hari, dan 30 hari, filter status, serta filter tahap.
- Pencarian dan filter mereset cursor ke halaman pertama. Pengguna dapat memuat halaman berikutnya tanpa kehilangan filter.
- Memilih satu item memuat detailnya. Pilihan run terpilih ditandai dengan bentuk dan teks status, bukan warna saja.
- Tidak ada data contoh yang dipakai untuk mengisi daftar. Bila belum ada record, tampilkan keadaan kosong dan tautan ke Chat.

### 5.4 Detail input dan fakta

- Tampilkan prompt yang disimpan persis sebagaimana diterima, dengan line wrap dan tombol salin.
- Tampilkan hanya fakta yang memiliki bukti konfirmasi pengguna. Jangan menyimpulkan fakta dari nama field atau menandai nilai yang belum dikonfirmasi sebagai fakta.
- Objek fakta ditampilkan sebagai pasangan label dan nilai yang mudah dipindai. Nilai nested hanya ditampilkan jika bagian tersebut punya penanda konfirmasi yang eksplisit.
- Untuk request yang ditolak sebelum body berhasil divalidasi, tampilkan bahwa prompt dan fakta tidak tersedia, bukan nilai kosong yang tampak seperti telah diperiksa.
- Untuk record sebelum perubahan skema, tampilkan bahwa detail input belum tersedia untuk run lama.

### 5.5 Rail tahap

Tampilkan tepat satu rail dengan lima label:

1. Request: request_received dan request_validation.
2. Validasi: intake_validation dan output_validation.
3. Inference: model_load dan inference.
4. Render: render_export.
5. Selesai: persist_result dan completed.

Status visual berasal dari events dan record aktual. Tahap yang gagal ditandai dengan status serta kode kegagalan aman. Tahap yang belum dimulai tetap pending. Server restart ditampilkan sebagai alasan terputus di detail event, tidak ditambahkan sebagai tahap visual keenam.

Durasi tahap hanya ditampilkan bila dapat dihitung dari timestamp event yang tersedia. Bila event tidak ada, tampilkan Tidak tersedia dan jangan membentuk estimasi.

### 5.6 Panel source mentah

- Baca source hanya setelah detail run dipilih dan source panel dibuka, menggunakan endpoint source yang sudah ada.
- Tampilkan masing-masing file dengan teks escaped pada elemen pre/code. Jangan gunakan dangerouslySetInnerHTML, iframe, atau evaluator JavaScript.
- Salin dan unduh mempertahankan byte/string source yang diterima API.
- Aksi unduh ZIP memakai endpoint ZIP existing.
- API yang menolak artefak harus menghasilkan keadaan source unavailable dengan alasan ringkas. Jangan tampilkan output parsial atau raw output model.
- Pada run gagal, source hanya ditampilkan bila endpoint artefak secara eksplisit mengembalikan source yang diterima. generation_id saja tidak cukup sebagai bukti source valid.
- Gunakan cache no-store dan jangan memasukkan source ke database audit atau localStorage Usage.

### 5.7 GPU dan ringkasan

- Bedakan tiga jenis data dengan label yang selalu terlihat:
  - Snapshot sekarang: keadaan perangkat saat halaman meminta data.
  - Ringkasan periode: statistik sample GPU yang dikumpulkan selama inference dalam rentang waktu.
  - Detail run: sample dan peak milik satu generation.
- Tampilkan jumlah sample dan cakupan run saat menunjukkan statistik agregat. Sample nvidia-smi adalah statistik seluruh perangkat dan dapat mencakup aplikasi lain.
- Tampilkan metrik proses PyTorch terpisah dari pemakaian memori total perangkat.
- Jika metrik null, telemetry gagal, atau tidak ada inference dalam rentang terpilih, tampilkan status unavailable atau belum ada data. Nilai tersebut tidak boleh divisualkan sebagai nol.
- Hanya tampilkan metrik yang dikembalikan API. Jangan menampilkan estimasi biaya, waktu antrean, model, atau GPU yang dibuat dari nilai comp.

## 6. Penyimpanan, API, dan privasi

### 6.1 Data yang disimpan

Tambahkan dua field pada record Usage:

- prompt: teks request generation yang dikirim pengguna.
- confirmed_facts: daftar kecil fakta bisnis yang memiliki bukti konfirmasi eksplisit.

Jangan menyimpan body request utuh. Jangan menyimpan extraction_token, requested_features yang tidak dikonfirmasi sebagai fakta, konten exception, output mentah, HTML/CSS/JavaScript, header sensitif, atau nilai environment.

Jika validasi Pydantic gagal sebelum generation handler, record tetap mencatat metadata operasional yang tersedia, tetapi prompt dan fakta bernilai null atau daftar kosong. Untuk request bertipe yang mencapai handler, recorder menyimpan prompt dan hanya fakta yang lolos pemeriksaan bukti konfirmasi. Implementasi harus memakai serializer allowlist yang menolak field tak dikenal.

### 6.2 Skema dan migrasi

- Tambahkan kolom nullable prompt dan confirmed_facts_json ke usage_records.
- Gunakan migrasi aditif yang memeriksa PRAGMA table_info sebelum menjalankan ALTER TABLE. Migrasi harus aman dijalankan kembali dan tidak membuat ulang database.
- Record lama tidak direkonstruksi dari log atau artefak. Untuk record lama, prompt tetap null dan confirmed_facts_json berisi daftar kosong.
- Ikuti retensi 90 hari yang sudah ada. Saat record dihapus, nilai prompt dan fakta ikut terhapus bersama row.
- Pertahankan pengaturan WAL, index, file sample, dan aturan satu instance.

### 6.3 Kontrak API

- GET /api/v1/usages/{usage_id} menambahkan prompt nullable dan confirmed_facts terstruktur ke detail.
- GET /api/v1/usages/ menambahkan title_preview yang dibatasi 80 karakter untuk daftar. Detail penuh tidak dikirim di seluruh daftar.
- Daftar menerima q dengan panjang maksimum 200 karakter. Filter pencarian pada prompt dan representasi JSON fakta dengan parameter SQL, batas hasil, cursor stabil, dan escaping wildcard.
- Summary, GPU/current, list, detail, source, dan download tetap no-store.
- Endpoint mengikuti kebijakan autentikasi aplikasi yang sama. Saat autentikasi diwajibkan, halaman dan API Usage memakai sesi yang sama. Tidak ada endpoint publik atau pengiriman data ke layanan eksternal.
- Tambahan response mengikuti Pydantic response model yang tertutup dan tipe TypeScript yang sama.

## 7. Keadaan layar dan aksesibilitas

- Loading daftar dan detail menggunakan indikator yang memiliki role status.
- Kegagalan memuat ringkasan, daftar, detail, source, atau GPU ditampilkan di area terkait dengan aksi coba lagi. Kegagalan GPU tidak menyembunyikan riwayat audit.
- Tampilan kosong membedakan belum pernah ada generation dari tidak ada hasil pada filter periode saat ini.
- Tampilan tanpa source menjelaskan bahwa artefak diterima tidak tersedia untuk run tersebut.
- Pengguna dapat mencapai navigasi, filter, file tabs, copy, unduh, serta pagination dengan keyboard.
- File tab menggunakan tablist/tab/tabpanel yang memiliki label dan hubungan ARIA valid.
- Semua tombol ikon memiliki nama aksesibel. Fokus terlihat. Status memakai teks atau ikon bersama warna.
- Prompt, fakta, dan source dapat dibaca dengan zoom browser serta tidak menyebabkan halaman horizontal overflow.
- Pada layar sempit, detail ditumpuk: header, prompt/fakta, rail, source, GPU. Daftar run dapat dibuka atau ditutup agar detail mendapat ruang penuh.

## 8. Kriteria penerimaan

1. Sidebar dan item navigasi Penggunaan tampil di Chat dan Usage. Membuka Usage mempertahankan sidebar pada desktop dan menyediakan drawer pada mobile.
2. Alur membuat Chat, memilih dan menghapus sesi, submit prompt, konfirmasi fakta, generation, preview, dan unduhan tetap sama sebelum dan sesudah rework.
3. Setiap record Usage yang mempunyai input tervalidasi menampilkan prompt sesuai teks tersimpan dan hanya fakta terkonfirmasi.
4. Request yang ditolak sebelum body terbaca tidak membuat aplikasi mengarang atau mengambil isi prompt dari log lain.
5. Database lama berhasil dinaikkan melalui migrasi aditif dan aman saat startup berikutnya. Record lama menampilkan detail input belum tersedia.
6. Retensi 90 hari menghapus prompt dan fakta bersama record yang kedaluwarsa.
7. extraction_token tidak ada di database, response Usage, log aplikasi, atau tampilan browser.
8. Pencarian bekerja pada prompt dan fakta, menerima query terbatas, menjaga cursor, dan tidak membocorkan error SQL.
9. Detail source selalu berasal dari endpoint artefak diterima. Source tidak dieksekusi pada halaman Usage.
10. Run gagal hanya menampilkan source bila endpoint accepted source berhasil mengembalikannya.
11. Tahap visual merangkum event aktual ke lima tahap dan menunjukkan kegagalan di tahap yang benar.
12. Metrik GPU membedakan snapshot sekarang, agregat periode, dan run terpilih. Null dan data kosong tidak tampil sebagai nol.
13. Semua jumlah run, status, prompt, durasi, dan nilai GPU berasal dari API. Tidak ada data comp sintetis di aplikasi.
14. Halaman dapat digunakan dengan keyboard, label dan fokus terbaca, serta tidak mengalami horizontal overflow pada viewport ponsel.
15. Usage tidak memuat model, menjalankan inference, atau memanggil extractor.
16. Perilaku login tidak berubah. Saat autentikasi diwajibkan, sesi yang sama melindungi halaman dan endpoint API Usage tanpa mengubah format cookie atau kredensial.

## 9. Risiko dan penanganan

- Prompt dapat memuat data sensitif. Mitigasi: simpan hanya di mesin lokal, tampilkan pemberitahuan retensi 90 hari, batasi akses dengan autentikasi yang ada, jangan kirim ke layanan luar, dan hapus sesuai retensi.
- Fakta bersarang dapat berisi campuran field terkonfirmasi dan belum terkonfirmasi. Mitigasi: serializer allowlist memeriksa bukti konfirmasi di setiap nilai, termasuk title_evidence dan text_evidence.
- Database yang sudah ada tidak memiliki kolom baru. Mitigasi: migrasi aditif yang idempotent dan fallback untuk row lama.
- Daftar dapat menampilkan judul yang berasal dari prompt. Mitigasi: preview dibatasi 80 karakter, akses tetap terautentikasi, dan detail hanya dimuat saat dipilih.
- Endpoint source dapat mengembalikan 404 untuk generation yang belum diterima renderer atau artefaknya sudah tidak tersedia. Mitigasi: state unavailable, tanpa membaca file mentah dari path lain.
- Shell berbagi riwayat browser yang sudah dikelola ChatShell. Mitigasi: gunakan kontrak HistorySidebar yang ada atau adapter tanpa mengubah format localStorage dan reducer Chat.

## 10. Batas implementasi dan review

Tahap ini hanya menghasilkan spesifikasi dan referensi comp. Belum ada perubahan komponen UI, kontrak API, database, migrasi, atau behavior aplikasi. Implementasi dimulai setelah pengguna menyetujui dokumen ini.

Setelah disetujui, implementasi mengikuti urutan: migrasi dan skema Usage, capture input terkonfirmasi, kontrak API dan client, shell bersama, workspace Usage, lalu review visual desktop dan mobile. Setiap tahap diverifikasi terhadap kriteria penerimaan sebelum perubahan berikutnya.
