"""Gemini API操作モジュール — コメントへの返信案を生成"""

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL, load_system_prompt


def _get_client() -> genai.Client:
    """Geminiクライアントを初期化"""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY が設定されていません。\n"
            ".env ファイルに GEMINI_API_KEY=your_key を追加してください。"
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_reply(original_comment: str, author_name: str) -> str:
    """
    視聴者コメントに対する返信案をGeminiで生成する。
    システムプロンプトは prompt.txt から読み込む。
    """
    client = _get_client()
    system_prompt = load_system_prompt()

    # ユーザーメッセージにコメント情報を含める
    user_message = (
        f"以下の視聴者コメントに返信してください。\n\n"
        f"【コメント主】{author_name}\n"
        f"【コメント内容】\n{original_comment}"
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
        ),
        contents=user_message,
    )

    return response.text.strip()
