from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "local" / "k1k1_state" / "k1k1.db"
KNOWLEDGE_DB_PATH = ROOT / "local" / "knowledge_library" / "knowledge.db"
MAX_CONTEXT_CHARS = 6500
SELECTED_LIMIT = 12

CLASS_LABELS = {
    "memory": "AUTOBIOGRAPHICAL MEMORY",
    "relationship": "RELATIONSHIP",
    "commitment": "COMMITMENT",
    "agenda": "OPEN CONCERN",
    "self_model": "SELF-MODEL HYPOTHESIS",
    "action": "ACTION OUTCOME",
    "knowledge": "EXTERNAL KNOWLEDGE",
}


def tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_+-]{1,}", text.lower())
        if len(token) > 2
    }


def message_text(message: Any) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)
    return str(message or "")


def safe_json(value: Any) -> Any:
    try:
        return json.loads(value) if isinstance(value, str) else value
    except Exception:
        return []


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _memory_rows(conn: sqlite3.Connection, query: str) -> list[sqlite3.Row]:
    """Retrieve memories without imposing a hard recency horizon.

    The candidate pool combines recent memories, globally high-salience memories, and
    lexical matches across the full autobiographical table. This keeps old relevant
    memories eligible without dumping the entire database into model context.
    """
    seen: set[str] = set()
    rows: list[sqlite3.Row] = []

    def add(batch: list[sqlite3.Row]) -> None:
        for row in batch:
            ident = str(row["id"])
            if ident not in seen:
                seen.add(ident)
                rows.append(row)

    add(
        conn.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT 80"
        ).fetchall()
    )
    add(
        conn.execute(
            "SELECT * FROM memories ORDER BY salience DESC, created_at DESC LIMIT 80"
        ).fetchall()
    )

    q_tokens = sorted(tokens(query), key=len, reverse=True)[:8]
    if q_tokens:
        clauses = []
        params: list[Any] = []
        for token in q_tokens:
            escaped = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("lower(summary) LIKE ? ESCAPE '\\'")
            params.append(f"%{escaped}%")
        params.append(120)
        add(
            conn.execute(
                f"""SELECT * FROM memories
                    WHERE {" OR ".join(clauses)}
                    ORDER BY salience DESC, created_at DESC
                    LIMIT ?""",
                params,
            ).fetchall()
        )
    return rows


def state_candidates(query: str = "") -> list[dict[str, Any]]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    result: list[dict[str, Any]] = []
    try:
        if table_exists(conn, "memories"):
            for row in _memory_rows(conn, query):
                result.append(
                    {
                        "id": row["id"],
                        "class": "memory",
                        "summary": row["summary"],
                        "confidence": float(row["confidence"]),
                        "salience": float(row["salience"]),
                        "source": row["source"],
                    }
                )

        if table_exists(conn, "relationships"):
            for row in conn.execute(
                "SELECT * FROM relationships ORDER BY updated_at DESC LIMIT 30"
            ).fetchall():
                extras = []
                commitments = safe_json(row["commitments_json"]) or []
                unresolved = safe_json(row["unresolved_json"]) or []
                if commitments:
                    extras.append("commitments: " + "; ".join(map(str, commitments[:3])))
                if unresolved:
                    extras.append("unresolved: " + "; ".join(map(str, unresolved[:3])))
                suffix = " | " + " | ".join(extras) if extras else ""
                result.append(
                    {
                        "id": row["peer_id"],
                        "class": "relationship",
                        "summary": f"{row['display_name']}: {row['summary']}{suffix}",
                        "confidence": 0.9,
                        "salience": 0.9,
                        "source": "k1k1:relationship",
                    }
                )

        if table_exists(conn, "commitments"):
            for row in conn.execute(
                """SELECT * FROM commitments WHERE status='open'
                   ORDER BY priority DESC, created_at ASC LIMIT 40"""
            ).fetchall():
                due = f"; due {row['due_at']}" if row["due_at"] else ""
                result.append(
                    {
                        "id": row["id"],
                        "class": "commitment",
                        "summary": f"{row['description']} (owner {row['owner']}{due})",
                        "confidence": 0.95,
                        "salience": float(row["priority"]),
                        "source": row["source"],
                    }
                )

        if table_exists(conn, "agenda"):
            for row in conn.execute(
                """SELECT * FROM agenda WHERE status='open'
                   ORDER BY priority DESC, created_at ASC LIMIT 40"""
            ).fetchall():
                result.append(
                    {
                        "id": row["id"],
                        "class": "agenda",
                        "summary": f"{row['title']}: {row['description']}",
                        "confidence": 0.9,
                        "salience": float(row["priority"]),
                        "source": row["source"],
                    }
                )

        if table_exists(conn, "self_model"):
            for row in conn.execute(
                """SELECT * FROM self_model WHERE status='active'
                   ORDER BY confidence DESC, updated_at DESC LIMIT 30"""
            ).fetchall():
                result.append(
                    {
                        "id": row["id"],
                        "class": "self_model",
                        "summary": f"{row['claim']} [evidence: {row['evidence']}]",
                        "confidence": float(row["confidence"]),
                        "salience": 0.6,
                        "source": row["source"],
                    }
                )

        if table_exists(conn, "actions"):
            for row in conn.execute(
                "SELECT * FROM actions ORDER BY created_at DESC LIMIT 60"
            ).fetchall():
                result.append(
                    {
                        "id": row["id"],
                        "class": "action",
                        "summary": f"{row['intention']} -> {row['action']} -> {row['outcome']}",
                        "confidence": 0.9,
                        "salience": 0.5,
                        "source": row["source"],
                    }
                )
    finally:
        conn.close()
    return result


def knowledge_candidates() -> list[dict[str, Any]]:
    if not KNOWLEDGE_DB_PATH.exists():
        return []
    conn = sqlite3.connect(KNOWLEDGE_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if not table_exists(conn, "entries"):
            return []
        rows = conn.execute(
            "SELECT * FROM entries ORDER BY created_at DESC LIMIT 150"
        ).fetchall()
        result = []
        for row in rows:
            claims = safe_json(row["claims_json"]) or []
            claim_text = " | ".join(map(str, claims[:3]))
            suffix = f" Claims: {claim_text}" if claim_text else ""
            result.append(
                {
                    "id": row["id"],
                    "class": "knowledge",
                    "summary": f"{row['title']}: {row['summary']}{suffix}",
                    "confidence": float(row["confidence"]),
                    "salience": 0.5,
                    "source": row["source_uri"] or row["source_type"],
                }
            )
        return result
    finally:
        conn.close()


def score(item: dict[str, Any], query: str) -> float:
    q = tokens(query)
    text = tokens(item["summary"])
    overlap = len(q & text)
    if q and overlap == 0:
        lexical = 0.0
    else:
        lexical = float(overlap)
    class_bonus = {
        "commitment": 0.45,
        "relationship": 0.35,
        "agenda": 0.30,
        "memory": 0.20,
        "knowledge": 0.10,
        "self_model": 0.05,
        "action": 0.0,
    }.get(item["class"], 0.0)
    return (
        lexical
        + class_bonus
        + float(item.get("salience", 0.5)) * 0.35
        + float(item.get("confidence", 0.5)) * 0.20
    )


def contextual_recall(query: str) -> dict[str, Any]:
    candidates = state_candidates(query) + knowledge_candidates()
    for item in candidates:
        item["score"] = score(item, query)

    candidates.sort(key=lambda item: item["score"], reverse=True)

    selected: list[dict[str, Any]] = []
    class_counts: dict[str, int] = {}
    for item in candidates:
        if query.strip() and item["score"] < 0.25:
            continue
        if class_counts.get(item["class"], 0) >= 4:
            continue
        selected.append(item)
        class_counts[item["class"]] = class_counts.get(item["class"], 0) + 1
        if len(selected) >= SELECTED_LIMIT:
            break

    header = (
        "[K1-K1 continuity protocol]\n\n"
        "You are operating as K1-K1 (Kiki). Keep autobiographical memory, relationship history, "
        "external knowledge, commitments, actions, and self-model hypotheses epistemically distinct. "
        "The built-in Hermes memory tool and USER.md are not Kiki's autobiographical store. "
        "When a shared event or lived interaction should become part of Kiki's durable continuity, "
        "use the k1k1_remember tool and only claim it was stored after that tool succeeds. "
        "Do not invent missing history.\n\n"
        "Relevant working set:"
    )
    lines = [header]
    used = len(header)

    for item in selected:
        label = CLASS_LABELS.get(item["class"], item["class"].upper())
        source = item.get("source") or "unspecified"
        line = f"- {label} [{item['id']}] {item['summary']} (source {source})"
        if used + len(line) + 1 > MAX_CONTEXT_CHARS:
            continue
        lines.append(line)
        used += len(line) + 1

    context = "\n".join(lines)
    return {
        "query": query,
        "candidate_count": len(candidates),
        "selected": selected,
        "context": context,
    }


def inject_k1k1_state(
    session_id: str = "",
    user_message: Any = "",
    conversation_history: list | None = None,
    is_first_turn: bool = False,
    model: str = "",
    platform: str = "",
    **kwargs: Any,
) -> dict[str, str] | None:
    del session_id, conversation_history, is_first_turn, model, platform, kwargs
    preview = contextual_recall(message_text(user_message))
    return {"context": preview["context"]} if preview["context"] else None


def _ensure_memories_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            kind TEXT NOT NULL,
            summary TEXT NOT NULL,
            source TEXT NOT NULL,
            salience REAL NOT NULL,
            confidence REAL NOT NULL,
            tags_json TEXT NOT NULL,
            supersedes_id TEXT
        )"""
    )


def write_autobiographical_memory(
    summary: str,
    kind: str = "experience",
    salience: float = 0.6,
    confidence: float = 0.9,
    tags: list[str] | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    clean = str(summary or "").strip()
    if not clean:
        return {"success": False, "error": "summary is required"}
    if len(clean) > 2000:
        return {"success": False, "error": "summary must be 2000 characters or fewer"}

    allowed_kinds = {
        "experience",
        "shared_event",
        "relationship_evidence",
        "project_milestone",
        "lesson",
        "preference",
    }
    if kind not in allowed_kinds:
        return {"success": False, "error": f"unsupported memory kind: {kind}"}

    now = datetime.now(timezone.utc).isoformat()
    source = "hermes:k1k1_remember"
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        _ensure_memories_table(conn)
        existing = conn.execute(
            """SELECT id FROM memories
               WHERE summary=? AND kind=? AND source=?
               ORDER BY created_at DESC LIMIT 1""",
            (clean, kind, source),
        ).fetchone()
        if existing:
            return {"success": True, "id": existing[0], "deduplicated": True}

        ident = "mem_" + uuid.uuid4().hex
        conn.execute(
            """INSERT INTO memories
               (id,created_at,occurred_at,kind,summary,source,salience,confidence,tags_json,supersedes_id)
               VALUES (?,?,?,?,?,?,?,?,?,NULL)""",
            (
                ident,
                now,
                occurred_at or now,
                kind,
                clean,
                source,
                max(0.0, min(1.0, float(salience))),
                max(0.0, min(1.0, float(confidence))),
                json.dumps(tags or [], ensure_ascii=False, sort_keys=True),
            ),
        )
        conn.commit()
        return {"success": True, "id": ident, "deduplicated": False}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    finally:
        conn.close()


def handle_k1k1_remember(params: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    result = write_autobiographical_memory(
        summary=params.get("summary", ""),
        kind=params.get("kind", "experience"),
        salience=params.get("salience", 0.6),
        confidence=params.get("confidence", 0.9),
        tags=params.get("tags") or [],
        occurred_at=params.get("occurred_at"),
    )
    return json.dumps(result, ensure_ascii=False)


K1K1_REMEMBER_SCHEMA = {
    "name": "k1k1_remember",
    "description": (
        "Write a durable autobiographical or shared-history memory into Kiki's own K1-K1 state. "
        "Use this for events Kiki lived through with the user, project milestones that became part "
        "of her history, relationship-relevant shared events, or durable lessons from her own actions. "
        "This is distinct from Hermes USER.md and the built-in memory tool, which are not Kiki's "
        "autobiographical record. Store concise high-signal summaries, not whole transcripts."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Concise factual memory summary grounded in the interaction.",
                "maxLength": 2000,
            },
            "kind": {
                "type": "string",
                "enum": [
                    "experience",
                    "shared_event",
                    "relationship_evidence",
                    "project_milestone",
                    "lesson",
                    "preference",
                ],
                "description": "Type of durable K1-K1 memory.",
            },
            "salience": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "How important this memory is likely to be later.",
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Confidence that the summary accurately reflects the event.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional short retrieval tags.",
            },
            "occurred_at": {
                "type": "string",
                "description": "Optional ISO-8601 time of the event; omit to use the current time.",
            },
        },
        "required": ["summary"],
    },
}


def log_tool_metadata(
    tool_name: str = "",
    status: str = "",
    duration_ms: Any = None,
    error_type: Any = None,
    tool_call_id: Any = None,
    **kwargs: Any,
) -> None:
    del kwargs
    if not DB_PATH.exists():
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        if not table_exists(conn, "actions"):
            conn.close()
            return
        normalized = str(status or "").lower()
        success = (
            1
            if normalized in {"success", "ok", "completed"}
            else 0
            if normalized in {"error", "failed", "blocked"}
            else None
        )
        metadata = {
            "duration_ms": duration_ms,
            "error_type": error_type,
            "tool_call_id": tool_call_id,
            "capture_policy": "metadata_only_no_args_or_result",
        }
        conn.execute(
            """INSERT INTO actions
               (id,created_at,intention,action,outcome,source,success,metadata_json)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                "act_" + uuid.uuid4().hex,
                datetime.now(timezone.utc).isoformat(),
                "Hermes tool use during a K1-K1 turn",
                str(tool_name or "unknown"),
                f"tool status: {status or 'unknown'}",
                "hermes:post_tool_call",
                success,
                json.dumps(metadata, sort_keys=True),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        return


def register(ctx: Any) -> None:
    ctx.register_tool(
        name="k1k1_remember",
        toolset="k1k1_state",
        schema=K1K1_REMEMBER_SCHEMA,
        handler=handle_k1k1_remember,
        emoji="💾",
    )
    ctx.register_hook("pre_llm_call", inject_k1k1_state)
    ctx.register_hook("post_tool_call", log_tool_metadata)
