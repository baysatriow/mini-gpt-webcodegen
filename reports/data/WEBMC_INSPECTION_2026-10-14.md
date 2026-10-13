# Inspeksi WebMC, 14 Oktober 2026

## Hasil download

Public repository IFM/WebMC pinned8090e6cd8cb71a5a0d5630da8eacd0b873963774 berhasil diunduh pada RUN-250. Repo berisi .gitattributes,README.md,WebMC.json. File data1168192bytes dan README13934bytes, total1182126bytes. SHA datae6bc8d57bedb3ca5120958450b026436741f463ba979ef856c6f600b38a9e9b7. License dalam README apache-2.0; Hub cardData tidak mengisi fieldlicense. Simpan kedua bukti, jangan menyamakan missing metadata dengan no license.

[File dataset lokal](../../data/raw/candidates/webmc/8090e6cd8cb71a5a0d5630da8eacd0b873963774/WebMC.json). [README asli](../../data/raw/candidates/webmc/8090e6cd8cb71a5a0d5630da8eacd0b873963774/README.md). [Report download](WEBMC_DOWNLOAD_INSPECTION_V1.json). [Report600records](WEBMC_CONTENT_INSPECTION_V1.json).

## Isi sebenarnya

600records pilihan ganda, fieldsquery/choices/gold. Seluruh600 memiliki4choices dan gold valid0..3. Tidak ada exact duplicate atau duplicate query. Jawaban tersebar index0=270,index1=125,index2=123,index3=82; baseline menebak0 adalah45%, sehingga akurasi perlu ditafsirkan dengan distribusi ini.

391queries dan391gold choices mempunyai salah satu tagHTML yang diperiksa; penghitungan ini berbasis regex, bukan validasi HTML/browser. Ada soal pemahaman, editing/generation, tetapi output tetap pilihan ganda. Gold labels belum diverifikasi kebenarannya oleh reviewer manusia pada inspeksi ini.

Dengan tokenizer proyek, panjang query+serializedchoices min116/median728/max2078; satu melebihi2048 sebelum tambahan marker/instruksi. Jangan menyebut semua muat context generator. Source HTML/script diperlakukan sebagai data dan tidak dieksekusi. Generator saat ini request-to-plan/section dan tidak mendukung taskMC secara langsung.

## Ketersediaan training

Card menyebut50000instruction pairs plus600evaluation, tetapi file yang dirilis di revision ini hanya600MC. Tidak ditemukan50000training di repository resmi yang diperiksa. Tidak mengklaim training tidak pernah ada di tempat lain. Gunakan600MC sebagai kandidat evaluasi terpisah; jangan masukkan benchmark ini sebagai train untuk kemudian mengklaim nilaievaluasinya.

WebMC belum dimasukkan ke training, benchmark final proyek tidak dibuka. Untuk peningkatan95%, fullpagev2 train-only augmentation yang disetujui lebih langsung sesuai kontrak. Datasetv2 yang baru dihasilkan mempunyai17280train tasks dari2400train request variations pada240families, denganvalidation960/final800bytes unchanged. TRAIN-017 hasil sebelumnya memakai5760traintasks, bukan17280.

## Koreksi Webdev

API publik https://huggingface.co/api/datasets/Hoglet-33/webdev-coding-dataset saat ini401. Search cache masih menampilkan dataset600MIT, tetapi cache tidak membuktikan aksesunduh saatini. Penyebab401 bisa private/deleted/renamed; tidak disimpulkan tanpa bukti. Rekomendasi lama diturunkan menjadi unavailable/unverified.

## Sumber primer

- [Card WebMC](https://huggingface.co/datasets/IFM/WebMC)
- [File list resmi](https://huggingface.co/datasets/IFM/WebMC/tree/8090e6cd8cb71a5a0d5630da8eacd0b873963774)
- [File data pinned](https://huggingface.co/datasets/IFM/WebMC/resolve/8090e6cd8cb71a5a0d5630da8eacd0b873963774/WebMC.json)
