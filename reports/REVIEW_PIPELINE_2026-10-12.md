# Review Pipeline Data, 12 Oktober 2026

Review independen dilakukan oleh agent pipeline_review, model GPT-6 Astra, dengan konteks baru dan akses read-only. Range review: planning baseline `7956be40214dcf98fbe3a3d23bda1d0eaf67b3b4` sampai implementasi `41608790d716e2e9e2682df0203756450d023284`. Scope Tasks 1-5: data, provenance, storage, schema, normalisasi, split, BPE, masking, dan integritas.

Verdict awal: with fixes. Critical 0, Important 4, Minor 0. Sebanyak 30 tests pada range awal lulus, tetapi belum mencakup empat kasus berikut.

| Temuan Important | Bukti perilaku lama | Perbaikan dan bukti |
| --- | --- | --- |
| SFT mengacak ulang subset group | Proyeksi read-only terhadap 119 draft menghasilkan 50 partition mismatch, termasuk 26 calon validation/test SFT dari keluarga train pretraining. Tidak ada draft yang diubah menjadi reviewed. | Persist peta keluarga pretraining, hitung source_group_id dari raw source, warisi partition, dan tolak penggabungan manual yang konflik. Test inheritance, unknown family, missing held-out, map tampering, dan SFT fixture lulus. |
| Atribut HTML tanpa nilai menyebabkan crash | `<div class>` memicu AttributeError; `<input type>` memicu TypeError. | Nilai atribut None diperlakukan sebagai string kosong. Test kedua kasus dan record berikutnya lulus tanpa menghentikan normalisasi. |
| Preparation anotasi menghilangkan lineage tokenizer/cache dari summary | Command tanpa --train-tokenizer menimpa summary lengkap dengan summary tanpa tokenizer/cache. | Verifikasi config, train hash, tokenizer hash, profile, cache hash/count/bytes sebelum reuse. Jika tidak cocok, status requires_tokenization. Fixture menguji reuse serta cache rusak. |
| Checker menolak semua SFT produksi yang berhasil | Assertion selalu meminta reviewed 0 dan train SFT tidak ada. | Checker mengikuti status SFT; completed diverifikasi schema, review, provenance, checksum, row count, dan partition sumber. Awaiting_review tidak boleh memiliki manifest SFT complete yang usable. |

## Verifikasi setelah satu pass perbaikan

- RUN-048: regression gagal pada implementasi lama, termasuk atribut kosong dan source linkage yang belum tersedia.
- RUN-049: 37 tests lulus; resource warning file queue ditemukan dan handle ditutup dengan context manager.
- RUN-050: 37 tests kembali lulus dengan ResourceWarning sebagai error. SFT complete diuji hanya pada data buatan TEST_FIXTURE, tanpa mengubah status anotasi produksi.
- RUN-051: preparation aktual kembali menerima 54.996, menolak 4, menghapus 3.785 duplicate, dan mempertahankan 51.211 contoh serta checksum split/tokenizer/cache. Tokenization action reused.
- RUN-052: checksum seluruh raw/split/peta keluarga/tokenizer/cache, lineage, masking, dan transfer batch [2,1024] ke RTX 5070 lulus. Free storage F 28.402.155.520 bytes.

RUN-048 sampai RUN-052 dijalankan pada working tree perbaikan sebelum commit, dengan HEAD dasar `4160879` seperti tercantum di log console. Perbaikan dan bukti disimpan bersama pada commit berikutnya di branch feature/pipeline-data-model-training. Tidak ada review independen kedua; perbaikan diverifikasi melalui regression suite dan pemeriksaan data aktual.

## Batas review

Model, optimizer, training, OOM/NaN, checkpoint, dan resume berada pada Tasks 6-9 dan belum dinilai. Validitas syntax penuh HTML/CSS/JavaScript, rendering browser, dan duplikasi semantik di luar fingerprint belum dibuktikan. Anotasi produksi: 119 draft, 0 reviewed. Klaim reviewer dalam fixture tidak berarti review manusia terhadap source produksi.

Code dan log dipush ke repo private; raw/processed data, tokenizer, cache, dan VENV tetap lokal serta di-ignore Git. Tidak ada merge ke main atau aplikasi produk pada tahap data ini.
