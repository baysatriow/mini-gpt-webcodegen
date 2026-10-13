# Pengembangan output Mini GPT WebCodeGen

Sesi AI-011, 13 Oktober 2026. Status catatan sementara: continuation v4 sedang berjalan pada RUN-130. Tidak menyatakan hasil v4/final/nama baru sebelum generasi diperiksa. Hasil berikutnya ditambahkan setelah tersedia.

## Bukti eksperimen

| Tahap | Data dan proses | Generasi development | Final |
| --- | --- | --- | --- |
| TRAIN-006 pilot | 4 human-reviewed train, 40 update | Diagnosis prefix/fit pada sesi berikutnya | Reviewed test 0/4 valid, hasil historis |
| TRAIN-007 | 400 update, corpus pilot sama | Train 4/4 valid/EOS, validation 0/4 valid; hafalan | Tidak membaca ulang pilot test |
| TRAIN-008/009 v1 | 11.040 train, 2.400 update dengan resume | 24/24 valid, 1/24 exact; tema salah | Suite v1 tidak dibuka |
| TRAIN-010 v2 | Makna data/split/budget sama, style/theme lebih awal | 24/24 valid dan exact | 48/48 valid/exact/link valid, EOS; loss 0,00001699 |
| TRAIN-011 v3 | 11.520 train, 2.400 brand strings, 4.800 update | 24/24 valid, 20/24 exact; satu brand dengan subword baru gagal | Belum dibuka |
| TRAIN-012 v4 | 19.068 train, copy vocabulary drills, continuation bobot proyek | Belum diukur saat catatan awal ini | Belum dibuka |

## Yang diperbaiki

1. Diagnosis memisahkan prefix/mask dari kekurangan latihan/data. Empat train mudah dihafal, sehingga loss train saja tidak menjadi gate.
2. Style/theme dipindahkan sebelum sections. Kontrol v2 mempertahankan semua prompt/target/family allocation, sehingga perubahan serialization dapat ditinjau terpisah.
3. Studio Cakrawala pada RUN-120 menjadi Studio Cahaya walaupun schema valid. File lama dipertahankan sebagai kegagalan nama, bukan keberhasilan website.
4. V3 memperluas brand/teks. Empat kesalahan development berasal dari Workstaralasa. Token sta nol exposure pada title train, seperti dicatat RUN-128.
5. V4 menambah 7.548 train-only copy drills. BPE alphabetic ASCII <=6 karakter mempunyai 4.998 eligible IDs; 4.072 terwakili, 926 belum terwakili melalui pola konstruksi yang dicoba. Tidak mengklaim semua token mampu disalin.
6. Validator prompt menolak nama/text/theme/komponen/interaksi yang tidak sesuai tanpa mengubah JSON asli model. Renderer hanya menerjemahkan output yang diterima.

## Provenance dan evaluasi

Model tetap 14.186.496 parameter, enam layer/head, width384, context1.024, BPE8.192. Bobot berasal dari pretraining proyek dari random weights, tanpa pretrained LLM eksternal. Dua belas human-reviewed annotations tetap terpisah dari curriculum `programmatic_contract`.

Corpus v3 memiliki split 11.520/1.440/1.440. V4 menambah hanya train menjadi19.068; validation/test/final tetap identik. Nama utuh dipisah, subword dan resep komponen dipakai bersama. Benchmark mengukur transfer pada resep/pola prompt yang dilatih, bukan layout baru atau bahasa bebas.

V3 gagal development sehingga final tidak dibaca. V4 memakai optimizer/schedule baru dari best validation model proyek v3; curriculum_parent berbeda dari ancestor pretraining yang tetap tercatat. Gate production human-reviewed tidak dilonggarkan. Threshold final tetap95% schema /90% exact. Final dipakai setelah budget selesai dengan best validation, tanpa repair atau memilih checkpoint dari test.

## Ekspor dan bukti yang tersedia

RUN-119 mengekspor 48 final v2 menjadi file HTML/CSS/JavaScript/JSON dan ZIP. Folder lokal `outputs/generated_websites/AI-011-v2`. RUN-118 yang gagal dan folder parsialnya tetap tersedia. Tailwind4.3.3 dikompilasi lokal, stylesheet tidak membutuhkan CDN. Form hanya validasi contoh tanpa pengiriman.

RUN-123 audit kontrak 48/48 v2 diterima; Cakrawala lama ditolak pada title/navbar/hero/footer. Ini pemeriksaan artifact, bukan generasi baru atau evaluasi visual.

OBS-BROWSER-001: alat browser menolak protokol file lokal. Tidak mencoba workaround. `browser_evaluated=false`; perilaku JavaScript dan tampilan desktop/mobile belum terbukti lewat browser.

## Yang masih memerlukan pekerjaan

- Selesaikan dan ukur continuation, baru nyatakan kemampuan menyalin nama baru berdasarkan output aktual.
- Buat notebook tahap06, raw examples dan grafik aktual setelah laporan akhir tersedia.
- Aplikasi input/preview sandbox/download tetap tahap akhir. CLI/static gallery bukan antarmuka generator prompt bebas.
- Prompt di luar katalog, bisnis/fakta nyata, layout baru, human quality review dan browser acceptance memerlukan evaluasi/data berikutnya.
- Lengkapi empat anggota kelompok dan konfirmasi penyesuaian domain ke dosen; persetujuan dosen tidak diasumsikan.

## Rujukan

- [Rancangan dan diagnosis](../docs/SFT_DEVELOPMENT_2026-10-13.md)
- [Panduan menghasilkan website](../docs/GENERATING_WEBSITES.md)
- [Notebook proses](../notebooks/README.md)
- [Log training komprehensif](../logs/LOG_TRAINING.md)
- [Interaksi LLM AI-011](../logs/interaksi_llm/AI-011_2026-10-13.md)
