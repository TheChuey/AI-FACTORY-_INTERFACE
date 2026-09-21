# GenV1 — Dependencies

> **Location:** `docs/DEPENDENCIES.md`
> **Next:** `docs/architecture/SYSTEM.md`

Python, JS and system dependencies of GenV1. Source: `requirements.txt`,
`dashboard/` imports, and the runtime environment.

---

## Python packages (from `requirements.txt`)

### Direct runtime dependencies

| Package | Version pin | Role |
|---|---|---|
| `chromadb` | `>=0.4.0` | Vector store for the RAG memory (`memory/`) |
| `docling` | `>=2.59.0` | Transcript/document chunking (`memory/ingest.py`) |
| `ollama` | `>=0.3.0` (pinned `0.6.2`) | Ollama HTTP client (`engine/core/llm.py`) |
| `pydantic` | `>=2.0.0` (pinned `2.13.4`) | Request models + validation (`server/server.py`) |

### Pinned transitive / framework packages

| Package | Version | Role |
|---|---|---|
| `fastapi` | `0.141.1` | Web framework (`server/server.py`) |
| `uvicorn` | `0.52.3` | ASGI server (dev runner) |
| `starlette` | `1.6.0` | Underlying ASGI toolkit |
| `pydantic_core` | `2.46.4` | Pydantic runtime |
| `annotated-types` | `0.8.0` | Typing support |
| `typing-inspection` | `0.4.4` | Typing introspection |
| `typing_extensions` | `4.16.0` | Backport typing helpers |
| `annotated-doc` | `0.0.5` | Docstring schema aid |
| `anyio` | `4.14.2` | Async I/O (Starlette) |
| `click` | `8.4.2` | CLI helpers |
| `colorama` | `0.4.6` | ANSI/color support (Windows) |
| `h11` | `0.16.0` | HTTP/1.1 protocol for uvicorn |
| `idna` | `3.18` | IDNA support |

## System dependencies

- **Python 3** (`py -3` on Windows; `python3` on Linux/macOS/Chromebook).
- **Ollama** running locally with models installed (the backend scans installed
  models at startup into `config/models.json`). No Ollama → agent replies fall
  back gracefully (`engine/core/llm.py`).

## Frontend

- Vanilla JavaScript (no build step, no npm packages). Uses native
  `fetch()`, `EventSource`-free polling, DOMParser/Element APIs.
- No CDN assets in the source tree.

## Installation

```powershell
py -3 -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

Linux:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python server.py
```

## Related documentation

- `docs/INDEX.md`
- `docs/architecture/CONFIGURATION.md`
- `docs/architecture/MEMORY.md`