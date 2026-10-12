# Review anotasi PageSpec

Pipeline membuat review_queue.jsonl lokal sebagai DRAFT. Bentuk hero sederhana hasil ekstraksi HTML bukan konversi lengkap dan tidak boleh dilatih sebagai target yang telah disetujui.

Kelompok meninjau sumber, menulis prompt Bahasa Indonesia, memeriksa seluruh PageSpec/tema/interaksi, mempertahankan group_id keluarga layout, lalu mengisi reviewer, annotation_revision, prompt_language=id, dan annotation_status=reviewed. Review JSON awal tidak menjadi bukti tampilan/interaksi browser.

Normalizer menolak draft, prompt kosong, reviewer kosong, unknown source_row_id, metadata lisensi yang kosong, dan schema invalid. Tidak ada anotasi produksi yang diklaim telah ditinjau manusia. JSONL review lokal di-ignore karena berisi turunan source data.
