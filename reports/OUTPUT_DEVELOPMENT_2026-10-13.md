# Pengembangan output Mini GPT WebCodeGen

Sesi AI-011, 13 Oktober 2026. Pipeline menghasilkan dua website Studio Cakrawala yang tepat terhadap prompt, CSS biasa dan Tailwind/tabs, tanpa repair. Keduanya research demo yang diterima per output, sementara model keseluruhan belum lulus quality gate43/48. UI generator prompt bebas belum dibuat.

[Lihat hasil](../examples/generated/AI-011/index.html), [unduh HTML/CSS/JavaScript/JSON](../examples/generated/AI-011/examples.zip), dan [notebook06](../notebooks/06_pengembangan_output_pagespec.ipynb).

## Bukti eksperimen

| Tahap | Data dan proses | Generasi development | Final |
| --- | --- | --- | --- |
| TRAIN-006 pilot | 4 human-reviewed train, 40 update | Diagnosis prefix/fit pada sesi berikutnya | Reviewed test 0/4 valid, hasil historis |
| TRAIN-007 | 400 update, corpus pilot sama | Train 4/4 valid/EOS, validation 0/4 valid; hafalan | Tidak membaca ulang pilot test |
| TRAIN-008/009 v1 | 11.040 train, 2.400 update dengan resume | 24/24 valid, 1/24 exact; tema salah | Suite v1 tidak dibuka |
| TRAIN-010 v2 | Makna data/split/budget sama, style/theme lebih awal | 24/24 valid dan exact | 48/48 valid/exact/link valid, EOS; loss 0,00001699 |
| TRAIN-011 v3 | 11.520 train, 2.400 brand strings, 4.800 update | 24/24 valid, 20/24 exact; satu brand dengan subword baru gagal | Belum dibuka |
| TRAIN-012 v4 | 19.068 train, copy vocabulary drills, 4.800 continuation updates | 24/24 valid,20/24exact; loss0,00565869 | 48/48valid/link/EOS,43/48exact89,58%; gate gagal90% |
| TRAIN-013 v5 | Name-token loss16x,3.600updates, full validation | Ordinary validation tidak membaik; beststep0 identik parent | Fresh suite belum dibuka, tidak mencari benchmark lain agar lulus |

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

V3 gagal development sehingga final ditahan, lalu diukur setelah budget v4 selesai. V4 memakai optimizer/schedule baru dari best validation model v3; curriculum_parent berbeda dari ancestor pretraining yang tetap tercatat. Threshold tetap95% schema /90% exact. V4 gagal43/48, tidak membulatkan89,58% menjadi90%. Gate production human-reviewed tidak dilonggarkan.

V5 train/validation identik v4, fresh test240brandstrings seed8675309. Token nama train berbobot16, prompt/pad0, target lain/EOS1; cache19.068row dan475.524weightedpositions memiliki hash. Train memakai weighted mean CE; validation/test ordinary CE. Full validation623.706labels dipakai untuk checkpoint selection. Tidak membandingkan kedua objective langsung.

TRAIN-013 selesai434,22detik/10.781.936targetlabels, tetapi ordinary validation0,00565869 menjadi0,00760650. Beststep0:77tensor identik TRAIN-012best, diperiksa RUN-147. Tidak menyatakan weighted training berhasil; runtime tetap TRAIN-012. V5 final belum dibaca agar tidak mencari skor yang kebetulan lulus dari model yang sama.

## Ekspor dan bukti yang tersedia

RUN-119 mengekspor 48 final v2 menjadi file HTML/CSS/JavaScript/JSON dan ZIP. Folder lokal `outputs/generated_websites/AI-011-v2`. RUN-118 yang gagal dan folder parsialnya tetap tersedia. Tailwind4.3.3 dikompilasi lokal, stylesheet tidak membutuhkan CDN. Form hanya validasi contoh tanpa pengiriman.

RUN-123 audit kontrak 48/48 v2 diterima; Cakrawala lama ditolak pada title/navbar/hero/footer. Ini pemeriksaan artifact, bukan generasi baru atau evaluasi visual.

OBS-BROWSER-001: alat browser menolak protokol file lokal. Tidak mencoba workaround. `browser_evaluated=false`; perilaku JavaScript dan tampilan desktop/mobile belum terbukti lewat browser.

## Hasil runtime dan artifact

| RUN | Prompt | Hasil |
| --- | --- | --- |
| RUN-120 | Studio Cakrawala, modelv2 | Salah nama Cahaya; status generated lama hanya schema |
| RUN-139 | Studio Cakrawala, TRAIN-012, CSS/menu/form | Accepted,582tokens/EOS, kontrak tepat |
| RUN-141 | Kafe Senandika, Tailwind/tabs | Senanka,420tokens/EOS; rejected, tanpa HTML |
| RUN-142 | Studio Cakrawala, Tailwind/serif/hijau/tabs | Accepted,416tokens/EOS, kontrak tepat |

Cakrawala/Senandika tidak ada sebagai title utuh train menurut RUN-132, namun ini development probes yang dipilih, bukan skor final independen. Pemilihan contoh berhasil setelah failure tidak dipakai sebagai persentase kemampuan.

Flag research --development hanya mengizinkan measured synthetic checkpoint dengan SHA evidence cocok. Aggregate gate tetap gagal. Schema/link/kontrak literal per output tetap wajib; tanpa fallback/repair/render target. Default CLI memerlukan passing final gate. Metadata merekam model_quality_gate_passed=false dan usage validated_development_demo.

RUN-144 menyimpan dua snapshot file asli dengan checksum/ZIP ke examples/generated/AI-011, dilacak Git agar tersedia setelah clone tanpa checkpoint. RUN-148 memeriksa50website:48v2historis+2runtime. Schema/raw fidelity, prompt contract, local link/ARIA targets, JSsyntax, ZIPCRC/filehash tanpa temuan. Ini bukan eksekusi JavaScript atau browser test. Root galeri baru hanya halaman indeks statis.

Runtime SHA `791a365463710f73dbfbba767bd8bd17f5b4442e8f6137a92ec8c5888d1a2ed3`, beststep3.600 TRAIN-012; run selesai4.800update. Runtime tidak memakai TRAIN-013last yang validation-nya memburuk.

## Yang masih memerlukan pekerjaan

- Perbaiki nama agar overall quality gate lulus. Workstaralasa/Senandika menunjukkan kegagalan yang belum selesai; jangan mengganti JSON model dengan target.
- Notebook06/grafik/dua contoh tersedia. Run All default tidak training/generate GPU; flag eksplisit dapat dipakai melalui RUN logger.
- Aplikasi input/preview sandbox/download tetap tahap akhir. CLI/static gallery bukan antarmuka generator prompt bebas.
- Prompt di luar katalog, bisnis/fakta nyata, layout baru, human quality review dan browser acceptance memerlukan evaluasi/data berikutnya.
- Lengkapi empat anggota kelompok dan konfirmasi penyesuaian domain ke dosen; persetujuan dosen tidak diasumsikan.

## Rujukan

- [Rancangan dan diagnosis](../docs/SFT_DEVELOPMENT_2026-10-13.md)
- [Panduan menghasilkan website](../docs/GENERATING_WEBSITES.md)
- [Notebook proses](../notebooks/README.md)
- [Log training komprehensif](../logs/LOG_TRAINING.md)
- [Interaksi LLM AI-011](../logs/interaksi_llm/AI-011_2026-10-13.md)
