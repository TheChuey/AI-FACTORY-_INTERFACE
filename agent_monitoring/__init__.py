"""agent_monitoring
=================

Default runtime data home for the app (``server/paths.py`` resolves
``DATA_DIR`` to ``agent_monitoring/data`` unless a custom ``dataDir`` is
configured).

Formerly hosted the agent turn/session telemetry subsystem (metrics
collector, JSONL store, snapshot backups and the ``/api/monitoring/*``
router). That layer was retired: chat transcripts are persisted by the
frontend via ``chat_store``, and the single monitoring channel is now the
tool-usage log (``server/tool_log.py`` -> ``data/toollog/tool_usage.jsonl``,
served at ``/api/logs/tools``).
"""