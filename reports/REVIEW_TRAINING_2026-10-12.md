# Review model, training, dan evaluasi

Frozen range: `b81cc6191a735df3a9aadf90b7cb0c5f47006816..dd2611001052346617b74856e1da4c609a353a8b`. Satu reviewer dengan konteks baru, read-only. Percobaan pertama tertahan usage limit; review dilanjutkan setelah pengguna meminta lanjut. Hasil: 0 Critical, 5 Important, 1 Minor.

## Perbaikan satu pass

| Important | Dampak | Perbaikan | Regression |
| --- | --- | --- | --- |
| Resume menulis last sebagai best dengan loss historis | Bobot tidak sesuai metrik | Bawa best sebenarnya lewat referensi generation immutable, checksum, step, dan loss | `test_resume_preserves_earlier_best_weights_and_actual_validation` |
| Payload terganti sebelum sidecar selesai | Save gagal menghilangkan checkpoint committed | Payload/manifest immutable dahulu, lalu satu pointer commit atomik | `test_every_failed_save_stage_retains_previous_committed_payload` |
| Parent SFT hanya diperiksa tokenizer | Held-out mungkin pernah dilihat parent | Fingerprint corpus/assignment semua partition, phase, update, smoke, tokenizer, checksum parent, dan riwayat pretraining | `test_sft_initializer_rejects_wrong_corpus_phase_and_untrained_or_smoke_parent` |
| Prompt produksi hanya mengaku reviewed/test | Data train dilabeli held-out | Keanggotaan identik dengan artifact SFT test yang sumber/review/family-nya diverifikasi; duplicate ditolak | `test_production_prompts_require_actual_reviewed_test_membership` |
| Evaluasi token tidak mencocokkan corpus checkpoint | Test baru belum tentu held-out | Cocokkan fingerprint corpus/assignment/tokenizer dan riwayat SFT sebelum evaluasi | `test_heldout_evaluation_rejects_different_assignment_even_with_same_tokenizer` |

RUN-071 red: best step salah, checksum checkpoint rusak setelah sidecar gagal, dan validator lineage belum tersedia. RUN-072 green 55 tests. RUN-074 red untuk helper binding legacy; RUN-075 green 58 tests, termasuk ResourceWarning sebagai error.

Regression tambahan memastikan generation best yang dirujuk last bertahan saat validation lebih sering daripada checkpoint save. Fixture end-to-end menyiapkan corpus kecil, BPE baru, dan anotasi reviewed khusus test; fingerprint pretraining tetap sama setelah preparation anotasi. Prompt train yang mengaku test dan prompt dengan isi berubah ditolak. Fixture tidak mengubah 119 draft produksi.

Reviewer menjalankan 12 tests model/training/evaluation. Suite penuh dijalankan implementer. Tidak ada review kedua setelah fix pass.

## Baseline legacy dan bukti aktual

Checkpoint TRAIN-004 asli tidak ditimpa. Legacy hanya diterima bila SHA pipeline snapshot yang direkam, tokenizer, train/validation cache, seluruh split, dan assignment saat ini masih cocok. Fingerprint tidak ditebak dari preparation yang sudah berubah.

RUN-076 membuat `checkpoints/TRAIN-004-VERIFIED/best.pt` sebelum preparation SFT mengubah summary. Model tensors identik bitwise dengan sumber, optimizer updates 0. Bukti: [migration](training/TRAIN-004_lineage_migration.json).

RUN-077 mengevaluasi copy yang sama melalui gate lineage baru: test loss 1,0709870979895217, perplexity 2,9182586860057063, label valid 2.074.051, probe JSON/schema 0/4. Nilai sama dengan baseline asli; tidak ada tuning atau training tambahan. Bukti: [evaluasi verified](training/TRAIN-004-VERIFIED_evaluation.json).

Format baru memakai pointer `.pt` menuju payload/manifest dalam `.versions/`. Baca melalui `read_checkpoint`; `checkpoint_sha256` mengembalikan SHA payload state yang diverifikasi. `torch.load` langsung hanya untuk payload atau format legacy. Generasi yang dirujuk last dipertahankan ketika best berganti.

## Minor ditunda

- `schema_path` alternatif hanya dihash, sementara validator memakai schema proyek. Config aktual memakai schema yang sama, sehingga bukti baseline tidak terdampak. Custom schema belum didukung. Jangan mengklaim validasi schema alternatif sampai parameter diikat ke validator atau ditolak secara eksplisit.

## Keputusan dan batas

- Ruling: terima lima Important dan tunda satu Minor. Alasan: lima temuan memengaruhi checkpoint atau isolasi data; schema alternatif tidak digunakan pada run aktual. Biaya bila salah: report custom schema masih bisa mencatat provenance yang salah.
- Ruling: verified copy mempertahankan bobot dan riwayat baseline asli. Biaya: sekitar 163 MiB tambahan; SHA payload berubah karena metadata baru.
- Ruling: aplikasi tetap needs-data. JSON probe 0/4 dan reviewed produksi 0. Biaya: software akhir menunggu kurasi/SFT.
- Reviewer mengonfirmasi artifact baseline aktual konsisten. Temuan tidak membuktikan leakage pada run aktual.
- Belum menilai kualitas SFT produksi, visual/browser, trajectory GPU bitwise penuh, crash/power-loss fisik, dan kebenaran review manusia. Recovery dibuktikan melalui fault injection proses, bukan power-loss hardware.
- Notebook berada di luar frozen range reviewer. Format, syntax, kernel, dan seluruh sel dibuktikan melalui eksekusi aktual.

Bukti final: RUN-078 ketiga notebook / 23 sel tanpa error; RUN-079 syntax/JSON/Markdown links/nbformat lulus; RUN-080 seluruh 58 tests lulus setelah penyesuaian reserve transaksi menjadi enam payload.
