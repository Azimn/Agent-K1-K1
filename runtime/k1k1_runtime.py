from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1
DEFAULT_DB = ROOT / "local" / "k1k1_state" / "k1k1.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
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
);

CREATE TABLE IF NOT EXISTS self_model (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    claim TEXT NOT NULL,
    evidence TEXT NOT NULL,
    confidence REAL NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relationships (
    peer_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    commitments_json TEXT NOT NULL,
    unresolved_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS commitments (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    description TEXT NOT NULL,
    owner TEXT NOT NULL,
    due_at TEXT,
    priority REAL NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agenda (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority REAL NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    outcome TEXT
);

CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    intention TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    source TEXT NOT NULL,
    success INTEGER,
    metadata_json TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return conn


def jdump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def rowdict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def cmd_init(conn: sqlite3.Connection, _args: argparse.Namespace) -> dict[str, Any]:
    return {"ok": True, "schema_version": SCHEMA_VERSION}


def cmd_memory_add(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    ident = new_id("mem")
    now = utc_now()
    conn.execute(
        """INSERT INTO memories
           (id,created_at,occurred_at,kind,summary,source,salience,confidence,tags_json,supersedes_id)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            ident,
            now,
            args.occurred_at or now,
            args.kind,
            args.summary,
            args.source,
            clamp01(args.salience),
            clamp01(args.confidence),
            jdump(args.tag or []),
            args.supersedes_id,
        ),
    )
    conn.commit()
    return {"ok": True, "id": ident}


def cmd_memory_list(conn: sqlite3.Connection, args: argparse.Namespace) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
        (args.limit,),
    ).fetchall()
    return [rowdict(row) for row in rows]


def cmd_relationship_upsert(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    now = utc_now()
    conn.execute(
        """INSERT INTO relationships
           (peer_id,display_name,updated_at,summary,evidence_json,commitments_json,unresolved_json)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(peer_id) DO UPDATE SET
             display_name=excluded.display_name,
             updated_at=excluded.updated_at,
             summary=excluded.summary,
             evidence_json=excluded.evidence_json,
             commitments_json=excluded.commitments_json,
             unresolved_json=excluded.unresolved_json""",
        (
            args.peer_id,
            args.display_name,
            now,
            args.summary,
            jdump(args.evidence or []),
            jdump(args.commitment or []),
            jdump(args.unresolved or []),
        ),
    )
    conn.commit()
    return {"ok": True, "peer_id": args.peer_id}


def cmd_commitment_add(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    ident = new_id("com")
    now = utc_now()
    conn.execute(
        """INSERT INTO commitments
           (id,created_at,updated_at,description,owner,due_at,priority,status,source,metadata_json)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            ident,
            now,
            now,
            args.description,
            args.owner,
            args.due_at,
            clamp01(args.priority),
            "open",
            args.source,
            jdump({}),
        ),
    )
    conn.commit()
    return {"ok": True, "id": ident}


def cmd_commitment_complete(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    cur = conn.execute(
        "UPDATE commitments SET status='completed', updated_at=? WHERE id=?",
        (utc_now(), args.id),
    )
    conn.commit()
    return {"ok": cur.rowcount == 1, "id": args.id}


def cmd_agenda_add(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    ident = new_id("agd")
    now = utc_now()
    conn.execute(
        """INSERT INTO agenda
           (id,created_at,updated_at,title,description,priority,status,source,outcome)
           VALUES (?,?,?,?,?,?, 'open', ?, NULL)""",
        (
            ident,
            now,
            now,
            args.title,
            args.description,
            clamp01(args.priority),
            args.source,
        ),
    )
    conn.commit()
    return {"ok": True, "id": ident}


def cmd_agenda_complete(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    cur = conn.execute(
        "UPDATE agenda SET status='completed', updated_at=?, outcome=? WHERE id=?",
        (utc_now(), args.outcome, args.id),
    )
    conn.commit()
    return {"ok": cur.rowcount == 1, "id": args.id}


def cmd_action_add(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    ident = new_id("act")
    success = None if args.success == "unknown" else int(args.success == "true")
    conn.execute(
        """INSERT INTO actions
           (id,created_at,intention,action,outcome,source,success,metadata_json)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            ident,
            utc_now(),
            args.intention,
            args.action,
            args.outcome,
            args.source,
            success,
            jdump({}),
        ),
    )
    conn.commit()
    return {"ok": True, "id": ident}


def cmd_self_add(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    ident = new_id("self")
    now = utc_now()
    conn.execute(
        """INSERT INTO self_model
           (id,created_at,updated_at,claim,evidence,confidence,status,source)
           VALUES (?,?,?,?,?,?, 'active', ?)""",
        (
            ident,
            now,
            now,
            args.claim,
            args.evidence,
            clamp01(args.confidence),
            args.source,
        ),
    )
    conn.commit()
    return {"ok": True, "id": ident}


def cmd_seed_agenda(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.path)
    items = json.loads(path.read_text(encoding="utf-8"))
    added = 0
    skipped = 0
    for item in items:
        existing = conn.execute(
            "SELECT id FROM agenda WHERE title=? AND status='open'",
            (item["title"],),
        ).fetchone()
        if existing:
            skipped += 1
            continue
        ns = argparse.Namespace(
            title=item["title"],
            description=item.get("description", ""),
            priority=float(item.get("priority", 0.5)),
            source=item.get("source", "seed"),
        )
        cmd_agenda_add(conn, ns)
        added += 1
    return {"ok": True, "added": added, "skipped": skipped}


def _latest(conn: sqlite3.Connection, table: str, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [rowdict(row) for row in rows]


def cmd_status(conn: sqlite3.Connection, _args: argparse.Namespace) -> dict[str, Any]:
    open_agenda = [
        rowdict(row)
        for row in conn.execute(
            "SELECT * FROM agenda WHERE status='open' ORDER BY priority DESC, created_at ASC LIMIT 8"
        ).fetchall()
    ]
    open_commitments = [
        rowdict(row)
        for row in conn.execute(
            "SELECT * FROM commitments WHERE status='open' ORDER BY priority DESC, created_at ASC LIMIT 8"
        ).fetchall()
    ]
    relationships = [
        rowdict(row)
        for row in conn.execute(
            "SELECT * FROM relationships ORDER BY updated_at DESC LIMIT 8"
        ).fetchall()
    ]
    self_model = [
        rowdict(row)
        for row in conn.execute(
            "SELECT * FROM self_model WHERE status='active' ORDER BY confidence DESC, updated_at DESC LIMIT 8"
        ).fetchall()
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "open_agenda": open_agenda,
        "open_commitments": open_commitments,
        "recent_memories": _latest(conn, "memories", 8),
        "recent_actions": _latest(conn, "actions", 8),
        "relationships": relationships,
        "self_model": self_model,
    }


def cmd_pulse(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    selected = conn.execute(
        """SELECT * FROM agenda
           WHERE status='open'
           ORDER BY priority DESC, created_at ASC LIMIT 1"""
    ).fetchone()
    commitments = [
        rowdict(row)
        for row in conn.execute(
            """SELECT * FROM commitments
               WHERE status='open'
               ORDER BY priority DESC, created_at ASC LIMIT 5"""
        ).fetchall()
    ]
    return {
        "mode": args.mode,
        "selected_agenda": rowdict(selected) if selected else None,
        "open_commitments": commitments,
        "recent_memories": _latest(conn, "memories", 5),
        "recent_actions": _latest(conn, "actions", 5),
        "instruction": (
            "Treat the selected agenda item as a candidate. Complete at most one useful bounded unit of work. "
            "If nothing meaningful is available, do not manufacture activity."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Persistent state runtime for Agent K1-K1")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    p = sub.add_parser("memory-add")
    p.add_argument("--summary", required=True)
    p.add_argument("--kind", default="experience")
    p.add_argument("--source", default="conversation")
    p.add_argument("--salience", type=float, default=0.6)
    p.add_argument("--confidence", type=float, default=0.9)
    p.add_argument("--occurred-at")
    p.add_argument("--supersedes-id")
    p.add_argument("--tag", action="append")

    p = sub.add_parser("memory-list")
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("relationship-upsert")
    p.add_argument("--peer-id", required=True)
    p.add_argument("--display-name", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--evidence", action="append")
    p.add_argument("--commitment", action="append")
    p.add_argument("--unresolved", action="append")

    p = sub.add_parser("commitment-add")
    p.add_argument("--description", required=True)
    p.add_argument("--owner", default="kiki")
    p.add_argument("--due-at")
    p.add_argument("--priority", type=float, default=0.5)
    p.add_argument("--source", default="conversation")

    p = sub.add_parser("commitment-complete")
    p.add_argument("id")

    p = sub.add_parser("agenda-add")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--priority", type=float, default=0.5)
    p.add_argument("--source", default="conversation")

    p = sub.add_parser("agenda-complete")
    p.add_argument("id")
    p.add_argument("--outcome", default="completed")

    p = sub.add_parser("action-add")
    p.add_argument("--intention", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--outcome", required=True)
    p.add_argument("--source", default="agent")
    p.add_argument("--success", choices=["true", "false", "unknown"], default="unknown")

    p = sub.add_parser("self-add")
    p.add_argument("--claim", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--confidence", type=float, default=0.5)
    p.add_argument("--source", default="reflection")

    p = sub.add_parser("seed-agenda")
    p.add_argument("path")

    sub.add_parser("status")

    p = sub.add_parser("pulse")
    p.add_argument("--mode", default="general")

    return parser


COMMANDS = {
    "init": cmd_init,
    "memory-add": cmd_memory_add,
    "memory-list": cmd_memory_list,
    "relationship-upsert": cmd_relationship_upsert,
    "commitment-add": cmd_commitment_add,
    "commitment-complete": cmd_commitment_complete,
    "agenda-add": cmd_agenda_add,
    "agenda-complete": cmd_agenda_complete,
    "action-add": cmd_action_add,
    "self-add": cmd_self_add,
    "seed-agenda": cmd_seed_agenda,
    "status": cmd_status,
    "pulse": cmd_pulse,
}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    conn = connect(Path(args.db))
    try:
        result = COMMANDS[args.command](conn, args)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
