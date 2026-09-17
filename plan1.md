### **Plan: agent_monitoring Top-Level Backend Subsystem**

#### **Goal**
Establish a standalone `agent_monitoring/` package (`store.py`, `collector.py`, `backup.py`, `manager.py`, `router.py`, `__init__.py`) to record agent-turn telemetry, calculate session metrics, manage snapshot backups, and expose REST endpoints under `/api/monitoring/*` without modifying core engine logic.

---

#### **Repo Grounding (Verified)**
* **`server/paths.py`** owns path resolution and exposes `DATA_DIR` and `EXPORTS_DIR`.
* The FastAPI application is instantiated at `server/server.py` (`app = FastAPI(lifespan=lifespan)`).
* **`POST /api/chat`** serves as the per-turn HTTP boundary where `agent.think` is executed.
* Snapshots are located under `DATA_DIR / "snapshots" / "monitoring"`, aligning with `RestoreManager` conventions.

---

#### **Files to CREATE**

| File | Role |
| :--- | :--- |
| **`agent_monitoring/__init__.py`** | Package boundary re-exporting `MonitoringService` and `get_monitoring_service()`. |
| **`agent_monitoring/store.py`** | `MonitoringStore` — thread-safe JSONL disk I/O under `DATA_DIR / "monitoring" / "agent_metrics.jsonl"`. |
| **`agent_monitoring/collector.py`** | `MetricsCollector` — thread-safe in-memory session tracking and turn metric aggregation. |
| **`agent_monitoring/backup.py`** | `BackupManager` — snapshot copies in `snapshots/monitoring/` and exports in `EXPORTS_DIR`. |
| **`agent_monitoring/manager.py`** | `MonitoringService` — central orchestrator facade and process singleton `get_monitoring_service()`. |
| **`agent_monitoring/router.py`** | `APIRouter(prefix="/api/monitoring")` — status, records, export, and reset REST endpoints. |

---

#### **Subsystem Source Code**

##### **1. `agent_monitoring/store.py`**
```python
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
```

##### **2. `agent_monitoring/collector.py`**
```python
"""
Role: Real-time telemetry tracking and session metric aggregation.
"""
import threading
from typing import Any

class MetricsCollector:
    """Thread-safe in-memory metric aggregator."""

    def __init__(self) -> None:
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self.total_turns: int = 0
        self._lock = threading.Lock()

    def start_session(self, session_id: str, agent_id: str) -> None:
        """Idempotently registers an active session in memory."""
        with self._lock:
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = {
                    "agent_id": agent_id,
                    "turns_count": 0,
                    "total_duration_ms": 0.0,
                }

    def record_turn(
        self,
        agent_id: str,
        duration_ms: float,
        tool_calls_count: int,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Calculates turn metrics and updates active session state."""
        with self._lock:
            self.total_turns += 1
            if session_id and session_id in self.active_sessions:
                sess = self.active_sessions[session_id]
                sess["turns_count"] += 1
                sess["total_duration_ms"] += duration_ms

            return {
                "agent_id": agent_id,
                "session_id": session_id,
                "duration_ms": duration_ms,
                "tool_calls_count": tool_calls_count,
                "cumulative_system_turns": self.total_turns,
            }

    def end_session(self, session_id: str) -> dict[str, Any] | None:
        """Removes session from memory and returns final stats."""
        with self._lock:
            return self.active_sessions.pop(session_id, None)
```

##### **3. `agent_monitoring/backup.py`**
```python
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
```

##### **4. `agent_monitoring/manager.py`**
```python
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
```

##### **5. `agent_monitoring/__init__.py`**
```python
from agent_monitoring.manager import get_monitoring_service, MonitoringService

__all__ = ["get_monitoring_service", "MonitoringService"]
```

##### **6. `agent_monitoring/router.py`**
```python
"""
Role: REST API boundary exposing status, records, export, and reset endpoints.
"""
from fastapi import APIRouter, HTTPException
from agent_monitoring.manager import get_monitoring_service

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/status")
def get_status():
    service = get_monitoring_service()
    return {
        "status": "active",
        "active_sessions": len(service.collector.active_sessions),
        "total_system_turns": service.collector.total_turns,
    }

@router.get("/records")
def get_records():
    service = get_monitoring_service()
    return {"status": "success", "records": service.store.read_records()}

@router.post("/export")
def export_report():
    try:
        service = get_monitoring_service()
        return {"status": "success", "export_file": service.export_telemetry_report()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
def reset_logs():
    try:
        service = get_monitoring_service()
        return service.safe_reset()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

#### **Integration Changes (Minimal, Boundary-Only)**

1. **`server/server.py` Import Block**:
   ```python
   from agent_monitoring.router import router as monitoring_router
   ```
2. **Router Mount**:
   ```python
   app.include_router(monitoring_router)
   ```
3. **Turn Telemetry Hook (`POST /api/chat`)**:
   ```python
   import time
   from agent_monitoring import get_monitoring_service

   start_time = time.perf_counter()
   reply = agent.think(data.message)
   duration_ms = (time.perf_counter() - start_time) * 1000.0

   # Non-blocking, fail-safe logging
   try:
       m_service = get_monitoring_service()
       m_service.collector.start_session(session["id"], agent_id)
       m_service.log_agent_turn(
           agent_id=agent_id,
           duration_ms=duration_ms,
           tool_calls_count=len(getattr(agent, "tool_events", [])),
           session_id=session["id"]
       )
   except Exception:
       pass
   ```
4. **Session Lifecycle Hook (`POST /api/chats/end`)**:
   ```python
   try:
       if row and row.get("id"):
           get_monitoring_service().collector.end_session(row["id"])
   except Exception:
       pass
   ```
5. **No edits** required in `engine/`, `tools/`, or `memory/`.

---

#### **Amendments to the Draft Code (Why)**
* **Thread Safety**: Wrapped `MonitoringStore` disk I/O and `MetricsCollector` memory operations in `threading.Lock()` to prevent race conditions during multi-threaded FastAPI execution.
* **Fail-Safe Writes**: `append_record` catches and swallows I/O exceptions so logging issues never break chat execution.
* **Robust Line Parsing**: `read_records` skips malformed JSON lines gracefully.
* **Session Threading**: Threaded `session_id` through `start_session`, `record_turn`, and `log_agent_turn` to link metrics directly to active user sessions.
* **Snapshot Conventions**: Saved backups to `DATA_DIR / "snapshots" / "monitoring"`, matching existing `RestoreManager` patterns.

---

#### **Verification**
1. Run `python -c "import agent_monitoring, server.server"` to verify clean imports.
2. Start server and query `GET /api/monitoring/status` to confirm `{"status":"active",...}`.
3. Send a message to `POST /api/chat` and verify a new JSONL line is appended in `DATA_DIR / "monitoring" / "agent_metrics.jsonl"`.
4. Query `GET /api/monitoring/records` and trigger `POST /api/monitoring/export` to confirm output in `EXPORTS_DIR`.
5. Trigger `POST /api/monitoring/reset` to confirm snapshot creation under `DATA_DIR / "snapshots" / "monitoring"` and log clearing.

---

#### **Risks / Notes**
* Path defaults resolve at import time via `server/paths.py`.
* In-memory active session metrics reset on server restart, while JSONL logs remain persistent.
* `server/server.py` handles root-level package resolution automatically.
