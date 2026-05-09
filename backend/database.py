import sqlite3
import uuid
from datetime import datetime
from contextlib import contextmanager
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "ai_logs.db")


# ─────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────

@contextmanager
def _get_conn():
    """
    Context manager that opens a connection, yields it, commits on
    success, and always closes — even if an exception is raised.
    Row factory makes every row a dict instead of a plain tuple.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Schema setup & migration
# ─────────────────────────────────────────────

def _existing_columns(conn: sqlite3.Connection, table: str) -> set:
    """Return the set of column names that already exist in a table."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def init_db():
    """
    Create tables if they don't exist, then run safe migrations
    to add any columns that were introduced after the initial schema.
    Safe to call multiple times — idempotent.
    """
    with _get_conn() as conn:
        # ── chat_logs ──────────────────────────────────────────────
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chat_logs (
                id            INTEGER  PRIMARY KEY AUTOINCREMENT,
                chat_id       TEXT     UNIQUE NOT NULL,
                timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_prompt   TEXT,
                generated_code TEXT,
                explanation   TEXT,
                status        TEXT     DEFAULT 'pending'
            )
        ''')

        # ── execution_logs ─────────────────────────────────────────
        conn.execute('''
            CREATE TABLE IF NOT EXISTS execution_logs (
                id            INTEGER  PRIMARY KEY AUTOINCREMENT,
                timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
                chat_id       TEXT,                        -- links back to chat_logs
                executed_code TEXT,
                stdout        TEXT,
                stderr        TEXT,
                success       INTEGER                      -- 0 = False, 1 = True
            )
        ''')

        # ── migration: add columns to pre-existing databases ───────
        chat_cols = _existing_columns(conn, "chat_logs")
        if "chat_id" not in chat_cols:
            conn.execute("ALTER TABLE chat_logs ADD COLUMN chat_id TEXT")
        if "status" not in chat_cols:
            conn.execute("ALTER TABLE chat_logs ADD COLUMN status TEXT DEFAULT 'pending'")

        exec_cols = _existing_columns(conn, "execution_logs")
        if "chat_id" not in exec_cols:
            conn.execute("ALTER TABLE execution_logs ADD COLUMN chat_id TEXT")


# ─────────────────────────────────────────────
# Write operations
# ─────────────────────────────────────────────

def log_chat(user_prompt: str, generated_code: str, explanation: str) -> str:
    """
    Insert a new chat turn. Generates and returns a unique chat_id
    that the frontend uses to tie approval → execution together.
    Status starts as 'pending' until the user executes the code.
    """
    chat_id = str(uuid.uuid4())
    with _get_conn() as conn:
        conn.execute(
            '''INSERT INTO chat_logs
               (chat_id, user_prompt, generated_code, explanation, status)
               VALUES (?, ?, ?, ?, 'pending')''',
            (chat_id, user_prompt, generated_code, explanation)
        )
    return chat_id


def log_execution(
    executed_code: str,
    stdout: str,
    stderr: str,
    success: bool,
    chat_id: str = None,       # optional — links execution back to its chat turn
) -> None:
    """
    Record the outcome of running a code snippet.
    If chat_id is provided, the corresponding chat_logs row is updated
    to 'executed' so the approval flow stays consistent.
    """
    with _get_conn() as conn:
        conn.execute(
            '''INSERT INTO execution_logs
               (chat_id, executed_code, stdout, stderr, success)
               VALUES (?, ?, ?, ?, ?)''',
            (chat_id, executed_code, stdout, stderr, int(success))
        )
        if chat_id:
            conn.execute(
                "UPDATE chat_logs SET status = 'executed' WHERE chat_id = ?",
                (chat_id,)
            )


# ─────────────────────────────────────────────
# Read operations
# ─────────────────────────────────────────────

def get_chat_by_id(chat_id: str) -> dict | None:
    """
    Return a single chat_logs row as a dict, or None if not found.
    Used by the execution endpoint to verify the chat_id is legitimate.
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM chat_logs WHERE chat_id = ?", (chat_id,)
        ).fetchone()
    return dict(row) if row else None


def get_chat_logs(limit: int = 50, offset: int = 0) -> list[dict]:
    """
    Return the most recent chat turns, newest first.
    Exposed by GET /api/logs to satisfy the retrieval requirement.
    """
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
    return [dict(r) for r in rows]


def get_execution_logs(limit: int = 50, offset: int = 0) -> list[dict]:
    """
    Return the most recent execution records, newest first.
    Exposed by GET /api/logs/executions.
    """
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM execution_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
    return [dict(r) for r in rows]


def get_log_stats() -> dict:
    """
    Return aggregate counts for the dashboard summary card:
    total chats, total executions, success rate.
    """
    with _get_conn() as conn:
        total_chats = conn.execute(
            "SELECT COUNT(*) FROM chat_logs"
        ).fetchone()[0]

        total_exec = conn.execute(
            "SELECT COUNT(*) FROM execution_logs"
        ).fetchone()[0]

        success_count = conn.execute(
            "SELECT COUNT(*) FROM execution_logs WHERE success = 1"
        ).fetchone()[0]

    success_rate = round(success_count / total_exec * 100, 1) if total_exec else 0.0

    return {
        "total_chats": total_chats,
        "total_executions": total_exec,
        "success_rate_pct": success_rate,
    }