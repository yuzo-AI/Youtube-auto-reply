"""SQLiteデータベース操作モジュール — コメント状態の永続化"""

import sqlite3
from contextlib import contextmanager
from typing import Generator

from config import DB_PATH

# --- テーブル定義 ---
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS comments_state (
    comment_id   TEXT PRIMARY KEY,
    video_id     TEXT    NOT NULL,
    author_name  TEXT    NOT NULL,
    original_text TEXT   NOT NULL,
    generated_reply TEXT NOT NULL DEFAULT '',
    status       TEXT    NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'approved', 'posted', 'error'))
);
"""


@contextmanager
def _get_conn() -> Generator[sqlite3.Connection, None, None]:
    """接続のライフサイクルをコンテキストマネージャで管理"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # dict風アクセスを有効化
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """テーブルが存在しなければ作成する（起動時に1回呼ぶ）"""
    with _get_conn() as conn:
        conn.execute(_CREATE_TABLE_SQL)


def upsert_comment(
    comment_id: str,
    video_id: str,
    author_name: str,
    original_text: str,
    generated_reply: str,
    status: str = "pending",
) -> None:
    """コメントを挿入 or 更新（重複取得に対応）"""
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO comments_state
                (comment_id, video_id, author_name, original_text, generated_reply, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(comment_id) DO UPDATE SET
                generated_reply = excluded.generated_reply,
                status          = excluded.status
            """,
            (comment_id, video_id, author_name, original_text, generated_reply, status),
        )


def fetch_pending() -> list[dict]:
    """status='pending' のレコードを全件取得"""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM comments_state WHERE status = 'pending' ORDER BY rowid"
        ).fetchall()
    return [dict(r) for r in rows]


def update_reply_text(comment_id: str, new_reply: str) -> None:
    """ユーザーが編集した返信テキストを保存"""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE comments_state SET generated_reply = ? WHERE comment_id = ?",
            (new_reply, comment_id),
        )


def update_status(comment_id: str, status: str) -> None:
    """ステータスを更新（approved / posted / error）"""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE comments_state SET status = ? WHERE comment_id = ?",
            (status, comment_id),
        )


def is_already_processed(comment_id: str) -> bool:
    """既にDBに存在するか確認（重複取得防止）"""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM comments_state WHERE comment_id = ?",
            (comment_id,),
        ).fetchone()
    return row is not None
