"""設定管理モジュール — .envから各種APIキー・設定を読み込む"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv(Path(__file__).parent / ".env")

# --- YouTube API ---
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv(
    "YOUTUBE_CLIENT_SECRETS_FILE",
    str(Path(__file__).parent / "client_secret.json"),
)
YOUTUBE_TOKEN_FILE = os.getenv(
    "YOUTUBE_TOKEN_FILE",
    str(Path(__file__).parent / "token.json"),
)
# OAuth 2.0スコープ（コメント読み書き + チャンネル情報取得）
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

# --- Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- データベース ---
DB_PATH = os.getenv(
    "DB_PATH",
    str(Path(__file__).parent / "comments.db"),
)

# --- プロンプト ---
PROMPT_FILE = os.getenv(
    "PROMPT_FILE",
    str(Path(__file__).parent / "prompt.txt"),
)


def load_system_prompt() -> str:
    """外部ファイルからGemini用システムプロンプトを読み込む"""
    path = Path(PROMPT_FILE)
    if not path.exists():
        raise FileNotFoundError(
            f"プロンプトファイルが見つかりません: {path}\n"
            "prompt.txt を作成してください。"
        )
    return path.read_text(encoding="utf-8").strip()
