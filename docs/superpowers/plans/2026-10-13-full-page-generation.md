# Full Page Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membuat Mini GPT menghasilkan landing page dan company profile lengkap melalui plan dan isi per bagian, dengan konteks 2.048 serta output maksimum 1.536 token.

**Architecture:** Dua task generasi memakai tokenizer proyek yang sama. Validator memastikan bentuk dan referensi, komposer menyatukan PageSpec2, renderer menghasilkan website dengan aset lokal. Migrasi posisi dipisahkan dari exact resume; engine training lama dipakai dengan adapter yang khusus untuk task baru.

**Tech Stack:** Python 3.11/VENV proyek, PyTorch/BF16/SDPA, byte-level BPE, JSON Schema, JSONL, nbformat/nbclient, HTML/CSS/Tailwind dan vanilla JavaScript.

**Spec:** `docs/superpowers/specs/2026-10-13-full-page-generation-design.md`.

## Global Constraints

- block_size=2048, vocab_size=8192, n_layer=6, n_head=6, n_embd=384. Tokenizer dan bobot proyek; tidak ada pretrained LLM eksternal.
- Output plan512, section1.536; prefix section termasuk tiga penanda maksimum512. Prefix plus budget output tidak melebihi2.048.
- Style plain_css/tailwind, bahasa awal Indonesia, request terstruktur, 8 sampai12 bagian default lengkap dan maksimum 16 sesuai schema.
- TRAIN-015/checkpoint, schema v1, final AI-013, data v6 dan notebook lama dipertahankan. Final AI-013 consumed.
- Dataset baru240 train/40 development/40 final families, dua genre seimbang dan dua style per keluarga. Pilot40 train/10 development. Semua task/variant/retry satu keluarga berada pada split yang sama.
- human_reviewed=False untuk data sintetis; reviewed manusia tetap 12 sampai ada keputusan anotasi terpisah.
- Reserve disk15GiB; anggaran artefak fase baru1,5GiB termasuk temporary write. Tidak menghapus artefak lama.
- Profil batch 4/8/12/16, gunakan BF16/SDPA dan optimasi yang terbukti. Tidak mengasumsikan batch48 masih cocok.
- Minimal95% complete/schema dan95% required-section coverage. Seluruh hasil ekspor harus lolos fakta terstruktur, tautan, interaksi serta aset. Rubrik manusia/browser terpisah.
- Tiap eksekusi memakai qa.run_logged; kegagalan/rerun punya RUN baru. Log training/interaksi bersifat append-only, tanpa rahasia, em dash atau Co-Authored-By.
- Commit/push pada feature/pipeline-data-model-training. Main tetap snapshot progres sementara sampai ada instruksi integrasi berikutnya.
- Sesuai instruksi sesi, jangan menambah atau menjalankan test suite tanpa permintaan pengguna. Langkah pemeriksaan di bawah adalah diagnosis, inspeksi artefak, profiling dan evaluasi pipeline yang diminta; bukan klaim unit tests.

## Review Focus

1. Prefix tepat512 dan513: terima512 dengan budget1.536, tolak513 sebelum generasi tanpa truncation. Task1/5 memeriksa batas termasuk penanda dan EOS.
2. Migrasi posisi atau parent palsu: hanya ekstensi1.024 ke2.048 dari parent proyek yang cocok, tensor lama identik dan optimizer baru. Task2 memeriksa tensor/hash/konfigurasi.
3. Variant/provenance tersebar antar-split: satu business family dan seluruh task turunannya harus tetap bersama; final tidak dibaca saat fitting. Task3 memeriksa manifest dan sumber input.
4. Aset/tautan/fakta salah meski JSON valid: tolak sebelum ekspor, termasuk path traversal serta CTA ke ID yang tidak ada. Task1/4/5 memeriksa fixture negatif dan raw outputs.
5. Model berhenti karena token/context limit atau retry berulang: simpan stop reason dan percobaan; maksimal satu retry, halaman tidak diterima jika masih gagal. Task5/7 memeriksa kegagalan per tahap.

## Struktur file dan tanggung jawab

| Unit | File baru | File existing yang disentuh |
| --- | --- | --- |
| Kontrak dan serializer | configs/fullpage/{request,plan,section,page}.schema.json; src/fullpage/{__init__,contracts,serialization}.py | Tidak mengubah schema v1 |
| Migrasi/checkpoint ancestry | src/training/context_extension.py; src/fullpage/lineage.py; qa/extend_context.py; configs/model_fullpage_2048.json | src/training/engine.py, hanya dispatch initial checkpoint baru |
| Curriculum/task loader | src/fullpage/{curriculum,dataset}.py; qa/prepare_fullpage_curriculum.py | src/training/engine.py, adapter data_origin baru |
| Media/komposer/renderer | src/fullpage/{assets,compose,renderer}.py; assets/fullpage/catalog.json; assets/fullpage/*.svg; qa/render_fullpage_fixture.py | src/rendering/renderer.py tetapv1 |
| Profil/training | qa/{profile_fullpage_training,train_fullpage}.py; configs/fullpage/{pilot,training,evaluation}.json | Reuse engine/performance/sampler checkpoint helpers |
| Generasi/evaluasi | src/fullpage/{generation,evaluation}.py; qa/{generate_fullpage,evaluate_fullpage}.py | Evaluator final lama tidak dimodifikasi |
| Notebook/report | qa/record_fullpage_progress.py; notebooks/10_fullpage_data_dan_konteks.ipynb; notebooks/11_fullpage_training_dan_generasi.ipynb | README dan logs ditambah |

Tabel adalah rencana file, bukan direktori produk yang sudah dibuat. Modul kecil dipisahkan menurut satu tanggung jawab. Tidak membangun API/UI aplikasi pada rencana ini.

## Task 1: Kontrak tertutup dan budget task

**Files:** Create configs/fullpage schemas, src/fullpage/contracts.py, serialization.py dan __init__.py.

**Interfaces:** `validate_request(request: dict, catalog: dict) -> list[str]`; `validate_plan_wire(plan: dict, request: dict, catalog: dict) -> list[str]`; `decode_plan(wire: dict) -> dict`; `validate_section(section: dict, descriptor: dict, request: dict, catalog: dict) -> list[str]`; `serialize_task(task: str, value: dict) -> str`; `check_budget(tokenizer, prompt: str, output_budget: int, block_size: int=2048) -> dict`.

- [ ] Buat schema Draft202012 tertutup. Request berisi request_id/prompt/genre/style_mode/business_facts. business_facts berbentuk array objek `{id, kind, value}` dengan ID unik, kind name/description/service/contact/project/price/testimonial/team/value/process/faq. name dan description wajib, service minimal satu; contact/project/dll opsional. Item complex value divalidasi menurut kind, bukan arbitrary JSON. Aset melalui asset_ids katalog.
- [ ] Plan root memuat schema_version1.0/title/genre/language/style_mode/theme/sections. Tiap descriptor berupa enam elemen; title maksimal 180, ID mengikuti pola v1, jenis/role/variant enum kompatibel, fact_ids/asset_ids harus tersedia pada input. Seluruh plan memakai satu genre/style, navbar pertama dan footer terakhir, required roles dari spec. Props section mewarisi delapan tipe v1 dengan tambahan media `{asset_id,alt,caption?}` dan varian terbatas.
- [ ] Implementasikan serializer tuple dan budget dengan isi berikut, melengkapi validasi sebelum decode dan memastikan input tanpa reserved delimiter:

```python
SECTION_FIELDS = ('id', 'type', 'role', 'variant', 'fact_ids', 'asset_ids')

def decode_descriptor(values):
    if not isinstance(values, list) or len(values) != 6:
        raise ValueError('Invalid section tuple length')
    return dict(zip(SECTION_FIELDS, values, strict=True))

def check_budget(tokenizer, prompt, output_budget, block_size=2048):
    prefix = 3 + len(tokenizer.encode(prompt, add_special_tokens=False).ids)
    if prefix + output_budget > block_size:
        raise ValueError(f'Budget overflow: prefix={prefix}, output={output_budget}, context={block_size}')
    return {'prefix_tokens': prefix, 'max_new_tokens': output_budget}
```

- [ ] Jalankan pemeriksaan diagnosis fixture melalui run_logged: target plan9 dan12 bagian, tuple lima/tujuh elemen, ID ganda, role hilang, fact_id palsu, variant salah, reserved delimiter dan prefix 512/513. Assert rencana valid benar-benar <=512 target tokens termasuk EOS. Cek prefix 1.536 untuk plan512 dan512 untuk section1.536. Snapshot error harus jelas, tidak ada repair.
- [ ] Commit/push kontrak, serializer dan laporan diagnosis: `feat: define full page tasks and strict token budgets`.

## Task 2: Migrasi positional embedding dan ancestry

**Files:** Create context_extension.py, fullpage/lineage.py, qa/extend_context.py, model_fullpage_2048.json; Modify engine.py initial checkpoint dispatch.

**Interfaces:** `extend_project_context(source: Path, destination: Path, *, root: Path, seed: int=42) -> dict`; `validate_fullpage_parent(parent: dict, config: dict, root: Path) -> None`. Consumes engine.read_checkpoint/checkpoint_sha256/save_checkpoint dan MiniGPT.

- [ ] Periksa disk dan SHA parent TRAIN-015 best 3399709ffe2fa7981c9d26b8ff5723f7821bd78e302bea6dfe63aaf1d27c8638, tokenizer serta ancestry pretraining. Destination checkpoints/INIT-2048-001 belum boleh ada. Model config baru hanya mengubah block_size; helper menolak vocab/lebar/layer/head berbeda.
- [ ] Implementasikan ekstensi tensor di CPU. Bentuk inti berikut ditempatkan di fungsi migrasi setelah verifikasi parent:

```python
torch.manual_seed(seed)
expanded = MiniGPT({**parent['model_config'], 'block_size': 2048})
copied = expanded.state_dict()
for name, value in parent['model'].items():
    if name == 'position_embedding.weight':
        copied[name][:1024].copy_(value)
    else:
        if copied[name].shape != value.shape:
            raise ValueError(f'Unexpected tensor change: {name}')
        copied[name].copy_(value)
expanded.load_state_dict(copied, strict=True)
```

- [ ] Simpan memakai atomic pointer helper, state run_id INIT-2048-001/global_step 0/model_config/model/config.lineage/best_checkpoint=None. Lineage mencatat migration_kind=position_extension, source config/data/tokenizer/checkpoint hashes, unchanged tensors dan new_position_seed. Tidak memasukkan optimizer/scheduler/RNG lama sebagai resume state.
- [ ] Adapter initial checkpoint engine memanggil validate_fullpage_parent hanya untuk data_origin=fullpage_curriculum. Parent INIT wajib 0 dengan migration descriptor cocok. Initial weights dipakai melalui load_checkpoint dengan optimizer/scheduler=None dan restore_rng=False; optimizer baru sudah dibuat engine. Exact resume cabang existing tetap strict config/state tanpa pengecualian baru.
- [ ] Periksa setiap tensor lama dengan torch.equal, 1.024 baris lama identik, shape 2.048, new rows finite, tied embeddings tetap tied, parent unchanged. Bandingkan logits prefix pendek pada mode eval sebagai diagnosis numerik. Simpan laporan, commit/push `feat: add auditable 2048 position extension`.

## Task 3: Curriculum baru dan loader hemat padding

**Files:** Create src/fullpage/curriculum.py, dataset.py dan qa/prepare_fullpage_curriculum.py. Wrapper train_fullpage membangun loader baru dan meneruskannya ke engine.run_training; engine tidak membangun loader dari data_origin.

**Interfaces:** `build_curriculum(root: Path, output: Path, *, seed: int=424242) -> dict`; `encode_task_row(row: dict, tokenizer) -> dict`; `TaskDataset(path: Path, tokenizer)`; `TaskBatchSampler(ResumableBatchSampler) dengan constructor (lengths: list[int], task_kinds: list[str], batch_size: int, seed: int)` dengan state_dict/load_state_dict; `trim_collate(rows: list[dict]) -> dict`.

- [ ] Bangun business facts fiktif dari katalog proyek. Tentukan manifest 320 families sebelum tokenization:240/40/40, genre seimbang dan kedua style satu family. Jangan memakai nama/fakta dari final lama untuk memilih train. Simpan final terpisah dengan hashes dan jangan buka targetnya pada profiler/train/selection.
- [ ] Untuk setiap page target valid hasil konstruksi curriculum, turunkan satu page_plan, satu section_content tiap bagian dan retry row dengan diagnosis error yang tidak mengandung target tersembunyi. Catat page_id/family_id/split/genre/style/task/origin/human_reviewed=False, input dan target hashes. Pilih pilot40/10 sebagai subset tetap dari train/development. Bukti final baru dibekukan sebelum eksperimen model.
- [ ] Jalankan encode_task_row melalui validator khusus task, bukan encode_sft v1. Urutan bos/prompt/prompt_tokens/target/target_tokens/eos; labels digeser sekali dan prompt/pad dimask -100. Tolak input/output di atas budget. Pastikan sedikitnya 32 contoh train punya supervised positions di atas 1.024 secara alami, tanpa padding sebagai data atau memanjang-manjangkan fakta pengguna.
- [ ] Buat bucket 256/512/1024/2048 berdasarkan panjang total. Sampler deterministik mengutamakan proporsi 30% plan/70% section dengan retry mengikuti task asal, menyimpan permutation/cursor/seed/task ratio/bucket info dalam checkpoint. Tidak menggunakan validation untuk fitting. Collator memotong hanya padding kanan:

```python
def trim_collate(rows):
    length = max(row['length'] for row in rows)
    return {
        'input_ids': torch.tensor([row['input_ids'][:length] for row in rows], dtype=torch.long),
        'labels': torch.tensor([row['labels'][:length] for row in rows], dtype=torch.long),
    }
```

- [ ] Periksa keluarga lintas-split, duplikasi teks/struktur dan overlap template yang disengaja, jumlah per genre/style/task, budget aktual, EOS/masking, sampler state dan batch trim. Cek sampler yang direstore mengeluarkan urutan sisa sama. Laporkan rejected row tanpa memotong target. Commit/push `feat: build full page curriculum and length aware task loader`.

## Task 4: Aset lokal, komposer dan renderer2

**Files:** Create src/fullpage/assets.py, compose.py, renderer.py, assets/fullpage/catalog.json/SVG milik proyek dan qa/render_fullpage_fixture.py.

**Interfaces:** `load_asset_catalog(root: Path) -> dict`; `resolve_asset(asset_id: str, catalog: dict, root: Path) -> Path`; `compose_page(plan: dict, sections: list[dict], request: dict, catalog: dict) -> dict`; `export_fullpage(spec: dict, output: Path, *, root: Path) -> dict`. Consumes decoded plan/section validators dan renderer v1.export_page untuk dispatch versi 1.

- [ ] Katalog aset mencatat id/path/width/height/origin/license/sha256. Mulai dua ilustrasi SVG lokal milik proyek tanpa unduhan dataset. Resolve harus tetap di assets/fullpage setelah canonical path; tolak traversal, symlink keluar, URL bebas dan asset_id tidak terdaftar. Media memiliki alt nonkosong.
- [ ] compose_page menuntut seluruh ID hasil sama dengan urutan plan, tanpa duplikasi/bagian hilang/props asing. Title/theme/style tidak dipilih ulang. Navbar/CTA menuju bagian tersedia; facts yang diberikan diperiksa tepat pada field brand/contact/price/name. FAQ menjadi feature_grid/accordion dan interactions hanya dari katalog sesuai descriptor.
- [ ] Renderer2 dispatch v1 ke renderer lama dan v2 ke fungsi baru. Pakai html.escape pada teks, enum variant sebagai selector dan tema validated; hero split dua kolom, numbered/cards, prose/split media, navbar responsive, contact panel dan footer berkelompok. Layout 390px satu kolom, desktop 1440px memberi hierarki/spasi konsisten. Export index/styles/app/page_spec/assets dengan attribution catalog subset.
- [ ] Jalankan fixture manual dua genre/dua style melalui run_logged. Periksa local file references, fragments, SVG/alt, field fakta, penolakan quote/script/path palsu, responsive CSS dan interaksi katalog. Periksa v1 snapshot tidak berubah. Label fixture manual, bukan model output. Browser inspection jika diizinkan; jika tidak, status visual pending, tanpa bypass.
- [ ] Commit/push `feat: render complete pages with trusted local assets`.

## Task 5: Generasi bertahap dan kegagalan terukur

**Files:** Create src/fullpage/generation.py dan qa/generate_fullpage.py; configs/fullpage/evaluation.json.

**Interfaces:** `generate_task(model, tokenizer, prompt: str, *, task: str, config: dict) -> dict`; `generate_full_page(request: dict, *, checkpoint: Path, root: Path, output: Path) -> dict`. Consumes check_budget, validators/decode_plan, compose_page/export_fullpage. Output status accepted/missing_information/stage_failed dengan attempts/raw/stops/metadata.

- [ ] Prefix task ringkas deterministik menyertakan business facts yang diperlukan dan ringkasan descriptor, seluruh fakta penting dipertahankan. Tolak overbudget terlebih dahulu. Config runtime plan 512/section 1536/temperature 0/seed 42; EOS berhenti dini. Generasi model output diparse persis tanpa slicing first JSON/target fallback.
- [ ] Inference memakai no_grad/BF16 SDPA. Hindari logits semua posisi dengan output_mask hanya posisi terakhir, tetap tanpa KV cache:

```python
mask = torch.zeros_like(ids, dtype=torch.bool)
mask[:, -1] = True
with torch.no_grad(), _autocast(ids.device, config['precision']):
    logits = model(ids, output_mask=mask)[0].float()
next_id = int(logits.argmax())
```

- [ ] Validasi raw plan kemudian decode ke object; hasil tiap section diperiksa pada descriptor/facts/catalog yang sama. Maksimal satu retry dengan error ringkas, disimpan terpisah. Incomplete EOS/token limit/unknown ID/errors setelah retry menyebabkan stage_failed. Komposer/export hanya berjalan setelah seluruh stage valid.
- [ ] Periksa validator dan orkestrasi memakai fixture manual yang diberi label jelas: required facts hilang, prefix overflow, invalid plan/section, mixed style, broken fragment/media, retry gagal dan EOS early. Rekam raw keluaran INIT2048 sebagai diagnosis kegagalan, bukan hasil model yang sudah dilatih. Setelah pilot pada Task 6, jalankan generator ini pada 20 page development pilot, simpan first attempt/post retry rates, total page elapsed dan token per stage. Jangan aktifkan checkpoint sebelum gate baru.
- [ ] Commit/push `feat: generate complete pages through validated staged tasks`.

## Task 6: Profil GPU dan pilot training

**Files:** Create qa/profile_fullpage_training.py, train_fullpage.py dan configs/fullpage/pilot.json/training.json. Reuse engine.train_one_step/run_training, GpuMonitor, atomic checkpoint/resume.

**Interfaces:** `profile_fullpage(root: Path, *, report_id: str) -> dict`; `run_fullpage_training(config_path: Path, *, run_id: str, resume: Path | None=None) -> dict`. Wrapper membangun TaskDataset/TaskBatchSampler/trim_collate. Tambahkan parameter keyword root=None pada engine.run_training; nilai default tetap config_path.parent.parent untuk caller lama, wrapper baru memberi root repo eksplisit karena konfigurasi berada di configs/fullpage. TaskBatchSampler subclass ResumableBatchSampler agar pemeriksaan exact resume existing tetap berlaku; num_workers=0.

- [ ] Profil di fresh child process dengan allocator sebelum import torch, INIT-2048 weights, batch 4/8/12/16; enam warmup dan 20 measured updates tiap kandidat, panjang representatif dan near 2048. State/probe weights dibuang, tidak dijadikan kandidat. Simpan elapsed/validtokens/VRAM/finite grad/temp/power/utilization serta OOM. Hentikan peningkatan batch jika failure atau desktop headroom <512MiB pada profil full context.
- [ ] Pilih throughput valid tokens tertinggi yang stabil pada panjang terburuk, dan ukur accumulation=48/batch untuk batch 4/8/12/16. Batch/accumulation/config/hash dicatat; profiler tidak membaca final. Budget disk diperiksa sebelum setiap write, termasuk temporary/retained payloads atomic engine.
- [ ] Bekukan pilot: 600 updates, seed 42, LR 5e-5 ke 5e-6, warmup 60, validate/checkpoint 100, ordinary CE semua development task pilot. INIT-2048 parent, BF16/SDPA, optimasi terukur, reserve 15 GiB. Profil dapat menolak konfigurasi sebelum 600 dimulai, bukan mengubah budget setelah melihat hasil.
- [ ] Jalankan pilot lewat run_logged. Gunakan engine exact resume jika terputus, dengan identitas data/config/sampler/RNG. Catat loss per task, labels di atas posisi 1024, global step/valid tokens, GPU/disk, best/last hashes. Kualitas generation diukur Task 5 pada 20 page development pilot; jangan buka final.
- [ ] Setelah diagnosis pilot, tulis training config utama sebelum mulai. Rencana awal budget 2.400 updates/warmup 120/validate 400 dengan LR 5e-5 ke 5e-6; jika pilot menunjukkan budget/data tidak cukup, revisi config sebagai eksperimen baru yang dicatat sebelum run. Pilih best ordinary CE dari run dengan budget beku, ukur best/last development dan hanya kandidat yang lulus gate lanjut final. Commit/push `perf: profile and train the 2048 full page tasks`.

## Task 7: Development gate dan satu final baru

**Files:** Create src/fullpage/evaluation.py dan qa/evaluate_fullpage.py; data/evaluation/fullpage benchmark manifest serta reports/fullpage candidate/final reports.

**Interfaces:** `evaluate_requests(requests: list[dict], *, checkpoint: Path, root: Path, output: Path) -> dict`; `lock_fullpage_candidate(development_report: Path, checkpoint: Path, destination: Path) -> dict`. Dataset task fitting tidak menerima final requests sebagai input.

- [ ] Evaluasi semua 40 development families×2 style dari best dan last, simpan per genre/style complete/schema/required roles/facts/links/assets/first attempt/retry/stop reason. Kandidat selalu best ordinary CE run dengan budget beku, bukan pemilihan last setelah final. Gate 95% pada denominator 80 request, minimal 76 complete serta 76 required coverage; exported diterima harus 100% structural facts/links/assets.
- [ ] Siapkan 12 review page IDs sebelum melihat output, tiga pada masing-masing kombinasi genre/style, seeded manifest. Manual rating relevansi/teks/layout/konsistensi tiap 1..5; mean dimension>=4 dan setiap rating>=3. Jangan membuat rating atas nama manusia; catat reviewer dan persetujuan nyata.
- [ ] Lock candidate berisi checkpoint SHA, config/schema/task serialization/data/benchmark hashes, selection rules, development result dan timestamps. Jika gate belum lulus, laporkan needs_more_data/model; final tidak dijalankan.
- [ ] Satu final 80 pages memakai candidate beku setelah development gate. Jangan update data/selection dari final errors; raw errors disimpan. Static pemeriksaan seluruh 80, review/browser 12 samples di 390/1440; status browser_pending jika tidak tersedia. Modelgate dan browser gate terpisah, acceptance penuh membutuhkan keduanya.
- [ ] Ekspor hanya raw accepted ke gallery/ZIP, manifest file hash/attribution dan rejected report. Runtime baru hanya diaktifkan jika model gate terbukti; UI tahap akhir tetap menunggu penerimaan page. Commit/push `feat: record independent full page quality gate`.

## Task 8: Notebook dan delivery yang dapat ditelusuri

**Files:** Create qa/record_fullpage_progress.py, notebooks10/11 dan reports/FULL_PAGE_PROGRESS_2026-10-13.md. Modify README.md, logs/LOG_TRAINING.md, PIPELINE_PROGRESS.md dan ledger.

**Interfaces:** `record_fullpage_progress(root: Path, *, reports: list[Path], output: Path) -> dict`. Membaca report aktual, tidak menyusun angka dari ekspektasi.

- [ ] Notebook10: panjang task/split/curriculum/serialized plan/migration tensor/profile. Notebook11: config training/kurva/token GPU, raw plan per section/retry/PageSpec gabungan/output gallery/evaluation gate. Sel notebook berfungsi memakai project kernel mini-gpt-webcodegen dan output dihasilkan dari eksekusi nyata.
- [ ] Validasi nbformat dan jalankan sel berurutan lewat run_logged. Training bukan otomatis dijalankan setiap notebook dibuka; sel training menjadi opt-in yang mereferensikan run config. Contoh manual/development/final diberi label dan final tidak otomatis dibuka notebook pengembangan.
- [ ] Rekam seluruh RUN, kegagalan/interruption/rerun, AI entries, source/data/checkpoint/config hashes, durations/validtokens/VRAM/telemetry, keputusan dan batas bukti. Immutable evidence JSON ditulis newline LF eksplisit untuk menjaga hash ketika Git menyimpan. ZIP harus cocok dengan manifest.
- [ ] Periksa artifacts lokal/staged bytes/link notebook/report sesuai file changed, git diff check, SHA remote dan private status. Jangan mengklaim browser atau human review yang belum dilakukan. Commit/push `docs: document full page training and generation evidence`.

## Perintah dan checkpoint eksekusi

Setiap CLI baru wajib menyediakan argumen --help, nama output unik/refuse overwrite, --root default repo dan reported input hashes. Contoh perintah setelah modul diimplementasikan:

```powershell
.venv/Scripts/python.exe -m qa.run_logged --label 'Extend project context to 2048' -- .venv/Scripts/python.exe -m qa.extend_context --source checkpoints/TRAIN-015/best.pt --output checkpoints/INIT-2048-001/initial.pt
.venv/Scripts/python.exe -m qa.run_logged --label 'Prepare fullpage curriculum' -- .venv/Scripts/python.exe -m qa.prepare_fullpage_curriculum --output data/processed/fullpage/v1
.venv/Scripts/python.exe -m qa.run_logged --label 'Profile fullpage training' -- .venv/Scripts/python.exe -m qa.profile_fullpage_training --report-id FULLPAGE-GPU-001
.venv/Scripts/python.exe -m qa.run_logged --label 'Train fullpage pilot' -- .venv/Scripts/python.exe -m qa.train_fullpage --config configs/fullpage/pilot.json --run-id TRAIN-016
```

TRAIN IDs/example commands bersifat rencana, ambil nomor aktual terbaru saat mulai. Profil/engine fresh process mengatur allocator di child environment dengan nama task spesifik, tidak merepurpose HOME/CODEX_HOME.

## Self-review dan handoff

Coverage: spec1/2/4→Task1; spec3→Task2; spec7→Task3; spec5/6→Task4/5; spec8→Task6; spec9→Task7; spec10→Task8. Lima Review Focus seluruhnya mempunyai pemeriksaan di task pemilik. Ini rencana pemeriksaan, belum hasil.

Rekomendasi metode: Native, implementasi oleh agen utama melalui executing-plans, karena interface antar task saling bergantung dan pengguna meminta efisiensi. Tidak spawn subagent sebelum pengguna memilih metode atau memberikan instruksi yang relevan. Rencana tertulis menunggu review dan pilihan eksekusi sesuai writing-plans; belum ada perubahan produk, migration, training atau test baru.
