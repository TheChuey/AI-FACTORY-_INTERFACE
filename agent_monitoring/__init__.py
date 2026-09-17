"""agent_monitoring
=================

Top-level backend subsystem for agent telemetry: metrics collection,
JSONL persistence, snapshot backups and JSON exports, exposed through a
single facade (`MonitoringService`) and a FastAPI router under
`/api/monitoring/*`.

Public surface:

    from agent_monitoring import get_monitoring_service
    get_monitoring_service().log_agent_turn(agent_id, duration_ms, tool_count)
"""

from agent_monitoring.manager import MonitoringService, get_monitoring_service

__all__ = ["MonitoringService", "get_monitoring_service"]
