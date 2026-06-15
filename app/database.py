import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "chargegrid.db"
MAX_CONVERSATIONS = 7


def get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def list_conversations() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM conversations "
            "ORDER BY created_at DESC LIMIT ?",
            (MAX_CONVERSATIONS,),
        ).fetchall()
    return [dict(r) for r in rows]


def _prune(conn):
    rows = conn.execute(
        "SELECT id FROM conversations ORDER BY created_at DESC"
    ).fetchall()
    if len(rows) >= MAX_CONVERSATIONS:
        to_delete = [r["id"] for r in rows[MAX_CONVERSATIONS - 1:]]
        placeholders = ",".join("?" * len(to_delete))
        conn.execute(
            f"DELETE FROM conversations WHERE id IN ({placeholders})",
            to_delete,
        )


def create_conversation(title: str) -> dict:
    conv_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        _prune(conn)
        conn.execute(
            "INSERT INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
            (conv_id, title, now),
        )
        conn.commit()
    return {"id": conv_id, "title": title, "created_at": now}


def conversation_exists(conversation_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
    return row is not None


def get_messages(conversation_id: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, role, content, sources, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["sources"] = json.loads(d["sources"]) if d["sources"] else []
        result.append(d)
    return result


def add_message(conversation_id: str, role: str, content: str, sources=None) -> dict:
    msg_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, sources, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, conversation_id, role, content,
             json.dumps(sources) if sources else None, now),
        )
        conn.commit()
    return {
        "id": msg_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "created_at": now,
    }


def delete_conversation(conversation_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()
