"""Inspect public dataset metadata and bounded samples without fetching images."""

import hashlib
import json
import re
import statistics
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "dataset_audit"
OUT = ROOT / "outputs" / "dataset_audit"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 8 * 1024 * 1024


def fetch(name, url, kind="json"):
    result = {"url": url}
    try:
        with urlopen(Request(url, headers={"User-Agent": "mini-gpt-webcodegen-dataset-audit"}), timeout=30) as response:
            payload = response.read(MAX_BYTES + 1)
            if len(payload) > MAX_BYTES:
                raise ValueError("Response exceeded bounded audit download size")
            result.update(status=response.status, bytes=len(payload))
        value = json.loads(payload) if kind == "json" else payload.decode("utf-8")
        if kind == "json" and isinstance(value, dict) and "rows" in value:
            for item in value["rows"]:
                for field in ("image", "images"):
                    image = item.get("row", {}).get(field)
                    if isinstance(image, dict):
                        image.pop("src", None)
            result["data"] = value
        else:
            result["data"] = value
        suffix = "json" if kind == "json" else "md"
        (RAW / f"{name}.{suffix}").write_text(
            json.dumps(value, ensure_ascii=False, indent=2) if kind == "json" else value,
            encoding="utf-8",
        )
    except HTTPError as exc:
        result.update(status=exc.code, error=str(exc))
    except Exception as exc:
        result.update(status=None, error=f"{type(exc).__name__}: {exc}")
    return name, result


def stats(rows, prompt_key, code_key):
    prompts = [str(row.get(prompt_key, "")) for row in rows]
    codes = [str(row.get(code_key, "")) for row in rows]
    lengths = sorted(map(len, codes))
    return {
        "sample_count": len(rows),
        "columns": sorted({key for row in rows for key in row}),
        "nonempty_prompt": sum(bool(p.strip()) for p in prompts),
        "nonempty_code": sum(bool(c.strip()) for c in codes),
        "duplicate_prompts_exact": len(prompts) - len(set(prompts)),
        "duplicate_codes_whitespace_normalized": len(codes) - len({hashlib.sha256(re.sub(r"\s+", " ", c).strip().encode()).hexdigest() for c in codes}),
        "code_chars_min": min(lengths) if lengths else None,
        "code_chars_median": statistics.median(lengths) if lengths else None,
        "code_chars_p95": lengths[min(len(lengths) - 1, int(len(lengths) * .95))] if lengths else None,
        "code_chars_max": max(lengths) if lengths else None,
        "tailwind_reference": sum("tailwind" in c.lower() for c in codes),
        "script_tag": sum(bool(re.search(r"<script\b", c, re.I)) for c in codes),
        "inline_event_attribute": sum(bool(re.search(r"\bon(?:click|change|submit|load|input)\s*=", c, re.I)) for c in codes),
        "http_url": sum(bool(re.search(r"https?://", c, re.I)) for c in codes),
        "source_unsplash_reference": sum("source.unsplash.com" in c.lower() for c in codes),
        "placeholder_text": sum(bool(re.search(r"lorem ipsum|some (information|text)|your .{0,20} here", c, re.I)) for c in codes),
        "prompt_cjk_characters_present": sum(bool(re.search(r"[\u3400-\u9fff]", p)) for p in prompts),
        "notes": "Lexical indicators only; no HTML/CSS/JS execution or browser validation. Character counts are not tokenizer counts.",
    }


jobs = []
for short, repo in (("webdev", "Hoglet-33/webdev-coding-dataset"), ("webmc", "IFM/WebMC"), ("websight", "HuggingFaceM4/WebSight")):
    jobs.extend([
        (f"{short}_metadata", f"https://huggingface.co/api/datasets/{repo}", "json"),
        (f"{short}_card", f"https://huggingface.co/datasets/{repo}/raw/main/README.md", "text"),
    ])
jobs.append(("webmc_tree", "https://huggingface.co/api/datasets/IFM/WebMC/tree/main", "json"))
jobs.append(("WebMC", "https://huggingface.co/datasets/IFM/WebMC/resolve/main/WebMC.json", "json"))
jobs.append(("webdev_rows", "https://datasets-server.huggingface.co/rows?" + urlencode({"dataset": "Hoglet-33/webdev-coding-dataset", "config": "default", "split": "train", "offset": 0, "length": 100}), "json"))
jobs.append(("websight_size", "https://datasets-server.huggingface.co/size?dataset=HuggingFaceM4%2FWebSight", "json"))
for offset in (0, 240000, 480000, 720000, 960000, 1200000, 1440000, 1680000):
    jobs.append((f"websight_rows_{offset}", "https://datasets-server.huggingface.co/rows?" + urlencode({"dataset": "HuggingFaceM4/WebSight", "config": "v0.2", "split": "train", "offset": offset, "length": 100}), "json"))

results = {}
with ThreadPoolExecutor(max_workers=4) as pool:
    for future in as_completed([pool.submit(fetch, *job) for job in jobs]):
        name, result = future.result()
        results[name] = result
        print(f"{name}: HTTP {result.get('status')} {result.get('error', '')}", flush=True)

report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "requests": {name: {key: val for key, val in result.items() if key != "data"} for name, result in results.items()}}
webmc = results.get("WebMC", {}).get("data", [])
report["webmc"] = {
    "count": len(webmc),
    "columns": sorted({key for row in webmc for key in row}),
    "choice_counts": dict(Counter(len(row.get("choices", [])) for row in webmc)),
    "gold_counts": dict(Counter(row.get("gold") for row in webmc)),
    "gold_out_of_bounds": sum(not isinstance(row.get("gold"), int) or not 0 <= row["gold"] < len(row.get("choices", [])) for row in webmc),
    "duplicate_queries_exact": len(webmc) - len({row.get("query") for row in webmc}),
    "queries_containing_html": sum("<html" in row.get("query", "").lower() for row in webmc),
    "example": webmc[0] if webmc else None,
    "repository_files": [{key: item.get(key) for key in ("path", "type", "size")} for item in results.get("webmc_tree", {}).get("data", [])],
}
websight = []
for offset in (0, 240000, 480000, 720000, 960000, 1200000, 1440000, 1680000):
    response = results.get(f"websight_rows_{offset}", {}).get("data", {})
    websight.extend(item["row"] for item in response.get("rows", []))
report["websight_sample"] = stats(websight, "llm_generated_idea", "text")
report["websight_sample"]["sampling"] = "Eight ordered blocks, length 100, offsets 0 through 1680000; not a random sample. Images were not downloaded."
report["websight_size"] = results.get("websight_size", {}).get("data")
report["webdev_access"] = {name: report["requests"][name] for name in ("webdev_metadata", "webdev_card", "webdev_rows")}
webdev_rows = results.get("webdev_rows", {}).get("data", {}).get("rows", [])
if webdev_rows:
    report["webdev_sample"] = stats([item["row"] for item in webdev_rows], "instruction", "output")
report["revisions"] = {name: results.get(f"{name}_metadata", {}).get("data", {}).get("sha") for name in ("webdev", "webmc", "websight")}
(OUT / "audit_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({key: val for key, val in report.items() if key not in ("requests", "websight_size")}, ensure_ascii=False, indent=2))
