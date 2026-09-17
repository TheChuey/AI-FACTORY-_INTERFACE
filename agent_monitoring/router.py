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
