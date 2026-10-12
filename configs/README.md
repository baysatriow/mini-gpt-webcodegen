# Konfigurasi

Konfigurasi YAML untuk implementasi kelak dipisah menurut bagian pipeline:

- `dataset.yaml`: source/revision, kolom, kuota streaming, filter, dedup, split seed, dan lisensi.
- `tokenizer.yaml`: byte-level BPE, vocabulary, special tokens, dan context length.
- `model.yaml`: dimensi embedding, layer/head, positional embedding, dropout, dan parameter.
- `training_pretrain.yaml`: objective next-token, optimizer, learning rate, effective batch, steps, precision, scheduler, dan checkpoint.
- `training_sft.yaml`: format prompt-target, target mask, continued training, serta interval validation.
- `evaluation.yaml`: held-out prompts, decoding, pemeriksaan schema, dan rubric manual.

Nilai hyperparameter ditentukan setelah data ditokenisasi dan baseline mengukur VRAM. Setiap run harus menyimpan snapshot konfigurasi, seed, commit, versi package, hash manifest, dan TRAIN ID. Jangan mengedit config run yang sedang aktif.
