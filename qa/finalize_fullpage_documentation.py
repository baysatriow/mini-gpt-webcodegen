"""Document actual fullpage evidence without replacing historical log entries."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); args=p.parse_args(); root=args.root.resolve()
    def read(path): return json.loads((root/path).read_text(encoding='utf-8'))
    pilot=read('reports/training/TRAIN-016.json'); main=read('reports/training/TRAIN-017.json')
    best=read('reports/fullpage/TRAIN-017_DEVELOPMENT_BEST_V2.json'); last=read('reports/fullpage/TRAIN-017_DEVELOPMENT_LAST_V2.json')
    if any(r['total']!=80 for r in (best,last)) or main['status']!='completed': raise ValueError('Delivery requires completed training/development evidence')
    if best['model_gate']: raise ValueError('Use locked final workflow before documenting final disposition')
    text=f'''# Progress halaman utuh, 14 Oktober 2026

## Hasil utama

Pipeline bertahap sudah menghasilkan halaman lengkap sembilan bagian pada sebagian request development. Model belum memenuhi gerbang95%; status **needs_more_model_work**. Final baru80 halaman tetap tertutup. Runtime v1/AI-013 dan artefak historis dipertahankan. UI aplikasi belum dikerjakan.

| Tahap | Update | Durasi | Ordinary CE terbaik | Complete generation |
| --- | ---: | ---: | ---: | ---: |
| TRAIN-016 pilot | 600 | {pilot['wall_seconds']:.2f} detik | {pilot['best_validation_loss']:.6f} | 0/20 development |
| TRAIN-017 best | 2400 total, best step1200 | {main['wall_seconds']:.2f} detik total | {main['best_validation_loss']:.6f} | {best['complete']}/80 ({best['complete_rate']*100:.2f}%) |
| TRAIN-017 last | 2400 | run yang sama | {main['final_validation']['loss']:.6f} | {last['complete']}/80 ({last['complete_rate']*100:.2f}%) |

Best dipilih dengan ordinary CE sesuai aturan yang dibekukan. Last dilaporkan sebagai diagnosis; tidak dipromosikan sebagai kandidat final. First-attempt complete best={best['first_attempt_complete']}, last={last['first_attempt_complete']}; sesudah maksimal satu retry={best['complete']}/{last['complete']}. Semua ekspor accepted lolos fakta terstruktur, required roles, CTA/fragment dan aset. Ini belum membuktikan kualitas browser atau penilaian manusia.

## Teknologi dan flow aktual

Request JSON berisi prompt, genre, style, business facts dan asset IDs. Model menghasilkan plan ringkas enam elemen per descriptor, kemudian menghasilkan isi masing-masing bagian. Validator menolak struktur/fakta yang salah. Komposer tidak mengisi konten yang gagal. Renderer mengekspor HTML, CSS biasa atau Tailwind lokal, SVG milik proyek dan JavaScript dari katalog. Formulir hanya memvalidasi lokal.

Context2048; plan output512; section output1536, prefix maksimal512 termasuk tiga penanda. EOS dapat mengakhiri keluaran lebih dini. Tidak ada truncation atau target fallback. Model14.579.712 parameter,6layer/6head/embed384, tokenizer proyek8192; tambahan posisi diperiksa dan dilatih, tanpa pretrained LLM eksternal.

## Data dan batas klaim

Curriculum baru240/40/40 families, dua genre dan dua style per family. Train5760, development960, final800 task rows. Semua sintetis, human_reviewed=False;12 anotasi human-reviewed historis tidak berubah. Shared component text dan template berulang secara sengaja. Empat sektor demo: studio, kafe, kursus, toko.

960 train rows termasuk retry mempunyai supervised labels setelah posisi1024. Sidecar6720 prompt/target hashes train/development tersedia. Final dibekukan sebelum training; target final tidak dipakai untuk fitting atau selection.

Urutan target tertentu ditahan antar split, tetapi request tidak meminta urutan tersebut secara eksplisit. Gerbang menerima urutan yang memenuhi role/fakta. Hasil ini bukan bukti generalisasi layout/order baru atau semua prompt bebas.

## RTX5070 dan storage

Profil batch4/8/12/16 dilakukan pada panjang2048 dan task sebenarnya. Batch16/accum3 dipilih, effective48, BF16/SDPA/fused AdamW, supervised-only projection. Throughput profil representative72030 target token/s; profil pendek dan campuran task berbeda mempunyai noise.

TRAIN-017 memakai {main['total_train_tokens']:,} label target. GPU telemetry seluruh run: mean utilization{main['gpu_telemetry']['utilization_pct']['mean']:.2f}%, max{main['gpu_telemetry']['utilization_pct']['max']:.0f}%, suhu max{main['gpu_telemetry']['temperature_c']['max']:.0f}C. Peak allocated{main['peak_allocated_bytes']/2**30:.2f}GiB. Disk free sesudah run{main['free_bytes_after']/2**30:.2f}GiB. Best weights-only; exact resume memakai last dengan optimizer/scheduler/RNG/sampler. Reserve15GiB dan phase budget1.5GiB diperiksa sebelum checkpoint writes; tidak menghapus checkpoint/data lama.

## Mapping delapan tahap

| Tahap | Bukti | Status |
| --- | --- | --- |
| Kontrak dan token budget | RUN-206/207/208 | Implemented, fixture diagnosis |
| Migrasi positional embedding | RUN-209/210 | Identical old tensors dan short-prefix logits |
| Curriculum dan loader | RUN-211/212/226 | Frozen families, EOS/masking/sampler checked |
| Composer/renderer/aset | RUN-213 | Empat fixture manual, browser pending |
| Generator bertahap | RUN-214/215/230/231 | Raw attempts, retry, failure; sebagian halaman lengkap |
| Profil dan training | RUN-216/217/220/225/229 | Pilot dan main selesai |
| Gate dan final | RUN-230/231 | Development gagal95%; final tidak dijalankan |
| Notebook dan delivery | Notebook10/11, log dan gallery | Output aktual, human/browser pending |

## Artefak

- [Gallery best{best['complete']}](../examples/generated/AI-018-best-v2/index.html), [ZIP best](../examples/generated/AI-018-best-v2/websites.zip).
- [Gallery last{last['complete']}, diagnosis](../examples/generated/AI-018-last-v2/index.html), [ZIP last](../examples/generated/AI-018-last-v2/websites.zip).
- [Notebook10](../notebooks/10_fullpage_data_context_dan_gpu.ipynb), [notebook11](../notebooks/11_fullpage_training_dan_generation.ipynb).
- [Best development](fullpage/TRAIN-017_DEVELOPMENT_BEST_V2.json), [last development](fullpage/TRAIN-017_DEVELOPMENT_LAST_V2.json), [log training](../logs/LOG_TRAINING.md).

## Koreksi review dan hasil historis

Review menemukan nama hero Studio Pusanu untuk request Studio Pusanupu pada dua halaman BEST. RUN-234 mereproduksi celah nama, fakta tambahan dan konsumsi final. RUN-235 memeriksa koreksi menggunakan output asli serta claim sementara tanpa membaca final. RUN-236/237 memvalidasi ulang raw accepted: best turun41 menjadi39, last tetap58. Tidak ada model generation, target fallback atau perubahan output asli. Report V2 menjadi sumber acceptance saat ini.

Fakta layanan/proyek/tim/proses/FAQ/testimoni/harga hanya boleh berasal dari facts yang dirujuk. fictitious=True adalah pengungkapan demo; fakta demo tetap harus diberikan di request. Teks pemasaran umum masih diperbolehkan dan tidak dinilai sebagai verifikasi semua klaim bahasa alami. Guard final menyimpan identitas sebelum membaca request final, dengan hanya matching resume; final sebenarnya belum diklaim/dibuka.

Gallery awal dan ZIP lama adalah snapshot sebelum koreksi. Index awal dipertahankan dengan nama index_pre_review.html; index saat ini menampilkan notice superseded. Manifest awal hanya mengikat ZIP historis. Gallery V2 mempunyai manifest/ZIP baru dan revalidation.json per halaman, sementara result.json asli tetap historis.

Dua minor ditunda: binding scope/development request identity pada candidate lock, dan retry error-category yang membutuhkan contoh curriculum baru. Lihat laporan review [AI-018_REVIEW_AND_RULINGS.md](fullpage/AI-018_REVIEW_AND_RULINGS.md). Final dan aktivasi runtime tetap ditutup karena gate belum95%.

## Pekerjaan berikutnya

Perlu eksperimen train-only untuk kesalahan tuple plan, referensi media dan field isi bagian; tetap gunakan final yang belum dibuka. Perjelas layout/urutan yang diminta di request pada revisi data baru. Setiap budget/data/selection revision dibekukan sebelum run dan wajib tetap muat disk, tanpa memperlonggar validator atau mengisi keluaran gagal.

Review manusia dan browser390/1440 belum selesai. Tidak ada rating yang dibuat atas nama manusia. Unit test suite tidak ditambahkan/dijalankan sesuai instruksi sesi; bukti yang dilaporkan berupa diagnosis pipeline, profiling, training dan generation aktual.
'''
    path=root/'reports/FULL_PAGE_PROGRESS_2026-10-13.md'
    if path.exists(): raise ValueError('Progress document exists')
    with path.open('x',encoding='utf-8',newline='\n') as h: h.write(text)
    section=f'''## Halaman utuh, AI-018

Generasi bertahap sudah diimplementasikan: request terstruktur → plan512 → isi section1536 → validasi fakta/komposer → HTML/CSS biasa atau Tailwind/JavaScript lokal. Context2048. TRAIN-016600 dan TRAIN-0172400 updates selesai di RTX5070 dengan batch16/accum3.

**Model belum mencapai gerbang95%.** Development best{best['complete']}/80 ({best['complete_rate']*100:.2f}%), last{last['complete']}/80 ({last['complete_rate']*100:.2f}%). Semua accepted menjadi halaman lengkap sembilan bagian, tetapi final baru tetap tertutup. Runtime historis v1 tidak diubah. UI, review manusia dan penerimaan browser masih pending.

Lihat [gallery last{last['complete']} untuk diagnosis](examples/generated/AI-018-last-v2/index.html), [gallery best{best['complete']}](examples/generated/AI-018-best-v2/index.html), [notebook10](notebooks/10_fullpage_data_context_dan_gpu.ipynb), [notebook11](notebooks/11_fullpage_training_dan_generation.ipynb) dan [laporan lengkap](reports/FULL_PAGE_PROGRESS_2026-10-13.md). Data baru sintetis empat sektor; ini belum membuktikan semua prompt/layout bebas.

'''
    readme=root/'README.md'; original=readme.read_text(encoding='utf-8')
    if '## Halaman utuh, AI-018' in original: raise ValueError('README delivery already recorded')
    readme.write_text(original.replace('## Pengembangan terbaru, 13 Oktober 2026',section+'## Pengembangan terbaru, 13 Oktober 2026',1),encoding='utf-8',newline='\n')
    with (root/'logs/PIPELINE_PROGRESS.md').open('a',encoding='utf-8',newline='\n') as h:
        h.write(f'\n## AI-018: implementasi dan training halaman utuh\n\n- Kontrak2.048/plan512/section1.536, migrasi posisi, curriculum320families, composer/renderer/aset lokal dan generator bertahap tersedia.\n- TRAIN-016600 dan TRAIN-0172400 selesai. Best{best["complete"]}/80, last{last["complete"]}/80 development; keduanya gagal95%. Final tetap tertutup.\n- Gallery accepted saja, notebook10/11 dan [laporan](../reports/FULL_PAGE_PROGRESS_2026-10-13.md) tersedia; human/browser/UI pending. Artefak lama tetap dipertahankan.\n')
    print(json.dumps({'document':str(path),'best_complete':best['complete'],'last_complete':last['complete'],'final_opened':False,'status':'needs_more_model_work'},indent=2))


if __name__=='__main__': main()
