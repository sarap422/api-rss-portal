"""
RSS Portal 設定ファイル
ColorfulBox共有サーバー用
"""

import os
from pathlib import Path

# ディレクトリ設定
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# SQLite データベース
DATABASE_PATH = DATA_DIR / "articles.db"

# 出力ファイル（WordPressから読み込む）
OUTPUT_JSON = OUTPUT_DIR / "articles.json"

# OpenRouter API設定
OPENROUTER_API_KEY = "sk-or-v1-your-api-key-here"
OPENROUTER_MODEL = "google/gemini-2.0-flash-001"  # 安価で高速

# サイト設定
SITE_URL = "https://your-site.com"

# ユーザーの興味分野（AIスコアリングに使用）
USER_INTERESTS = """
【技術分野】
- WordPress開発・カスタマイズ・プラグイン開発
- AIコーディング（Claude Code, Cursor, GitHub Copilot等）
- Web制作全般（HTML/CSS/JavaScript）
- React/Vue/Next.js等のフロントエンド開発
- Python/PHP/Node.js等のバックエンド開発
- AIツール活用（ChatGPT, Gemini, Claude等）
- 画像生成AI（Nano Banana, Stable Diffusion等）
- 動画制作（Premiare Pro, Suno, PVのBGM, インタビュー音声編集, 動画自動編集等）
- デプロイ環境（Vercel, Cloudflare, AWS等）
- 新しい開発ツール・プラットフォーム（Tauri等）

【重視するポイント】
- 具体的な実装例・コード例がある記事
- 実際に動くサンプルやデモがある
- すぐに試せる・即効性がある内容
- 比較検証や性能測定の結果がある
- プロンプト例やテンプレートが含まれる
- 「何ができるか」「どんなメリットがあるか」が明確
"""

# 興味がない分野（低スコアにする）
USER_DISLIKES = """
【興味がない分野】
- モバイルアプリ開発（iOS/Android）
- ゲーム開発
- 機械学習の理論・数学的な内容
- インフラ・DevOps（Docker, Kubernetes等の深い話）
- 資格試験・キャリア論
- セキュリティの一般論

【避けたい記事の特徴】
- 日記・体験談・ポエム的な内容（「〜した話」「〜してみた感想」）
- 「まとめてみた」「考えてみた」だけで具体的な実装がない
- 「検討」「考察」だけで、結論や成果物がない
- 大げさ・煽り気味のタイトルで中身が薄い
- 「速報」「登場」だけで何ができるか不明
- 漠然とした概念論・抽象的な話
- 「初心者向け」「入門」で内容が浅い
- ネタ記事・ジョーク記事
"""

# RSSフィード設定（OPMLが無い場合のデフォルト）
DEFAULT_FEEDS = [
    {"name": "Qiita 人気", "url": "https://qiita.com/popular-items/feed", "category": "tech"},
    {"name": "Zenn トレンド", "url": "https://zenn.dev/feed", "category": "tech"},
]

# OPMLファイルパス（Feedlyからエクスポート）
OPML_FILE = DATA_DIR / "feeds.opml"

# スコアリング設定
MIN_SCORE_TO_DISPLAY = 3       # 表示する最低スコア（1-5）
MAX_ARTICLES_PER_FETCH = 2000  # 1回の取得で処理する最大記事数
MAX_ITEMS_PER_FEED = 100       # 各フィードから取得する最大記事数
ARTICLE_RETENTION_DAYS = 14    # 記事を保持する日数
MAX_DISPLAY_PER_FEED = 10      # 同一フィードから表示する最大記事数

# Cron実行間隔（参考情報）
FETCH_INTERVAL_HOURS = 6       # 6時間ごとに取得

# CORS設定
CORS_ORIGINS = [
    SITE_URL,                  # サイト設定
    "http://localhost:3000",
]
