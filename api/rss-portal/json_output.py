"""
RSS Portal JSON出力モジュール
WordPressから読み込むためのJSONファイルを生成
"""

import json
from datetime import datetime

from config import OUTPUT_JSON, MIN_SCORE_TO_DISPLAY
from database import get_scored_articles, get_articles_count


def generate_output_json(min_score: int = None, limit: int = 100) -> dict:
    """記事一覧のJSONを生成"""
    
    if min_score is None:
        min_score = MIN_SCORE_TO_DISPLAY
    
    articles = get_scored_articles(min_score=min_score, limit=limit)
    stats = get_articles_count()
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "stats": {
            "total_articles": stats['total'],
            "scored_articles": stats['scored'],
            "high_score_articles": stats['high_score'],
            "displayed": len(articles)
        },
        "articles": []
    }
    
    for article in articles:
        output["articles"].append({
            "id": article['id'],
            "title": article['title'],
            "link": article['link'],
            "feed_name": article['feed_name'],
            "summary": article['summary'][:200] if article['summary'] else "",
            "score": article['ai_score'],
            "summary": article['score_summary'] or "",
            "published_at": article['published_at'],
            "fetched_at": article['fetched_at'],
            "likes": article['likes'],
            "dislikes": article['dislikes']
        })
    
    return output


def save_output_json() -> str:
    """JSONファイルを保存"""
    
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    
    output = generate_output_json()
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"[INFO] Saved {len(output['articles'])} articles to {OUTPUT_JSON}")
    return str(OUTPUT_JSON)


if __name__ == "__main__":
    # テスト実行
    print("=" * 50)
    print("JSON Output Test")
    print("=" * 50)
    path = save_output_json()
    print(f"Output: {path}")
