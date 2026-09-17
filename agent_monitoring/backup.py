"""
Role: Snapshot backups, exported summaries, and state purging.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from server.paths import DATA_DIR, EXPORTS_DIR  # Path authority

SNAPSHOTS_DIR = DATA_DIR / "snapshots" / "monitoring"


class BackupManager:
    """Manages snapshot backups and JSON reports."""

    def __init__(self) -> None:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, source_file: Path) -> Path:
        """Creates a timestamped snapshot in DATA_DIR / snapshots / monitoring."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target_path = SNAPSHOTS_DIR / f"agent_metrics_{stamp}.jsonl"
        if source_file.exists():
            shutil.copy2(source_file, target_path)
        return target_path

    def export_summary_json(self, records: list[dict]) -> Path:
        """Exports formatted telemetry records to EXPORTS_DIR."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        export_file = EXPORTS_DIR / f"monitoring_export_{stamp}.json"
        payload = {
            "exported_at": datetime.now().isoformat(),
            "record_count": len(records),
            "records": records,
        }
        export_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return export_file
