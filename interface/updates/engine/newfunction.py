"""
LOCATION: interface/updates/engine/newfunction.py
USAGE (Option B Direct Access):
    module = update_manager.get_active_module("engine", "newfunction")
    result = module.execute_new_logic("Input Data")
"""
import logging

logger = logging.getLogger("app_change_tracker")


def execute_new_logic(data_payload: str):
    """Example logic function for engine updates."""
    logger.info(f"[ENGINE: newfunction] Processing payload: {data_payload}")
    return f"Engine processed payload: {data_payload}"


def secondary_engine_action(value: int):
    """Secondary action inside the same module file."""
    return value * 10