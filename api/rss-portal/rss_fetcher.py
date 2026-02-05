"""
RSS Portal RSSフィード取得モジュール
feedparserを使用してRSSフィードから記事を取得
"""

import calendar
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests as http_requests

from config import DEFAULT_FEEDS, OPML_FILE, MAX_ARTICLES_PER_FETCH
from database import (
    get_active_feeds,
    add_feed,
    import_feeds_from_opml,
    article_exists,
    insert_article,
    get_feeds_count
)


def generate_guid(link: str, title: str) -> str:
    """記事のユニークIDを生成"""
    content = f"{link}:{title}"
    return hashlib.md5(content.encode()).hexdigest()


def parse_published_date(entry) -> Optional[str]:
    """記事の公開日時をISO形式で返す（UTC）"""
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime.fromtimestamp(
                calendar.timegm(entry.published_parsed), tz=timezone.utc
            ).isoformat()
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime.fromtimestamp(
                calendar.timegm(entry.updated_parsed), tz=timezone.utc
            ).isoformat()
    except Exception:
        pass
    return None


def clean_html(text: str) -> str:
    """HTMLタグを除去してテキストのみ抽出"""
    if not text:
        return ""
    # HTMLタグを除去
    text = re.sub(r'<[^>]+>', ' ', text)
    # 連続する空白を1つに
    text = re.sub(r'\s+', ' ', text)
    # 前後の空白を除去
    return text.strip()


def get_entry_summary(entry) -> str:
    """記事の概要を取得（最大500文字）"""
    summary = ""
    if hasattr(entry, 'summary') and entry.summary:
        summary = entry.summary
    elif hasattr(entry, 'description') and entry.description:
        summary = entry.description
    elif hasattr(entry, 'content') and entry.content:
        summary = entry.content[0].get('value', '')
    
    return clean_html(summary)[:500]


def fetch_single_feed(feed_url: str, feed_name: str, max_items: int = 20) -> list:
    """単一のフィードから記事を取得"""
    articles = []
    
    try:
        response = http_requests.get(feed_url, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        if feed.bozo and not feed.entries:
            print(f"  [WARN] Parse error: {feed_name}")
            return articles
        
        for entry in feed.entries[:max_items]:
            link = entry.get('link', '')
            title = entry.get('title', '')
            
            if not link or not title:
                continue
            
            # GUID生成（フィード提供のIDがあれば使用）
            guid = entry.get('id') or generate_guid(link, title)
            
            # 既存チェック
            if article_exists(guid):
                continue
            
            articles.append({
                'guid': guid,
                'feed_name': feed_name,
                'title': clean_html(title),
                'link': link,
                'summary': get_entry_summary(entry),
                'published_at': parse_published_date(entry)
            })
    
    except Exception as e:
        print(f"  [ERROR] {feed_name}: {e}")
    
    return articles


def fetch_all_feeds() -> dict:
    """全てのフィードから記事を取得してDBに保存"""
    result = {
        'fetched': 0,
        'inserted': 0,
        'feeds_processed': 0,
        'errors': []
    }
    
    # 毎回OPMLから新しいフィードをインポート（既存はスキップされる）
    imported = import_feeds_from_opml(OPML_FILE)
    if imported > 0:
        print(f"[INFO] Imported {imported} new feeds from OPML")
    
    # OPMLが無い or 空の場合、フィードが0件ならデフォルトを追加
    if get_feeds_count() == 0:
        print("[INFO] No feeds found. Adding default feeds...")
        for feed in DEFAULT_FEEDS:
            add_feed(feed['name'], feed['url'], feed.get('category', ''))
    
    # アクティブなフィードを取得
    feeds = get_active_feeds()
    
    if not feeds:
        result['errors'].append("No feeds configured")
        return result
    
    print(f"[INFO] Processing {len(feeds)} feeds...")
    
    all_articles = []
    
    for feed in feeds:
        print(f"  Fetching: {feed['name'][:30]}...")
        articles = fetch_single_feed(feed['url'], feed['name'])
        all_articles.extend(articles)
        result['feeds_processed'] += 1
        
        # 最大記事数に達したら終了
        if len(all_articles) >= MAX_ARTICLES_PER_FETCH:
            print(f"[INFO] Reached max articles limit ({MAX_ARTICLES_PER_FETCH})")
            break
    
    result['fetched'] = len(all_articles)
    
    # データベースに挿入
    for article in all_articles[:MAX_ARTICLES_PER_FETCH]:
        try:
            insert_article(
                guid=article['guid'],
                feed_name=article['feed_name'],
                title=article['title'],
                link=article['link'],
                summary=article['summary'],
                published_at=article['published_at']
            )
            result['inserted'] += 1
        except Exception as e:
            result['errors'].append(str(e))
    
    print(f"[INFO] Fetched: {result['fetched']}, Inserted: {result['inserted']}")
    return result


if __name__ == "__main__":
    # テスト実行
    print("=" * 50)
    print("RSS Fetcher Test")
    print("=" * 50)
    result = fetch_all_feeds()
    print(f"\nResult: {result}")