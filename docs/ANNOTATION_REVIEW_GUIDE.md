# Kurasi prompt Indonesia dan target PageSpec

## Tujuan tahap ini

Menyiapkan pasangan prompt Indonesia dan PageSpec untuk continued training model proyek. Pretraining baseline tersedia, tetapi probe JSON masih 0/4 valid. Data instruksi harus diperiksa sebelum SFT. Semua kandidat pilot masih **draft**, reviewer dan keputusan manusia kosong.

Ini pelaksanaan tahap anotasi pada rencana pipeline yang sudah disetujui. Tidak ada training baru atau aplikasi generator pada tahap ini.

## Paket lokal

Buka paket terbaru `outputs/annotation_review/pilot-id-v2/packet.html` di browser atau baca [notebook kurasi](../notebooks/04_kurasi_dan_sft.ipynb). Paket v1 dipertahankan sebagai riwayat. Dokumen HTML menampilkan prompt, PageSpec, catatan perubahan, provenance, idea dan kode sumber sebagai teks yang di-escape. Dokumen tidak menjalankan HTML/JavaScript sumber dan tidak memuat gambar/CDN sumber.

File paket:

| File | Isi |
| --- | --- |
| `packet.html` | 12 kartu perbandingan sumber dan draft |
| `review.csv` | 12 kandidat dengan kolom penilaian manusia kosong |
| `inventory.csv` | Audit seluruh 119 draft awal |
| `drafts.jsonl` / `drafts.json` | Target dan prompt pilot, tetap draft |
| `manifest.json` | Hash input/output, tokenizer, family assignment dan coverage |

Paket dan source turunan tetap lokal. Ringkasan terbaru tanpa teks sumber ada di [laporan pilot v2](../reports/data/ANNOTATION_REVIEW_PILOT_ID_V2.json), dan [laporan v1](../reports/data/ANNOTATION_REVIEW_PILOT_ID_V1.json) menyimpan hasil sebelumnya. Setelah clone, paket tidak otomatis tersedia; siapkan corpus dan file draft hasil kurasi di mesin tersebut.

## Hasil pilot v1

- Queue awal: 119 baris, 102 keluarga; 94 train, 11 validation, 14 test. Semua berupa satu hero sederhana, tanpa interaksi, dan belum memenuhi prompt Indonesia.
- Pilot: 12 kandidat dari 12 keluarga berbeda, 6 CSS biasa dan 6 Tailwind. Dua kandidat setiap kombinasi style/partition menghasilkan 4 train, 4 validation, 4 test; tidak ada reshuffle keluarga.
- Ada 6 tipe section dan 2 tipe interaksi: `form_validate` dan `menu_toggle`, diturunkan dari JavaScript sumber Vulcan.
- Semua 12 target lolos schema dan batas sequence 1.024 token; maksimum 640 token. Ini hanya kesiapan format.
- Belum ada `testimonial`, `pricing_table`, `accordion`, `tabs`, `modal`, atau `filter` dalam pilot. Perlu contoh yang benar-benar mendukung tipe tersebut untuk memperluas coverage.
- Pilot dipilih untuk memeriksa proses anotasi dan proyeksi schema. Ukuran 12 dan distribusi seimbang ini bukan corpus SFT yang memadai atau evaluasi representatif.

## Checklist manusia

Isi `review.csv` sambil membaca kartu yang memiliki `review_id` dan `source_row_id` sama. Nilai kolom checklist dengan `yes`, `no`, atau `needs_revision`.

1. `prompt_ok`: prompt Indonesia jelas, menyebut style yang benar, selaras dengan seluruh target; tidak meminta fitur yang tidak terwakili.
2. `content_ok`: judul, teks, nama, harga, tahun dan tujuan halaman sesuai sumber atau perubahan yang dicatat. Tidak mengarang testimoni/klaim/layanan.
3. `projection_ok`: perubahan tabel/list/sidebar/logo/gambar menjadi komponen PageSpec dapat diterima. Catat elemen yang hilang dan alasan menerima, merevisi atau menolak.
4. `interactions_ok`: ID interaksi memang didukung sumber, target section sesuai, dan label tautan sesuai tujuan. Halaman statis tidak diberi JavaScript rekaan.
5. `human_decision`: pilih `approve`, `revise`, atau `reject`. Isi nama reviewer, waktu dengan zona waktu, dan alasan pada `notes`. Kolom kosong berarti belum ditinjau.

Semua proyeksi perlu penilaian manusia. Empat kandidat memiliki perubahan fungsi pada v2 yang harus ditinjau: **Navigasi Brand**, **EdTech Startup**, **Toko Aksesori Otomotif**, dan **Perusahaan Penerbitan**. Fragmen tak tersedia dan label tujuan yang belum tepat pada v1 direvisi seperti tabel berikut. Pemeriksaan tambahan pada exporter hanya memastikan ID section tujuan tersedia; kesesuaian label, makna, dan perilaku browser tetap dinilai terpisah.

## Revisi pilot v2

| Kandidat | Perbaikan |
| --- | --- |
| Navigasi Brand | Komponen navbar mandiri dengan satu tautan Navigasi menuju navbar. Empat tujuan yang tidak memiliki section dihapus. |
| EdTech Startup | CTA menjadi Lihat Fitur menuju section fitur; tidak menjanjikan pendaftaran. |
| Toko Aksesori Otomotif | Hanya tautan produk dan profil yang tersedia. Kontak tanpa detail dihapus; hero menjadi teks centered karena gambar tidak didukung. |
| Perusahaan Penerbitan | Dibatasi menjadi profil penerbit; tautan toko, bergabung dan kontak dihapus. Beranda/Kembali ke awal menuju hero. |

Empat target dan lima prompt berubah. Prompt organisasi sosial diperjelas agar warna dan kartu sesuai target. Source ID, family dan partition dipertahankan. Semua 12 target lolos schema/context, maksimum **612 token**; fragmen tidak tersedia turun dari 4 menjadi 0. Status tetap draft dengan reviewer kosong. Rincian: [perbandingan revisi](../reports/data/ANNOTATION_PILOT_REVISIONS_V2.json).

Gunakan `outputs/annotation_review/pilot-id-v2/review.csv` untuk review terbaru. Persetujuan v1, jika ada, tidak otomatis berlaku untuk target yang berubah pada v2.

## Kandidat tambahan dan batas corpus

Pemindaian train membaca 41.639 baris, termasuk 38.666 HTML, dan menyimpan 14 kandidat dari 14 keluarga: enam testimonial, enam pricing, satu accordion dan satu tabs. Ini sinyal untuk inspeksi, belum pasangan instruksi atau data reviewed. Kandidat disimpan di `outputs/annotation_candidates/coverage-v1/` dengan provenance; ringkasan di [laporan coverage](../reports/data/ANNOTATION_CANDIDATE_COVERAGE_V1.json).

Source tabs terpilih hanya memanggil `openTab` lewat atribut onclick dan tidak menyediakan implementasi fungsi atau script eksternal. Jangan menganggap interaksi tersebut tersedia atau memberi label target tabs tanpa memperbaiki/menilai adaptasinya. Source accordion memakai details/summary native HTML, sehingga memerlukan penilaian adaptasi ke katalog renderer JavaScript proyek.

Pencarian heuristik tidak menemukan modal/filter; hasil nol tidak membuktikan keduanya tidak ada. Pola lain bisa terlewat. Review dan penambahan bahan yang benar-benar mendukung interaksi diperlukan sebelum mengklaim coverage lengkap. Source validation/test tidak dipakai untuk memilih kandidat perluasan ini.

Pada Misi Organisasi Sosial, tombol donasi dihilangkan karena fragmen sumber tidak memiliki section donasi. Pada katalog aksesori/mobil, tabel menjadi kartu. Pada Fitness Company, sidebar atau warna per blok hilang. Reviewer harus menerima atau merevisi perubahan tersebut secara sadar.

Browser acceptance dilakukan setelah renderer dibuat. Menyetujui JSON tidak membuktikan layout, aksesibilitas atau interaksi browser.

## Setelah review

1. Simpan worksheet sebagai revisi baru. Jangan menimpa paket v1 yang sudah memiliki checksum.
2. Revisi prompt/target yang perlu diubah. Pertahankan `source_row_id`, source family, lisensi dan partisi asal. Revisi yang mengubah makna perlu ditinjau ulang.
3. Buat `data/annotations/reviewed.jsonl` hanya dari kandidat yang benar-benar disetujui manusia. Isi `annotation_status=reviewed`, `reviewer`, `annotation_revision` baru dan `prompt_language=id`. CSV adalah bukti review, bukan input training otomatis.
4. Perluas corpus secara bertahap. Pertahankan mapping keluarga pretraining; jangan memindahkan contoh test ke train untuk memperbaiki hasil model. Minimal teknis 10 keluarga dan cakupan tiga partition tidak berarti cukup untuk generalisasi.
5. Persiapkan ulang SFT dengan tokenizer/cache pretraining yang sama. Periksa jumlah accepted/rejected, provenance, coverage dan panjang sequence tanpa memotong JSON.
6. Setelah data lolos gate, lanjutkan SFT dari `checkpoints/TRAIN-004-VERIFIED/best.pt`, lalu evaluasi dengan prompt dari artifact test SFT yang sah. Pemilihan checkpoint memakai validation.

Perintah tahap 5, setelah file reviewed benar-benar tersedia:

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label prepare_reviewed_sft -- .\.venv\Scripts\python.exe -m src.data.pipeline --config configs/dataset.json --annotations data/annotations/reviewed.jsonl
```

Panduan training dan konfigurasi ada di [TRAINING_GUIDE](TRAINING_GUIDE.md). Notebook 04 tidak menjalankan perintah tersebut atau SFT.

## Mengekspor revisi paket

Gunakan dua path output baru, bukan menimpa hasil review sebelumnya:

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label export_annotation_review_packet -- .\.venv\Scripts\python.exe -m qa.prepare_annotation_review --drafts data/annotations/pilot_drafts_id_v3.jsonl --output outputs/annotation_review/pilot-id-v3 --report reports/data/ANNOTATION_REVIEW_PILOT_ID_V3.json
```

Exporter menerima subset draft dari queue yang ada, memverifikasi source text/provenance/family assignment, memeriksa schema, fragmen lokal serta tokenizer/context, dan mengekspor checklist kosong. Exporter tidak menerjemahkan sendiri, tidak menetapkan persetujuan manusia, serta tidak mengimpor CSV ke training. Draft v1 ditulis oleh LLM pada sesi AI-008 dan direvisi pada AI-009; semuanya membutuhkan review manusia.
