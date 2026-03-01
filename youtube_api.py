"""YouTube Data API v3 操作モジュール — コメント取得・返信投稿"""

import os
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import (
    YOUTUBE_CLIENT_SECRETS_FILE,
    YOUTUBE_TOKEN_FILE,
    YOUTUBE_SCOPES,
)


def _authenticate() -> Credentials:
    """OAuth 2.0認証 — トークンのキャッシュと自動更新に対応"""
    creds = None
    token_path = Path(YOUTUBE_TOKEN_FILE)

    # 既存トークンがあれば読み込む
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), YOUTUBE_SCOPES)

    # トークンが無効 or 期限切れなら再認証
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(YOUTUBE_CLIENT_SECRETS_FILE).exists():
                raise FileNotFoundError(
                    f"OAuth クライアントシークレットが見つかりません: {YOUTUBE_CLIENT_SECRETS_FILE}\n"
                    "Google Cloud Console からダウンロードして配置してください。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_SCOPES
            )
            creds = flow.run_local_server(port=0)

        # トークンを保存して次回以降の再認証を省略
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def get_youtube_service():
    """認証済みYouTubeサービスオブジェクトを取得"""
    creds = _authenticate()
    return build("youtube", "v3", credentials=creds)


def get_my_channel_id(service) -> str:
    """認証ユーザー自身のチャンネルIDを取得"""
    resp = service.channels().list(part="id", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        raise RuntimeError("チャンネルが見つかりません。OAuth認証を確認してください。")
    return items[0]["id"]


def get_my_video_ids(service, channel_id: str, max_results: int = 50) -> list[str]:
    """チャンネルのアップロード動画IDリストを取得"""
    # アップロードプレイリストIDを取得
    ch_resp = service.channels().list(
        part="contentDetails", id=channel_id
    ).execute()
    uploads_playlist_id = (
        ch_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    )

    video_ids = []
    next_page = None
    while True:
        pl_resp = service.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=min(max_results - len(video_ids), 50),
            pageToken=next_page,
        ).execute()

        for item in pl_resp.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])

        next_page = pl_resp.get("nextPageToken")
        if not next_page or len(video_ids) >= max_results:
            break

    return video_ids


def get_unreplied_comments(
    service, video_id: str, my_channel_id: str
) -> list[dict]:
    """
    指定動画の未返信コメント（トップレベル）を取得する。
    自分のチャンネルが返信済みのコメントは除外する。
    """
    unreplied = []
    next_page = None

    while True:
        resp = service.commentThreads().list(
            part="snippet,replies",
            videoId=video_id,
            maxResults=100,
            pageToken=next_page,
            textFormat="plainText",
        ).execute()

        for thread in resp.get("items", []):
            snippet = thread["snippet"]["topLevelComment"]["snippet"]

            # 自分自身のコメントはスキップ
            if snippet.get("authorChannelId", {}).get("value") == my_channel_id:
                continue

            # 既に自分が返信しているかチェック
            already_replied = False
            if thread["snippet"]["totalReplyCount"] > 0:
                replies = thread.get("replies", {}).get("comments", [])
                for reply in replies:
                    reply_channel = (
                        reply["snippet"]
                        .get("authorChannelId", {})
                        .get("value", "")
                    )
                    if reply_channel == my_channel_id:
                        already_replied = True
                        break

            if not already_replied:
                unreplied.append(
                    {
                        "comment_id": thread["snippet"]["topLevelComment"]["id"],
                        "video_id": video_id,
                        "author_name": snippet["authorDisplayName"],
                        "original_text": snippet["textDisplay"],
                    }
                )

        next_page = resp.get("nextPageToken")
        if not next_page:
            break

    return unreplied


def post_reply(service, parent_comment_id: str, reply_text: str) -> dict:
    """
    コメントに返信を投稿する。
    ※ この関数はユーザーが明示的に「投稿」ボタンを押した場合のみ呼ばれる。
    """
    body = {
        "snippet": {
            "parentId": parent_comment_id,
            "textOriginal": reply_text,
        }
    }
    response = service.comments().insert(part="snippet", body=body).execute()
    return response
