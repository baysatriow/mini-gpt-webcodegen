# Kelanjutan kualitas penyalinan, AI-013

Pengguna mengizinkan kelanjutan sesuai planning pada 13 Oktober 2026. Tahap ini melanjutkan peningkatan kualitas sebelum UI aplikasi.

## Bukti dan keputusan sebelum training

- TRAIN-013 last diukur pada development: 23/24 schema, 20/24 exact. Best ordinary CE tetap parent. Bobot nama 16 kali belum menghasilkan perbaikan generation.
- Diagnosis development menemukan empat kesalahan nama pada baseline, dengan salah satu potongan hanya dua row train. Frekuensi train berasal dari data train, bukan final.
- RUN-170 diagnosis gagal karena path report relatif dibandingkan dengan root absolut. RUN-171 memperbaiki path dan menghasilkan laporan. Riwayat gagal tetap disimpan.

## Urutan pekerjaan

1. Siapkan v6 baru. Pertahankan seluruh train v5 dan tambahkan konteks penyalinan untuk semua potongan BPE alphabet ASCII panjang sampai enam yang muncul pada 1 sampai 63 row nama train. Delapan judul baru per potongan, dua pasangan recipe/style per judul.
2. Pemilihan potongan berasal dari train saja. Nama baru ditolak jika hash nama dengan salah satu prefix sudah ada di alokasi historis. Validation, test dan final disalin byte-identik, tanpa membaca target final untuk pengembangan.
3. Jalankan continuation baru dari TRAIN-012 best, ordinary CE, 2.400 update batch48, BF16, SDPA dan konfigurasi GPU terukur. LR 0,00005 ke 0,000005, warmup120. Arsitektur/tokenizer tidak berubah. Sisa disk minimum15GiB dipertahankan.
4. Pilih best full validation CE pada interval400, lalu ukur 24 generation development dari best dan last. Budget dan aturan ini ditetapkan sebelum training. Final v5 tetap tertutup pada tahap ini.
5. Catat hasil, kegagalan, kurva, hash, telemetry dan keterbatasan. Buat notebook08 dengan hasil nyata, jalankan sel baca artifact menggunakan kernel proyek. Commit dan push tanpa coauthor.

## Keputusan fase final, ditetapkan sebelum generation development TRAIN-015

Setelah eksperimen development di atas selesai dicatat, lanjutkan satu evaluasi final independen hanya jika best yang dipilih ordinaryCE memperbaiki full validation CE dan mencapai minimal95%schema serta90%exact pada generation development. Kandidat selalu best dari budget2.400, bukan last yang dipilih sesudah melihat final. Ambang final tetap95%schema/90%exact, greedy768, tanpa repair. Jangan membuka final jika kondisi development gagal. Jangan melatih ulang atau memilih checkpoint lain berdasarkan hasil final pada fase ini. Catat hasil final terpisah dan perbarui runtime hanya jika bukti final mendukung. Ini melanjutkan gerbang evaluasi pipeline yang sudah disetujui pengguna.

## Batas klaim

Data tambahan sintetis dengan kontrak programmatic, bukan anotasi reviewed manusia. Perbaikan development belum merupakan kelulusan final atau bukti kualitas browser. Runtime website tetap checkpoint yang sudah memiliki evidence sampai keputusan evaluasi berikutnya dibuat. Aplikasi UI mengikuti fase kualitas yang sudah ditetapkan.
