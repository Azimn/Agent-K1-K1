from __future__ import annotations

import argparse
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "local" / "knowledge_library" / "knowledge.db"
DEFAULT_RECORDS = ROOT / "local" / "knowledge_library" / "records"

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    title TEXT NOT NULL,
    source_uri TEXT,
    source_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    claims_json TEXT NOT NULL,
    confidence REAL NOT NULL,
    tags_json TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_+-]{1,}", text.lower())
        if len(token) > 2
    }


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def record_markdown(records_dir: Path, entry: dict[str, Any]) -> None:
    records_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", entry["id"])
    path = records_dir / f"{safe}.md"
    claims = "\n".join(f"- {item}" for item in entry["claims"])
    tags = ", ".join(entry["tags"])
    text = (
        f"# {entry['title']}\n\n"
        f"Source: {entry['source_uri'] or 'not supplied'}\n\n"
        f"Source type: {entry['source_type']}\n\n"
        f"Confidence: {entry['confidence']:.2f}\n\n"
        f"Tags: {tags}\n\n"
        f"## Summary\n\n{entry['summary']}\n\n"
        f"## Claims\n\n{claims or '- none recorded'}\n"
    )
    path.write_text(text, encoding="utf-8")


def add_entry(conn: sqlite3.Connection, args: argparse.Namespace, records_dir: Path) -> dict[str, Any]:
    ident = "kn_" + uuid.uuid4().hex
    entry = {
        "id": ident,
        "created_at": utc_now(),
        "title": args.title,
        "source_uri": args.source,
        "source_type": args.source_type,
        "summary": args.summary,
        "claims": args.claim or [],
        "confidence": max(0.0, min(1.0, float(args.confidence))),
        "tags": args.tag or [],
    }
    conn.execute(
        """INSERT INTO entries
           (id,created_at,title,source_uri,source_type,summary,claims_json,confidence,tags_json)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            entry["id"],
            entry["created_at"],
            entry["title"],
            entry["source_uri"],
            entry["source_type"],
            entry["summary"],
            json.dumps(entry["claims"], ensure_ascii=False),
            entry["confidence"],
            json.dumps(entry["tags"], ensure_ascii=False),
        ),
    )
    conn.commit()
    record_markdown(records_dir, entry)
    return {"ok": True, "id": ident}


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["claims"] = json.loads(result.pop("claims_json"))
    result["tags"] = json.loads(result.pop("tags_json"))
    return result


def search(conn: sqlite3.Connection, query: str, limit: int) -> list[dict[str, Any]]:
    q = tokenize(query)
    rows = conn.execute("SELECT * FROM entries ORDER BY created_at DESC LIMIT 500").fetchall()
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        item = row_to_dict(row)
        hay = tokenize(
            " ".join(
                [
                    item["title"],
                    item["summary"],
                    " ".join(item["claims"]),
                    " ".join(item["tags"]),
                ]
            )
        )
        overlap = len(q & hay)
        if q and overlap == 0:
            continue
        score = overlap + (item["confidence"] * 0.25)
        scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Provenance-aware knowledge library for Agent K1-K1")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--records-dir", default=str(DEFAULT_RECORDS))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    p = sub.add_parser("add")
    p.add_argument("--title", required=True)
    p.add_argument("--source")
    p.add_argument("--source-type", default="unknown")
    p.add_argument("--summary", required=True)
    p.add_argument("--claim", action="append")
    p.add_argument("--confidence", type=float, default=0.8)
    p.add_argument("--tag", action="append")

    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=8)

    p = sub.add_parser("recent")
    p.add_argument("--limit", type=int, default=8)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    conn = connect(Path(args.db))
    try:
        if args.command == "init":
            result: Any = {"ok": True, "db": str(Path(args.db))}
        elif args.command == "add":
            result = add_entry(conn, args, Path(args.records_dir))
        elif args.command == "search":
            result = search(conn, args.query, args.limit)
        else:
            rows = conn.execute(
                "SELECT * FROM entries ORDER BY created_at DESC LIMIT ?",
                (args.limit,),
            ).fetchall()
            result = [row_to_dict(row) for row in rows]
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
