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
