# Konfigurasi

Konfigurasi JSON dipisah menurut bagian pipeline:

- `dataset.json`: source/revision, kolom, kuota streaming, disk budget/reserve, split seed, dan lisensi.
- `page_spec.schema.json`: schema komponen, tema, link, dan interaksi yang diizinkan.
- `tokenizer.json`: byte-level BPE, vocabulary 8.192, special tokens, dan blok 1.024.
- `training_pretrain.json`: data path, objective next-token, dan label alignment. Hyperparameter optimizer/model belum dipilih.
- `training_sft.json`: format prompt-target, target mask, serta oversize rejection.
- `model.json` dan `evaluation.json`: disusun pada tahap model/evaluasi berikutnya.

Nilai hyperparameter ditentukan setelah data ditokenisasi dan baseline mengukur VRAM. Setiap run harus menyimpan snapshot konfigurasi, seed, commit, versi package, hash manifest, dan TRAIN ID. Jangan mengedit config run yang sedang aktif.
