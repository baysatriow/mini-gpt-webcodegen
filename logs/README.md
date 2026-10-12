# Log Eksperimen

Gunakan [log utama](LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md) untuk setiap run command/audit dan interaksi LLM. Gunakan [log training](LOG_TRAINING.md) untuk percobaan pretraining, penyelarasan, resume, dan evaluasi.

- Setiap proses mendapat `RUN-NNN`; setiap percobaan training mendapat `TRAIN-NNN` dan merujuk RUN IDs.
- Setiap sesi pembuatan kode atau debugging LLM mendapat `AI-NNN` dengan ringkasan dan path ekspor Markdown/PDF atau share link.
- Simpan kronologi prompt, output ringkas, keputusan kelompok, error penuh, solusi, verifikasi, commit, data/config, metrik, dan path artefak.
- Proses gagal atau dihentikan tetap dicatat. Jangan menghapus atau menimpa riwayat.
- Jangan mencatat API key, password, token, URL bertanda tangan, atau data pribadi.
- Training Mini GPT belum dimulai. `TRAIN-001` adalah nomor yang disiapkan, bukan hasil eksperimen.
