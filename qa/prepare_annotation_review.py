"""Export a local annotation review packet without approving data or starting SFT."""
import argparse
import csv
import hashlib
import html
import json
import shutil
from collections import Counter
from pathlib import Path

from tokenizers import Tokenizer

from src.data.dataset import encode_sft
from src.data.normalize import normalize_source_code, read_jsonl
from src.data.schema import validate_page_spec
from src.data.sources import sha256_file, write_manifest
from src.data.split import assignment_hash, read_group_assignment

ROOT = Path(__file__).resolve().parents[1]


def inspect_candidate(annotation, source, assignment, tokenizer, block_size):
    group = normalize_source_code(source["text"])[3]
    if annotation["group_id"] != group or group not in assignment:
        raise ValueError("Draft family differs from the verified source family")
    if hashlib.sha256(source["text"].encode()).hexdigest() != source["text_sha256"]:
        raise ValueError("Raw source text checksum mismatch")
    if annotation["annotation_status"] != "draft" or annotation.get("reviewer"):
        raise ValueError("Review exporter accepts drafts with an empty human reviewer only")
    if annotation["target_spec"]["style_mode"] != source["style_mode"]:
        raise ValueError("Draft styling differs from the source configuration")
    canonical = json.dumps(annotation["target_spec"], sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    errors = validate_page_spec(annotation["target_spec"])
    tokens = len(tokenizer.encode(annotation["prompt"], add_special_tokens=False).ids)
    tokens += len(tokenizer.encode(canonical, add_special_tokens=False).ids) + 3
    blockers = list(errors)
    if annotation.get("prompt_language") != "id":
        blockers.append("Prompt belum berbahasa Indonesia")
    try:
        encode_sft(annotation["prompt"], canonical, tokenizer, block_size)
    except ValueError as error:
        blockers.append(str(error))
    return {"source_group_id": group, "authoritative_split": assignment[group],
            "schema_valid": not errors, "sequence_tokens": tokens,
            "block_size": block_size, "technical_blockers": blockers,
            "human_review_required": True}


def prepare_packet(queue_path, drafts_path, output, report_path):
    if not output.is_relative_to(ROOT / "outputs/annotation_review") or not report_path.is_relative_to(ROOT / "reports/data"):
        raise ValueError("Packet must stay under outputs/annotation_review and report under reports/data")
    if output.exists() or report_path.exists():
        raise ValueError("Use new packet and report paths; previous review evidence is immutable")
    config = json.loads((ROOT / "configs/dataset.json").read_text(encoding="utf-8"))
    block_size = json.loads((ROOT / "configs/model.json").read_text(encoding="utf-8"))["block_size"]
    assignment = read_group_assignment(ROOT / "data/processed/pretrain")
    tokenizer = Tokenizer.from_file(str(ROOT / "data/tokenizer/tokenizer.json"))
    queue, drafts = list(read_jsonl(queue_path)), list(read_jsonl(drafts_path))
    queue_by_id = {row["source_row_id"]: row for row in queue}
    if len(queue_by_id) != len(queue) or len({row["source_row_id"] for row in drafts}) != len(drafts):
        raise ValueError("Duplicate source IDs in queue or pilot")
    if not drafts or any(row["source_row_id"] not in queue_by_id for row in drafts):
        raise ValueError("Pilot must be a nonempty subset of the existing queue")
    sources, raw_hashes = {}, {}
    for meta in config["sources"]:
        path = ROOT / "data/raw" / f"{meta['id']}-{meta['limit']}.jsonl"
        raw_hashes[str(path.relative_to(ROOT))] = sha256_file(path)
        for row in read_jsonl(path):
            if row["source_row_id"] not in queue_by_id:
                continue
            for key in ("source_revision", "license_id", "source_url", "attribution", "style_mode"):
                expected = meta["revision"] if key == "source_revision" else meta[key]
                if row[key] != expected:
                    raise ValueError(f"Source config mismatch: {key}")
            if row["source_id"] != meta["id"] or row["source_row_id"] in sources:
                raise ValueError("Source identity mismatch or duplicate raw ID")
            sources[row["source_row_id"]] = row
    if sources.keys() != queue_by_id.keys():
        raise ValueError("Queue contains an unknown source row")
    inventory = [inspect_candidate(row, sources[row["source_row_id"]], assignment, tokenizer, block_size) for row in queue]
    assessments = [inspect_candidate(row, sources[row["source_row_id"]], assignment, tokenizer, block_size) for row in drafts]
    if any(item["technical_blockers"] for item in assessments):
        raise ValueError("Pilot contains a schema, language, payload, or context blocker")
    free_before = shutil.disk_usage(ROOT).free
    if free_before < config["reserve_free_bytes"] + 10 * 1024 * 1024:
        raise ValueError("Review packet would violate the configured storage reserve")
    output.mkdir(parents=True)
    write_manifest(output / "drafts.json", drafts)
    # Keep a JSONL compatible with the normalizer, still explicitly draft.
    with (output / "drafts.jsonl").open("w", encoding="utf-8") as handle:
        for row in drafts:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    fields = ["review_id", "source_row_id", "source_id", "source_revision", "license_id",
              "source_group_id", "authoritative_split", "style_mode", "schema_valid", "sequence_tokens",
              "technical_blockers", "prompt", "annotation_revision", "human_decision", "reviewer",
              "reviewed_at", "prompt_ok", "content_ok", "projection_ok", "interactions_ok", "notes"]
    def worksheet(path, rows, checks):
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row, check in zip(rows, checks):
                source = sources[row["source_row_id"]]
                record = {key: source[key] for key in ("source_row_id", "source_id", "source_revision", "license_id", "style_mode")}
                record.update({key: check[key] for key in ("source_group_id", "authoritative_split", "schema_valid", "sequence_tokens")})
                record.update(review_id="R-" + hashlib.sha256(row["source_row_id"].encode()).hexdigest()[:12],
                              technical_blockers="; ".join(check["technical_blockers"]), prompt=row["prompt"],
                              annotation_revision=row["annotation_revision"])
                # Spreadsheet formulas are escaped for display only; canonical JSONL is unchanged.
                writer.writerow({key: "'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value
                                 for key, value in record.items()})
    worksheet(output / "inventory.csv", queue, inventory)
    worksheet(output / "review.csv", drafts, assessments)
    pages = ["<!doctype html><html lang='id'><meta charset='utf-8'><title>Review anotasi pilot</title>",
             "<style>body{font:16px sans-serif;max-width:1100px;margin:30px auto;padding:0 20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f4f6;padding:16px}article{border-top:2px solid #ccc;margin:30px 0}h2{color:#155e75}</style>",
             "<h1>Review anotasi pilot</h1><p>Seluruh kandidat masih DRAFT. Isi review.csv setelah membandingkan prompt, target, dan sumber. Kode sumber ditampilkan sebagai teks.</p>"]
    for index, (row, check) in enumerate(zip(drafts, assessments), 1):
        source = sources[row["source_row_id"]]
        review_id = "R-" + hashlib.sha256(row["source_row_id"].encode()).hexdigest()[:12]
        pages.append(f"<article><h2>{index}. {review_id}: {html.escape(row['target_spec']['title'])}</h2>")
        for title, value in [("Provenance dan pemeriksaan", {**check, **{key: source[key] for key in ("source_row_id", "source_id", "source_revision", "license_id", "source_url", "attribution", "text_sha256")}}),
                             ("Prompt Indonesia", row["prompt"]), ("Target PageSpec draft", row["target_spec"]),
                             ("Catatan proyeksi", row.get("review_notes", "")), ("Idea sumber", source.get("idea", "")),
                             ("Kode sumber asli", source["text"])]:
            text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
            pages.append(f"<h3>{title}</h3><pre>{html.escape(text)}</pre>")
        pages.append("</article>")
    pages.append("</html>")
    (output / "packet.html").write_text("\n".join(pages), encoding="utf-8")
    def coverage(rows, checks):
        return {"rows": len(rows), "unique_families": len({x['source_group_id'] for x in checks}),
                "split_counts": dict(Counter(x["authoritative_split"] for x in checks)),
                "style_counts": dict(Counter(x["target_spec"]["style_mode"] for x in rows)),
                "source_counts": dict(Counter(sources[x["source_row_id"]]["source_id"] for x in rows)),
                "section_counts": dict(Counter(s["type"] for x in rows for s in x["target_spec"]["sections"])),
                "interaction_counts": dict(Counter(i["type"] for x in rows for i in x["target_spec"]["interactions"])),
                "schema_valid_rows": sum(x["schema_valid"] for x in checks),
                "within_context_rows": sum(x["sequence_tokens"] <= block_size for x in checks),
                "technical_ready_rows": sum(not x["technical_blockers"] for x in checks),
                "max_sequence_tokens": max(x["sequence_tokens"] for x in checks)}
    report = {"status": "awaiting_human_review", "reviewed_production_rows": 0,
              "queue": coverage(queue, inventory), "pilot": coverage(drafts, assessments),
              "block_size": block_size, "selection": "operator-curated subset; authoritative partitions inherited; not representative evaluation",
              "tokenizer_sha256": sha256_file(ROOT / "data/tokenizer/tokenizer.json"),
              "assignment_sha256": assignment_hash(assignment), "raw_files_sha256": raw_hashes,
              "queue_sha256": sha256_file(queue_path), "pilot_input_sha256": sha256_file(drafts_path),
              "packet_path": str(output.relative_to(ROOT)), "free_bytes_before": free_before,
              "files": {p.name: sha256_file(p) for p in sorted(output.iterdir()) if p.is_file()},
              "limits": ["No human decisions supplied", "No source HTML executed or browser layout checked",
                         "No SFT updates", "Manual projection and translated texts require review",
                         "Missing interaction types and limited sample size prevent broad quality claims"]}
    write_manifest(output / "manifest.json", report)
    write_manifest(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=ROOT / "data/annotations/review_queue.jsonl")
    parser.add_argument("--drafts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = prepare_packet(args.queue.resolve(), args.drafts.resolve(), args.output.resolve(), args.report.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
