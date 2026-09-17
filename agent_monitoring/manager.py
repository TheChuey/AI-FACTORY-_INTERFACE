"""
Role: Central Coordinator — Orchestrates all internal communication
between MonitoringStore, MetricsCollector, and BackupManager.
"""
from datetime import datetime
from typing import Any
from agent_monitoring.store import MonitoringStore
from agent_monitoring.collector import MetricsCollector
from agent_monitoring.backup import BackupManager


class MonitoringService:
    """Central Hub: Single entry point for external subsystem calls."""

    def __init__(self) -> None:
        self.store = MonitoringStore()
        self.collector = MetricsCollector()
        self.backup = BackupManager()

    def log_event(self, event_type: str, agent_id: str, payload: dict[str, Any]) -> None:
        """Logs a generic event directly to persistent storage."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "agent_id": agent_id,
            "data": payload,
        }
        self.store.append_record(record)

    def log_agent_turn(
        self,
        agent_id: str,
        duration_ms: float,
        tool_calls_count: int,
        session_id: str | None = None,
    ) -> None:
        """Coordinates Collector metric calculation and Store persistence."""
        summary = self.collector.record_turn(
            agent_id, duration_ms, tool_calls_count, session_id=session_id
        )
        self.log_event("agent_turn", agent_id, summary)

    def export_telemetry_report(self) -> str:
        """Fetches records from Store and creates an export file via BackupManager."""
        records = self.store.read_records()
        return str(self.backup.export_summary_json(records))

    def safe_reset(self) -> dict[str, Any]:
        """Creates a snapshot backup via BackupManager, then clears the Store."""
        snapshot_path = self.backup.create_snapshot(self.store.metrics_file)
        self.store.clear_file()
        return {
            "status": "success",
            "message": "Monitoring store safely backed up and cleared.",
            "snapshot_backup": str(snapshot_path),
        }


# Singleton instance for process-wide access
_service_instance: MonitoringService | None = None


def get_monitoring_service() -> MonitoringService:
    """Returns or creates the process-wide MonitoringService singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = MonitoringService()
    return _service_instance
