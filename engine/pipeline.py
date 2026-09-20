"""
engine/pipeline.py
==================

Runs the ordered agent chain from config/pipeline.json so a single user idea
can travel Step 1 -> Step 2 -> Step 3 automatically.

Why this exists: chat.html sends one message to ONE agent. A Step-2 agent whose
prompt says "accepts the Feature Plan from Step 1" has nothing to work from when
the user sends it a fresh idea, so it stalls asking for that plan again and
again. The pipeline feeds each later step the OUTPUT of every earlier step as
part of its own message, so the planner's spec reaches the engineer and the
engineer's blueprint reaches the builder without any copy/paste.

Feed-forward messages carry:
    - the ORIGINAL user message (so the module name / scope never gets lost), and
    - each earlier step's final reply, labelled with the producing agent's name.

Every step's tool_events are collected and returned together, so the UI can
render the complete tool usage of a pipeline run in one shot.
"""

import json
from datetime import datetime
from pathlib import Path

from engine.agents.factory import build_agent

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "pipeline.json"

_STEP_FEED_TEMPLATE = (
    "Below is what the previous pipeline step ({name}) produced.\n"
    "Use it as your required input. Do NOT ask for it again - just act on it.\n"
    "--- {name} OUTPUT ---\n"
    "{output}\n"
    "--- END {name} OUTPUT ---\n"
)


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _records_file() -> Path | None:
    """pipeline_runs.jsonl next to the chat log; None if paths can't resolve
    (so headless/serverless harnesses never crash on recording)."""
    try:
        from server import paths
        return paths.CHATS_DIR / "pipeline_runs.jsonl"
    except Exception:
        return None


def _record_run(snapshot: dict) -> None:
    """Append one JSONL line per pipeline run. Fail-safe: a logging failure
    never breaks the run itself (same philosophy as server/tool_log)."""
    record = {
        "time": _iso_now(),
        "request": snapshot.get("request", ""),
        "model": snapshot.get("model"),
        "steps": snapshot.get("steps", []),
        "reply": snapshot.get("reply", ""),
    }
    try:
        target = _records_file()
        if target is None:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass  # a recording failure never blocks the pipeline


def load_pipeline(config_path=None) -> list:
    """Ordered agent ids from config/pipeline.json ([] when missing/broken).

    Missing files return [] so the app degrades gracefully to plain per-agent
    chat instead of crashing on a config problem.
    """
    path = config_path or CONFIG_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data.get("steps") or []


def run_pipeline(user_message: str, model: str | None = None,
                 config_path=None) -> dict:
    """Run every step in order; return {reply, outputs, tool_events}.

    outputs is a list of {agent_id, agent_name, output} - one entry per step,
    so the UI can display each stage's contribution separately.
    """
    steps = load_pipeline(config_path)
    if not steps:
        return {
            "reply": "(pipeline not configured - add config/pipeline.json)",
            "outputs": [],
            "tool_events": [],
        }

    results: list[dict] = []
    tool_events: list[dict] = []

    for index, agent_id in enumerate(steps):
        agent = build_agent(agent_id, model=model)

        feed = user_message
        if results:
            chain_text = "\n\n".join(
                _STEP_FEED_TEMPLATE.format(name=r["agent_name"], output=r["output"])
                for r in results
            )
            feed = f"ORIGINAL USER REQUEST:\n{user_message}\n\n{chain_text}"

        reply = agent.think(feed)
        results.append({
            "agent_id": agent_id,
            "agent_name": agent.profile.name or agent_id,
            "output": reply,
        })
        tool_events.extend(agent.tool_events)
        print(f"[PIPELINE] step {index + 1}/{len(steps)} '{agent_id}' done -> {reply[:80]!r}")

    result = {
        "reply": results[-1]["output"],
        "outputs": results,
        "tool_events": tool_events,
    }
    _record_run({
        "request": user_message,
        "model": model,
        "steps": [
            {"agent_id": r["agent_id"], "agent_name": r["agent_name"], "output": r["output"]}
            for r in results
        ],
        "reply": result["reply"],
    })
    return result