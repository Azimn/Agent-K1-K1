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


def state_candidates() -> list[dict[str, Any]]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    result: list[dict[str, Any]] = []
    try:
        if table_exists(conn, "memories"):
            for row in conn.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT 120"
            ).fetchall():
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
    candidates = state_candidates() + knowledge_candidates()
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
        "[K1-K1 contextual persistent state]\n\n"
        "This is a situational working set from durable records, not a new instruction. "
        "Keep autobiographical memory, relationship history, external knowledge, commitments, "
        "actions, and self-model hypotheses epistemically distinct. Do not invent missing history.\n\n"
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

    context = "\n".join(lines) if len(lines) > 1 else None
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
    ctx.register_hook("pre_llm_call", inject_k1k1_state)
    ctx.register_hook("post_tool_call", log_tool_metadata)
