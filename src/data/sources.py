"""Download bounded, revision-pinned text subsets with atomic provenance manifests."""
import argparse
import hashlib
import itertools
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(path: Path, metadata: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def configure_cache(root: Path):
    cache = root / ".cache/huggingface"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(cache)
    os.environ["HF_HUB_CACHE"] = str(cache / "hub")
    os.environ["HF_DATASETS_CACHE"] = str(cache / "datasets")
    return cache


def stream_websight(config_name: str, revision: str, limit: int, seed: int,
                    *, loader=None, buffer_size=1000, cache_dir=None):
    if config_name not in {"v0.1", "v0.2"} or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("WebSight requires a known config and a pinned 40-character revision")
    if limit <= 0 or buffer_size <= 0:
        raise ValueError("limit and buffer_size must be positive")
    if loader is None:
        from datasets import load_dataset
        loader = load_dataset
    columns = ["text"] + (["llm_generated_idea"] if config_name == "v0.2" else [])
    dataset = loader("HuggingFaceM4/WebSight", config_name, split="train", revision=revision,
                     streaming=True, columns=columns, cache_dir=str(cache_dir) if cache_dir else None)
    dataset = dataset.select_columns(columns).shuffle(seed=seed, buffer_size=buffer_size)
    for index, row in enumerate(dataset.take(limit)):
        text = row["text"]
        if not isinstance(text, str):
            raise ValueError("Expected text string from WebSight")
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        yield {"source_row_id": f"{config_name}:{revision}:{index}:{text_hash[:16]}",
               "source_revision": revision, "source_index": index, "text_sha256": text_hash,
               "text": text, "idea": row.get("llm_generated_idea", "")}


def stream_vulcan(source: dict):
    from urllib.request import Request, urlopen
    url = f"https://huggingface.co/datasets/{source['dataset']}/resolve/{source['revision']}/{source['filename']}"
    with urlopen(Request(url, headers={"User-Agent": "mini-gpt-webcodegen"}), timeout=60) as response:
        for index, line in enumerate(itertools.islice(response, source["limit"])):
            row = json.loads(line)
            messages = row["messages"]
            prompt = next(m["content"] for m in messages if m["role"] == "user")
            text = next(m["content"] for m in messages if m["role"] == "assistant")
            if not isinstance(text, str) or not isinstance(prompt, str):
                raise ValueError("Vulcan messages must contain text strings")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            yield {"source_row_id": f"vulcan:{source['revision']}:{index}:{digest[:16]}",
                   "source_revision": source["revision"], "source_index": index,
                   "text_sha256": digest, "text": text, "idea": prompt}


def download_source(source: dict, root: Path, *, rows=None, reserve_bytes=15 * 1024**3,
                    max_bytes=1024**3, seed=42) -> dict:
    source_id, limit = source["id"], source["limit"]
    if not re.fullmatch(r"[a-z0-9_]+", source_id) or not isinstance(limit, int) or limit < 1:
        raise ValueError("Invalid source id or limit")
    root.mkdir(parents=True, exist_ok=True)
    output = root / f"data/raw/{source_id}-{limit}.jsonl"
    partial = output.with_suffix(".jsonl.partial")
    manifest_path = root / f"data/manifests/{source_id}-{limit}.json"
    signature = hashlib.sha256(json.dumps({"source": source, "seed": seed}, sort_keys=True).encode()).hexdigest()
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old.get("status") == "complete":
            if old.get("selection_sha256") != signature or not output.exists() or sha256_file(output) != old.get("sha256"):
                raise ValueError("Existing download does not match manifest/config; do not use it")
            print(f"reuse {source_id}: {old['rows']} rows, SHA-256 verified", flush=True)
            return old
    if output.exists():
        raise ValueError("Final source file exists without a complete matching manifest")
    before = shutil.disk_usage(root).free
    if before < reserve_bytes + max_bytes:
        raise OSError(f"Storage insufficient: free={before}, reserve={reserve_bytes}, budget={max_bytes}")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"status": "running", "source": source, "selection_sha256": signature,
                "seed": seed, "sampling": "seeded buffer and shard shuffle" if source.get("kind") == "parquet" else "bounded source order",
                "started_utc": datetime.now(timezone.utc).isoformat(), "rows": 0, "bytes": 0,
                "free_bytes_before": before, "output": output.relative_to(root).as_posix()}
    write_manifest(manifest_path, manifest)
    try:
        if rows is None:
            rows = stream_websight(source["config_name"], source["revision"], limit, seed,
                                   buffer_size=source["buffer_size"], cache_dir=root / ".cache/huggingface/datasets") if source["kind"] == "parquet" else stream_vulcan(source)
        with partial.open("wb") as handle:
            for row in itertools.islice(rows, limit):
                if not isinstance(row.get("text"), str):
                    raise ValueError("Source row must contain text string")
                record = {**row, **{key: source[key] for key in ["license_id", "source_url", "attribution", "style_mode"] if key in source},
                          "source_id": source_id, "source_revision": source.get("revision", "")}
                payload = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
                if manifest["bytes"] + len(payload) > max_bytes:
                    raise ValueError("Raw byte budget exceeded; partial data stays excluded")
                handle.write(payload)
                manifest["rows"] += 1
                manifest["bytes"] += len(payload)
                if manifest["rows"] % 100 == 0 and shutil.disk_usage(root).free < reserve_bytes:
                    raise OSError("Storage reserve reached; stop downloading")
                if manifest["rows"] % 1000 == 0:
                    print(f"{source_id}: {manifest['rows']}/{limit} rows, {manifest['bytes']/1024**2:.1f} MiB", flush=True)
        if manifest["rows"] != limit:
            raise ValueError(f"Source ended early: {manifest['rows']} of {limit} requested rows")
        os.replace(partial, output)
        manifest.update(status="complete", sha256=sha256_file(output),
                        completed_utc=datetime.now(timezone.utc).isoformat(), free_bytes_after=shutil.disk_usage(root).free)
        write_manifest(manifest_path, manifest)
        print(f"complete {source_id}: {manifest['rows']} rows, {manifest['bytes']} bytes", flush=True)
        return manifest
    except Exception as error:
        manifest.update(status="failed", error=f"{type(error).__name__}: {error}",
                        partial_file=partial.relative_to(root).as_posix())
        write_manifest(manifest_path, manifest)
        raise


def verify_license(source, root):
    from huggingface_hub import HfApi, hf_hub_download
    info = HfApi().dataset_info(source["dataset"], revision=source["revision"])
    if info.sha != source["revision"] or info.card_data.to_dict().get("license") != source["license_id"]:
        raise ValueError(f"License or revision mismatch: {source['id']}")
    card = hf_hub_download(source["dataset"], "README.md", repo_type="dataset", revision=source["revision"])
    target = root / "data/licenses" / (source["id"] + "_CARD.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(card, target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/dataset.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--source", action="append")
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    configure_cache(ROOT)
    total = 0
    for raw_source in config["sources"]:
        source = dict(raw_source)
        if args.source and source["id"] not in args.source:
            continue
        if args.limit is not None:
            source["limit"] = min(source["limit"], args.limit)
        verify_license(source, ROOT)
        result = download_source(source, ROOT, seed=config["seed"], reserve_bytes=config["reserve_free_bytes"],
                                 max_bytes=config["raw_max_bytes"] - total)
        total += result["bytes"]
    print(json.dumps({"total_raw_bytes": total, "free_bytes_after": shutil.disk_usage(ROOT).free}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
