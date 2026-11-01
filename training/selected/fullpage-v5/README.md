# Kandidat runtime FULLPAGE-V5

Paket ini mengikat aplikasi ke TRAIN-025 step 1800. selection.json menyimpan identitas kandidat; folder model dan development-output menyediakan salinan lokal yang diabaikan Git.

## Identitas

| Atribut | Nilai |
| --- | --- |
| Run / step | TRAIN-025 / 1800 |
| Checkpoint pointer lokal | model/TRAIN-025-step1800.pt |
| Checkpoint payload SHA-256 | c1a450149eb8f860cc42595bba283e0f9e915a436f38f967516bc5107bd1c446 |
| Selection report | reports/training/FULLPAGE-V5_DEVELOPMENT_SELECTION.json |
| Selection report SHA-256 | f637c04e80f01d55ff6b37d6b0f2e6b1434a50da572597fd57a80b32bb83f512 |
| Development | 80 dari 80 request diterima validator |
| Final used | false |

Hash request dan identitas output development tersimpan dalam [selection.json](selection.json). Audit 1 November memeriksa kecocokan payload kanonis, salinan lokal, tokenizer, serta laporan seleksi.

## Susunan model lokal

Pointer .pt terluar adalah JSON 213 byte. Folder model/.versions memuat payload bobot dan manifest hash. Pertahankan ketiganya saat menyalin model.

Checkpoint kanonis tetap di checkpoints/FULLPAGE-V5. Output development kanonis tetap di outputs/fullpage/FULLPAGE-V5/TRAIN-025-step1800. Source training tetap di src.

## Menjalankan atau menyiapkan upload

Gunakan [panduan model dan upload](../../../docs/MODEL_RUNTIME_AND_UPLOAD.md) untuk menemukan ZIP terbaru, dependency, dan contoh command. Paket upload memuat kode runtime, tokenizer, schema, aset, serta model lengkap. Bobot dan ZIP tetap diabaikan Git; pengguna dapat mengunggah paket lokal yang sudah disiapkan.

Runtime FastAPI di apps/api memverifikasi selection, laporan, serta hash checkpoint sebelum memuat generator. Frontend chat berada di apps/web. Pemuatan model bersifat lazy.

## Batas evaluasi

Audit berhasil memuat model terpilih pada CUDA tanpa generation baru. Validator development 80/80 mengukur kontrak dan fakta yang diterima pipeline. Inspeksi beberapa halaman di browser merupakan contoh terpilih, bukan pengukuran benchmark visual. Untuk scope mini-proyek, pemilik proyek menerima desain aplikasi. Skor visual 95 persen untuk hasil generasi tidak diklaim dan bukan gerbang penerimaan. Final FULLPAGE-V5 tetap tertutup.
