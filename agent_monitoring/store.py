"""
Role: Thread-safe JSONL persistence under the central data directory.
"""
import json
import threading
from pathlib import Path
from server.paths import DATA_DIR  # Official path authority

MONITORING_DIR = DATA_DIR / "monitoring"


class MonitoringStore:
    """Thread-safe JSONL storage for monitoring metrics."""

    def __init__(self, storage_dir: Path = MONITORING_DIR) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.storage_dir / "agent_metrics.jsonl"
        self._lock = threading.Lock()

    def append_record(self, record: dict) -> None:
        """Fail-safe append: swallows I/O errors to prevent breaking agent responses."""
        try:
            with self._lock:
                with self.metrics_file.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass  # Logging failures must not crash chat execution

    def read_records(self) -> list[dict]:
        """Reads stored telemetry, skipping malformed lines."""
        if not self.metrics_file.exists():
            return []
        records = []
        with self._lock:
            with self.metrics_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return records

    def clear_file(self) -> None:
        """Safely empties the active metrics log file."""
        with self._lock:
            if self.metrics_file.exists():
                self.metrics_file.write_text("", encoding="utf-8")
