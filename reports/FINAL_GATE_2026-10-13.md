# Gerbang final model, AI-013

Kandidat TRAIN-015 best dikunci lewat best full validation CE dan development24/24exact sebelum evaluasi final. [Keputusan sebelum final](training/TRAIN-015_FINAL_SELECTION.json) mencatat checkpoint/decode/prompt hash. Hanya satu evaluasi final dilakukan, tanpa memilih ulang checkpoint atau melatih ulang dari hasilnya.

| Pengukuran final | Hasil |
| --- | --- |
| JSON/schema valid | 48/48 |
| Sesuai target persis | 44/48 (91.67%) |
| Link terselesaikan | 48/48 |
| Seluruh output EOS | True |
| Full test token CE / PPL | 0.00298939 / 1.00299386 |
| Gerbang controlled contract | True |
| Runtime terpilih | TRAIN-015/best |

Final v6 byte-identik dengan v5 yang belum dipakai untuk pengembangan. Ambang95%schema/90%exact dan greedy768 tetap. Model memakai bobot dari proyek, bukan pretrained LLM eksternal. 4kesalahan disimpan dalam [record final](training/TRAIN-015_FINAL_GATE.json), tidak diperbaiki setelah decoding.

[Gallery 44 website](../examples\generated\AI-013/index.html), [ZIP hasil](../examples\generated\AI-013/websites.zip). Hanya raw output yang valid dan sesuai kontrak diekspor; 4 output ditolak. HTML/CSS/JS dan Tailwind lokal disediakan, tanpa substitusi target.

## Batas kesiapan

Ini benchmark sintetis dengan recipe komponen yang sama dan keluarga nama baru. Hasil final bukan bukti generalisasi prompt bebas atau layout baru. Benchmark final ini sudah terpakai dan tidak boleh dipakai untuk pemilihan eksperimen berikutnya. Hasil TRAIN-01243/48 berasal dari finalv4 yang berbeda, sehingga bukan perbandingan paired dengan final ini.

**Browser acceptance belum dilakukan. UI aplikasi generator belum dibuat.** Browser lokal sebelumnya ditolak kebijakan tool; tidak memakai jalur alternatif untuk melewati pembatasan tersebut. Preview/interaksi visual tetap tahap terpisah. Setelah kualitas dikaji, tahap berikutnya adalah UI input, validasi, preview sandbox dan unduhan untuk grammar prompt yang didukung.

[Notebook08 training/development](../notebooks/08_kualitas_penyalinan_dan_training.ipynb), [notebook09 final/output](../notebooks/09_evaluasi_final_dan_output.ipynb), [training log](../logs/LOG_TRAINING.md), [evaluasi final](training/TRAIN-015-FINAL_curriculum_evaluation.json).
