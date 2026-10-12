# Menjalankan Mini GPT dan Training

Semua command dijalankan dari root proyek menggunakan VENV lokal. Config dan bobot model proyek tidak berasal dari checkpoint pralatih. Hasil baseline saat ini ada di [laporan training](../reports/PIPELINE_TRAINING_SUMMARY.md).

## Profiling, smoke, dan baseline

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label gpu_profile -- .\.venv\Scripts\python.exe qa/profile_minigpt.py --run-id TRAIN-005
.\.venv\Scripts\python.exe qa/run_logged.py --label smoke -- .\.venv\Scripts\python.exe -m qa.train_minigpt --config configs/training_pretrain.json --max-steps 5 --smoke
.\.venv\Scripts\python.exe qa/run_logged.py --label baseline -- .\.venv\Scripts\python.exe -m qa.train_minigpt --config configs/training_pretrain.json
```

Trainer otomatis memilih TRAIN ID berikutnya. `--run-id` dapat dipakai bila nama tersebut belum ada. Profiling memerlukan ID eksplisit dan menyimpan bobot sementara yang dibuang; gunakan ID baru. Smoke memakai subset32train / 8validationblocks, accumulation1, validation/checkpoint setiap step, dan artifact terpisah. `--max-steps` menyimpan override pada snapshot lokal dan tidak mengubah config sumber.

Baseline saat ini dibatasi1.200update, context1.024, BF16, batch4xaccumulation4. Nilai ini berasal dari profiling, bukan ukuran optimal yang dibuktikan. Preparation data/tokenizer harus complete dan hash/cache/config harus cocok. F mempertahankan reserve15GiB sebelum menyediakan ruang last/best checkpoint. GPU dipakai juga oleh aplikasi lain, jadi profil dapat berubah.

## Resume dari checkpoint

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label resume -- .\.venv\Scripts\python.exe -m qa.train_minigpt --config configs/training_pretrain.json --resume checkpoints/TRAIN-003/last.pt
```

Setiap resume mendapat TRAIN ID baru. Model, optimizer, scheduler, RNG, total token, global step, dan posisi batch dipulihkan. Config/data lineage harus identik. `--stop-after` adalah batas run sementara; schedule tetap mengikuti max_steps config. Resume dari checkpoint yang sudah mencapai max_steps hanya memulihkan dan memvalidasi state, tanpa update tambahan. Untuk percobaan baru dengan schedule/data berbeda, gunakan run baru atau continued training dengan inisialisasi bobot proyek.

Data loader memakai sampler deterministik dan num_workers0 agar cursor dapat dipulihkan. Label sudah next-token; loss tidak menggeser lagi. Accumulation dihitung berdasarkan seluruh token valid pada microbatch. Validation mengagregasi token loss dan mengembalikan RNG/mode model sebelum training dilanjutkan.

## Anotasi dan continued training SFT

SFT produksi memerlukan preparation reviewed yang complete. Jangan mengganti status119draft menjadi reviewed tanpa tinjauan manusia. Ikuti [panduan data](PIPELINE_DATA_GUIDE.md).

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label sft -- .\.venv\Scripts\python.exe -m qa.train_minigpt --config configs/training_sft.json --initialize-from checkpoints/TRAIN-004-VERIFIED/best.pt
```

Command tersebut belum dijalankan pada produksi. SFT memakai bobot checkpoint proyek, tokenizer yang sama, optimizer/schedule baru, dan target/padding mask. Resume SFT memakai checkpoint SFT sendiri. Target JSON yang melebihi context ditolak utuh. Config SFT merupakan kandidat dan harus diprofilkan kembali setelah anotasi tersedia.

Parent harus menjalani pretraining proyek, memiliki update, dan bukan smoke. Fingerprint mengikat tokenizer, revision corpus, assignment family, semua partition teks dan token cache. SFT mencatat checksum/phase/step parent serta manifest reviewed. Fingerprint pretraining tetap sama saat hanya menambahkan anotasi; hash seluruh pipeline summary dapat berubah.

TRAIN-004 lama sudah mendapat verified copy pada RUN-076, dengan bobot identik dan tanpa optimizer update. Copy dibuat sebelum summary berubah karena preparation SFT. Untuk checkpoint legacy lain:

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label bind_legacy -- .\.venv\Scripts\python.exe qa/migrate_checkpoint_lineage.py --checkpoint checkpoints/TRAIN-NNN/best.pt --output checkpoints/TRAIN-NNN-VERIFIED/best.pt --report-id TRAIN-NNN
```

Gunakan path/report ID baru. Migration menolak lineage historis yang tidak dapat dibuktikan; tidak menebak split atau menimpa checkpoint lama.

## Artifact dan penanganan kegagalan

- `checkpoints/TRAIN-NNN/`: last.pt/best.pt adalah pointer format baru, payload/manifest checksum immutable dalam `.versions/`, dan config snapshot lokal. Checkpoint lama tetap dibaca dengan format legacy.
- `outputs/metrics/TRAIN-NNN.jsonl`: satu record train setiap update, validation, dan failure event.
- `logs/training/TRAIN-NNN.log`: console ringkas lokal; output command penuh juga dicatat pada RUN yang dilacak Git.
- `reports/training/TRAIN-NNN.json`: status, config/lineage, metric, hash, waktu, environment, peak VRAM, resume parent.

Loss atau gradient nonfinite menghentikan update; OOM/exception dicatat sebagai failed, interupsi sebagai interrupted. Checkpoint terakhir yang sudah selesai dipertahankan; state separuh optimizer update tidak disimpan sebagai checkpoint sukses. Resume dari last_committed_step dapat mengulang kerja sejak checkpoint terakhir, seperti tercatat di failure summary. OOM hardware belum terjadi pada run aktual; jalur failure OOM diuji melalui simulasi pada fixture.

## Evaluasi

Gunakan `src.training.engine.read_checkpoint` untuk membaca pointer/payload verified; `checkpoint_sha256` mengembalikan SHA payload, bukan pointer. Payload/manifest baru diselesaikan dahulu lalu satu pointer di-commit atomik. Generation yang dirujuk last dipertahankan walau best berganti. Recovery dibuktikan lewat fault injection proses, bukan power-loss fisik. Storage trainer memasukkan sampai enam payload selama transaksi/retention.

Mode `production` memerlukan checkpoint SFT dengan ancestry verified. Prompt harus identik dengan isi/ID sumber/review/family artifact SFT test; label reviewed/test saja tidak cukup. Evaluasi token memeriksa fingerprint checkpoint terhadap corpus. Schema alternatif belum didukung, seperti pada [review training](../reports/REVIEW_TRAINING_2026-10-12.md).

Proses per sel tersedia di [notebook](../notebooks/README.md).

```powershell
.\.venv\Scripts\python.exe qa/run_logged.py --label evaluate -- .\.venv\Scripts\python.exe -m qa.evaluate_minigpt --checkpoint checkpoints/TRAIN-004/best.pt --report-id TRAIN-004
```

Config saat ini mengukur test token penuh dan4probe PageSpec buatan dengan label exploratory_unreviewed. Probe tersebut bukan benchmark SFT reviewed. Parsing JSON dan schema diperiksa terpisah; raw output serta error tetap dicatat. Tidak ada skor browser/visual otomatis. Untuk evaluasi produksi, diperlukan reviewed test annotations dan isolasi family yang sama dengan pipeline data.

Rujukan API dasar: [PyTorch AMP](https://docs.pytorch.org/docs/2.14/amp.html), [reproducibility](https://docs.pytorch.org/docs/2.14/notes/randomness.html), [checkpoint](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html). Struktur model/loop proyek ditulis mengikuti kontrak sendiri.
