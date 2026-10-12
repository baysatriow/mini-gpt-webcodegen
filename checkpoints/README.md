# Checkpoint Model

Checkpoint besar hanya disimpan di folder lokal ini dan tidak dilacak Git.

- Simpan `last` untuk resume dan `best` berdasarkan metrik validation yang ditentukan sebelum run.
- Sertakan state model, optimizer, scheduler, RNG, global step, tokenizer hash, config, source manifest hash, dan TRAIN ID.
- Catat path, ukuran, langkah training, serta hasil load/resume di `logs/LOG_TRAINING.md`.
- Jangan menaruh bobot model pralatih pihak ketiga. Mini GPT proyek dimulai dari bobot acak.
