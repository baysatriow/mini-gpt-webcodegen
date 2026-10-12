"""Separate HTML pretraining data from reviewed Indonesian PageSpec instruction data."""
import argparse
import hashlib
import json
import os
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from .schema import PageExample, validate_page_spec
from .sources import write_manifest


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{Path(path).name}:{number}: invalid JSON") from error


class StructureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tokens = []
        self.tags = set()
        self.closed = set()
        self.headings = []
        self.text = []
        self.current = ""
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        self.current = tag
        if tag in {"style", "script"}:
            self.skip += 1
        values = dict(attrs)
        layout = sorted(c for c in values.get("class", "").split() if re.match(
            r"^(?:[a-z]+:)?(?:flex|grid|container|hidden|block|relative|absolute|fixed|sticky|w-|h-|p[xytrbl]?-|m[xytrbl]?-|gap-|space-|justify-|items-)", c))
        self.tokens.append("+" + tag + ":" + ",".join(layout) + ":" + values.get("type", ""))

    def handle_endtag(self, tag):
        self.closed.add(tag)
        self.tokens.append("-" + tag)
        if tag in {"style", "script"}:
            self.skip = max(0, self.skip - 1)
        self.current = ""

    def handle_data(self, data):
        value = " ".join(data.split())
        if value and not self.skip:
            self.text.append(value)
            if self.current == "h1":
                self.headings.append(value)


def normalize_html_document(text):
    parser = StructureParser()
    parser.feed(text)
    parser.close()
    if {"html", "body"}.issubset(parser.tags) and {"html", "body"}.issubset(parser.closed):
        return text, "none"
    if {"html", "body"} & (parser.tags | parser.closed) or not (parser.tags - {"style", "script"}):
        raise ValueError("html_structure: incomplete document or no component markup")
    return "<html><body>" + text + "</body></html>", "wrapped_component_fragment"


def parse_html(text):
    document, _ = normalize_html_document(text)
    parser = StructureParser()
    parser.feed(document)
    parser.close()
    return parser


def structural_group(text: str) -> str:
    parser = parse_html(text)
    return "layout-" + hashlib.sha256("|".join(parser.tokens).encode()).hexdigest()[:24]


def classify_code(text):
    parser = StructureParser()
    parser.feed(text)
    if parser.tags:
        return "html"
    if re.search(r"\b(?:const|let|var)\s+[A-Za-z_$]|\bfunction\s*(?:[A-Za-z_$][\w$]*)?\s*\(|(?:document|window)\.|=>", text):
        return "javascript"
    if "{" in text and text.count("{") == text.count("}") and re.search(r"[\w-]+\s*:\s*[^;{}]+;", text):
        return "css"
    raise ValueError("code_language: unrecognized HTML/CSS/JavaScript source")


def code_group(text, language):
    if language == "html":
        return structural_group(text)
    skeleton = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    if language == "css":
        skeleton = re.sub(r"([\w-]+)\s*:\s*[^;{}]+;", r"\1:VALUE;", skeleton)
    else:
        skeleton = re.sub(r"([\"']).*?\1", "STRING", skeleton)
        skeleton = re.sub(r"\b\d+(?:\.\d+)?\b", "NUMBER", skeleton)
    skeleton = re.sub(r"\s+", "", skeleton)
    return language + "-" + hashlib.sha256(skeleton.encode()).hexdigest()[:24]


def _require_provenance(row):
    for key in ["source_row_id", "source_id", "source_revision", "license_id", "source_url", "attribution"]:
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(f"{key}: missing provenance")
    if row["license_id"] not in {"cc-by-4.0", "mit"}:
        raise ValueError("license_id: unsupported/unverified license")
    if not re.fullmatch(r"[0-9a-f]{40}", row["source_revision"]):
        raise ValueError("source_revision: expected pinned commit")


def normalize_annotation(row: dict, annotation: dict, source_meta: dict) -> PageExample:
    _require_provenance(row)
    if source_meta.get("id") != row["source_id"] or annotation.get("source_row_id") != row["source_row_id"]:
        raise ValueError("source_row_id: source metadata or row reference mismatch")
    if annotation.get("annotation_status") != "reviewed":
        raise ValueError("annotation_status: draft/unreviewed records cannot enter SFT")
    for key in ["reviewer", "annotation_revision", "prompt", "group_id"]:
        if not isinstance(annotation.get(key), str) or not annotation[key].strip():
            raise ValueError(f"{key}: missing annotation field")
    if annotation.get("prompt_language") != "id":
        raise ValueError("prompt_language: Indonesian reviewed prompt required")
    if len(annotation["prompt"]) > 2000 or not re.fullmatch(r"[a-z0-9_-]{1,100}", annotation["group_id"]):
        raise ValueError("prompt/group_id: invalid length or identifier")
    errors = validate_page_spec(annotation.get("target_spec"))
    if errors:
        raise ValueError("target_spec: " + "; ".join(errors))
    canonical = json.dumps(annotation["target_spec"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    example_id = hashlib.sha256((row["source_row_id"] + annotation["prompt"] + canonical).encode()).hexdigest()
    return PageExample(example_id, annotation["prompt"].strip(), annotation["target_spec"], row["source_id"],
                       row["source_revision"], row["license_id"], annotation["group_id"],
                       source_url=row["source_url"], attribution=row["attribution"],
                       annotation_revision=annotation["annotation_revision"], reviewer=annotation["reviewer"])


def normalize_jsonl(source_path: Path, annotation_path: Path, output_path: Path) -> tuple[int, int]:
    source_paths = source_path if isinstance(source_path, (list, tuple)) else [source_path]
    sources = {row["source_row_id"]: row for path in source_paths for row in read_jsonl(path)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial = output_path.with_suffix(".jsonl.partial")
    accepted, rejects = 0, []
    with partial.open("w", encoding="utf-8") as handle:
        for index, ann in enumerate(read_jsonl(annotation_path)):
            try:
                row = sources.get(ann.get("source_row_id"))
                if row is None:
                    raise ValueError("source_row_id: unknown source row")
                record = normalize_annotation(row, ann, {"id": row["source_id"]})
                handle.write(json.dumps(record.to_record(), ensure_ascii=False) + "\n")
                accepted += 1
            except ValueError as error:
                rejects.append({"annotation_index": index, "source_row_id": ann.get("source_row_id"), "reason": str(error)})
    if accepted:
        os.replace(partial, output_path)
    else:
        partial.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
    write_manifest(output_path.with_suffix(".rejects.json"), {"accepted": accepted, "rejected": len(rejects),
                   "status": "ready" if accepted else "awaiting_review", "rejects": rejects})
    return accepted, len(rejects)


def prepare_pretraining(source_paths, output_path, max_text_bytes=262144):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial = output_path.with_suffix(".jsonl.partial")
    counts, rejects = Counter(), []
    with partial.open("w", encoding="utf-8") as output:
        for path in source_paths:
            for row in read_jsonl(path):
                try:
                    _require_provenance(row)
                    text = row.get("text")
                    if not isinstance(text, str) or not text.strip():
                        raise ValueError("text: empty/non-text source")
                    text = re.sub(r"^```(?:html)?\s*\n|\n```\s*$", "", text.strip())
                    if len(text.encode("utf-8")) > max_text_bytes:
                        raise ValueError("text: exceeds byte limit")
                    source_hash = hashlib.sha256(row["text"].encode()).hexdigest()
                    language = classify_code(text)
                    text, transform = normalize_html_document(text) if language == "html" else (text, "not_html")
                    group = code_group(text, language)
                    record = {**row, "text": text, "group_id": group, "split": "unsplit",
                              "text_sha256": source_hash, "html_transform": transform,
                              "normalized_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                              "example_id": hashlib.sha256(text.encode()).hexdigest(),
                              "data_mode": "pretrain", "code_language": language, "basic_html_parse": language == "html"}
                    output.write(json.dumps(record, ensure_ascii=False) + "\n")
                    counts["accepted"] += 1
                except ValueError as error:
                    counts["rejected"] += 1
                    rejects.append({"source_row_id": row.get("source_row_id"), "reason": str(error)})
    os.replace(partial, output_path)
    report = {"accepted": counts["accepted"], "rejected": counts["rejected"], "rejects": rejects,
              "html_check": "basic parse and root/body presence; not browser validation"}
    write_manifest(output_path.with_suffix(".rejects.json"), report)
    return report


def create_review_queue(source_paths, output_path, per_source=50):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as output:
        for path in source_paths:
            for row in __import__("itertools").islice(read_jsonl(path), per_source):
                try:
                    parsed = parse_html(row["text"])
                except ValueError:
                    continue
                heading = (parsed.headings or ["Website"])[0][:180]
                spec = {"schema_version": "1.0", "title": heading, "language": "en", "style_mode": row["style_mode"],
                        "theme": {"primary": "#2563eb", "background": "#ffffff", "text": "#111827", "font": "sans"},
                        "sections": [{"id": "hero-1", "type": "hero", "props": {"heading": heading,
                                      "text": " ".join(parsed.text)[:1000] or "Website content"}}], "interactions": []}
                ann = {"source_row_id": row["source_row_id"], "prompt": row.get("idea", ""), "prompt_language": "en",
                       "target_spec": spec, "group_id": structural_group(row["text"]), "annotation_status": "draft",
                       "reviewer": "", "annotation_revision": "draft-1",
                       "review_notes": "Simplified extraction. Review layout, theme, interactions, content, Indonesian prompt and PageSpec; not a faithful conversion."}
                output.write(json.dumps(ann, ensure_ascii=False) + "\n")
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(normalize_jsonl(args.source, args.annotations, args.output) if args.annotations else
          {k: v for k, v in prepare_pretraining([args.source], args.output).items() if k != "rejects"})


if __name__ == "__main__":
    main()
