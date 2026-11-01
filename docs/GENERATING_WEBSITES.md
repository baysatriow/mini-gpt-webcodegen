# Menjalankan generator website terpilih

Runtime aplikasi memakai TRAIN-025 step 1800 dengan kontrak source-bound-v1. Generator menerima request JSON berisi fakta dan ID yang tervalidasi, membuat plan dan draft section, lalu komposer serta renderer menghasilkan website.

## Persiapan

Gunakan Python 3.11 dalam .venv proyek, PyTorch CUDA yang cocok dengan perangkat, dan tokenizer yang sesuai checkpoint. [Panduan model](MODEL_RUNTIME_AND_UPLOAD.md) menjelaskan susunan file serta paket upload.

Untuk keluaran Tailwind, pasang compiler lokal:

~~~powershell
npm ci --prefix tooling/tailwind
~~~

CSS biasa memakai renderer Python. Runtime FullPageGenerator saat ini memuat model ke CUDA.

## Mencoba pada checkout ini

Jalankan dari root repository. Contoh berikut memakai request development yang disertakan dalam paket upload lokal:

~~~powershell
./.venv/Scripts/python.exe -m qa.generate_fullpage --request outputs/releases/fullpage-v5-TRAIN-025-step1800/examples/requests/demo.json --checkpoint training/selected/fullpage-v5/model/TRAIN-025-step1800.pt --output outputs/manual-TRAIN025-demo
~~~

Pilih nama folder output baru untuk setiap percobaan. Generator menolak direktori output yang sudah ada agar hasil sebelumnya tetap tersimpan.

Contoh request adalah data fiktif dari development yang sudah pernah dievaluasi. Keberhasilan contoh tersebut tidak mengukur generalisasi ke prompt baru. Jangan memakai data final untuk mencoba perubahan.

## Mencoba dari paket yang diekstrak

Dari root paket, siapkan environment sesuai panduan model, lalu jalankan:

~~~powershell
./.venv/Scripts/python.exe -m qa.generate_fullpage --request examples/requests/demo.json --checkpoint training/selected/fullpage-v5/model/TRAIN-025-step1800.pt --output outputs/demo
~~~

CLI ini menerima request JSON terstruktur. Pada aplikasi chat, intake dan editor mengubah brief atau template menjadi fakta yang dikonfirmasi sebelum generator dijalankan.

## Memeriksa hasil

result.json mencatat status, durasi, metadata model, dan attempts. Status accepted berarti hasil melewati validator pipeline. Folder website berisi index.html, styles.css, app.js, PageSpec serta metadata/aset yang diekspor renderer.

Periksa teks, tautan, perilaku interaksi, layout desktop/mobile, dan kesesuaian fakta pada browser sebelum memakai hasil. Form kontak yang disediakan renderer adalah demo lokal sampai ada integrasi pengiriman nyata.

Untuk preview hasil melalui aplikasi, ikuti [panduan frontend](../apps/web/README.md) dan [panduan API](../apps/api/README.md). Preview memakai dokumen mandiri dalam iframe sandbox. Source viewer memformat tampilan kode, sedangkan unduhan mempertahankan artefak renderer asli.

## Batas bukti

Audit 1 November memverifikasi hash, tokenizer, dan pemuatan kandidat pada CUDA tanpa inference baru. Laporan seleksi menerima 80/80 request development. Review visual manusia serta evaluasi final FULLPAGE-V5 belum selesai.

Panduan TRAIN-012/015 disimpan dalam [arsip CLI](history/GENERATING_WEBSITES_BEFORE_2026-11-01.md).
