#!/usr/bin/env python3
"""
RSS Portal - Cronバッチスクリプト
定期的にRSSフィードを取得してスコアリングを実行

使用方法:
  python cron_job.py

Cron設定例（12時間ごと）:
  0 */12 * * * cd /path/to/rss-portal && /path/to/python cron_job.py >> /path/to/logs/cron.log 2>&1
"""

import sys
from datetime import datetime


def main():
    print("=" * 60)
    print(f"RSS Portal Cron Job - {datetime.now().isoformat()}")
    print("=" * 60)
    
    # 1. RSSフィード取得
    print("\n[Step 1] Fetching RSS feeds...")
    from rss_fetcher import fetch_all_feeds
    fetch_result = fetch_all_feeds()
    print(f"  -> Fetched: {fetch_result['fetched']}, Inserted: {fetch_result['inserted']}")
    
    # 2. AIスコアリング
    print("\n[Step 2] Scoring articles with AI...")
    from ai_scorer import score_articles
    score_result = score_articles(limit=50, delay=1.5)  # レート制限対策で遅延を入れる
    print(f"  -> Scored: {score_result['scored']}/{score_result['processed']}")
    
    # 3. JSON出力
    print("\n[Step 3] Generating output JSON...")
    from json_output import save_output_json
    output_path = save_output_json()
    print(f"  -> Output: {output_path}")
    
    # 4. 古い記事を削除
    print("\n[Step 4] Cleaning up old articles...")
    from database import cleanup_old_articles, get_articles_count
    deleted = cleanup_old_articles()
    print(f"  -> Deleted: {deleted} old articles")
    
    # 5. 統計表示
    stats = get_articles_count()
    print("\n[Summary]")
    print(f"  Total articles: {stats['total']}")
    print(f"  Scored articles: {stats['scored']}")
    print(f"  High score (4-5): {stats['high_score']}")
    
    print("\n" + "=" * 60)
    print("Cron job completed successfully!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
