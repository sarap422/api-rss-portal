"""
RSS Portal データベース操作
SQLiteを使用して記事とフィードバックを保存
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

from config import DATABASE_PATH, ARTICLE_RETENTION_DAYS


def init_database():
    """データベースとテーブルを初期化"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 記事テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT UNIQUE NOT NULL,
                feed_name TEXT,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                summary TEXT,
                published_at TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ai_score INTEGER DEFAULT 0,
                score_summary TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # フィードバックテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                feedback_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)
        
        # フィード設定テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                category TEXT,
                is_active INTEGER DEFAULT 1,
                last_fetched_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_guid ON articles(guid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_score ON articles(ai_score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_article ON feedback(article_id)")
        
        conn.commit()


@contextmanager
def get_connection():
    """データベース接続のコンテキストマネージャー"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


# ========== 記事関連 ==========

def article_exists(guid: str) -> bool:
    """記事が既に存在するかチェック"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM articles WHERE guid = ?", (guid,))
        return cursor.fetchone() is not None


def insert_article(
    guid: str,
    feed_name: str,
    title: str,
    link: str,
    summary: str = "",
    published_at: Optional[str] = None
) -> Optional[int]:
    """新しい記事を挿入（重複時はNoneを返す）"""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO articles (guid, feed_name, title, link, summary, published_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (guid, feed_name, title, link, summary, published_at))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None


def update_article_score(article_id: int, score: int, summary: str = ""):
    """記事のAIスコアを更新"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE articles SET ai_score = ?, score_summary = ? WHERE id = ?
        """, (score, summary, article_id))
        conn.commit()


def get_unscored_articles(limit: int = 50) -> list:
    """スコアリングされていない記事を取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, feed_name, title, link, summary
            FROM articles
            WHERE ai_score = 0
            ORDER BY fetched_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_scored_articles(min_score: int = 1, limit: int = 100) -> list:
    """スコアリング済みの記事を取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                a.id, a.feed_name, a.title, a.link, a.summary,
                a.ai_score, a.score_summary, a.published_at, a.fetched_at,
                COALESCE((SELECT COUNT(*) FROM feedback f WHERE f.article_id = a.id AND f.feedback_type = 'like'), 0) as likes,
                COALESCE((SELECT COUNT(*) FROM feedback f WHERE f.article_id = a.id AND f.feedback_type = 'dislike'), 0) as dislikes
            FROM articles a
            WHERE a.ai_score >= ?
            ORDER BY a.published_at DESC, a.ai_score DESC
            LIMIT ?
        """, (min_score, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_article_by_id(article_id: int) -> Optional[dict]:
    """IDで記事を取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def cleanup_old_articles() -> int:
    """古い記事を削除（トランザクションで一貫性を保証）"""
    cutoff = (datetime.now() - timedelta(days=ARTICLE_RETENTION_DAYS)).isoformat()
    with get_connection() as conn:
        try:
            cursor = conn.cursor()
            # まず関連するfeedbackを削除
            cursor.execute("""
                DELETE FROM feedback WHERE article_id IN (
                    SELECT id FROM articles WHERE fetched_at < ?
                )
            """, (cutoff,))
            # 次に記事を削除
            cursor.execute("DELETE FROM articles WHERE fetched_at < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        except Exception:
            conn.rollback()
            raise


def get_articles_count() -> dict:
    """記事の統計情報"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM articles")
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) as scored FROM articles WHERE ai_score > 0")
        scored = cursor.fetchone()["scored"]
        cursor.execute("SELECT COUNT(*) as high FROM articles WHERE ai_score >= 4")
        high = cursor.fetchone()["high"]
        return {"total": total, "scored": scored, "high_score": high}


# ========== フィードバック関連 ==========

def add_feedback(article_id: int, feedback_type: str) -> bool:
    """フィードバックを追加（like/dislike/click）"""
    if feedback_type not in ('like', 'dislike', 'click'):
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM articles WHERE id = ?", (article_id,))
        if cursor.fetchone() is None:
            return False
        cursor.execute("""
            INSERT INTO feedback (article_id, feedback_type)
            VALUES (?, ?)
        """, (article_id, feedback_type))
        conn.commit()
        return True


def get_liked_articles(limit: int = 10) -> list:
    """高評価された記事を取得（AIプロンプト用）"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT a.title, a.feed_name
            FROM articles a
            JOIN feedback f ON a.id = f.article_id
            WHERE f.feedback_type = 'like'
            ORDER BY f.created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_disliked_articles(limit: int = 10) -> list:
    """低評価された記事を取得（AIプロンプト用）"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT a.title, a.feed_name
            FROM articles a
            JOIN feedback f ON a.id = f.article_id
            WHERE f.feedback_type = 'dislike'
            ORDER BY f.created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_clicked_articles(limit: int = 10) -> list:
    """クリックした記事を取得（AIプロンプト用）"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT a.title, a.feed_name
            FROM articles a
            JOIN feedback f ON a.id = f.article_id
            WHERE f.feedback_type = 'click'
            ORDER BY f.created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


# ========== フィード関連 ==========

def get_active_feeds() -> list:
    """有効なフィード一覧を取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, url, category
            FROM feeds
            WHERE is_active = 1
        """)
        return [dict(row) for row in cursor.fetchall()]


def add_feed(name: str, url: str, category: str = "") -> bool:
    """フィードを追加（重複時はスキップ）"""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO feeds (name, url, category)
                VALUES (?, ?, ?)
            """, (name, url, category))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def import_feeds_from_opml(opml_path: Path) -> int:
    """OPMLファイルからフィードをインポート"""
    try:
        import defusedxml.ElementTree as ET
    except ImportError:
        import xml.etree.ElementTree as ET

    if not opml_path.exists():
        logger.warning("OPML file not found: %s", opml_path)
        return 0

    try:
        tree = ET.parse(opml_path)
        root = tree.getroot()
    except Exception as e:
        logger.error("Failed to parse OPML: %s", e)
        return 0
    
    imported = 0
    
    def process_outline(outline, parent_category=""):
        nonlocal imported
        xml_url = outline.get("xmlUrl")
        title = outline.get("title") or outline.get("text", "Unknown")
        category = outline.get("text", parent_category) if not xml_url else parent_category
        
        if xml_url:
            if add_feed(title, xml_url, category):
                imported += 1
                logger.info("Imported feed: %s", title)
        
        # 子要素を再帰的に処理
        for child in outline:
            if child.tag == "outline":
                process_outline(child, category if not xml_url else parent_category)
    
    body = root.find(".//body")
    if body is not None:
        for outline in body:
            if outline.tag == "outline":
                process_outline(outline)
    
    return imported


def get_feeds_count() -> int:
    """登録されたフィード数を取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM feeds WHERE is_active = 1")
        return cursor.fetchone()["cnt"]


# 初期化
init_database()
