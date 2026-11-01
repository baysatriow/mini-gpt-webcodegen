# Catatan proyek dan runtime

## Lokasi pencatatan

| Lokasi | Isi | Cara diperbarui |
| --- | --- | --- |
| [Log utama](LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md) | Permintaan, keputusan, perubahan, hasil pemeriksaan, kendala dan commit | Ditambahkan per kegiatan oleh pelaksana atau asisten |
| [Log training](LOG_TRAINING.md) | Pretraining, SFT, resume, checkpoint, metrik dan evaluasi | Ditambahkan ketika pekerjaan training atau evaluasi dilakukan |
| RUN-*.txt di folder ini | Catatan rinci untuk run yang memiliki berkas pendamping | Ditulis per run; sebagian run hanya memiliki bagian pada log utama |
| outputs/webapp/usages/usage.sqlite3 | Metadata request generate, status, tahapan dan telemetri | Dicatat otomatis oleh fitur Usage |
| stdout/stderr server | Pesan Next.js, FastAPI dan cloudflared | Ditulis proses selama berjalan |

Log Markdown menyimpan ringkasan pelaksanaan. Tidak ada proses yang otomatis menyalin setiap pesan chat ke file ini. Konfirmasi dan hasil commit/push perlu dicatat secara eksplisit setelah kegiatan. Usage menyimpan metadata operasional, bukan transkrip chat.

## Penomoran dan koreksi

- Gunakan RUN-NNN untuk pelaksanaan dan AI-NNN untuk ringkasan bantuan LLM.
- Gunakan TRAIN-NNN atau ID eksperimen terkait untuk training; sertakan konfigurasi, lineage, checkpoint dan metrik yang diperiksa.
- Pertahankan riwayat. Tambahkan koreksi atau catatan susulan dengan tanggal pemeriksaan jika ada catatan terlewat.
- Bedakan pemeriksaan source, unit test, build, browser, inference dan endpoint publik.
- Catat kode kendala serta diagnosis yang diperlukan. Kredensial, session secret, token dan informasi sensitif tidak dimasukkan.

Setiap RUN tidak harus memiliki file .txt tersendiri. Bagian RUN pada log utama tetap merupakan catatan run; berkas pendamping dirujuk bila tersedia.

## Pemeriksaan sinkronisasi 1 November 2026

Sebelum pemeriksaan runtime ini, log utama sudah mencapai AI-061/RUN-681 sesuai tahap review frontend. Hasil commit/push terbaru belum ditulis sebagai outcome eksplisit. Catatan susulan AI-062/RUN-682 melengkapinya.

Pernyataan lama pada indeks ini bahwa training belum dimulai sudah dihapus. Log training telah berisi eksperimen nyata. Entry terakhir yang diperiksa adalah RUN-662, continuation REQEXT-V1-3600 pada 17 Oktober. Pekerjaan aplikasi, audit dan dokumentasi sesudahnya masuk log utama.

[Laporan sinkronisasi](../reports/structure/LOG_SYNC_2026-11-01.json) mencatat cakupan pemeriksaan: tahap terbaru dan lima commit terkait. Pemeriksaan ini tidak mengaudit kelengkapan setiap pesan sejak awal proyek.

## Runtime lokal terbaru

Pada start 1 November, stdout/stderr disimpan dalam direktori TEMP Windows dengan nama berikut:

- vibecraft-20261101-api.stdout.log dan vibecraft-20261101-api.stderr.log
- vibecraft-20261101-web.stdout.log dan vibecraft-20261101-web.stderr.log
- vibecraft-20261101-cloudflared.stdout.log dan vibecraft-20261101-cloudflared.stderr.log

Receipt lokal outputs/runtime/latest-session.json mencatat waktu verifikasi, URL tunnel sementara, PID, status HTTP, dan commit setelah push. Receipt ini diabaikan Git dan merupakan snapshot, bukan monitor latar belakang.

Log utama dan indeks ini masuk Git. Database Usage, receipt runtime, dan log proses tetap lokal.
