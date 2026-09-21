# GenV1 — Memory (RAG) Architecture

> **Location:** `docs/architecture/MEMORY.md`
> **Next:** `docs/architecture/DATA.md` · **Prev:** `docs/architecture/INTERFACE.md`

## Purpose

Describe the RAG memory store: transcript ingestion, Chroma-backed search, and
the memory endpoints/CLI.

## Responsibilities

- Chunk and index saved chat transcripts into a persistent vector store.
- Let agents recall past sessions via the `search_chat_logs` tool.
- Support full rebuild / purge without touching the transcript `.txt` files.

## Does Not Own

- The chat transcript lifecycle (see `docs/architecture/BACKEND.md`).
- Prompt construction (agents include tool docs; see `docs/architecture/AGENTS.md`).

## Components

- `memory/ingest.py` — transcript chunking (`ingest_file` / `ingest_directory`).
- `memory/search.py` — `RAGStorage`: Chroma store + fallback vector DB.
- `memory/rag_commit.py` — `status()` / `rebuild_store()` / `purge_store()`
  logic used by both endpoints and CLI.
- `memory/main.py` — standalone RAG CLI / cognitive-loop experiment.

## Inputs

- Saved transcripts (`<chatSavePath>/agent-text-records/*.txt`,
  default `<dataDir>/chatlog/agent-text-records`).
- `/api/rag/*` requests; `scripts/rebuild_rag.py` CLI args.

## Processing

- `POST /api/chats/end` may commit the transcript when `rag.commitOnSave`
  (default) or a per-request `rag` override is set.
- When the store is empty, the first search ingests every transcript
  automatically unless `rag.autoIngest` is off.
- `rebuild_store` re-indexes all transcripts; `purge_store` clears the store.

## Outputs

- Store at `<dataDir>/rag_db/chroma.sqlite3` by default (embeddings persist
  even if transcripts are deleted).
- `GET /api/rag/status` payload (location + indexed chunk count + paths).

## Dependencies

- `chromadb`, `docling` (see `docs/DEPENDENCIES.md`).
- `server/paths.py` (`RAG_DB_DIR`).
- `engine/core/llm.py` embeddings path (via Ollama).

## Consumers

- `search_chat_logs` tool (agents); the Configuration "Rebuild memory" /
  "Forget everything" buttons; `chat.html` "Clear Memory"; the RAG CLI.

## Extension Points

- New ingest sources via `memory/ingest.py`.
- Alternative vector backends (fallback DB in `memory/search.py`).

## Rules

- Transcripts follow **Chat save path**, not the Data folder.
- Clearing the store never deletes transcripts.

## Failure Behavior

- Missing/unreadable RAG data degrades to status reports instead of crashing.
- Standalone CLI calls fall back to `agent_monitoring/data/rag_db` defaults.

## Runtime Flow

```text
Chat saved (commitOnSave)
  -> finalize_session -> commit_transcript -> ingest -> store
Search query (rag_assistant)
  -> search_chat_logs(tool) -> RAGStorage.search -> results fed to agent
Configuration / manual
  -> POST /api/rag/rebuild | /api/rag/reset
  -> python scripts/rebuild_rag.py build|purge|status
```

## Configuration

- `ragDbPath` / `ragDbPathLinux` + `GENESSIS_RAG_DB_PATH`.
- `rag.commitOnSave`, `rag.autoIngest` in `app_settings.json`.

## APIs

- `GET /api/rag/status`
- `POST /api/rag/rebuild`
- `POST /api/rag/reset`

## Source Files

```text
memory/ingest.py
memory/search.py
memory/rag_commit.py
memory/main.py
scripts/rebuild_rag.py
```

## Related Documentation

- `docs/architecture/CONFIGURATION.md`
- `docs/architecture/DATA.md`
- `docs/reference/TOOL_REFERENCE.md` (`search_chat_logs`)