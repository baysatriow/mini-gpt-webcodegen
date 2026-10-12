# Analisis Dataset untuk Mini GPT WebCodeGen

Tanggal pemeriksaan: 12 Oktober 2026. Target proyek saat ini adalah prompt pengguna ke spesifikasi halaman JSON, kemudian validator dan renderer menghasilkan HTML, CSS, dan JavaScript.

## Metode dan batas pemeriksaan

Kartu dataset dibandingkan dengan metadata, daftar file, dan isi data yang benar-benar tersedia. Seluruh 600 soal WebMC diperiksa. Untuk WebSight v0.2, diperiksa 800 baris dari delapan blok masing-masing 100 baris pada offset 0, 240000, 480000, 720000, 960000, 1200000, 1440000, dan 1680000. Blok tersebut tersebar, tetapi bukan sampel acak. Screenshot tidak diunduh. Pemeriksaan kode berupa indikator teks; halaman tidak dijalankan di browser.

Hasil angka tersedia di `outputs/dataset_audit/audit_summary.json`, sumber mentah di `data/raw/dataset_audit/`, dan perintah pemeriksaan di `qa/audit_dataset_sources.py`. Metadata dan angka hanya menggambarkan sumber pada tanggal pemeriksaan.

## Perbandingan

| Dataset | Isi yang dapat diperiksa | Format target asal | Keputusan untuk proyek |
| --- | --- | --- | --- |
| Webdev Coding Dataset | Kartu terindeks menyebut 600 contoh; akses live ke metadata, README, dan rows menghasilkan 401 | Kode HTML/CSS/JS, termasuk potongan kode, editing, dan debugging | Kandidat seed setelah akses pulih dan isi dapat diaudit |
| WebMC | Repo live menyediakan 600 soal pilihan ganda; 50.000 pasangan training tidak tersedia di file repo ini | `query`, `choices`, `gold` | Benchmark tambahan untuk pemahaman kode, disimpan terpisah dari training |
| WebSight v0.2 | 1.922.671 baris; 800 pasangan ide dan HTML diperiksa | `llm_generated_idea`, `text`, `image`; HTML + Tailwind | Kandidat terkuat dari tiga sumber untuk ide dan layout, memakai subset teks yang dikurasi |

## Webdev Coding Dataset

Sumber: https://huggingface.co/datasets/Hoglet-33/webdev-coding-dataset

Kartu yang masih terindeks menyebut 600 contoh, ukuran sekitar 732 kB, dan MIT. Kolom yang ditampilkan adalah `instruction`, `input`, `output`, `language`, `category`, dan `difficulty`. Tugas mencakup halaman, styling, manipulasi DOM, perbaikan bug, dan refactor. Karena tipe tugas beragam, hanya contoh pembuatan halaman yang sesuai untuk seed generator halaman.

Pada audit live, ketiga endpoint mengembalikan HTTP 401. Status ini tidak cukup untuk menentukan apakah repo berubah menjadi privat, dihapus, atau memiliki pembatasan lain. Sampel penuh, jumlah aktual, distribusi, dan lisensi file saat ini belum dapat diverifikasi. Klaim kartu tidak diperlakukan sebagai hasil pemeriksaan langsung.

Keputusan: jangan memasukkannya ke daftar sumber training aktif sebelum dapat diakses. Jika tersedia kembali, gunakan sebagai seed kecil dan periksa kategori, kualitas interaksi, dependensi, serta duplikasi. Ukuran 600 contoh tidak menjamin kemampuan serbaguna pada model dari nol.

## WebMC

Sumber: https://huggingface.co/datasets/IFM/WebMC

Revision yang diperiksa: `8090e6cd8cb71a5a0d5630da8eacd0b873963774`.

Kartu menyatakan pembuatan 50.000 pasangan instruksi untuk generation/editing menggunakan GPT-3.5 serta 600 soal evaluasi. Kartu menuliskan Apache-2.0 dalam isi README, tetapi metadata `cardData.license` tidak terisi.

Daftar file repo yang diperiksa hanya memuat `.gitattributes`, `README.md`, dan `WebMC.json`. File JSON berukuran 1.168.192 byte dan berisi tepat 600 soal. Setiap soal memiliki empat pilihan, label `gold` berupa indeks 0 sampai 3, dan tidak memiliki pasangan `instruction`/`input`/`output` training. Viewer juga melaporkan referensi `webqa.json` yang tidak tersedia.

Hasil pemeriksaan seluruh file:

| Indikator | Hasil |
| --- | ---: |
| Soal | 600 |
| Pilihan per soal | 4 |
| Label di luar rentang | 0 |
| Pertanyaan duplikat persis | 0 |
| Pertanyaan mengandung `<html` | 384 |
| Label 0 / 1 / 2 / 3 | 270 / 125 / 123 / 82 |

Contoh yang diperiksa berbahasa Inggris dan menanyakan fungsi elemen HTML dari kode yang diberikan. Distribusi label tidak seimbang: selalu memilih label 0 menghasilkan baseline 45%, sehingga hasil evaluasi harus dibandingkan dengan baseline ini.

Keputusan: tidak dipakai sebagai korpus 50.000 pasangan training karena berkas tersebut belum ditemukan di repo yang diberikan. Soal tersedia dapat menjadi benchmark tambahan pemahaman website. Skor pilihan ganda tidak membuktikan kualitas spesifikasi JSON, tampilan, atau fungsi halaman. Pertahankan soal sebagai data evaluasi jika benchmark dipakai.

## WebSight

Sumber: https://huggingface.co/datasets/HuggingFaceM4/WebSight

Revision yang diperiksa: `b11f8172f89c992b56ac702319e02c428cca4a4e`.

Dataset berisi website sintetis berbahasa Inggris dengan kode dan screenshot. v0.1 memiliki 822.987 baris HTML/CSS dan tidak menyediakan kolom ide pada skema yang ditampilkan. v0.2 memiliki 1.922.671 baris HTML/Tailwind, screenshot, dan `llm_generated_idea`. Kolom ide v0.2 paling berguna sebagai calon prompt.

Ukuran file seluruh versi adalah 317.180.094.013 byte, sekitar 317,18 GB desimal. v0.2 sendiri sekitar 285,79 GB. Semua versi hanya memiliki split `train`. Dengan sekitar 30 GB ruang F: sebelum instalasi, pengambilan penuh tidak sesuai kapasitas penyimpanan proyek. Subset teks melalui streaming dan pemilihan kolom lebih sesuai; pemilihan kolom Parquet dapat membatasi pembacaan payload screenshot.

Hasil dari 800 sampel v0.2:

| Indikator | Hasil |
| --- | ---: |
| Ide dan kode tidak kosong | 800 / 800 |
| Ide duplikat persis | 0 |
| Kode duplikat setelah normalisasi whitespace | 0 |
| Referensi Tailwind | 800 |
| Memiliki tag script | 1 |
| Atribut inline onclick/change/submit/load/input | 0 |
| Referensi URL HTTP/HTTPS | 800 |
| Referensi source.unsplash.com | 522 |
| Indikator teks placeholder | 127 |
| Panjang kode minimum / median / P95 / maksimum, karakter | 463 / 1600,5 / 2542 / 4815 |

Satu sampel dengan script menjalankan toggle sidebar. Beberapa ide meminta animasi atau carousel, sehingga kelengkapan fungsi tidak dapat disimpulkan dari deskripsi saja. Data cocok untuk layout dan teks, sedangkan sumber interaksi JavaScript tetap perlu ditambah. Angka placeholder berasal dari pola teks sederhana dan dapat menghasilkan false positive. Tidak adanya duplikasi pada sampel tidak membuktikan seluruh korpus bebas duplikasi. Ukuran karakter juga bukan panjang token model.

Kartu menuliskan CC-BY-4.0, kewajiban mematuhi lisensi konten sumber, dan pengungkapan penggunaan dataset saat merilis model atau aplikasinya. Simpan identitas sumber, revision, dan atribusi pada contoh turunan. Data memakai Tailwind/CDN dan aset eksternal; untuk paket unduhan mandiri, transformasi ke komponen renderer perlu mengatasi dependensi tersebut.

## Rekomendasi untuk workflow yang dipilih

Dari tiga sumber, WebSight v0.2 paling layak untuk penelitian lanjutan terhadap pasangan ide dan halaman. Ambil subset teks kecil lebih dulu, kemudian seleksi halaman yang dapat dipetakan ke katalog komponen renderer. Webdev dapat ditambahkan sebagai seed interaksi jika dapat diakses. Untuk workflow JSON, tambahan data interaksi berupa pasangan prompt dan ID fitur yang disediakan renderer. WebMC digunakan secara terpisah untuk benchmark tambahan.

Ketiganya belum menyediakan target spesifikasi JSON sesuai renderer proyek. Dataset training akhir perlu berisi pasangan prompt dan JSON yang mengikuti satu skema. Konversi harus mempertahankan maksud prompt, isi, susunan bagian, dan jenis interaksi yang didukung. Validitas JSON saja belum membuktikan kesesuaian isi terhadap prompt; sebagian contoh perlu diperiksa manusia.

Pembagian train/validasi/test dilakukan setelah pengelompokan halaman atau template serupa, agar variasi dari satu sumber tidak bocor antarsplit. Bila prompt pengguna ditargetkan berbahasa Indonesia, siapkan pasangan prompt Indonesia yang dikurasi; data Inggris tidak menjamin kemampuan Bahasa Indonesia. Keputusan jumlah sampel dan ukuran model menunggu hasil seleksi data serta pengukuran token.

Belum ada data dikonversi ke JSON proyek, model dilatih, atau website dihasilkan pada tahap ini.

## Referensi metode

- Streaming dan pemilihan kolom: https://huggingface.co/docs/datasets/stream
- Daftar file WebMC: https://huggingface.co/api/datasets/IFM/WebMC/tree/main
- Data WebMC: https://huggingface.co/datasets/IFM/WebMC/resolve/main/WebMC.json
- Ukuran WebSight: https://datasets-server.huggingface.co/size?dataset=HuggingFaceM4%2FWebSight
