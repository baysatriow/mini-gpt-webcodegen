# Review anotasi PageSpec

Pipeline membuat review_queue.jsonl lokal sebagai DRAFT. Bentuk hero sederhana hasil ekstraksi HTML bukan konversi lengkap dan tidak boleh dilatih sebagai target yang telah disetujui.

Kelompok meninjau sumber, menulis prompt Bahasa Indonesia, memeriksa seluruh PageSpec/tema/interaksi, mempertahankan group_id keluarga layout, lalu mengisi reviewer, annotation_revision, prompt_language=id, dan annotation_status=reviewed. Review JSON awal tidak menjadi bukti tampilan/interaksi browser.

Normalizer menolak draft, prompt kosong, reviewer kosong, unknown source_row_id, metadata lisensi yang kosong, dan schema invalid. Tidak ada anotasi produksi yang diklaim telah ditinjau manusia. JSONL review lokal di-ignore karena berisi turunan source data.

## Pilot prompt Indonesia

AI-008 menyiapkan `pilot_drafts_id_v1.jsonl`: 12 draft dari 12 keluarga, 6 CSS biasa dan 6 Tailwind. Semua tetap draft, tanpa reviewer. Paket perbandingan dan worksheet lokal ada di `outputs/annotation_review/pilot-id-v1/`.

Baca [panduan review](../../docs/ANNOTATION_REVIEW_GUIDE.md) dan [notebook kurasi](../../notebooks/04_kurasi_dan_sft.ipynb). Pertahankan paket awal sebagai bukti, simpan revisi di path baru, dan jangan mengganti status menjadi reviewed melalui persetujuan otomatis.

AI-009 menyiapkan revisi `pilot_drafts_id_v2.jsonl` dan paket terbaru `outputs/annotation_review/pilot-id-v2/`. Empat target/lima prompt diperbaiki; family dan partition sama. Seluruh fragmen kini menunjuk section yang tersedia. Tetap draft, reviewed produksi 0. Katalog tambahan 14 kandidat train tersimpan terpisah dan belum berisi target SFT.
