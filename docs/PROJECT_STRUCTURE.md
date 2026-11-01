# Struktur proyek

Repository memisahkan aplikasi, pipeline riset, dan artefak lokal. Penataan ini mempertahankan path yang dipakai checksum checkpoint serta laporan eksperimen.

## Batas modul

| Folder | Tanggung jawab | Perlakuan |
| --- | --- | --- |
| apps/web | Antarmuka pengguna, sesi login, preview dan audit Usage | Source disimpan Git; .env.local dan build lokal diabaikan |
| apps/api | Adapter HTTP, intake, model lazy-load dan pengelolaan artefak | Memakai library src; bind loopback dan satu worker |
| src/data, src/models, src/training | Preparation data, arsitektur dan training | Perubahan yang memengaruhi lineage memerlukan eksperimen baru |
| src/fullpage | Kontrak, prompt, generation bertahap, resolver dan renderer | Katalog dan schema harus cocok dengan checkpoint |
| qa | Perintah eksperimen dan pemeriksaan | Pertahankan script yang dirujuk notebook atau laporan |
| configs | Konfigurasi dan schema | File yang terikat hash diperlakukan sebagai bukti beku |
| training/selected | Manifest pilihan runtime | Bobot model dan salinan output tetap lokal |
| checkpoints | Checkpoint kanonis | Simpan pointer, payload .versions dan manifest bersama |
| data | Data dan tokenizer lokal serta provenance | Ikuti .gitignore dan lisensi sumber |
| assets | Katalog ilustrasi renderer | Gunakan ID dan hash yang diterima validator |
| tooling/tailwind | Compiler CSS lokal | Dependency dipasang dari package-lock |
| outputs | Website hasil, database Usage dan paket release lokal | Buat subfolder per run; jangan masukkan kredensial ke ekspor |
| reports | Hasil dan bukti terukur | Pertahankan laporan lama yang dirujuk selection atau log |
| notebooks | Proses yang dapat ditelusuri pengguna | Gunakan kernel environment proyek |
| logs | Riwayat eksperimen dan training | Tambahkan catatan baru, pertahankan isi historis |
| docs | Panduan aktif, spesifikasi dan arsip | Panduan aktif mengacu ke status terverifikasi terbaru |
| examples | Contoh dan gallery historis | Cantumkan run asal; contoh lama tidak menggantikan benchmark |
| sampah | Karantina yang dapat dipulihkan | Catat asal dan alasan pemindahan |

## Hasil audit 1 November 2026

Root app/ tidak memiliki file source maupun file tracked. Direktori kosong itu dipindahkan ke sampah/local-cache/2026-11-01/app/. Aplikasi aktif berada di apps/web dan apps/api. Git tidak menyimpan direktori kosong.

README sebelumnya mencampur status TRAIN-012, TRAIN-015, TRAIN-017, dan TRAIN-025. Isi historis disimpan di docs/history, sementara README utama kini menunjuk satu kandidat aplikasi: TRAIN-025 step 1800.

Source pipeline, konfigurasi beku, checkpoint kanonis, dan hasil eksperimen tetap pada path yang diverifikasi oleh lineage. Pemindahan massal dapat membatalkan pemeriksaan hash dan path di checkpoint.

Tiga belas file frontend memiliki perubahan lokal sebelum audit. Perubahan itu memerlukan review tersendiri sebelum menjadi bagian dari commit aplikasi. Commit penataan ini hanya memuat dokumentasi dan bukti audit.

## Aturan perapihan berikutnya

1. Periksa pemakai suatu file melalui CodeGraph dan referensi source, notebook, laporan, serta manifest.
2. Jika file sudah tidak dipakai, pindahkan ke sampah dengan catatan asal dan cara pemulihan.
3. Pertahankan bukti eksperimen yang dirujuk hash atau laporan seleksi.
4. Simpan artefak baru di outputs dengan nama run atau paket yang jelas.
5. Catat hasil pemeriksaan dan batasnya sebelum commit.

Paket upload berada di outputs/releases. Folder itu diabaikan Git; metadata identitas dan checksum paket dicatat dalam reports/structure.
