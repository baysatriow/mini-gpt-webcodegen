"""Privacy-minimized, process-local Usage persistence."""

from __future__ import annotations

import base64
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import threading
import uuid
from typing import Any


class ActiveUsageInstanceError(RuntimeError):
    """Raised when another API process owns the Usage database."""


_ACTIVE_LOCKS: set[str] = set()
_ACTIVE_LOCKS_GUARD = threading.Lock()
_OUTCOMES = {"running", "completed", "rejected", "failed", "interrupted"}
_STAGES = {
    "request_received",
    "request_validation",
    "intake_validation",
    "model_load",
    "inference",
    "output_validation",
    "render_export",
    "persist_result",
    "completed",
    "server_restart",
}
_FAILURE_CODES = {
    "input_rejected",
    "input_too_long",
    "unsupported_request",
    "generation_busy",
    "model_unavailable",
    "inference_failed",
    "cuda_out_of_memory",
    "output_invalid",
    "render_failed",
    "storage_failed",
    "invalid_request",
    "internal_error",
    "server_interrupted",
    "gpu_telemetry_unavailable",
}
_RECORD_COLUMNS = {
    "usage_id",
    "server_instance_id",
    "generation_id",
    "started_at",
    "finished_at",
    "duration_ms",
    "http_status",
    "outcome",
    "stage",
    "failure_code",
    "prompt",
    "confirmed_facts_json",
    "inference_started",
    "input_tokens",
    "output_tokens",
    "attempt_count",
    "retry_count",
    "section_count",
    "renderer_status",
    "model_id",
    "gpu_sample_count",
    "gpu_device_name",
    "gpu_utilization_sum_pct",
    "gpu_utilization_max_pct",
    "gpu_memory_sum_mib",
    "gpu_memory_max_mib",
    "gpu_memory_total_mib",
    "gpu_power_sum_w",
    "gpu_temperature_max_c",
    "gpu_sm_clock_sum_mhz",
    "torch_allocated_baseline_bytes",
    "torch_reserved_baseline_bytes",
    "torch_allocated_peak_bytes",
    "torch_reserved_peak_bytes",
    "torch_allocated_delta_bytes",
    "torch_reserved_delta_bytes",
}
_NUMERIC_FIELDS = {
    "duration_ms",
    "http_status",
    "input_tokens",
    "output_tokens",
    "attempt_count",
    "retry_count",
    "section_count",
    "gpu_sample_count",
    "gpu_utilization_sum_pct",
    "gpu_utilization_max_pct",
    "gpu_memory_sum_mib",
    "gpu_memory_max_mib",
    "gpu_memory_total_mib",
    "gpu_power_sum_w",
    "gpu_temperature_max_c",
    "gpu_sm_clock_sum_mhz",
    "torch_allocated_baseline_bytes",
    "torch_reserved_baseline_bytes",
    "torch_allocated_peak_bytes",
    "torch_reserved_peak_bytes",
    "torch_allocated_delta_bytes",
    "torch_reserved_delta_bytes",
}
_SAMPLE_FIELDS = {
    "sampled_at",
    "device_name",
    "utilization_pct",
    "memory_used_mib",
    "memory_total_mib",
    "power_w",
    "temperature_c",
    "sm_clock_mhz",
}
_WINDOWS = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
_TIME_FIELDS = {"started_at", "finished_at"}
_MAX_PROMPT_CHARS = 4000
_MAX_CONFIRMED_FACTS_JSON_CHARS = 96_000
_CONFIRMED_FACT_KINDS = {"name", "description", "value", "service", "project", "process", "faq"}


def _validate_confirmed_facts_json(value: Any) -> str:
    if not isinstance(value, str) or len(value) > _MAX_CONFIRMED_FACTS_JSON_CHARS:
        raise ValueError("Confirmed Usage facts are outside the storage limit")
    try:
        facts = json.loads(value)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("Confirmed Usage facts must be valid JSON") from error
    if not isinstance(facts, list) or len(facts) > 24:
        raise ValueError("Confirmed Usage facts must be a bounded list")
    for fact in facts:
        if not isinstance(fact, dict) or set(fact) != {"id", "kind", "label", "title", "value"}:
            raise ValueError("Confirmed Usage fact contains fields outside the privacy allowlist")
        kind = fact["kind"]
        if not isinstance(kind, str) or kind not in _CONFIRMED_FACT_KINDS:
            raise ValueError("Confirmed Usage fact has an invalid kind")
        scalar_limit = 3000 if kind == "description" else 1000 if kind == "value" else 100
        value_limit = scalar_limit if kind in {"name", "description", "value"} else 3000
        title = fact["title"]
        if (
            not isinstance(fact["id"], str)
            or not fact["id"]
            or len(fact["id"]) > 64
            or not isinstance(fact["label"], str)
            or not fact["label"]
            or len(fact["label"]) > 100
            or (title is not None and (not isinstance(title, str) or len(title) > 100))
            or (kind in {"name", "description", "value"} and title is not None)
            or (kind in {"service", "project", "process", "faq"} and (not isinstance(title, str) or not title))
            or not isinstance(fact["value"], str)
            or not fact["value"]
            or len(fact["value"]) > value_limit
        ):
            raise ValueError("Confirmed Usage fact has an invalid value")
    normalized = json.dumps(facts, separators=(",", ":"), ensure_ascii=False)
    if len(normalized) > _MAX_CONFIRMED_FACTS_JSON_CHARS:
        raise ValueError("Confirmed Usage facts are outside the storage limit")
    return normalized


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Usage timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _encode_cursor(started_at: str, usage_id: str) -> str:
    raw = json.dumps([started_at, usage_id], separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    if len(cursor) > 512:
        raise ValueError("Invalid Usage cursor")
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError
        started_at, usage_id = value
        if not isinstance(started_at, str) or not isinstance(usage_id, str):
            raise ValueError
        _timestamp(started_at)
        uuid.UUID(usage_id)
        return started_at, usage_id
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid Usage cursor") from error


class UsageStore:
    def __init__(self, root: Path, retention_days: int = 90) -> None:
        if type(retention_days) is not int or retention_days < 1:
            raise ValueError("Usage retention must be a positive number of days")
        self.root = Path(root).resolve()
        self.db_path = self.root / "usage.sqlite3"
        self.samples_dir = self.root / "samples"
        self.retention_days = retention_days
        self._data_lock = threading.RLock()
        self._lock_handle = None
        self._lock_key = str(self.db_path).casefold()
        self.instance_id: str | None = None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.samples_dir.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS server_instances (
                    instance_id TEXT PRIMARY KEY,
                    pid INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    stopped_at TEXT
                );
                CREATE TABLE IF NOT EXISTS usage_records (
                    usage_id TEXT PRIMARY KEY,
                    server_instance_id TEXT NOT NULL REFERENCES server_instances(instance_id),
                    generation_id TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    duration_ms INTEGER,
                    http_status INTEGER,
                    outcome TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    failure_code TEXT,
                    prompt TEXT,
                    confirmed_facts_json TEXT NOT NULL DEFAULT '[]',
                    inference_started INTEGER NOT NULL DEFAULT 0,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    attempt_count INTEGER,
                    retry_count INTEGER,
                    section_count INTEGER,
                    renderer_status TEXT,
                    model_id TEXT,
                    gpu_sample_count INTEGER NOT NULL DEFAULT 0,
                    gpu_device_name TEXT,
                    gpu_utilization_sum_pct REAL,
                    gpu_utilization_max_pct REAL,
                    gpu_memory_sum_mib REAL,
                    gpu_memory_max_mib REAL,
                    gpu_memory_total_mib REAL,
                    gpu_power_sum_w REAL,
                    gpu_temperature_max_c REAL,
                    gpu_sm_clock_sum_mhz REAL,
                    torch_allocated_baseline_bytes INTEGER,
                    torch_reserved_baseline_bytes INTEGER,
                    torch_allocated_peak_bytes INTEGER,
                    torch_reserved_peak_bytes INTEGER,
                    torch_allocated_delta_bytes INTEGER,
                    torch_reserved_delta_bytes INTEGER
                );
                CREATE TABLE IF NOT EXISTS usage_stage_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usage_id TEXT NOT NULL REFERENCES usage_records(usage_id) ON DELETE CASCADE,
                    stage TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    failure_code TEXT,
                    occurred_at TEXT NOT NULL,
                    elapsed_ms INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS usage_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_usage_started ON usage_records(started_at DESC, usage_id DESC);
                CREATE INDEX IF NOT EXISTS idx_usage_outcome_started ON usage_records(outcome, started_at DESC);
                CREATE INDEX IF NOT EXISTS idx_usage_stage_started ON usage_records(stage, started_at DESC);
                CREATE INDEX IF NOT EXISTS idx_usage_instance_outcome ON usage_records(server_instance_id, outcome);
                CREATE INDEX IF NOT EXISTS idx_usage_events_run ON usage_stage_events(usage_id, event_id);
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(usage_records)").fetchall()
            }
            if "prompt" not in columns:
                connection.execute("ALTER TABLE usage_records ADD COLUMN prompt TEXT")
            if "confirmed_facts_json" not in columns:
                connection.execute(
                    "ALTER TABLE usage_records ADD COLUMN confirmed_facts_json TEXT NOT NULL DEFAULT '[]'"
                )
            connection.commit()

    def _acquire_process_lock(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with _ACTIVE_LOCKS_GUARD:
            if self._lock_key in _ACTIVE_LOCKS:
                raise ActiveUsageInstanceError("Another API process owns the local Usage store")
            handle = self.db_path.with_name(".instance.lock").open("a+b")
            try:
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                handle.close()
                raise ActiveUsageInstanceError("Another API process owns the local Usage store") from error
            self._lock_handle = handle
            _ACTIVE_LOCKS.add(self._lock_key)

    def _release_process_lock(self) -> None:
        handle = self._lock_handle
        if handle is None:
            return
        with _ACTIVE_LOCKS_GUARD:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            finally:
                handle.close()
                self._lock_handle = None
                _ACTIVE_LOCKS.discard(self._lock_key)
                self.instance_id = None

    def start_instance(self) -> str:
        if self.instance_id is not None:
            raise ActiveUsageInstanceError("This API process already owns the local Usage store")
        self._acquire_process_lock()
        instance_id = str(uuid.uuid4())
        now_datetime = _utc_now()
        now = now_datetime.isoformat()
        try:
            self._initialize()
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                previous = connection.execute(
                    "SELECT instance_id FROM server_instances WHERE stopped_at IS NULL"
                ).fetchall()
                for row in previous:
                    running = connection.execute(
                        "SELECT usage_id, started_at FROM usage_records "
                        "WHERE server_instance_id = ? AND outcome = 'running'",
                        (row["instance_id"],),
                    ).fetchall()
                    connection.execute(
                        "UPDATE usage_records SET outcome = 'interrupted', stage = 'server_restart', "
                        "failure_code = 'server_interrupted', finished_at = ?, "
                        "duration_ms = max(0, CAST((julianday(?) - julianday(started_at)) * 86400000 AS INTEGER)) "
                        "WHERE server_instance_id = ? AND outcome = 'running'",
                        (now, now, row["instance_id"]),
                    )
                    for record in running:
                        elapsed_ms = max(
                            0,
                            int((now_datetime - _timestamp(record["started_at"])).total_seconds() * 1000),
                        )
                        connection.execute(
                            "INSERT INTO usage_stage_events "
                            "(usage_id, stage, event_type, failure_code, occurred_at, elapsed_ms) "
                            "VALUES (?, 'server_restart', 'interrupted', 'server_interrupted', ?, ?)",
                            (record["usage_id"], now, elapsed_ms),
                        )
                    connection.execute(
                        "UPDATE server_instances SET stopped_at = ?, last_seen_at = ? WHERE instance_id = ?",
                        (now, now, row["instance_id"]),
                    )
                connection.execute(
                    "INSERT INTO server_instances(instance_id, pid, started_at, last_seen_at) VALUES (?, ?, ?, ?)",
                    (instance_id, os.getpid(), now, now),
                )
                connection.commit()
            self.instance_id = instance_id
            self.prune_if_due(_utc_now())
            return instance_id
        except Exception:
            self._release_process_lock()
            raise

    def heartbeat_instance(self, instance_id: str) -> None:
        now = _utc_now().isoformat()
        with self._data_lock, closing(self._connect()) as connection:
            cursor = connection.execute(
                "UPDATE server_instances SET last_seen_at = ? WHERE instance_id = ? AND stopped_at IS NULL",
                (now, instance_id),
            )
            connection.commit()
            if cursor.rowcount != 1:
                raise RuntimeError("Usage instance heartbeat was not recorded")

    def stop_instance(self, instance_id: str) -> None:
        now_datetime = _utc_now()
        now = now_datetime.isoformat()
        try:
            with self._data_lock, closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                running = connection.execute(
                    "SELECT usage_id, started_at FROM usage_records "
                    "WHERE server_instance_id = ? AND outcome = 'running'",
                    (instance_id,),
                ).fetchall()
                connection.execute(
                    "UPDATE usage_records SET outcome = 'interrupted', stage = 'server_restart', "
                    "failure_code = 'server_interrupted', finished_at = ?, "
                    "duration_ms = max(0, CAST((julianday(?) - julianday(started_at)) * 86400000 AS INTEGER)) "
                    "WHERE server_instance_id = ? AND outcome = 'running'",
                    (now, now, instance_id),
                )
                for record in running:
                    elapsed_ms = max(
                        0,
                        int((now_datetime - _timestamp(record["started_at"])).total_seconds() * 1000),
                    )
                    connection.execute(
                        "INSERT INTO usage_stage_events "
                        "(usage_id, stage, event_type, failure_code, occurred_at, elapsed_ms) "
                        "VALUES (?, 'server_restart', 'interrupted', 'server_interrupted', ?, ?)",
                        (record["usage_id"], now, elapsed_ms),
                    )
                connection.execute(
                    "UPDATE server_instances SET stopped_at = ?, last_seen_at = ? WHERE instance_id = ?",
                    (now, now, instance_id),
                )
                connection.commit()
        finally:
            if instance_id == self.instance_id:
                self._release_process_lock()

    @staticmethod
    def _validate_usage_id(usage_id: str) -> str:
        try:
            parsed = uuid.UUID(usage_id)
        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError("Invalid Usage ID") from error
        if str(parsed) != usage_id.lower():
            raise ValueError("Invalid Usage ID")
        return str(parsed)

    @staticmethod
    def _validate_fields(record: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        unknown = set(record) - _RECORD_COLUMNS
        if unknown:
            raise ValueError("Usage record contains fields outside the privacy allowlist")
        clean = dict(record)
        if "usage_id" in clean:
            clean["usage_id"] = UsageStore._validate_usage_id(clean["usage_id"])
        if "generation_id" in clean and clean["generation_id"] is not None:
            clean["generation_id"] = UsageStore._validate_usage_id(clean["generation_id"])
        if "outcome" in clean and clean["outcome"] not in _OUTCOMES:
            raise ValueError("Invalid Usage outcome")
        if "stage" in clean and clean["stage"] not in _STAGES:
            raise ValueError("Invalid Usage stage")
        if "failure_code" in clean and clean["failure_code"] not in _FAILURE_CODES | {None}:
            raise ValueError("Invalid Usage failure code")
        if "model_id" in clean and clean["model_id"] is not None:
            value = clean["model_id"]
            if not isinstance(value, str) or len(value) > 120 or "/" in value or "\\" in value:
                raise ValueError("Invalid safe model identifier")
        if "renderer_status" in clean and clean["renderer_status"] is not None:
            value = clean["renderer_status"]
            if value not in {"accepted", "stage_failed", "input_too_long", "missing_information", "unknown"}:
                raise ValueError("Invalid renderer status")
        if "prompt" in clean:
            value = clean["prompt"]
            if value is not None and (not isinstance(value, str) or len(value) > _MAX_PROMPT_CHARS):
                raise ValueError("Usage prompt is outside the storage limit")
        if "confirmed_facts_json" in clean:
            clean["confirmed_facts_json"] = _validate_confirmed_facts_json(clean["confirmed_facts_json"])
        if "server_instance_id" in clean:
            clean["server_instance_id"] = UsageStore._validate_usage_id(clean["server_instance_id"])
        for field in _TIME_FIELDS & clean.keys():
            value = clean[field]
            if value is not None:
                if not isinstance(value, str):
                    raise ValueError("Usage timestamps must be strings")
                clean[field] = _timestamp(value).isoformat()
        for field in _NUMERIC_FIELDS & clean.keys():
            value = clean[field]
            if value is not None and (type(value) not in {int, float} or value < 0):
                raise ValueError("Usage metrics must be non-negative numbers")
        if "inference_started" in clean:
            if type(clean["inference_started"]) is bool:
                clean["inference_started"] = int(clean["inference_started"])
            elif clean["inference_started"] not in {0, 1}:
                raise ValueError("Invalid inference-started flag")
        if not partial:
            for required in ("usage_id", "server_instance_id", "started_at", "outcome", "stage"):
                if required not in clean:
                    raise ValueError("Usage record is missing a required field")
            if clean["outcome"] != "running":
                raise ValueError("New Usage records must start as running")
        return clean

    def create_record(self, record: dict[str, Any]) -> None:
        clean = self._validate_fields(record)
        columns = list(clean)
        placeholders = ",".join("?" for _ in columns)
        values = [clean[column] for column in columns]
        with self._data_lock, closing(self._connect()) as connection:
            instance = connection.execute(
                "SELECT 1 FROM server_instances WHERE instance_id = ? AND stopped_at IS NULL",
                (clean["server_instance_id"],),
            ).fetchone()
            if instance is None:
                raise RuntimeError("Usage record has no active server instance")
            connection.execute(
                f"INSERT INTO usage_records({','.join(columns)}) VALUES ({placeholders})",
                values,
            )
            connection.execute(
                "INSERT INTO usage_stage_events(usage_id, stage, event_type, occurred_at, elapsed_ms) "
                "VALUES (?, ?, 'started', ?, 0)",
                (clean["usage_id"], clean["stage"], clean["started_at"]),
            )
            connection.commit()

    def update_record(self, usage_id: str, **fields: Any) -> None:
        safe_id = self._validate_usage_id(usage_id)
        clean = self._validate_fields(fields, partial=True)
        clean.pop("usage_id", None)
        clean.pop("server_instance_id", None)
        clean.pop("started_at", None)
        if not clean:
            return
        assignments = ",".join(f"{column} = ?" for column in clean)
        with self._data_lock, closing(self._connect()) as connection:
            cursor = connection.execute(
                f"UPDATE usage_records SET {assignments} WHERE usage_id = ?",
                [*clean.values(), safe_id],
            )
            connection.commit()
            if cursor.rowcount != 1:
                raise KeyError("Usage record was not found")

    def add_event(
        self,
        usage_id: str,
        stage: str,
        event_type: str,
        *,
        failure_code: str | None = None,
        occurred_at: str | None = None,
        elapsed_ms: int = 0,
    ) -> None:
        safe_id = self._validate_usage_id(usage_id)
        if stage not in _STAGES or event_type not in _OUTCOMES | {"started", "stage"}:
            raise ValueError("Invalid Usage event")
        if failure_code not in _FAILURE_CODES | {None}:
            raise ValueError("Invalid Usage failure code")
        if type(elapsed_ms) is not int or elapsed_ms < 0:
            raise ValueError("Invalid Usage event duration")
        timestamp = _timestamp(occurred_at or _utc_now().isoformat()).isoformat()
        with self._data_lock, closing(self._connect()) as connection:
            connection.execute(
                "INSERT INTO usage_stage_events(usage_id, stage, event_type, failure_code, occurred_at, elapsed_ms) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (safe_id, stage, event_type, failure_code, timestamp, elapsed_ms),
            )
            connection.commit()

    def append_sample(self, usage_id: str, sample: dict[str, Any]) -> None:
        safe_id = self._validate_usage_id(usage_id)
        if set(sample) - _SAMPLE_FIELDS or "sampled_at" not in sample:
            raise ValueError("GPU sample contains fields outside the telemetry allowlist")
        clean: dict[str, Any] = {}
        for key, value in sample.items():
            if key == "sampled_at":
                if not isinstance(value, str):
                    raise ValueError("GPU sample timestamp must be a string")
                clean[key] = _timestamp(value).isoformat()
            elif key == "device_name":
                if value is not None and (not isinstance(value, str) or len(value) > 120):
                    raise ValueError("Invalid GPU device name")
                clean[key] = value
            else:
                if value is not None and (type(value) not in {int, float} or value < 0):
                    raise ValueError("GPU sample values must be non-negative numbers")
                clean[key] = value
        path = self.samples_dir / f"{safe_id}.jsonl"
        with self._data_lock, closing(self._connect()) as connection:
            if connection.execute("SELECT 1 FROM usage_records WHERE usage_id = ?", (safe_id,)).fetchone() is None:
                raise KeyError("Usage record was not found")
            self.samples_dir.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(clean, separators=(",", ":"), ensure_ascii=False) + "\n")

    def get_samples(self, usage_id: str, limit: int = 300) -> list[dict[str, Any]]:
        safe_id = self._validate_usage_id(usage_id)
        if type(limit) is not int or not 1 <= limit <= 300:
            raise ValueError("Usage sample limit must be between 1 and 300")
        with self._data_lock, closing(self._connect()) as connection:
            if connection.execute("SELECT 1 FROM usage_records WHERE usage_id = ?", (safe_id,)).fetchone() is None:
                return []
            path = self.samples_dir / f"{safe_id}.jsonl"
            if not path.is_file() or path.is_symlink():
                return []
            try:
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(self.samples_dir.resolve(strict=True)):
                    return []
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            except (OSError, ValueError, json.JSONDecodeError):
                return []
        if len(rows) <= limit:
            return rows
        stride = (len(rows) - 1) / (limit - 1) if limit > 1 else len(rows)
        indexes = sorted({round(index * stride) for index in range(limit)})
        return [rows[index] for index in indexes]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["inference_started"] = bool(result["inference_started"])
        return result

    def get_record(self, usage_id: str) -> dict[str, Any] | None:
        safe_id = self._validate_usage_id(usage_id)
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM usage_records WHERE usage_id = ?", (safe_id,)).fetchone()
            if row is None:
                return None
            result = self._row(row)
            result["events"] = [dict(item) for item in connection.execute(
                "SELECT stage, event_type, failure_code, occurred_at, elapsed_ms "
                "FROM usage_stage_events WHERE usage_id = ? ORDER BY event_id",
                (safe_id,),
            ).fetchall()]
            return result

    def list_records(
        self,
        *,
        cursor: str | None,
        limit: int,
        window: str | None,
        status: str | None,
        stage: str | None,
        q: str | None = None,
    ) -> dict[str, Any]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Usage page limit must be between 1 and 100")
        if window is not None and window not in _WINDOWS:
            raise ValueError("Invalid Usage time window")
        if status is not None and status not in _OUTCOMES:
            raise ValueError("Invalid Usage status filter")
        if stage is not None and stage not in _STAGES:
            raise ValueError("Invalid Usage stage filter")
        if q is not None and (not isinstance(q, str) or len(q) > 200):
            raise ValueError("Invalid Usage search query")
        clauses: list[str] = []
        parameters: list[Any] = []
        search = (q or "").strip()
        if search:
            escaped = search.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            clauses.append("(prompt LIKE ? ESCAPE '!' OR confirmed_facts_json LIKE ? ESCAPE '!')")
            parameters.extend((f"%{escaped}%", f"%{escaped}%"))
        if window:
            clauses.append("started_at >= ?")
            parameters.append((_utc_now() - _WINDOWS[window]).isoformat())
        if status:
            clauses.append("outcome = ?")
            parameters.append(status)
        if stage:
            clauses.append("stage = ?")
            parameters.append(stage)
        if cursor:
            started_at, usage_id = _decode_cursor(cursor)
            clauses.append("(started_at < ? OR (started_at = ? AND usage_id < ?))")
            parameters.extend((started_at, started_at, usage_id))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        parameters.append(limit + 1)
        list_columns = sorted(_RECORD_COLUMNS - {"prompt", "confirmed_facts_json"})
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT "
                + ",".join(list_columns)
                + ",substr(prompt, 1, 80) AS prompt_preview FROM usage_records"
                + where
                + " ORDER BY started_at DESC, usage_id DESC LIMIT ?",
                parameters,
            ).fetchall()
        has_more = len(rows) > limit
        selected = rows[:limit]
        next_cursor = _encode_cursor(selected[-1]["started_at"], selected[-1]["usage_id"]) if has_more and selected else None
        return {"items": [self._row(row) for row in selected], "next_cursor": next_cursor, "limit": limit}

    def summarize(self, window: str) -> dict[str, Any]:
        if window not in _WINDOWS:
            raise ValueError("Invalid Usage time window")
        start = (_utc_now() - _WINDOWS[window]).isoformat()
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN outcome = 'completed' THEN 1 ELSE 0 END) AS completed, "
                "SUM(CASE WHEN outcome = 'rejected' THEN 1 ELSE 0 END) AS rejected, "
                "SUM(CASE WHEN outcome = 'failed' THEN 1 ELSE 0 END) AS failed, "
                "SUM(CASE WHEN outcome = 'interrupted' THEN 1 ELSE 0 END) AS interrupted, "
                "SUM(CASE WHEN inference_started = 1 THEN 1 ELSE 0 END) AS inference_started, "
                "AVG(CASE WHEN outcome = 'completed' THEN duration_ms END) AS mean_duration_ms, "
                "SUM(gpu_sample_count) AS gpu_sample_count, "
                "SUM(CASE WHEN gpu_sample_count > 0 THEN 1 ELSE 0 END) AS gpu_run_count, "
                "SUM(gpu_utilization_sum_pct) AS gpu_utilization_sum, "
                "MAX(gpu_utilization_max_pct) AS gpu_utilization_max_pct, "
                "SUM(gpu_memory_sum_mib) AS gpu_memory_sum, "
                "MAX(gpu_memory_max_mib) AS gpu_memory_max_mib, "
                "MAX(gpu_memory_total_mib) AS gpu_memory_total_mib, "
                "SUM(gpu_power_sum_w) AS gpu_power_sum, "
                "MAX(gpu_temperature_max_c) AS gpu_temperature_max_c, "
                "SUM(gpu_sm_clock_sum_mhz) AS gpu_sm_clock_sum "
                "FROM usage_records WHERE started_at >= ?",
                (start,),
            ).fetchone()
        total = row["total"] or 0
        completed = row["completed"] or 0
        rejected = row["rejected"] or 0
        failed = row["failed"] or 0
        interrupted = row["interrupted"] or 0
        inference_started = row["inference_started"] or 0
        sample_count = row["gpu_sample_count"] or 0
        gpu_runs = row["gpu_run_count"] or 0
        gpu_denominator = sample_count or 0
        return {
            "window": window,
            "total_requests": total,
            "inference_started": inference_started,
            "completed": completed,
            "rejected": rejected,
            "failed": failed,
            "interrupted": interrupted,
            "success_rate_all": completed / total if total else None,
            "success_rate_inference": completed / inference_started if inference_started else None,
            "mean_duration_ms": row["mean_duration_ms"],
            "gpu_run_count": gpu_runs,
            "gpu_sample_count": sample_count,
            "gpu_coverage_ratio": gpu_runs / inference_started if inference_started else None,
            "gpu_utilization_mean_pct": row["gpu_utilization_sum"] / gpu_denominator if gpu_denominator else None,
            "gpu_utilization_max_pct": row["gpu_utilization_max_pct"],
            "gpu_memory_mean_mib": row["gpu_memory_sum"] / gpu_denominator if gpu_denominator else None,
            "gpu_memory_max_mib": row["gpu_memory_max_mib"],
            "gpu_memory_total_mib": row["gpu_memory_total_mib"],
            "gpu_power_mean_w": row["gpu_power_sum"] / gpu_denominator if gpu_denominator else None,
            "gpu_temperature_max_c": row["gpu_temperature_max_c"],
            "gpu_sm_clock_mean_mhz": row["gpu_sm_clock_sum"] / gpu_denominator if gpu_denominator else None,
            "gpu_scope": "Sampel nvidia-smi mencatat penggunaan seluruh GPU hanya selama proses generate.",
        }

    def prune(self, now: datetime) -> int:
        if now.tzinfo is None:
            raise ValueError("Prune timestamp must include timezone")
        cutoff = (now.astimezone(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        removed = 0
        with self._data_lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute("SELECT usage_id FROM usage_records WHERE started_at < ?", (cutoff,)).fetchall()
            for row in rows:
                usage_id = row["usage_id"]
                sample_path = self.samples_dir / f"{usage_id}.jsonl"
                try:
                    if sample_path.exists() and not sample_path.is_symlink():
                        sample_path.unlink()
                except OSError:
                    continue
                connection.execute("DELETE FROM usage_records WHERE usage_id = ?", (usage_id,))
                removed += 1
            if self.samples_dir.is_dir() and not self.samples_dir.is_symlink():
                samples_root = self.samples_dir.resolve(strict=True)
                for sample_path in self.samples_dir.glob("*.jsonl"):
                    try:
                        sample_id = str(uuid.UUID(sample_path.stem))
                        if sample_id != sample_path.stem or sample_path.is_symlink() or not sample_path.is_file():
                            continue
                        if not sample_path.resolve(strict=True).is_relative_to(samples_root):
                            continue
                        exists = connection.execute(
                            "SELECT 1 FROM usage_records WHERE usage_id = ?", (sample_id,)
                        ).fetchone()
                        if exists is None:
                            sample_path.unlink()
                    except (OSError, ValueError):
                        continue
            connection.execute(
                "INSERT INTO usage_metadata(key, value) VALUES ('retention_last_run', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (_utc_now().isoformat(),),
            )
            connection.commit()
        return removed

    def prune_if_due(self, now: datetime | None = None) -> int:
        current = (now or _utc_now()).astimezone(timezone.utc)
        with self._data_lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT value FROM usage_metadata WHERE key = 'retention_last_run'"
            ).fetchone()
        if row is not None and current - _timestamp(row["value"]) < timedelta(days=1):
            return 0
        return self.prune(current)
