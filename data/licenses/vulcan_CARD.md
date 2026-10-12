---
license: mit
task_categories:
  - text-generation
language:
  - en
tags:
  - code
  - frontend
  - html
  - css
  - javascript
  - web-development
  - ui
  - synthetic
  - sft
  - fine-tuning
pretty_name: Vulcan — Front-End Code SFT
size_categories:
  - 1K<n<10K
---

<div align="center">

# 🔥 Vulcan

### A high-signal, fully-deduplicated SFT dataset for front-end code generation

**HTML · CSS · Vanilla JS — self-contained, accessible, production-ready**

![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)
![Format](https://img.shields.io/badge/format-JSONL%20%2F%20messages-6366f1?style=flat-square)
![Dedup](https://img.shields.io/badge/duplicate%20outputs-0%25-f97316?style=flat-square)
![Status](https://img.shields.io/badge/status-active-8b5cf6?style=flat-square)

</div>

---

## Overview

**Vulcan** is a curated supervised fine-tuning (SFT) dataset built to teach language
models how to write **clean, modern, self-contained front-end code**. Every example
pairs a realistic developer request with a complete, working answer — semantic HTML5,
responsive CSS (Flexbox / Grid), and dependency-free vanilla JavaScript.

It is designed to be dropped straight into a fine-tuning pipeline. Each row is already
in the **chat `messages` format**, so it works out of the box with Hugging Face
`transformers` chat templates (including Harmony-format models such as GPT-OSS) and with
TRL's `SFTTrainer`.

> **Design principle:** quality over volume. Every assistant output in Vulcan is unique —
> verified by hashing — because near-duplicate rows teach a model to memorize instead of
> generalize. No padding, no filler.

---

## ✨ Highlights

| | |
|---|---|
| 🧩 **Component-rich** | Buttons, cards, navbars, hero sections, responsive grids, contact forms with validation, loaders, and more |
| 🎨 **Design-token driven** | Every example uses CSS variables across multiple cohesive color schemes, font stacks, radii, and shadow systems |
| ♿ **Accessibility-aware** | ARIA labels, keyboard focus styles, semantic markup, sufficient contrast |
| 📱 **Responsive by default** | Mobile-first layouts with proper breakpoints — no horizontal overflow |
| 🧼 **0% duplicate outputs** | Every assistant response is SHA-256 deduplicated |
| 📦 **Zero external deps** | Self-contained HTML/CSS/JS — no frameworks, no CDNs |
| 🤖 **Chat-template ready** | Native `messages` schema for instant SFT |

---

## 📐 Schema

Each line is a JSON object containing a single conversation:

```json
{
  "messages": [
    { "role": "system",    "content": "You are an expert front-end engineer..." },
    { "role": "user",      "content": "Create a CSS feature card with a hover lift effect." },
    { "role": "assistant", "content": ":root { --accent: #6366f1; ... }" }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `messages` | `list[dict]` | An ordered conversation |
| `messages[].role` | `string` | One of `system`, `user`, `assistant` |
| `messages[].content` | `string` | The message text / code |

The `system` turn sets the persona, the `user` turn is the request, and the
`assistant` turn is the complete, copy-pasteable answer.

---

## 🚀 Quickstart

### Load with 🤗 `datasets`

```python
from datasets import load_dataset

ds = load_dataset("xlelords/vulcan", split="train")
print(ds[0]["messages"][1]["content"])   # the user request
print(ds[0]["messages"][2]["content"])   # the code answer
```

### Apply a chat template (Harmony / GPT-OSS, Llama, Qwen, etc.)

```python
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained("openai/gpt-oss-20b")
text = tok.apply_chat_template(ds[0]["messages"], tokenize=False)
```

### Fine-tune with TRL

```python
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=ds,
    processing_class=tokenizer,
)
trainer.train()
```

---

## 🎯 Intended Use

- Fine-tuning small/mid models to generate **front-end UI code** on request
- Building a **coding assistant** specialized in HTML/CSS/JS
- Bootstrapping a **web-component** generation capability
- Instruction-tuning experiments where clean, verifiable outputs matter

### Not intended for

- Back-end, systems, or non-web programming tasks
- Production code review or security-critical generation without human oversight
- Tasks requiring external frameworks (the data is intentionally dependency-free)

---

## 🛠️ How Vulcan Is Built

Vulcan is **synthetically generated**. Examples are produced by combinatorially mixing
a library of hand-written, working front-end components with a matrix of design tokens
(color schemes × font stacks × border radii × shadow systems), then varying the task
phrasing. Every generated answer is hashed and de-duplicated, so the dataset contains
only distinct outputs.

Because the data is generated from scratch rather than scraped, it carries **no
third-party copyright baggage** — which is why it ships under a permissive MIT license.

> **A note on scale:** Vulcan favors *distinct, correct* examples over raw row count.
> For capable base models, a few thousand high-quality SFT rows typically outperforms a
> much larger set padded with near-duplicates, which encourages memorization and
> overfitting.

---

## 📂 Files

| File | Description |
|------|-------------|
| `frontend_sft.jsonl` | Full dataset |
| `train.jsonl` | Training split (~95%) |
| `val.jsonl` | Validation split (~5%) |

---

## ⚖️ License

Released under the **MIT License**. You are free to use, modify, and redistribute —
including commercially — with attribution.

---

## 📣 Citation

```bibtex
@misc{vulcan2026,
  title        = {Vulcan: A Front-End Code SFT Dataset},
  author       = {xlelords},
  year         = {2026},
  howpublished = {\url{https://huggingface.co/datasets/xlelords/vulcan}}
}
```

<div align="center">

---

*Built for builders. Forge something great.* 🔨

</div>