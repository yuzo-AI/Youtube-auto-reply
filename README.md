# 💬 YouTube コメント半自動返信システム

YouTube Data API と Gemini API を使い、未返信コメントの取得 → AI返信案の生成 → 確認・編集 → 投稿を行う Streamlit アプリです。

## ✨ 特徴

- **未返信コメントを自動検出** — 既に返信済みのコメントはスキップ
- **Gemini で返信案を自動生成** — プロンプトをカスタマイズ可能
- **Human-in-the-Loop** — ボタンを押さない限り投稿されない安全設計
- **一括投稿** — 承認したコメントのみまとめて投稿

## 📁 構成

```
├── app.py                # Streamlit UI（メインアプリ）
├── youtube_api.py         # YouTube Data API 操作
├── gemini_api.py          # Gemini API 操作（返信生成）
├── db.py                  # SQLite データベース管理
├── config.py              # 設定管理（.env読み込み）
├── prompt.txt             # Gemini用システムプロンプト ★カスタマイズ可
├── requirements.txt       # 依存パッケージ
├── .env.example           # 環境変数テンプレート
└── .gitignore
```

## 🚀 セットアップ

### 1. クローン & 依存インストール

```bash
git clone https://github.com/yuzo-AI/Youtube-auto-reply.git
cd Youtube-auto-reply
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 2. API キーの準備

#### Gemini API Key
- [Google AI Studio](https://aistudio.google.com/apikey) でAPIキーを取得

#### YouTube OAuth 2.0
1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 「YouTube Data API v3」を有効化
3. 「OAuth 同意画面」を設定 → テストユーザーに自分を追加
4. 「認証情報」→「OAuth クライアントID」→ デスクトップアプリで作成
5. JSONをダウンロード → `client_secret.json` にリネームしてプロジェクトルートに配置

### 3. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集：
```
GEMINI_API_KEY=your_actual_api_key
```

### 4. 起動

```bash
streamlit run app.py
```

## 🎨 返信スタイルのカスタマイズ

`prompt.txt` を編集するだけで、返信のトーン・キャラクター・ルールを自由に変更できます。コードの変更は不要です。

**例：**
- 占いチャンネル → 母性ある60代女性のペルソナ
- ゲームチャンネル → フレンドリーなゲーマー口調
- 教育チャンネル → 丁寧で知的なトーン

## 📝 使い方

1. **フェーズ1**：「コメント取得＆返信案生成」ボタンを押す
   - 未返信コメントを自動取得 → Gemini で返信案を生成
2. **フェーズ2**：返信案を確認・編集
   - 各返信案は自由に編集可能
   - OKなものに「承認」チェック
3. **投稿**：承認済みコメントのみ一括投稿

> ⚠️ 投稿ボタンを押さない限り、YouTubeには何も投稿されません。

## ⚙️ 技術スタック

| 技術 | 用途 |
|---|---|
| Python | バックエンド |
| Streamlit | Web UI |
| YouTube Data API v3 | コメント取得・返信投稿 |
| Gemini API | 返信案の生成 |
| SQLite | コメント状態管理 |
