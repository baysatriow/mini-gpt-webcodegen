# Pipeline Data dan Model Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Langkah memakai checkbox agar progres dapat dicatat. Untuk sesi ini, jalankan secara inline dalam commit terpisah dan push setiap commit.

**Goal:** Membangun pipeline data yang dapat diulang dan Mini GPT decoder-only dari bobot acak, lalu melatihnya menghasilkan PageSpec JSON yang tervalidasi.

**Architecture:** Ambil subset teks WebSight v0.1/v0.2 secara streaming dan tambahkan seed Vulcan yang lolos kurasi. Simpan provenance, normalisasikan pasangan prompt-ke-PageSpec, kelompokkan template sebelum split, latih tokenizer hanya pada data train, pretrain Mini GPT pada teks/kode, lanjutkan optimasi prompt-ke-JSON, lalu ukur token loss serta validitas dan mutu hasil tugas.

**Tech Stack:** Windows, CPython 3.11.9, PyTorch 2.14.1+cu130, Hugging Face Datasets streaming, JSONL, JSON Schema, Tokenizers byte-level BPE, `unittest`, CUDA RTX 5070.

**Spec:** `docs/PROJECT_SCOPE_AND_PIPELINE.md`

## Global Constraints

- Model Mini GPT diinisialisasi dari bobot acak dan tidak menggunakan bobot bahasa pralatih.
- Implementasi memakai PyTorch pada `.venv` proyek, CPython 3.11.9, dan GPU RTX 5070.
- WebSight diproses sebagai subset teks streaming; jangan mengunduh seluruh corpus atau screenshot.
- Setiap baris data membawa source URL, revision, license, attribution, group ID, split, dan alasan filter.
- Train, validation, dan test dibagi berdasarkan keluarga template, bukan baris acak.
- Target instruksi adalah PageSpec JSON dengan style `plain_css` atau `tailwind` dan ID JavaScript yang diizinkan.
- SFT loss hanya diterapkan ke token target JSON; token prompt dimask.
- Catat setiap command sebagai RUN, setiap percobaan training sebagai TRAIN, dan setiap sesi LLM kode/debug sebagai AI.
- Pertahankan data mentah, cache, output besar, VENV, dan checkpoint di luar Git.
- Gunakan kode yang dirancang untuk proyek ini; dokumentasi resmi pustaka adalah referensi dasar, bukan blok implementasi siap salin.
- Setiap tahap selesai dalam commit tunggal tanpa trailer Co-Authored-By, kemudian push branch.
- Setelah planning disetujui, buat `feature/pipeline-data-model-training` dari `main`; commit setiap task di branch ini dan push setelah tiap commit.
- Pipeline hanya dimulai setelah planning ini ditinjau dan disetujui.

## File Structure

- `configs/dataset.json`: dataset, revision, streaming limit, filter, group split, dan seed.
- `configs/tokenizer.json`: trainer BPE, vocabulary, special tokens, dan output.
- `configs/model.json`: ukuran decoder-only dan dropout.
- `configs/training_pretrain.json`: optimizer dan next-token objective.
- `configs/training_sft.json`: format prompt-target, target masking, dan continued training.
- `configs/evaluation.json`: prompt held-out, decoding, rubric, dan batas evaluasi.
- `src/data/schema.py`: record kanonis dan schema validation.
- `src/data/sources.py`: pembaca dataset streaming dan provenance manifest.
- `src/data/normalize.py`: konversi anotasi yang ditinjau menjadi PageSpec.
- `src/data/split.py`: dedup, kelompok template, dan pembagian dataset.
- `src/data/tokenizer.py`: training BPE dan encode/decode.
- `src/data/dataset.py`: token block dan masking label.
- `src/models/minigpt.py`: embedding, causal attention, MLP, block, dan language model.
- `src/training/engine.py`: loop, optimizer, validasi berkala, resume, dan checkpoint.
- `src/evaluation/metrics.py`: loss, perplexity, parse/schema, dan rubric laporan.
- `qa/`: pemeriksaan lingkungan dan evaluasi command line, bukan tempat kode library.
- `tests/data/`, `tests/models/`, `tests/training/`: unit dan integrasi berbasis unittest.
- `tests/__init__.py`, `tests/data/__init__.py`, `tests/models/__init__.py`, `tests/training/__init__.py`, `tests/evaluation/__init__.py`: package markers untuk pemanggilan unittest pada Windows.
- `data/annotations/`: anotasi PageSpec yang ditinjau kelompok; source data besar tetap berada di raw/processed lokal.
- `logs/LOG_TRAINING.md`: ledger training, path log console, metrik, model, data, dan debugging.
- `outputs/metrics/`: JSONL metrik dan grafik lokal.
- `checkpoints/TRAIN-NNN/`: snapshot resume lokal.

## Review Focus

- Revision WebSight tidak tersedia, viewer mengalami gangguan, atau streaming berhenti di tengah: run gagal jelas, manifest tidak ditandai selesai, dan file parsial tidak masuk train.
- Contoh tanpa idea, markup kosong, invalid HTML, URL aset luar, atau field nonteks: normalizer memberi alasan reject yang stabil dan tidak menyimpan image payload.
- Dua variasi warna dari satu template masuk ke split berbeda: group split mencegah leakage sebelum tokenizer dibuat.
- Target sequence terpotong di tengah JSON atau label prompt ikut masuk loss SFT: dataloader menolak/truncate sesuai aturan serta memask prompt.
- RTX 5070 menghasilkan OOM, NaN, atau resume yang mengulang state: training mengakhiri run dengan catatan dan checkpoint konsisten.

---

### Task 1: Tetapkan PageSpec dan record provenance

**Files:**

- Create: `src/data/schema.py`
- Create: `configs/page_spec.schema.json`
- Create: `tests/data/test_schema.py`
- Create: `tests/__init__.py`
- Create: `tests/data/__init__.py`

**Interfaces:**

- `PageExample` memiliki `example_id`, `prompt`, `target_spec`, `source_id`, `source_revision`, `license_id`, `group_id`, `split`, dan `annotation_status`.
- `validate_page_spec(spec: dict) -> list[str]` mengembalikan daftar kesalahan kosong jika schema benar.
- PageSpec berisi `schema_version`, `title`, `language`, `style_mode`, `theme`, `sections`, dan `interactions`.
- `style_mode` hanya `plain_css` atau `tailwind`.
- Section types: `navbar`, `hero`, `feature_grid`, `text_section`, `testimonial`, `pricing_table`, `contact_form`, dan `footer`.
- Interaction types: `menu_toggle`, `accordion`, `tabs`, `modal`, `filter`, dan `form_validate`.
- Theme menerima warna hexadecimal dan font dari enum. Link hanya menerima `https`, `mailto`, `tel`, atau fragment lokal.
- Komponen tidak menerima `script`, atribut `on*`, protokol URL selain `https`, `mailto`, `tel`, dan fragment lokal.

- [x] **Step 1: Tulis pemeriksaan schema yang akan gagal**

Tambahkan `unittest.TestCase` yang memeriksa PageSpec valid, field `style_mode` invalid, ID interaksi di luar katalog, `script` sebagai component, dan atribut `onclick`. Gunakan object minimal eksplisit dengan satu section `hero` dan satu paragraph.

- [x] **Step 2: Jalankan pemeriksaan sebelum fungsi tersedia**

Run: `python -m unittest tests.data.test_schema -v`

Expected: gagal karena module/schema belum tersedia.

- [x] **Step 3: Buat record dan schema ketat**

Implementasikan `PageExample` sebagai `dataclass(frozen=True)` dan `validate_page_spec` menggunakan `jsonschema.Draft202012Validator`. Gunakan `additionalProperties: false` pada object utama dan tiap component, panjang string maksimum, batas section, serta enum tag/interaksi.

- [x] **Step 4: Jalankan seluruh pemeriksaan schema**

Run: `python -m unittest tests.data.test_schema -v`

Expected: seluruh assertion lulus dan semua error menyebut JSON path yang ditolak.

- [x] **Step 5: Commit dan push**

```powershell
git add src/data/schema.py configs/page_spec.schema.json tests/__init__.py tests/data/__init__.py tests/data/test_schema.py
git commit -m "feat: define validated page specification"
git push -u origin HEAD
```

---

### Task 2: Ambil subset teks dataset dengan provenance

**Files:**

- Create: `src/data/sources.py`
- Create: `configs/dataset.json`
- Create: `tests/data/test_sources.py`
- Create: `data/manifests/README.md`

**Interfaces:**

- `stream_websight(config_name: str, revision: str, limit: int, seed: int) -> Iterator[dict]` membaca split `train` secara streaming dan memilih kolom teks/idea saja.
- `write_manifest(path: Path, metadata: dict) -> None` menulis JSON secara atomik setelah run selesai.
- `main(argv: list[str] | None = None) -> int` menyediakan CLI untuk smoke fetch terbatas.
- Konfigurasi awal mematok dataset `HuggingFaceM4/WebSight`, config `v0.1` atau `v0.2`, split `train`, field text dan `llm_generated_idea` yang tersedia, serta limit contoh yang dapat diubah.
- Setiap source row mendapat index lokal, revision, konfigurasi, waktu akses, dan hash teks.

- [x] **Step 1: Tulis pemeriksaan dengan loader palsu**

Buat test yang menyuntikkan iterable 3 record serta loader palsu. Minta `limit=2`, lalu pastikan hanya dua record yang dikembalikan, field image tidak disentuh, dan dataset name/config/revision/split tercatat.

- [x] **Step 2: Jalankan test loader palsu**

Run: `python -m unittest tests.data.test_sources -v`

Expected: gagal karena `stream_websight` dan `write_manifest` belum ada.

- [x] **Step 3: Implementasikan adapter streaming**

Panggil `datasets.load_dataset("HuggingFaceM4/WebSight", config_name, split="train", revision=revision, streaming=True)`. Panggil `select_columns` sebelum iterasi. Terapkan shuffle buffer terbatas dengan seed config, lalu `take(limit)`. Buat seed, buffer size, column list, dan limit eksplisit di `configs/dataset.json`. Jangan memanggil `load_dataset` tanpa `streaming=True`.

- [x] **Step 4: Jalankan unit dan smoke fetch terbatas**

Run: `python -m unittest tests.data.test_sources -v`

Expected: semua test lokal lulus. Jalankan `python -m src.data.sources --config configs/dataset.json --limit 20`; expected: maksimal 20 teks diterima, tidak ada image payload pada JSONL, revision tetap di manifest, dan disk usage dicatat di RUN.

- [x] **Step 5: Commit dan push**

```powershell
git add src/data/sources.py configs/dataset.json tests/data/test_sources.py data/manifests/README.md
git commit -m "feat: stream licensed website text samples"
git push origin HEAD
```

---

### Task 3: Normalisasi anotasi menjadi contoh prompt-ke-PageSpec

**Files:**

- Create: `src/data/normalize.py`
- Create: `data/annotations/README.md`
- Create: `tests/data/test_normalize.py`
- Modify: `configs/dataset.json`

**Interfaces:**

- `normalize_annotation(row: dict, annotation: dict, source_meta: dict) -> PageExample` membentuk pasangan final dari idea/prompt, target PageSpec yang telah ditinjau, dan provenance.
- `normalize_jsonl(source_path: Path, annotation_path: Path, output_path: Path) -> tuple[int, int]` menulis contoh valid dan statistik reject secara terpisah.
- Satu anotasi memetakan `source_row_id`, prompt Bahasa Indonesia, content language, `group_id`, PageSpec, status review, reviewer initials, dan alasan perubahan.
- WebSight v0.1 dapat dipakai untuk pretraining markup; untuk SFT, pasangkan dengan prompt hasil anotasi dan tinjauan manusia. WebSight v0.2 dapat memakai `llm_generated_idea` sebagai bahan prompt, tetapi terjemahan/penyusunan prompt tetap ditinjau.

- [x] **Step 1: Tulis pemeriksaan normalizer**

Periksa prompt kosong, source id tidak dikenal, target schema invalid, license tidak ada, `annotation_status` belum `reviewed`, serta pasangan valid. Untuk record ditolak, pastikan alasan menyebut field yang menyebabkan reject.

- [x] **Step 2: Jalankan pemeriksaan normalizer**

Run: `python -m unittest tests.data.test_normalize -v`

Expected: gagal sebelum normalizer dibuat.

- [x] **Step 3: Implementasikan konversi dan report reject**

Implementasikan normalizer sebagai transformasi lokal deterministik. Simpan anotasi bersama source row ID dan revision, validasi PageSpec sebelum ditulis, tolak record tanpa review, dan keluarkan jumlah accepted/rejected beserta alasan ke file report terpisah. Jangan memanggil layanan LLM jaringan dari preprocessing.

- [x] **Step 4: Jalankan unit dan konversi fixture**

Run: `python -m unittest tests.data.test_normalize -v`

Expected: fixture menghasilkan satu baris JSONL kanonis dan record invalid hanya masuk report reject.

- [x] **Step 5: Commit dan push**

```powershell
git add src/data/normalize.py data/annotations/README.md tests/data/test_normalize.py configs/dataset.json
git commit -m "feat: normalize reviewed website annotations"
git push origin HEAD
```

---

### Task 4: Dedup dan split berdasar keluarga template

**Files:**

- Create: `src/data/split.py`
- Create: `tests/data/test_split.py`
- Modify: `configs/dataset.json`

**Interfaces:**

- `canonical_hash(example: PageExample) -> str` menghash canonical JSON dari prompt, PageSpec, mode style, dan interaksi.
- `assign_splits(examples: Sequence[PageExample], seed: int, ratios: tuple[float, float, float]) -> list[PageExample]` membagi group ke `train`, `validation`, `test`.
- Default rasio konfigurasi `0.80, 0.10, 0.10` berlaku pada jumlah group, bukan jumlah baris. Simpan seed, group count, example count, dan hash split.

- [x] **Step 1: Tulis test anti-leakage**

Buat dua PageExample dari `group_id="layout-hero-001"` dan satu dari `layout-form-004`; pastikan dua contoh pertama selalu satu split dan seed sama menghasilkan hasil sama.

- [x] **Step 2: Jalankan test anti-leakage**

Run: `python -m unittest tests.data.test_split -v`

Expected: gagal karena split belum dibuat.

- [x] **Step 3: Implementasikan dedup dan group allocation**

Urutkan group IDs dengan seeded RNG, alokasikan group utuh ke split menurut rasio jumlah group, kemudian tulis contoh dalam urutan stabil. Jika group kurang dari 10, hentikan dengan pesan yang menjelaskan bahwa validation/test tidak dapat diandalkan. Jangan menurunkan group ID saat warna atau sinonim berubah.

- [x] **Step 4: Jalankan pemeriksaan repeatability dan overlap**

Run: `python -m unittest tests.data.test_split -v`

Expected: `group_id` antar split tidak beririsan, hasil seed sama persis, dan duplicate canonical hash masuk reject list.

- [x] **Step 5: Commit dan push**

```powershell
git add src/data/split.py tests/data/test_split.py configs/dataset.json
git commit -m "feat: split examples by template family"
git push origin HEAD
```

---

### Task 5: Latih tokenizer proyek dan buat batch token

**Files:**

- Create: `src/data/tokenizer.py`
- Create: `src/data/dataset.py`
- Create: `tests/data/test_tokenizer_dataset.py`
- Create: `configs/tokenizer.json`
- Create: `configs/training_pretrain.json`
- Create: `configs/training_sft.json`

**Interfaces:**

- `train_tokenizer(train_jsonl: Path, output_dir: Path, config: dict) -> Path` melatih byte-level BPE hanya pada train split.
- `encode_pretraining(text: str, tokenizer) -> tuple[list[int], list[int]]` menghasilkan input dan next-token label.
- `encode_sft(prompt: str, target_json: str, tokenizer, block_size: int) -> tuple[list[int], list[int]]` memberi label `-100` pada seluruh posisi prompt dan padding.
- `PageSpecDataset(rows, tokenizer, mode, block_size)` mengembalikan tensor `input_ids` dan `labels` panjang tetap.

- [x] **Step 1: Tulis test token round trip dan label mask**

Gunakan fixture Unicode Indonesia, HTML tag, CSS punctuation, Tailwind class, serta token special. Pastikan decode mempertahankan karakter, dan label SFT pada prompt/padding bernilai `-100`.

- [x] **Step 2: Jalankan test tokenizer/dataset**

Run: `python -m unittest tests.data.test_tokenizer_dataset -v`

Expected: gagal sebelum tokenizer dan dataset dibuat.

- [x] **Step 3: Implementasikan BPE dan batch packing**

Buat tokenizer byte-level baru dari iterator train split, special token untuk awal/akhir prompt dan target serta padding. Tolak target JSON lebih panjang dari block size dan catat jumlah truncation; jangan memotong JSON tanpa penanda. Simpan tokenizer JSON, vocab, special-token map, block size, dan hash.

- [x] **Step 4: Jalankan unit dan hitung distribusi token**

Run: `python -m unittest tests.data.test_tokenizer_dataset -v`

Expected: semua mask dan round-trip benar; report menampilkan p50/p95/max tokens per contoh dan jumlah contoh yang melewati block size sebelum training dimulai.

- [x] **Step 5: Commit dan push**

```powershell
git add src/data/tokenizer.py src/data/dataset.py tests/data/test_tokenizer_dataset.py configs/tokenizer.json configs/training_pretrain.json configs/training_sft.json
git commit -m "feat: tokenize curated page specifications"
git push origin HEAD
```

---

### Task 6: Implementasikan decoder-only Mini GPT

**Files:**

- Create: `src/models/minigpt.py`
- Create: `tests/models/test_minigpt.py`
- Create: `tests/models/__init__.py`
- Create: `configs/model.json`

**Interfaces:**

- `MiniGPT(config: dict)` menerima `input_ids` berbentuk `[batch, sequence]` dan mengembalikan `logits` berbentuk `[batch, sequence, vocab_size]`.
- `CausalSelfAttention.forward(x)` melakukan q/k/v linear projection, reshape multi-head, masked attention scores, softmax, dropout, concatenation, dan output projection.
- `Block.forward(x)` melakukan pre-layer normalization, causal attention residual, MLP/GELU residual.
- Embedding token dijumlahkan dengan learned positional embedding; model memakai final layer norm dan linear language-model head.

- [x] **Step 1: Tulis test causal attention dan ukuran tensor**

Uji output shape, causal mask dengan membandingkan prefix logits sebelum/sesudah token suffix diubah, backward menghasilkan gradien finite, serta panjang sequence di atas block size ditolak.

- [x] **Step 2: Jalankan model test**

Run: `python -m unittest tests.models.test_minigpt -v`

Expected: gagal sebelum modul model dibuat.

- [x] **Step 3: Implementasikan komponen dengan operasi PyTorch dasar**

Gunakan `nn.Embedding`, `nn.Linear`, `nn.LayerNorm`, `nn.Dropout`, `torch.matmul`, dan mask segitiga kausal. Tulis struktur attention dan decoder block sendiri; jangan memakai `nn.Transformer` atau bobot model lain. Inisialisasi linear/embedding dengan normal ber-mean nol, std `0.02`, serta bias nol.

- [x] **Step 4: Jalankan CPU, CUDA dan BF16 forward/backward**

Run: `python -m unittest tests.models.test_minigpt -v`

Expected: seluruh output shape benar dan loss/gradien finite pada CPU serta RTX 5070; catat parameter count dan peak VRAM pada RUN.

- [x] **Step 5: Commit dan push**

```powershell
git add src/models/minigpt.py tests/models/__init__.py tests/models/test_minigpt.py configs/model.json
git commit -m "feat: implement mini decoder-only transformer"
git push origin HEAD
```

---

### Task 7: Training loop, validation, checkpoint, dan resume

**Files:**

- Create: `src/training/engine.py`
- Create: `tests/training/test_engine.py`
- Create: `tests/training/test_checkpoint.py`
- Create: `tests/training/__init__.py`
- Modify: `configs/training_sft.json`
- Create: `qa/train_minigpt.py`
- Modify: `logs/LOG_TRAINING.md`

**Interfaces:**

- `train_one_step(model, batch, optimizer, scaler, phase) -> dict[str, float]` menjalankan forward, cross-entropy, backward, gradient clipping, optimizer, dan mengembalikan loss/grad norm.
- `run_training(config_path: Path, train_loader, validation_loader, run_id: str) -> Path` menjalankan steps, metrics, periodic validation, dan saves.
- `save_checkpoint(path, state: dict) -> None`; `load_checkpoint(path, model, optimizer, scheduler) -> dict` memulihkan model, optimizer, scheduler, step, dan RNG state.
- SFT loss menghitung hanya label bukan `-100`. Pretraining loss memprediksi token berikutnya untuk seluruh token valid.

- [x] **Step 1: Tulis test satu optimizer step dan resume**

Gunakan model mini deterministik dan batch kecil. Pastikan parameter berubah setelah step, loss finite, prompt loss diabaikan pada SFT, dan state hasil save/load meneruskan `global_step` serta parameter yang sama.

- [x] **Step 2: Jalankan training/checkpoint test**

Run: `python -m unittest tests.training -v`

Expected: gagal sebelum engine tersedia.

- [x] **Step 3: Implementasikan loop dengan config immutable per run**

Set seed sebelum loader/model. Gunakan AdamW dan konfigurasi optimizer eksplisit. BF16 CUDA berjalan dalam `torch.autocast("cuda", dtype=torch.bfloat16)` hanya jika config mengaktifkannya. Jalankan validation tanpa grad, append satu record JSONL per step, simpan checkpoint `last` dan `best` berdasarkan validation loss, serta tulis console output ke log TRAIN.

- [x] **Step 4: Jalankan unit dan smoke training tanpa dataset penuh**

Run: `python -m unittest tests.training -v`

Expected: test resume identik dan batch mini berakhir dengan loss finite. Jalankan `python -m qa.train_minigpt --config configs/training_pretrain.json --max-steps 5 --smoke`; expected: menyimpan artifact terpisah, tidak menimpa config produksi, dan membuat entry TRAIN baru.

- [x] **Step 5: Commit dan push**

```powershell
git add src/training/engine.py tests/training/__init__.py tests/training/test_engine.py tests/training/test_checkpoint.py qa/train_minigpt.py configs/training_sft.json logs/LOG_TRAINING.md
git commit -m "feat: add reproducible training and checkpoint resume"
git push origin HEAD
```

---

### Task 8: Evaluasi token dan PageSpec held-out

**Files:**

- Create: `src/evaluation/metrics.py`
- Create: `src/evaluation/generate.py`
- Create: `tests/evaluation/test_metrics.py`
- Create: `tests/evaluation/__init__.py`
- Create: `configs/evaluation.json`
- Create: `qa/evaluate_minigpt.py`

**Interfaces:**

- `token_metrics(logits, labels) -> dict` melaporkan mean cross entropy dan perplexity hanya pada label bukan `-100`.
- `generate_page_spec(model, tokenizer, prompt, config) -> tuple[str, dict | None]` melakukan autoregressive decode, parse JSON, dan schema validation.
- `evaluate_checkpoint(checkpoint, prompts_path, schema_path) -> dict` menulis JSON summary, contoh output, dan jumlah parse/schema failures.
- Prompt held-out berisi keluarga layout yang tidak masuk train atau validation.

- [x] **Step 1: Tulis test metric mask dan JSON invalid**

Pastikan label `-100` tidak dihitung pada loss, perplexity sama dengan eksponensial loss token yang dihitung, JSON invalid tercatat gagal tanpa menghentikan batch evaluasi.

- [x] **Step 2: Jalankan evaluation test**

Run: `python -m unittest tests.evaluation -v`

Expected: gagal sebelum metric dan evaluator dibuat.

- [x] **Step 3: Implementasikan evaluator dan output machine-readable**

Tulis satu record per prompt berisi prompt ID, checkpoint hash, raw output, parse status, schema errors, seed/decode config, serta rubric manual kosong untuk reviewer. Jangan menulis skor visual otomatis tanpa browser.

- [x] **Step 4: Jalankan evaluasi pada fixture dan checkpoint**

Run: `python -m unittest tests.evaluation -v`

Expected: test fixture lulus. Evaluasi checkpoint menulis parse/schema rates dan daftar error; reviewer melengkapi rubric layout, teks, aksesibilitas, dan style.

- [x] **Step 5: Commit dan push**

```powershell
git add src/evaluation/metrics.py src/evaluation/generate.py tests/evaluation/__init__.py tests/evaluation/test_metrics.py configs/evaluation.json qa/evaluate_minigpt.py
git commit -m "feat: evaluate held-out page specifications"
git push origin HEAD
```

---

### Task 9: Tutup gerbang pipeline sebelum aplikasi akhir

**Files:**

- Create: `reports/PIPELINE_TRAINING_SUMMARY.md`
- Modify: `README.md`
- Modify: `logs/LOG_TRAINING.md`
- Modify: `docs/PROJECT_SCOPE_AND_PIPELINE.md`

**Interfaces:**

- Ringkasan laporan merujuk commit, TRAIN IDs, dataset manifests, training graphs, held-out metrics, checkpoint hash, attribution, keterbatasan, dan rekomendasi.
- Status gerbang bernilai `ready`, `needs-data`, atau `needs-model-work`, dengan bukti untuk setiap nilai.

- [x] **Step 1: Cocokkan setiap klaim dengan run artifact**

Bangun tabel klaim, TRAIN/RUN ID, artifact, dan nilai aktual. Hilangkan klaim yang tidak didukung output run.

- [x] **Step 2: Jalankan pemeriksaan dokumentasi dan license**

Pastikan manifest mencatat WebSight revision/CC-BY attribution, Webdev tidak disebut sebagai training source, WebMC tetap benchmark saja, dan log mencakup run gagal.

- [x] **Step 3: Tulis laporan hasil**

Masukkan parameter/model hash, ukuran dataset dan split, token counts, kurva loss, parse/schema rates, contoh prompt/output, reviewer rubric, serta keterbatasan. Jangan melatih ulang hanya untuk mempercantik hasil.

- [x] **Step 4: Minta persetujuan sebelum aplikasi**

Perlihatkan laporan, README, dan planning kepada pengguna. Implementasi antarmuka, preview iframe, packaging Tailwind, dan unduhan dimulai hanya setelah pipeline serta kualitas model ditinjau.

- [x] **Step 5: Commit dan push**

```powershell
git add reports/PIPELINE_TRAINING_SUMMARY.md README.md logs/LOG_TRAINING.md docs/PROJECT_SCOPE_AND_PIPELINE.md
git commit -m "docs: report mini gpt pipeline results"
git push origin HEAD
```

## Self-review planning

- Setiap kebutuhan scope punya task pemilik: data/provenance Tasks 1-5; model/training Tasks 6-7; evaluasi Task 8; keputusan aplikasi Task 9.
- Lima risiko Review Focus masing-masing dimasukkan ke unit/integrasi checks pemiliknya.
- Antarmuka `PageExample`, `stream_websight`, `validate_page_spec`, `MiniGPT`, `run_training`, dan evaluator konsisten dengan dokumen desain.
- Dataset penuh tidak diunduh; pipeline diarahkan ke streaming dan subset limit.
- Tugas ini tidak menjalankan training, membangun aplikasi, atau mengubah dependency.
