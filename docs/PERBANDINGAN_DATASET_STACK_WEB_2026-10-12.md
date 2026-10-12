# Perbandingan dataset untuk HTML, CSS, dan JavaScript

Tanggal: 12 Oktober 2026. Status: rekomendasi penelitian, belum keputusan arsitektur atau dataset final.

## Rekomendasi

Untuk website sederhana dengan variasi layout, kandidat utama paling sesuai dari sumber yang sudah diperiksa adalah WebSight v0.2 jika keluaran website memakai HTML + Tailwind CSS. Interaksi tetap menggunakan JavaScript murni, dengan data tambahan yang dikurasi. Untuk keluaran HTML + CSS biasa + JavaScript murni, Vulcan paling sesuai formatnya, tetapi hanya layak sebagai seed percobaan komponen karena keragaman tugasnya sangat terbatas. Belum ada korpus Bootstrap yang cukup kuat dan sudah terverifikasi untuk direkomendasikan sebagai sumber utama.

Framework untuk antarmuka aplikasi generator dapat dipilih terpisah. Dataset perlu cocok dengan bahasa dan framework website yang dihasilkan model atau renderer.

| Keluaran website | Kandidat data | Batas penggunaan |
| --- | --- | --- |
| HTML + CSS biasa + JavaScript murni | Vulcan sebagai seed; WebSight v0.1 sebagai tambahan layout | Vulcan sangat repetitif; v0.1 tidak menyediakan kolom ide sehingga pasangan instruksi perlu dibuat dan diperiksa |
| HTML + Tailwind CSS + JavaScript murni | Subset teks WebSight v0.2, ditambah data interaksi yang dikurasi | Data utama mengajarkan layout; belum cukup untuk JavaScript interaktif |
| HTML + Bootstrap + JavaScript | Data khusus Bootstrap atau konversi yang diperiksa | Jangan menganggap data CSS biasa atau Tailwind langsung mengajarkan Bootstrap |

## Audit lengkap Vulcan

Sumber: [xlelords/vulcan](https://huggingface.co/datasets/xlelords/vulcan).
Revision: `19d2a482c78554e59feca0ce2b50fb7835e90c6f`. Lisensi yang dinyatakan: MIT. RUN-011 berhasil mengambil file pada revision tersebut dan melakukan pemeriksaan teks statis.

- 5.000 baris total, 4.750 train, dan 250 validation.
- Hanya 14 teks prompt pengguna unik.
- Seluruh 5.000 keluaran assistant unik secara persis dan setelah normalisasi whitespace. Ini tidak membuktikan 5.000 jenis tugas atau template berbeda.
- 1.200 baris mempunyai script dan addEventListener, tetapi hanya dua isi script unik setelah normalisasi whitespace.
- Pemeriksaan isi dua script pada RUN-012 menunjukkan menu hamburger dan validasi formulir kontak.
- 1.800 baris mempunyai doctype; sumber juga berisi snippet CSS dan komponen, sehingga keluaran tidak selalu dokumen HTML lengkap.
- Tidak ada referensi Tailwind atau Bootstrap pada keluaran assistant.
- Semua 250 baris validation memiliki prompt yang sudah ada pada train. Tidak ada keluaran validation yang sama persis setelah normalisasi whitespace dengan keluaran train.

Kesimpulan: split bawaan dapat mengukur variasi keluaran untuk tugas yang sama, tetapi tidak membuktikan kemampuan pada jenis permintaan baru. Evaluasi proyek perlu memisahkan keluarga komponen/template dan menyediakan tugas baru. Tidak ada kode dataset yang dieksekusi dalam audit ini; fungsi JavaScript belum diuji di browser.

## WebSight dan dataset sebelumnya

[WebSight](https://huggingface.co/datasets/HuggingFaceM4/WebSight) v0.2 menyediakan HTML dengan Tailwind serta kolom llm_generated_idea. Ini memungkinkan pasangan ide-ke-kode setelah kurasi. Audit sebelumnya atas 800 baris dalam delapan blok nonacak menemukan semua memakai Tailwind dan hanya satu memiliki script. Angka sampel bukan statistik seluruh korpus. Subset teks dapat diambil tanpa mengunduh seluruh screenshot.

Kartu WebSight memberi contoh referensi Tailwind 2.2.19. Versi framework pada target training dan renderer perlu ditetapkan, lalu referensi dan kelas dinormalisasi. Jangan menganggap dataset sudah sesuai versi Tailwind yang nantinya dipilih. Lisensi CC-BY-4.0 dan ketentuan pengungkapan penggunaan perlu dipertahankan dalam provenance data.

WebMC yang benar-benar tersedia adalah 600 soal pilihan ganda, sehingga bukan korpus utama instruksi-ke-website. Webdev Coding Dataset dapat menjadi seed tambahan setelah aksesnya berhasil; tiga endpoint sebelumnya menghasilkan HTTP 401.

## Dampak terhadap workflow proyek

Jika Mini GPT tetap menghasilkan spesifikasi JSON, data ide-ke-HTML perlu dikonversi menjadi pasangan prompt-ke-spesifikasi dan ditinjau secara semantik. Tailwind atau CSS biasa kemudian dipakai oleh renderer, sedangkan interaksi seperti menu, tabs, accordion, validasi form, filter, dan modal dipilih dari fungsi renderer yang sudah disediakan. Tidak perlu memaksa model menghasilkan semua JavaScript dari nol untuk workflow ini.

Jika Mini GPT langsung menghasilkan kode, gunakan target output konsisten untuk HTML, CSS, dan JavaScript. Tambahkan pasangan instruksi yang mencakup interaksi dan hasil pemeriksaan browser. Dataset Vulcan sendiri tidak cukup sebagai bukti bahwa model dari nol akan menjadi generator website serbaguna; kartunya memang menargetkan SFT/fine-tuning.

Usulan tahap berikutnya: tetapkan satu stack keluaran dan pilihan kode langsung atau spesifikasi JSON, kurasi subset layout yang pendek dan beragam, susun data interaksi yang cocok, lalu buat split berdasarkan keluarga template. Tidak ada training, implementasi model, atau perubahan pipeline yang dilakukan pada sesi ini.

Artefak audit: outputs/dataset_audit/vulcan_summary.json, qa/audit_vulcan.py, logs/RUN-011_vulcan_audit.txt.
