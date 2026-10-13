# Konfigurasi

Konfigurasi JSON dipisah menurut bagian pipeline:

- `dataset.json`: source/revision, kolom, kuota streaming, disk budget/reserve, split seed, dan lisensi.
- `page_spec.schema.json`: schema komponen, tema, link, dan interaksi yang diizinkan.
- `tokenizer.json`: byte-level BPE, vocabulary 8.192, special tokens, dan blok 1.024.
- `training_pretrain.json`: baseline 1.200 update, optimizer/schedule/BF16/batch, data path, objective dan label alignment.
- `training_sft.json`: kandidat continued training dari checkpoint proyek, format prompt-target, target mask, dan oversize rejection. Memerlukan reviewed production data.
- `model.json`: 6 layer / 6 head / embedding 384 / context 1.024, total 14.186.496 parameter.
- `evaluation.json`: test token penuh dan probe eksploratif PageSpec; bukan benchmark SFT reviewed.

Nilai hyperparameter ditentukan setelah data ditokenisasi dan baseline mengukur VRAM. Setiap run harus menyimpan snapshot konfigurasi, seed, commit, versi package, hash manifest, dan TRAIN ID. Jangan mengedit config run yang sedang aktif.
