# Menjalankan pipeline data

Pipeline ini sudah menyediakan acquisition, PageSpec validation, normalisasi sumber, anotasi, dedup, split, BPE baru, dan batch token. Model dan training model adalah tahap berikutnya. Hasil aktual ada pada `data/manifests/pipeline_summary.json` dan laporan status pipeline di folder reports.

## Pengambilan dan storage

Aktifkan VENV proyek. Jalankan dari root repository:

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label download_dataset -- .\.venv\Scripts\python.exe -m src.data.sources --config configs/dataset.json
```

Config mematok 20.000 WebSight v0.1, 30.000 WebSight v0.2, dan 5.000 Vulcan. WebSight memakai streaming Parquet dengan `columns` pada loader sebelum iterasi. Shuffle memakai seed 42 dan buffer 1.000, bukan sampel acak seragam dari seluruh populasi. Screenshot dan aset URL HTML tidak disimpan atau diambil.

Raw dibatasi total 1 GiB; download dan preparation mempertahankan reserve disk 15 GiB. Seluruh cache baru berada pada `.cache/huggingface` di proyek. Download lengkap diperiksa checksum ketika dipakai ulang. File `.partial`, manifest failed, dan file rusak tidak menjadi input preparation. Partial run yang gagal akan diambil ulang; belum ada resume per baris di tengah source.

## Normalisasi, split, dan tokenizer

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label prepare_dataset -- .\.venv\Scripts\python.exe -m src.data.pipeline --config configs/dataset.json --train-tokenizer
```

Source dipakai untuk pretraining sebagai kode HTML, CSS, atau JavaScript, dengan provenance tetap tersimpan. HTML diberi pemeriksaan root/basic parse. Potongan komponen dapat mendapat pembungkus dengan `html_transform` tercatat; CSS/JS disimpan sebagai teks kode. Deteksi bahasa dan pemeriksaan HTML ini tidak membuktikan kode valid atau berjalan di browser.

Exact duplicate dideduplikasi berdasarkan isi kanonis. Family grouping mengabaikan variasi warna/teks tertentu pada struktur HTML dan nilai tema pada CSS. Seed split 80/10/10 berlaku pada jumlah group, sehingga rasio baris dapat berbeda. Grouping merupakan heuristik dan tidak membuktikan ketiadaan seluruh duplikasi semantik.

BPE baru dilatih hanya dari train partition, vocabulary 8.192, min_frequency 2. Tokenizer disimpan lokal di `data/tokenizer/tokenizer.json`. Token profile mencatat p50/p95/max; metadata train hash dan tokenizer hash ada di manifest. Pretraining memakai blok 1.024 token yang dikemas tanpa membuang ekor dokumen panjang. Token cache uint32 dapat dibaca dengan memory mapping agar tidak memuat seluruh corpus ke VRAM.

`labels[i]` sudah merupakan next token untuk `input_ids[i]`. Training engine nanti harus memakai label secara langsung, tanpa menggesernya lagi. SFT memask label prompt dan padding dengan -100; target JSON yang melebihi konteks ditolak utuh.

## Kurasi instruksi

`data/annotations/review_queue.jsonl` adalah draft hasil ekstraksi sederhana. Anotasi harus di-review, dilengkapi prompt Indonesia, PageSpec yang sesuai, reviewer, annotation_revision, dan group_id. Jangan mengganti label draft menjadi reviewed tanpa benar-benar melakukan tinjauan.

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label prepare_reviewed_sft -- .\.venv\Scripts\python.exe -m src.data.pipeline --config configs/dataset.json --annotations data/annotations/reviewed.jsonl
```

Hanya anotasi yang lulus pemeriksaan menjadi SFT. Dataset SFT membutuhkan setidaknya 10 keluarga template untuk split. Tanpa anotasi reviewed, status `awaiting_review` dilaporkan dengan jelas dan tidak ada SFT train set yang diklaim siap.

## Pemeriksaan dan bukti

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label data_tests -- .\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe qa/run_logged.py --label data_integrity -- .\.venv\Scripts\python.exe qa/check_data_pipeline.py
```

Pemeriksaan integritas memastikan row count, revision/license, raw checksum, split isolation, tokenizer lineage, token cache, label alignment, dan transfer batch kecil ke CUDA. Transfer tensor GPU tidak sama dengan training Mini GPT. Nama reviewer TEST_FIXTURE dalam tests adalah data buatan untuk pengujian, bukan review kelompok atas source produksi.

Raw, processed data, cache, dan tokenizer lokal di-ignore Git. Code, config, manifest kecil, attribution, serta log di-commit dan dipush pada branch feature/pipeline-data-model-training tanpa trailer Co-Authored-By.

Referensi API: [HF Datasets streaming dan projection](https://huggingface.co/docs/datasets/stream), [Tokenizers BPE](https://huggingface.co/docs/tokenizers/en/quicktour). Implementasi proyek ditulis sesuai kontrak sendiri.
