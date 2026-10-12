"""Run a project command and retain its output, exit status, and Git revision."""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIB = dt.timezone(dt.timedelta(hours=7), "Asia/Jakarta")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Supply a command after --")
    logs = ROOT / "logs"
    ledger = logs / "LOG_EKSPERIMEN_DAN_INTERAKSI_LLM.md"
    content = ledger.read_text(encoding="utf-8")
    ids = [int(n) for n in re.findall(r"^### RUN-(\d+)", content, re.M)]
    # Reserve ID at process start so overlapping downloads and tests do not reuse it.
    reserved = [int(p.name[4:7]) for p in logs.glob("RUN-[0-9][0-9][0-9]_*.txt")]
    run_id = f"RUN-{max(ids + reserved + [0]) + 1:03d}"
    slug = re.sub(r"[^a-z0-9]+", "_", args.label.lower()).strip("_")[:70]
    path = logs / f"{run_id}_{slug}.txt"
    start = dt.datetime.now(WIB)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip()
    display = subprocess.list2cmdline(command).replace(str(ROOT), ".")
    with path.open("x", encoding="utf-8") as log:
        log.write(f"{run_id} | {start.isoformat()} | {args.label}\nCommand: {display}\nCommit: {revision}\n\n")
        log.flush()
        print(f"{run_id}: {args.label}", flush=True)
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                   errors="replace", env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"})
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        code = process.wait()
        log.write(f"\nExit code: {code}\n")
    end = dt.datetime.now(WIB)
    # Re-read because a second process may have completed while this one was running.
    content = ledger.read_text(encoding="utf-8")
    entry = (f"\n### {run_id}\n\n- **Waktu:** {start.isoformat()} sampai {end.isoformat()}.\n"
             f"- **Tujuan:** {args.label}.\n- **Command:** `{display}`.\n"
             f"- **Commit:** `{revision}`.\n- **Hasil:** exit {code}.\n"
             f"- **Output lengkap:** `logs/{path.name}`.\n")
    content = re.sub(r"Nomor run berikutnya: RUN-\d+", "Nomor run berikutnya: lihat ID tertinggi pada logs/RUN-*.txt", content)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(entry)
    return code


if __name__ == "__main__":
    sys.exit(main())
