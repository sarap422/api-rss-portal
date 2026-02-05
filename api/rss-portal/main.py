"""
RSS Portal - FastAPI メインアプリケーション
ColorfulBox共有サーバー用
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from config import CORS_ORIGINS, OUTPUT_JSON, MIN_SCORE_TO_DISPLAY
from database import (
    add_feedback,
    get_article_by_id,
    get_scored_articles,
    get_articles_count,
    cleanup_old_articles,
    get_feeds_count
)
from rss_fetcher import fetch_all_feeds
from ai_scorer import score_articles
from json_output import generate_output_json, save_output_json


# FastAPIアプリ初期化
app = FastAPI(
    title="RSS Portal API",
    description="AI-powered RSS feed filtering and scoring",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ========== モデル定義 ==========

class FeedbackRequest(BaseModel):
    article_id: int
    feedback: str  # "like" or "dislike"


class RefreshRequest(BaseModel):
    fetch_limit: Optional[int] = 100
    score_limit: Optional[int] = 50


# ========== エンドポイント ==========

@app.get("/")
async def root():
    """ヘルスチェック"""
    stats = get_articles_count()
    feeds = get_feeds_count()
    return {
        "status": "ok",
        "service": "RSS Portal API",
        "stats": {
            "feeds": feeds,
            "articles": stats['total'],
            "scored": stats['scored']
        }
    }


@app.get("/articles")
async def get_articles(
    min_score: int = MIN_SCORE_TO_DISPLAY,
    limit: int = 100
):
    """記事一覧を取得"""
    return generate_output_json(min_score=min_score, limit=limit)


@app.get("/articles.json")
async def get_articles_json():
    """静的JSONファイルを返す（WordPressから直接参照用）"""
    if OUTPUT_JSON.exists():
        return FileResponse(
            path=str(OUTPUT_JSON),
            media_type="application/json",
            headers={"Cache-Control": "public, max-age=300"}  # 5分キャッシュ
        )
    # ファイルが無ければ動的生成
    return generate_output_json()


@app.post("/feedback")
async def post_feedback(request: FeedbackRequest):
    """記事へのフィードバックを送信"""
    if request.feedback not in ('like', 'dislike', 'click'):  # 'click' 追加
        raise HTTPException(status_code=400, detail="Invalid feedback type")
    
    article = get_article_by_id(request.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    add_feedback(request.article_id, request.feedback)
    
    return {"status": "ok", "article_id": request.article_id, "feedback": request.feedback}


@app.post("/refresh")
async def refresh_feeds(
    background_tasks: BackgroundTasks,
    request: RefreshRequest = None
):
    """フィードを更新（バックグラウンド実行）"""
    if request is None:
        request = RefreshRequest()
    
    # バックグラウンドで実行
    background_tasks.add_task(run_refresh, request.fetch_limit, request.score_limit)
    
    return {
        "status": "started",
        "message": "Refresh started in background"
    }


async def run_refresh(fetch_limit: int, score_limit: int):
    """リフレッシュ処理の実際の実行"""
    try:
        # 1. RSSフィード取得
        fetch_result = fetch_all_feeds()
        
        # 2. AIスコアリング
        score_result = score_articles(limit=score_limit)
        
        # 3. JSON出力
        save_output_json()
        
        # 4. 古い記事を削除
        deleted = cleanup_old_articles()
        
        print(f"[REFRESH] Completed - Fetched: {fetch_result['inserted']}, Scored: {score_result['scored']}, Deleted: {deleted}")
        
    except Exception as e:
        print(f"[REFRESH] Error: {e}")


@app.get("/stats")
async def get_stats():
    """統計情報を取得"""
    stats = get_articles_count()
    feeds = get_feeds_count()
    return {
        "feeds": feeds,
        "articles": {
            "total": stats['total'],
            "scored": stats['scored'],
            "high_score": stats['high_score']
        }
    }


# ========== CLIコマンド用 ==========

def run_cli_refresh():
    """CLI用のリフレッシュコマンド（Cronから呼び出し）"""
    import asyncio
    asyncio.run(run_refresh(100, 50))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
