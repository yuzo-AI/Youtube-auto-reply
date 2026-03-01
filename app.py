"""
YouTubeコメント半自動返信システム — Streamlit UI

実行方法:
  streamlit run app.py
"""

import streamlit as st

import db
from youtube_api import (
    get_youtube_service,
    get_my_channel_id,
    get_my_video_ids,
    get_unreplied_comments,
    post_reply,
)
from gemini_api import generate_reply

# ──────────────────────────────────────
# 初期化
# ──────────────────────────────────────
db.init_db()

st.set_page_config(
    page_title="YouTube コメント返信システム",
    page_icon="💬",
    layout="wide",
)

st.title("💬 YouTube コメント半自動返信システム")

# セッション状態の初期化
if "phase1_done" not in st.session_state:
    st.session_state.phase1_done = False
if "fetch_log" not in st.session_state:
    st.session_state.fetch_log = []


# ──────────────────────────────────────
# フェーズ1：データ準備
# ──────────────────────────────────────
st.header("📥 フェーズ1：コメント取得 ＆ 返信案生成")

col1, col2 = st.columns([1, 3])
with col1:
    max_videos = st.number_input(
        "取得する動画数", min_value=1, max_value=200, value=10, step=5
    )

with col2:
    st.markdown("")  # スペーサー

if st.button("🚀 コメント取得＆返信案生成", type="primary", use_container_width=True):
    st.session_state.fetch_log = []

    with st.status("処理中...", expanded=True) as status_ui:
        # Step 1: YouTube認証
        st.write("🔑 YouTube API 認証中...")
        try:
            service = get_youtube_service()
            my_channel_id = get_my_channel_id(service)
            st.write(f"✅ 認証成功（チャンネルID: `{my_channel_id}`）")
        except Exception as e:
            st.error(f"❌ YouTube認証に失敗しました: {e}")
            st.stop()

        # Step 2: 動画一覧の取得
        st.write(f"📹 最新 {max_videos} 件の動画を取得中...")
        try:
            video_ids = get_my_video_ids(service, my_channel_id, max_results=max_videos)
            st.write(f"✅ {len(video_ids)} 件の動画を取得")
        except Exception as e:
            st.error(f"❌ 動画一覧の取得に失敗しました: {e}")
            st.stop()

        # Step 3: 未返信コメントの取得
        st.write("💬 未返信コメントを検索中...")
        all_comments = []
        for i, vid in enumerate(video_ids):
            try:
                comments = get_unreplied_comments(service, vid, my_channel_id)
                # DB上で既に処理済みのコメントは除外
                new_comments = [
                    c for c in comments if not db.is_already_processed(c["comment_id"])
                ]
                all_comments.extend(new_comments)
                if new_comments:
                    st.write(f"  動画 {i+1}/{len(video_ids)}: {len(new_comments)} 件の新規コメント")
            except Exception as e:
                st.write(f"  ⚠️ 動画 {vid} のコメント取得エラー: {e}")

        st.write(f"✅ 合計 {len(all_comments)} 件の未返信コメントを検出")

        if not all_comments:
            status_ui.update(label="✅ 完了（新規コメントなし）", state="complete")
        else:
            # Step 4: Gemini で返信案を生成
            st.write("🤖 Gemini で返信案を生成中...")
            progress = st.progress(0)
            for idx, comment in enumerate(all_comments):
                try:
                    reply = generate_reply(
                        comment["original_text"], comment["author_name"]
                    )
                    db.upsert_comment(
                        comment_id=comment["comment_id"],
                        video_id=comment["video_id"],
                        author_name=comment["author_name"],
                        original_text=comment["original_text"],
                        generated_reply=reply,
                        status="pending",
                    )
                    st.session_state.fetch_log.append(
                        f"✅ {comment['author_name']}: 返信案生成完了"
                    )
                except Exception as e:
                    st.session_state.fetch_log.append(
                        f"❌ {comment['author_name']}: 生成失敗 ({e})"
                    )
                progress.progress((idx + 1) / len(all_comments))

            status_ui.update(label="✅ フェーズ1 完了！", state="complete")
            st.session_state.phase1_done = True

# 処理ログの表示
if st.session_state.fetch_log:
    with st.expander("📋 処理ログ", expanded=False):
        for log in st.session_state.fetch_log:
            st.text(log)

st.divider()

# ──────────────────────────────────────
# フェーズ2：確認・修正・投稿
# ──────────────────────────────────────
st.header("📝 フェーズ2：確認・修正・投稿")

pending = db.fetch_pending()

if not pending:
    st.info("📭 未承認のコメントはありません。フェーズ1を実行してコメントを取得してください。")
else:
    st.success(f"📬 {len(pending)} 件の未承認コメントがあります。")

    # 承認状態を管理するセッション変数
    if "approved_ids" not in st.session_state:
        st.session_state.approved_ids = set()

    # 全選択/全解除
    col_sel1, col_sel2, _ = st.columns([1, 1, 4])
    with col_sel1:
        if st.button("☑️ 全て選択"):
            st.session_state.approved_ids = {c["comment_id"] for c in pending}
            st.rerun()
    with col_sel2:
        if st.button("⬜ 全て解除"):
            st.session_state.approved_ids = set()
            st.rerun()

    # --- コメント一覧 ---
    for comment in pending:
        cid = comment["comment_id"]

        with st.container(border=True):
            # ヘッダー行：誰のコメントか + 承認チェック
            header_col, check_col = st.columns([4, 1])
            with header_col:
                st.markdown(f"**👤 {comment['author_name']}**　｜　動画ID: `{comment['video_id']}`")
            with check_col:
                is_approved = st.checkbox(
                    "承認",
                    value=cid in st.session_state.approved_ids,
                    key=f"approve_{cid}",
                )
                if is_approved:
                    st.session_state.approved_ids.add(cid)
                else:
                    st.session_state.approved_ids.discard(cid)

            # 元コメント（読み取り専用）+ 返信案（編集可能）を横並び
            left, right = st.columns(2)
            with left:
                st.markdown("**💬 元のコメント:**")
                st.text_area(
                    "元コメント",
                    value=comment["original_text"],
                    disabled=True,
                    key=f"orig_{cid}",
                    label_visibility="collapsed",
                    height=120,
                )
            with right:
                st.markdown("**🤖 返信案（編集可能）:**")
                edited_reply = st.text_area(
                    "返信案",
                    value=comment["generated_reply"],
                    key=f"reply_{cid}",
                    label_visibility="collapsed",
                    height=120,
                )
                # 編集内容をDBに即時反映
                if edited_reply != comment["generated_reply"]:
                    db.update_reply_text(cid, edited_reply)

    st.divider()

    # --- 投稿ボタン ---
    approved_count = len(st.session_state.approved_ids)
    st.warning(
        f"⚠️ 承認済み: **{approved_count}** 件 — "
        "下のボタンを押すと、承認済みコメントがYouTubeに実際に投稿されます。"
    )

    if st.button(
        f"📤 選択した {approved_count} 件のコメントを投稿",
        type="primary",
        disabled=approved_count == 0,
        use_container_width=True,
    ):
        # 安全確認ダイアログ
        service = get_youtube_service()

        posted_count = 0
        error_count = 0
        post_progress = st.progress(0)

        approved_list = [
            c for c in pending if c["comment_id"] in st.session_state.approved_ids
        ]

        for idx, comment in enumerate(approved_list):
            cid = comment["comment_id"]
            # 最新の返信テキストをセッションから取得
            reply_text = st.session_state.get(f"reply_{cid}", comment["generated_reply"])

            try:
                post_reply(service, cid, reply_text)
                db.update_status(cid, "posted")
                posted_count += 1
            except Exception as e:
                db.update_status(cid, "error")
                st.error(f"❌ {comment['author_name']} への返信投稿に失敗: {e}")
                error_count += 1

            post_progress.progress((idx + 1) / len(approved_list))

        # 投稿結果の表示
        st.session_state.approved_ids.clear()
        st.success(
            f"🎉 投稿完了！　成功: {posted_count} 件　｜　失敗: {error_count} 件"
        )
        st.rerun()


# ──────────────────────────────────────
# サイドバー：使い方ガイド
# ──────────────────────────────────────
with st.sidebar:
    st.header("📖 使い方")
    st.markdown(
        """
        **Step 1**: 「コメント取得＆返信案生成」ボタンを押す
        - YouTube APIで未返信コメントを自動取得
        - Gemini で返信案を自動生成

        **Step 2**: 返信案を確認・修正
        - 各コメントの返信案を自由に編集可能
        - 問題なければ「承認」チェックをオン

        **Step 3**: 「投稿」ボタンで一括投稿
        - 承認チェックが入ったコメントのみ投稿
        - **ボタンを押さない限り投稿されません**
        """
    )
    st.divider()
    st.caption("⚠️ 投稿は取り消せません。投稿前に必ず内容を確認してください。")
