"""Find train-only annotation candidates by HTML signals, without creating labels."""
import argparse
import csv
import json
import re
import shutil
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from src.data.normalize import read_jsonl
from src.data.sources import sha256_file, write_manifest
from src.data.split import assignment_hash, read_group_assignment

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("testimonial", "pricing_table", "accordion", "tabs", "modal", "filter")


class Signals(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags, self.roles, self.words, self.scripts, self.handlers = set(), set(), [], [], []
        self.hidden = []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        values = dict(attrs)
        self.roles.add(values.get("role", ""))
        self.handlers.extend(value or "" for key, value in attrs if key.startswith("on"))
        if tag in {"style", "script"}:
            self.hidden.append(tag)

    def handle_endtag(self, tag):
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()

    def handle_data(self, data):
        if self.hidden:
            if self.hidden[-1] == "script":
                self.scripts.append(data)
        elif data.strip():
            self.words.append(" ".join(data.split()))


def candidate_signals(text):
    parsed = Signals()
    parsed.feed(text)
    parsed.close()
    body = " ".join(parsed.words)
    lower = body.lower()
    js = " ".join(parsed.scripts + parsed.handlers).lower()
    signals = {}
    if re.search(r"testimonial|customer reviews|success stories|what our (?:customers|clients) say", lower):
        signals["testimonial"] = "visible review/testimonial heading; quote and author still need inspection"
    if re.search(r"pricing|subscription|per month|monthly|/mo\b", lower) and re.search(r"[$€£]\s*\d|\d\s*(?:usd|eur)", lower):
        signals["pricing_table"] = "visible pricing/subscription wording and currency amount; plans still need inspection"
    if {"details", "summary"}.issubset(parsed.tags):
        signals["accordion"] = "details/summary markup; native interaction needs renderer-catalog adaptation"
    elif "accordion" in js and ("addeventlistener" in js or parsed.handlers):
        signals["accordion"] = "accordion script with event hooks; expand/collapse behavior unverified"
    if ({"tab", "tablist"} & parsed.roles or re.search(r"\b(?:opentab|switchtab|activatetab)\b", js)) and js:
        signals["tabs"] = "tab role or tab function with script/event code; panel wiring unverified"
    if ("dialog" in parsed.tags or "dialog" in parsed.roles or "modal" in js) and js:
        signals["modal"] = "dialog/modal signal with script/event code; opening and closing unverified"
    if {"input", "select"} & parsed.tags and ".filter(" in js and ("addeventlistener" in js or parsed.handlers):
        signals["filter"] = "input/select markup with filter and event code; dataset filtering semantics unverified"
    return signals, body[:600]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--per-type", type=int, default=6)
    args = parser.parse_args()
    output, report_path = args.output.resolve(), args.report.resolve()
    if not output.is_relative_to(ROOT / "outputs/annotation_candidates") or not report_path.is_relative_to(ROOT / "reports/data"):
        raise ValueError("Candidate artifacts must stay in their project directories")
    if output.exists() or report_path.exists() or not 1 <= args.per_type <= 50:
        raise ValueError("Use new output paths and a per-type limit from 1 to 50")
    reserve = json.loads((ROOT / "configs/dataset.json").read_text(encoding="utf-8"))["reserve_free_bytes"]
    if shutil.disk_usage(ROOT).free < reserve + 32 * 1024 * 1024:
        raise ValueError("Candidate catalog would violate the storage reserve")
    assignment = read_group_assignment(ROOT / "data/processed/pretrain")
    train_path = ROOT / "data/processed/pretrain/train.jsonl"
    manifest = json.loads((train_path.parent / "manifest.json").read_text(encoding="utf-8"))
    counts, selected_counts, families, picked_families = Counter(), Counter(), {k: set() for k in KINDS}, {k: set() for k in KINDS}
    picked, total, html_rows, vulcan_ideas = [], 0, 0, Counter()
    for row in read_jsonl(train_path):
        total += 1
        if row["split"] != "train" or assignment.get(row["group_id"]) != "train":
            raise ValueError("Candidate discovery accepts authoritative train rows only")
        if row["source_id"] == "vulcan":
            vulcan_ideas[row.get("idea", "")] += 1
        if row["code_language"] != "html":
            continue
        html_rows += 1
        signals, excerpt = candidate_signals(row["text"])
        for kind, signal in signals.items():
            counts[kind] += 1
            families[kind].add(row["group_id"])
            if selected_counts[kind] >= args.per_type or row["group_id"] in picked_families[kind]:
                continue
            selected_counts[kind] += 1
            picked_families[kind].add(row["group_id"])
            picked.append({"candidate_type": kind, "signal": signal, "visible_excerpt": excerpt,
                           **{key: row[key] for key in ("source_row_id", "source_id", "source_revision", "license_id", "source_url", "attribution", "style_mode", "group_id", "split", "text_sha256", "normalized_text_sha256")},
                           "candidate_status": "unreviewed_signal", "source_text": row["text"]})
    if total != manifest["row_counts"]["train"] or sha256_file(train_path) != manifest["files"]["train"]["sha256"]:
        raise ValueError("Train corpus changed during candidate discovery")
    output.mkdir(parents=True)
    with (output / "candidates.jsonl").open("w", encoding="utf-8") as handle:
        for row in picked:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    fields = ["candidate_type", "source_row_id", "source_id", "source_revision", "license_id", "group_id", "split", "style_mode", "signal", "visible_excerpt", "candidate_status"]
    with (output / "candidates.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in picked:
            writer.writerow({key: "'" + row[key] if row[key].startswith(("=", "+", "-", "@")) else row[key] for key in fields})
    report = {"status": "candidate_signals_only", "rows_scanned": total, "html_rows_scanned": html_rows,
              "split": "train", "per_type_limit": args.per_type,
              "candidate_row_counts": {k: counts[k] for k in KINDS},
              "candidate_family_counts": {k: len(families[k]) for k in KINDS},
              "selected_counts": {k: selected_counts[k] for k in KINDS},
              "selected_records": len(picked), "selected_unique_source_rows": len({r['source_row_id'] for r in picked}),
              "selected_unique_families": len({r['group_id'] for r in picked}),
              "vulcan_train_idea_counts": dict(vulcan_ideas),
              "train_sha256": sha256_file(train_path), "assignment_sha256": assignment_hash(assignment),
              "output_path": str(output.relative_to(ROOT)),
              "files": {p.name: sha256_file(p) for p in output.iterdir()},
              "limits": ["Heuristic signals can include placeholders or miss differently named components",
                         "No Indonesian prompts or PageSpec targets created", "No human review or browser execution",
                         "Only train corpus inspected; validation/test not used for selection", "No SFT updates"]}
    write_manifest(output / "manifest.json", report)
    write_manifest(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
