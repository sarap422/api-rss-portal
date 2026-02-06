# APP RSS Portal v1.0.3

<p align="center">
  <strong>AIがRSS記事を自動スコアリングし、興味のある記事だけを表示するパーソナライズ情報ポータル</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
</p>

---

## 特徴

- **AIスコアリング** - Gemini（Gemini 2.0 Flash）が記事を1〜5で評価
- **パーソナライズ** - 興味分野を設定して、自分好みの記事だけを表示
- **学習機能** - Like/Dislike/クリック追跡でスコアリング精度が向上
- **低コスト運用** - 月額約50〜200円（Gemini API）
- **WordPress連携** - PHPスニペットで簡単に組み込み可能
- **共用サーバー対応** - cPanel環境（カラフルボックス等）で動作

---

## デモ

![RSS Portal Demo](https://i.gyazo.com/62ef300d8309e9e4954f5a1c22a9c1ab.png)

---

## システム構成

```
┌─────────────────────────────────────────────────────────────────┐
│                         サーバー                                │
│                                                                 │
│  ┌─────────────┐    ┌─────────────────────────────────────┐    │
│  │   Cron      │    │         Python FastAPI              │    │
│  │  (12時間毎)   │───▶│                                     │    │
│  └─────────────┘    │  1. RSS取得 (feedparser)            │    │
│                     │  2. AIスコアリング (Gemini)      │    │
│                     │  3. SQLiteに保存                    │    │
│                     │  4. JSONファイル出力                 │    │
│                     └─────────────────────────────────────┘    │
│                                    │                           │
│                                    ▼                           │
│                     ┌─────────────────────────────────────┐    │
│                     │          uvicorn (port 8001)        │    │
│                     │          /api/rss-portal/           │    │
│                     └─────────────────────────────────────┘    │
│                                    │                           │
│                                    ▼                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    WordPress                            │   │
│  │                                                         │   │
│  │   [JavaScript] ─fetch─▶ /api/rss-portal/articles        │   │
│  │   [評価ボタン] ─POST──▶ /api/rss-portal/feedback        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 必要要件

- Python 3.11+
- cPanel対応の共用サーバー（カラフルボックス、Xserver等）
- APIキー（無料枠あり）
- WordPress（フロントエンド表示用）

---

## インストール

### 1. ファイル配置

```
/home/[ユーザー名]/
├── api/
│   ├── start_uvicorn.sh
│   └── rss-portal/
│       ├── main.py
│       ├── config.py
│       ├── rss_fetcher.py
│       ├── ai_scorer.py
│       ├── database.py
│       ├── json_output.py
│       ├── cron_job.py
│       ├── requirements.txt
│       ├── data/
│       │   └── feeds.opml
│       ├── output/
│       └── logs/
│
└── public_html/api/rss-portal/
    └── .htaccess
```

### 2. Python仮想環境のセットアップ

```bash
# cPanelでPythonアプリを作成後
cd /home/[ユーザー名]/api/rss-portal
source /home/[ユーザー名]/virtualenv/api/rss-portal/3.11/bin/activate

# パッケージインストール
pip install -r requirements.txt
```

### 3. 設定ファイルの編集

`config.py` を編集：

```python
# APIキーを設定
API_KEY = "your-gemini-api-key"

# 興味分野をカスタマイズ
USER_INTERESTS = """
【技術分野】
- あなたの興味のある分野
...
"""

# CORSに自分のサイトを追加
CORS_ORIGINS = [
    "https://your-site.com",
    "http://localhost:3000",
]
```

### 4. RSSフィードの設定

`data/feeds.opml` を編集するか、Feedlyからエクスポートしたファイルを配置：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head><title>My Feeds</title></head>
    <body>
        <outline text="Tech" title="Tech">
            <outline type="rss" text="Zenn" xmlUrl="https://zenn.dev/feed"/>
            <outline type="rss" text="Qiita" xmlUrl="https://qiita.com/popular-items/feed"/>
        </outline>
    </body>
</opml>
```

※ `feeds.opml` を更新すると、次回の `cron_job.py` 実行時に新しいフィードが自動で追加されます。

### 5. 初回実行

```bash
# RSS取得
python rss_fetcher.py

# AIスコアリング
python -c "from ai_scorer import score_articles; score_articles(limit=100, delay=2.0)"

# JSON出力
python json_output.py
```

### 6. Cron設定

cPanelのCronジョブに追加：

```bash
# uvicorn自動起動（5分毎）
*/5 * * * * /home/[ユーザー名]/api/start_uvicorn.sh

# RSS取得・スコアリング（12時間毎）
0 */12 * * * cd /home/[ユーザー名]/api/rss-portal && /home/[ユーザー名]/virtualenv/api/rss-portal/3.11/bin/python cron_job.py >> logs/cron.log 2>&1
```

### 手動でuvicornを再起動する場合

> **注意**: 以下のコマンドはcrontabに追加しないでください。手動でターミナルから実行するものです。
> `pkill` は意図しないプロセスを停止する可能性があるため、実行前に `ps aux | grep uvicorn` で対象プロセスを確認してください。

```bash
pkill -u [ユーザー名] -f "uvicorn main:app.*port 8001"
sleep 2
/home/[ユーザー名]/api/start_uvicorn.sh
```

### 7. WordPress組み込み

固定ページに `rss-portal.php` の内容を追加（カスタムHTMLブロック等）

---

## 設定項目

### config.py

| 項目 | 説明 | デフォルト |
|------|------|-----------|
| `API_KEY` | APIキー | - |
| `API_MODEL` | 使用するAIモデル | `gemini-2.0-flash` |
| `USER_INTERESTS` | 興味のある分野（AIプロンプト用） | - |
| `USER_DISLIKES` | 興味のない分野（AIプロンプト用） | - |
| `MIN_SCORE_TO_DISPLAY` | 表示する最低スコア | `3` |
| `MAX_ITEMS_PER_FEED` | 各フィードから取得する最大記事数 | `100` |
| `MAX_DISPLAY_PER_FEED` | 同一フィードから表示する最大記事数 | `10` |
| `ARTICLE_RETENTION_DAYS` | 記事を保持する日数 | `14` |

---

## API仕様

### GET /articles

スコアリング済み記事一覧を取得

```json
{
  "generated_at": "2026-01-30T12:00:00",
  "stats": {
    "total_articles": 392,
    "scored_articles": 342,
    "high_score_articles": 146,
    "displayed": 100
  },
  "articles": [
    {
      "id": 1,
      "title": "記事タイトル",
      "link": "https://example.com/article",
      "feed_name": "フィード名",
      "summary": "AIが生成した要約...",
      "score": 5,
      "published_at": "2026-01-30T10:00:00",
      "likes": 0,
      "dislikes": 0
    }
  ]
}
```

### POST /feedback

記事へのフィードバックを送信

```json
{
  "article_id": 1,
  "feedback": "like"
}
```

| feedback | 説明 |
|----------|------|
| `like` | 高評価（次回スコアリングの参考に） |
| `dislike` | 低評価（記事を非表示にする） |
| `click` | クリック追跡（暗黙のLikeとして学習） |

---

## 運用コスト

| 項目 | 費用 |
|------|------|
| Gemini API | 約50〜200円/月（使用量による） |
| サーバー | 既存のWordPressサーバーを利用 |

※ Gemini 2.0 Flash は非常に安価（1記事あたり約0.07円）

---

## トラブルシューティング

### uvicornが停止している

```bash
cd /home/[ユーザー名]/api/rss-portal
source /home/[ユーザー名]/virtualenv/api/rss-portal/3.11/bin/activate

# uvicornを再起動
pkill -u [ユーザー名] -f "uvicorn main:app.*port 8001"
sleep 2
/home/[ユーザー名]/api/start_uvicorn.sh

# 確認
ps aux | grep uvicorn
```

### Rate limitedエラー

`ai_scorer.py` の `delay` パラメータを増やす（例: `3.0`）

### 古い記事をクリア（新しい状態で始めたい場合）

```bash
# 古いフィードをクリア
sqlite3 data/articles.db "DELETE FROM feeds;"

# 古い記事をクリア
sqlite3 data/articles.db "DELETE FROM articles;"
sqlite3 data/articles.db "DELETE FROM feedback;"

python rss_fetcher.py
python cron_job.py
```

### SQLiteファイルの破損

```bash
mv data/articles.db data/articles.db.corrupted
python rss_fetcher.py
python cron_job.py
```


---

## 技術スタック

- **バックエンド**: Python, FastAPI, uvicorn
- **データベース**: SQLite
- **AI**: Gemini (Gemini 2.0 Flash)
- **RSS解析**: feedparser
- **フロントエンド**: JavaScript (Vanilla)

---

## 参考リンク

- [Gemini API](https://ai.google.dev/) - AI API
- [FastAPI](https://fastapi.tiangolo.com/) - Pythonフレームワーク
- [feedparser](https://feedparser.readthedocs.io/) - RSS解析ライブラリ

---

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照

---

## Author

[@sarap422](https://github.com/sarap422)