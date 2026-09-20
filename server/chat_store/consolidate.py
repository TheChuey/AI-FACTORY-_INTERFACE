"""
app/chat_store/consolidate.py
=============================

AI consolidation for single-file chat transcripts.

A chat transcript can grow '# VERSION N' sections as the user saves/resets it.
Once 3+ versions exist the frontend offers "consolidate": the LLM reads the
combined conversation and produces a short summary. The consolidated result is
APPENDED to the same transcript file as a '# CONSOLIDATED' section (with the
summary + the FULL conversation kept), and the chat's metadata row is updated
to version "C". Nothing is ever deleted or overwritten.
"""

from server.chat_store import store
from engine.core.llm import ask_llm

SYSTEM_PROMPT = (
    "You are a transcript archivist. You are given the full history of a "
    "chat session as plain text.\n"
    "Write a dense markdown summary of it. Capture the goals discussed, key "
    "decisions, open questions, and any concrete artifacts (files/code/"
    "commands). Use short '## ' subheadings where helpful and stay under 400 "
    "words. Return ONLY the summary text - do not echo or reproduce any part "
    "of the transcript, and do not add a '## Full Conversation' section "
    "(the full conversation is archived separately)."
)


def consolidate_chat(chat_id: str, model=None) -> dict:
    """Consolidate a chat's single-file transcript into summary + full text.

    Returns {ok, summary_preview, file, version}. Raises ValueError when the
    chat has fewer than 2 sections (nothing worth consolidating yet) and
    RuntimeError when the LLM call fails - in both cases the transcript is
    left exactly as it was (consolidation never mutates on failure).
    """
    current = store.read_chat_file(chat_id)
    if current is None:
        raise ValueError(f"no transcript for chat '{chat_id}'")
    sections = [s for s in current.get("sections", []) if s.get("kind") == "version"]
    if len(sections) < 2:
        raise ValueError(
            f"chat '{chat_id}' only has {len(sections)} version(s); "
            f"consolidation needs at least 2"
        )

    combined = "\n\n".join(
        f"# VERSION {s.get('version')}\n\n{s.get('content', '')}" for s in reversed(sections)
    )
    try:
        result = ask_llm(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": combined},
            ],
            model=model,
        )
    except Exception as e:  # LLM is cooperative, never fatal.
        raise RuntimeError(f"consolidation LLM call failed: {e}") from e

    summary = str(result.get("content", result.get("response", "")) or "").strip()
    if not summary:
        raise RuntimeError("consolidation returned an empty result")

    path = store.write_consolidated(chat_id, summary, combined)
    if path is None:
        raise RuntimeError(f"could not persist consolidated transcript for '{chat_id}'")

    # Point the chat's log record at the consolidated section (version 'C').
    store.mark_consolidated(chat_id, path.name)

    try:
        _maybe_rag_commit(path)
    except Exception:
        pass

    preview = summary.splitlines()[0][:140] + "..." if len(summary.splitlines()[0]) > 140 else summary
    return {
        "ok": True,
        "summary_preview": preview,
        "file": str(path),
        "version": "C",
    }


def _maybe_rag_commit(path) -> None:
    """Best-effort RAG commit of the consolidated file (save-to-memory chats)."""
    from app.rag_commit import commit_transcript

    commit_transcript(path)