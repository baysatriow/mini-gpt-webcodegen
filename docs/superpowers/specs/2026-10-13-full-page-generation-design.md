# Spesifikasi generasi halaman lengkap dan konteks 2.048

Tanggal: 13 Oktober 2026. Interaksi: AI-015.

Status: arah generasi bertahap disetujui pengguna; spesifikasi tertulis ini menunggu review. Belum ada perubahan model, training, atau renderer dari spesifikasi ini.

## 1. Tujuan dan batas proyek

Menghasilkan landing page dan company profile Indonesia yang lengkap, relevan, responsif dan memiliki interaksi yang bekerja. Halaman memakai HTML, CSS biasa atau Tailwind, dan vanilla JavaScript dari katalog. Model serta tokenizer tetap milik proyek yang berawal dari bobot acak. Kelanjutan dari TRAIN-015 bukan pemakaian LLM pralatih eksternal.

Panduan kelas dan scope sebelumnya tetap berlaku: Mini GPT decoder-only, dokumentasi interaksi/debugging, kerja kelompok empat orang, dan orisinalitas implementasi. Persetujuan dosen atas perubahan corpus kutipan menjadi domain website belum tercatat; persetujuan pengguna terhadap desain ini tidak dianggap persetujuan dosen. Lihat docs/PROJECT_SCOPE_AND_PIPELINE.md.

Tahap ini mencakup kontrak data, training, generasi, validator, komposer dan renderer. UI aplikasi input/preview/unduhan dikerjakan setelah kualitas model dan halaman lolos evaluasi. Backend website, autentikasi, database, JavaScript bebas dan screenshot-ke-kode tetap di luar scope.

## 2. Keputusan konteks dan panjang output

Target kandidat baru: block_size=2048, vocab_size=8192, enam layer, enam head, embedding 384. Tokenizer tidak dilatih ulang. Ukuran konteks diperbesar tanpa memperbesar lebar atau kedalaman model.

RUN-200 menghitung tambahan embedding posisi sebesar 393.216 parameter, sekitar 1,5 MiB bobot FP32. Attention memiliki empat kali pasangan posisi pada panjang penuh dibanding 1.024, dengan batch sama. Ini perhitungan, bukan klaim VRAM naik empat kali atau GPU sudah diprofilkan. SDPA dapat menghindari materialisasi matriks attention manual, tetapi biaya posisi panjang tetap perlu diukur.

Konteks memuat prompt, penanda dan keluaran. Batas output terpisah dari konteks:

| Tugas | Konteks maksimum | Budget generasi maksimum, termasuk kesempatan EOS |
| --- | ---: | ---: |
| Rencana halaman | 2.048 | 512 |
| Isi satu bagian | 2.048 | 1.536 |
| Perbandingan satu JSON halaman lengkap, eksperimen development opsional | 2.048 | 1.536 |

Untuk setiap panggilan, prefix mencakup tiga penanda yang digunakan generator. Budget harus memenuhi prefix_tokens + max_new_tokens <= block_size. Input yang terlalu panjang ditolak dengan keterangan kebutuhan token; jangan memangkas fakta atau JSON diam-diam. Data juga harus memenuhi budget per task, bukan hanya muat pada training. Padding bukan bagian dari panjang sebenarnya.

Dua fixture manual AI-014 membutuhkan total 1.498/1.479 token dan target dengan EOS 1.375/1.358. Keduanya muat di 2.048 serta budget output 1.536, tetapi tidak di budget 768. Itu tidak menjamin semua halaman baru muat, atau checkpoint sekarang langsung dapat menghasilkannya. Generasi bertahap menjadi runtime utama; output gabungan dapat melampaui satu konteks karena komposer tidak memerlukan panggilan model tambahan.

Keputusan pengguna AI-016 menetapkan maksimum output 1.536, menggantikan usulan 1.600. Dengan budget penuh tersebut, prefix termasuk penanda dibatasi maksimum 512 token. Task rencana tetap memakai budget 512 karena isinya ringkas. EOS boleh menghentikan generasi lebih awal; model tidak diwajibkan mengisi seluruh budget. Jika prefix task isi melebihi 512 token, sistem melaporkan kebutuhan token sebelum generasi, sehingga tidak menurunkan budget atau memangkas informasi diam-diam.

Perbandingan satu JSON hanya dilakukan jika data task dan budget eksperimennya ditetapkan lebih dahulu. Tidak menambah task itu ke MVP secara otomatis.

## 3. Migrasi checkpoint yang dapat ditelusuri

TRAIN-015 memakai learned position_embedding dengan 1.024 baris. load_checkpoint dan pemeriksaan continuation saat ini mensyaratkan model_config identik, sehingga penggantian angka saja akan ditolak.

Sediakan jalur migrasi khusus, terpisah dari exact resume:

1. Verifikasi checkpoint TRAIN-015 best, tokenizer, konfigurasi, manifest dan ancestry pretraining proyek.
2. Buat model 2.048 dengan seed tercatat. Salin seluruh tensor yang bentuknya tetap, termasuk 1.024 baris posisi lama, tanpa modifikasi nilai. Inisialisasi hanya 1.024 baris posisi baru dengan normal mean 0/std 0,02.
3. Pastikan perubahan konfigurasi arsitektur hanya block_size; pertahankan weight tying. Tulis laporan tensor yang disalin/ditambah dan hash checkpoint asal/hasil.
4. Simpan artefak inisialisasi baru tanpa menimpa TRAIN-015. Tandai sebagai weights-only warm start dengan position extension, bukan exact optimizer/RNG resume. Optimizer, scheduler dan seed training baru dimulai ulang.
5. Latih task dengan panjang beragam, termasuk posisi di atas 1.024. Posisi baru belum dipelajari hanya karena tensor diperbesar.

Jangan melonggarkan validasi lineage global atau mengabaikan mismatch secara umum. Resume eksperimen 2.048 setelah checkpoint baru dibuat tetap wajib identik konfigurasi, data, optimizer, scheduler dan RNG. Kandidat baru perlu gate sendiri sebelum menjadi runtime; checkpoint lama tetap tersedia.

## 4. Kontrak request dan task

Input pipeline berupa request terstruktur dengan request_id, prompt, genre, style_mode dan business_facts. Genre hanya landing_page/company_profile. business_facts memuat nama, deskripsi, layanan, dan informasi opsional seperti kontak, proyek, harga, testimoni atau anggota tim. Setiap item ber-ID agar referensi dapat diperiksa. Asset ID berasal dari katalog lokal.

MVP memakai request terstruktur dan prompt Indonesia yang didukung curriculum. Pipeline tidak mengklaim mampu mengekstrak semua fakta dari prompt bebas. Informasi wajib yang kosong menghasilkan missing_information. Normalizer hanya memeriksa bentuk dan panjang, bukan mengarang fakta yang tidak diberikan.

Dua task model memakai tokenizer/penanda proyek yang ada:

- page_plan: request terukur menjadi PlanSpec 1.0, berisi title, genre, language, style_mode, theme dan ordered sections. Tiap section memiliki id, type, role, variant, fact_ids dan asset_ids. Plan tidak mengandung seluruh paragraf halaman.
- section_content: ringkasan plan, fakta yang relevan dan satu section descriptor menjadi SectionSpec 1.0, berisi id/type/role/variant dan props sesuai schema komponennya.

PlanValidator memeriksa jumlah/urutan/jenis bagian, referensi fakta/aset, variasi yang kompatibel serta kecocokan genre. SectionValidator memeriksa schema props dan identitas descriptor. Task serializer bersifat deterministik dan dicatat dalam manifest. Encoder baru harus task-aware; encode_sft lama memvalidasi PageSpec v1 dan tidak digunakan untuk PlanSpec/SectionSpec secara langsung.

Komposer menghasilkan PageSpec 2.0 dengan metadata plan dan seluruh bagian valid. Theme dan style mode berasal dari plan, bukan dipilih ulang per bagian. Navbar dan CTA menggunakan ID bagian yang benar. Kontak, harga, angka dan nama yang diberikan harus dipertahankan tepat. Teks kreatif harus relevan terhadap fakta; ketepatan makna tetap membutuhkan review, tidak dianggap terbukti oleh JSON Schema.

## 5. Kelengkapan dan renderer

Default landing page terdiri dari sembilan bagian: navbar, hero/CTA, pengenalan, layanan/produk, manfaat, proses, FAQ, kontak/CTA akhir, footer. Default company profile terdiri dari delapan: navbar, hero, profil, visi/nilai, layanan, proses, kontak, footer. Portfolio dan tim ditambahkan jika informasi tersedia atau contoh secara eksplisit fiktif. Target halaman lengkap 8 sampai 12 bagian; schema tetap dapat menampung maksimum 16.

Pertahankan delapan tipe komponen lama. PageSpec 2.0 menambahkan role, variant dan referensi media terbatas. FAQ memakai feature_grid plus accordion; portofolio memakai feature_grid plus media. Tidak menambah bahasa markup bebas.

Varian awal yang harus didukung:

- Hero centered atau split dengan kolom visual dari aset katalog.
- Feature grid berupa cards atau numbered untuk layanan/proses.
- Text section berupa prose atau split dengan media.
- Navbar inline dengan menu responsif, contact panel, dan footer dengan kelompok tautan.

Variant memiliki daftar tipe yang kompatibel. Renderer menangani spacing, tipografi, kontras, lebar konten dan breakpoint secara konsisten. Setidaknya dua komposisi halaman yang berbeda harus tersedia, dengan CSS biasa dan Tailwind sebagai dua mode styling. Tailwind tetap dikompilasi lokal dari toolchain proyek.

Media menggunakan asset_id, alt dan caption opsional. Katalog menyimpan path lokal, dimensi, asal serta lisensi; path tidak berasal bebas dari model. Mulai dengan aset ilustrasi milik proyek agar tidak perlu unduhan dataset gambar baru. Render dan ekspor mempertahankan berkas aset yang digunakan.

Schema serta renderer v1 tetap tersedia untuk mereproduksi hasil historis. Version dispatch memilih validator/renderer yang tepat; tidak menulis ulang schema lama atau artefak AI-013.

## 6. Kegagalan dan hasil antara

Setiap task disimpan sebagai raw output, parsed result, prompt/token counts, stop reason, durasi dan checkpoint hash. Validasi tidak memperbaiki JSON diam-diam.

Jika output gagal, izinkan maksimal satu pengulangan pada task tersebut dengan ringkasan error dalam prompt yang tetap muat konteks. Retry harus tercakup dalam curriculum dan dicatat terpisah. Rate percobaan pertama serta setelah retry dilaporkan terpisah. Tanpa target pembanding sebagai fallback. Jika tetap gagal, return stage_failed dan daftar bagian bermasalah; jangan mengekspor halaman yang disebut lengkap.

Formulir hanya memvalidasi lokal sampai integrasi pengiriman dirancang terpisah. Status di halaman harus sesuai perilaku tersebut. JavaScript tetap berasal dari katalog yang sudah diizinkan, tanpa script model, event handler bebas atau URL aset eksternal.

## 7. Data dan efisiensi

Gunakan dataset lokal yang sudah tersedia untuk referensi pola halaman; task plan/section memerlukan pasangan baru. Contoh sintetis mencatat asal, transformasi dan human_reviewed=False. Persetujuan arah tidak menambah jumlah reviewed manusia, yang saat ini tetap 12.

Target curriculum awal: 240 keluarga train, 40 development dan 40 final, dengan kedua genre seimbang serta dua style mode per keluarga. Pilot memakai subset 40 train dan 10 development untuk diagnosis sebelum memperluas seluruh train. Final baru dibekukan pada manifest sebelum eksperimen, tidak dibuka pada pilot atau pemilihan kandidat.

Semua style variant, halaman lengkap, task plan, section dan retry dari satu keluarga masuk partisi yang sama. Selain nama/fakta baru, gunakan kombinasi susunan/layout yang ditahan untuk development/final. Deteksi duplikasi termasuk template struktur dan teks; catat overlap pola yang disengaja. Final AI-013 tidak dipakai ulang atau ditargetkan untuk augmentasi.

Simpan task JSONL serta indeks panjang; bentuk tensor saat dibutuhkan. Bucket berdasarkan panjang dan potong padding batch sampai panjang sebenarnya tanpa membuang token prompt/target. Ini menghindari semua task pendek selalu memakai tensor 2.048. Validasi masking dan penyebut loss tetap berdasarkan supervised tokens, termasuk EOS.

Tetap gunakan BF16, SDPA, fused AdamW dan supervised-only logits jika profil mendukung. Tidak memasukkan KV cache atau perubahan arsitektur attention sebagai prasyarat MVP. Untuk inference bertahap, ukur biaya panggilan dan total halaman dahulu; optimasi tambahan ditentukan dari bottleneck aktual.

## 8. Sumber daya dan training

Jangan memakai batch 48 lama langsung pada konteks penuh 2.048. Profil kandidat batch 4, 8, 12 dan 16 secara berurutan, pada panjang task representatif dan panjang maksimum; hentikan peningkatan ketika tidak stabil atau tidak memiliki headroom desktop. Pilih berdasarkan supervised tokens/detik, waktu total dan VRAM, bukan hanya GPU utilization.

Jika perlu, gunakan gradient accumulation untuk mendekati effective batch 48. Jadwal/probe harus mencatat batch dan accumulation serta jumlah token supervised; effective batch sama tidak menjamin workload atau kualitas identik. Uji task di atas posisi 1.024 pada data train/development.

Pertahankan reserve disk 15 GiB sebelum download, penulisan dataset dan checkpoint. Perhitungan terdahulu menunjukkan free sekitar 17,73 GiB, perlu diperiksa lagi saat implementasi. Estimasi artefak fase baru maksimum 1,5 GiB termasuk data, aset, checkpoint best/last dan temporary write; jika anggaran tidak muat, kecilkan materialisasi atau hentikan dengan laporan kebutuhan ruang. Jangan menghapus checkpoint/data lama tanpa instruksi pengguna.

Budget update dan pemilihan kandidat dibekukan setelah pilot/profil development, sebelum training utama. Pilih kandidat berdasarkan generation success dan kualitas isi development, disertai loss; loss rendah saja tidak cukup. TRAIN-016 belum dijalankan. Nama run selanjutnya mengikuti nomor tertinggi saat eksekusi.

## 9. Evaluasi dan penerimaan

Final baru terdiri dari 40 keluarga, dua style mode, total 80 halaman. Rencana benchmark, contoh dan hashes dibekukan sebelum eksperimen; kandidat dipilih hanya dari development. Satu evaluasi final dilakukan setelah kandidat dikunci. Evaluasi lama tetap hasil historis.

Gerbang development/final untuk halaman lengkap:

- Minimal 95% request menjadi halaman lengkap dan schema-valid, dilaporkan dengan jumlah absolut dan per genre/style.
- Minimal 95% memenuhi seluruh bagian yang diminta. Tidak hanya menghitung jumlah bagian.
- Semua halaman yang diekspor memiliki tautan internal, target interaksi serta referensi aset valid dan mempertahankan field fakta yang dapat diperiksa tepat.
- Review manusia menilai relevansi, kualitas teks, hierarki/layout dan konsistensi pada skala 1 sampai 5. Rata-rata minimal 4 untuk setiap dimensi serta tidak ada skor di bawah 3 pada sampel yang diperiksa. Sample review ditetapkan sebelum melihat hasil: 12 halaman, seimbang dua genre/two styles, dipilih deterministik dengan seed manifest.
- Pemeriksaan browser pada sampel yang sama di lebar 390 dan 1440 pixel: tidak ada overflow horizontal, teks/CTA terbaca, menu/navigasi/FAQ/form berfungsi dan gambar/asset lokal termuat. Simpan bukti aktual; pemeriksaan statis tidak memenuhi gerbang browser.

Seluruh 80 halaman mendapat pemeriksaan schema, fakta terstruktur, aset dan tautan. Kualitas semantik/desain hanya terbukti pada sampel manusia/browser yang benar-benar diperiksa. Klaim rilis dibatasi corpus dan request format yang dievaluasi, bukan semua prompt bebas.

Jika akses browser terhalang, dokumentasikan batas tersebut dan simpan status browser_pending. Jangan melewati penolakan akses melalui jalur alternatif. Gerbang penerimaan tetap belum selesai sampai bukti tersedia.

## 10. Notebook, artefak dan transisi

Notebook baru menunjukkan secara berurutan: inspeksi panjang dan family split, migrasi posisi, profil GPU, training/kurva, raw plan, hasil per bagian, error/retry, PageSpec gabungan, serta contoh ekspor. Kernel memakai VENV proyek; hasil sel nyata dibedakan dari fixture manual. Notebook lama tidak ditulis ulang.

Manifest dan log mencatat hashes source/config/schema/tokenizer/data/checkpoint, seed, provenance, budget, loss, valid tokens, duration, VRAM/telemetry, stop reason, hasil tiap tahap dan review. Tiap eksekusi mendapatkan RUN baru, termasuk kegagalan/rerun; interaksi LLM dicatat terpisah. Commit/push dilakukan di feature/pipeline-data-model-training tanpa Co-Authored-By. Main telah menerima progres sementara; perubahan berikut tetap di branch tersebut.

Dokumen pendukung: reports/FULL_PAGE_DIRECTION_2026-10-13.md dan reports/analysis/AI-015_CONTEXT_2048_DESIGN.json. Berikutnya adalah review spesifikasi ini, lalu rencana implementasi sesuai skill writing-plans. Belum ada implementasi atau jaminan kualitas halaman lengkap dari spesifikasi ini.
