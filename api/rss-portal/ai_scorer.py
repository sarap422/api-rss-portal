"""
RSS Portal AIスコアリングモジュール
Gemini API（Google AI Studio）を使用して記事の関連度をスコアリング
"""

import json
import re
import time
from typing import Optional

import requests

from config import USER_INTERESTS, USER_DISLIKES, SITE_URL
from database import (
    get_unscored_articles,
    update_article_score,
    get_liked_articles,
    get_disliked_articles,
    get_clicked_articles
)

# ============================================================
# API 設定
# ============================================================
try:
    from config import API_KEY, API_MODEL
except ImportError:
    API_KEY = None
    API_MODEL = "gemini-2.0-flash"

# API エンドポイント
API_MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def build_scoring_prompt(title: str, summary: str, feed_name: str) -> str:
    """スコアリング用のプロンプトを構築"""

    # 過去のフィードバックを取得
    liked = get_liked_articles(5)
    disliked = get_disliked_articles(5)
    clicked = get_clicked_articles(5)

    liked_text = ""
    if liked:
        liked_text = "\n【過去に高評価した記事】\n"
        for a in liked:
            liked_text += f"- {a['title']}\n"

    disliked_text = ""
    if disliked:
        disliked_text = "\n【過去に低評価した記事】\n"
        for a in disliked:
            disliked_text += f"- {a['title']}\n"

    clicked_text = ""
    if clicked:
        clicked_text = "\n【過去にクリックした記事（興味あり）】\n"
        for a in clicked:
            clicked_text += f"- {a['title']}\n"

    prompt = f"""以下の記事を、ユーザーの興味に基づいて1〜5でスコアリングし、130文字以内の日本語要約を作成してください。

【ユーザーの興味分野】
{USER_INTERESTS}

【興味がない分野】
{USER_DISLIKES}
{liked_text}{disliked_text}{clicked_text}
【スコア基準】
5: 非常に興味深い、すぐ読みたい
4: 興味あり、時間があれば読みたい
3: 普通、特に興味を引かない
2: あまり興味がない
1: 全く興味がない、読む必要なし

【記事情報】
フィード: {feed_name}
タイトル: {title}
概要: {summary[:300] if summary else '（概要なし）'}

【出力形式】
必ず以下のJSON形式のみで出力してください。それ以外のテキストは不要です。
{{"score": 数字, "summary": "130文字以内の日本語要約"}}
"""
    return prompt


def extract_json_from_response(text: str) -> Optional[dict]:
    """レスポンスからJSONを抽出"""

    # 1. 前後の空白を除去
    text = text.strip()

    # 2. コードブロック内のJSONを探す
    code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    # 3. そのままJSONとして解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 4. JSONオブジェクトを正規表現で探す
    json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # 5. 正規表現でscore と summaryを含むJSONを探す（エスケープされた引用符に対応）
    json_match = re.search(r'\{\s*"score"\s*:\s*\d+\s*,\s*"summary"\s*:\s*"(?:[^"\\]|\\.)*"\s*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # 6. scoreだけでも取り出す（JSONが途中で切れている場合）
    score_match = re.search(r'"score"\s*:\s*(\d+)', text)
    if score_match:
        score = int(score_match.group(1))
        # summaryも取れれば取る
        summary_match = re.search(r'"summary"\s*:\s*"([^"]*)', text)
        summary = summary_match.group(1) if summary_match else ""
        return {"score": score, "summary": summary}

    return None


def call_api(prompt: str) -> Optional[dict]:
    """APIを呼び出してスコアを取得"""

    if not API_KEY:
        print("[ERROR] API key not configured")
        print("[INFO] Add to config.py: API_KEY = 'your-api-key'")
        return None

    url = f"{API_MODEL_URL}/{API_MODEL}:generateContent?key={API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 500
        }
    }

    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )

        if response.status_code == 429:
            print("[WARN] Rate limited. Waiting 60 seconds...")
            time.sleep(60)
            return None

        if response.status_code == 403:
            print("[ERROR] API key invalid or billing not enabled.")
            print("[INFO] Check: https://aistudio.google.com/apikey")
            return None

        response.raise_for_status()
        data = response.json()

        # APIのレスポンス形式からテキストを抽出
        text = data['candidates'][0]['content']['parts'][0]['text']

        # JSONを抽出
        result = extract_json_from_response(text)
        if result:
            return result

        print(f"[WARN] Could not parse response: {text[:100]}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API request failed: {e}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"[ERROR] Failed to parse response: {e}")
        return None


def score_articles(limit: int = 20, delay: float = 1.0) -> dict:
    """未スコアの記事をスコアリング"""

    result = {
        'processed': 0,
        'scored': 0,
        'errors': 0
    }

    articles = get_unscored_articles(limit)

    if not articles:
        print("[INFO] No articles to score")
        return result

    print(f"[INFO] Scoring {len(articles)} articles...")
    print(f"[INFO] Using model: {API_MODEL}")

    for article in articles:
        result['processed'] += 1

        prompt = build_scoring_prompt(
            title=article['title'],
            summary=article['summary'] or '',
            feed_name=article['feed_name']
        )

        ai_result = call_api(prompt)

        if ai_result and 'score' in ai_result:
            score = int(ai_result['score'])
            score = max(1, min(5, score))  # 1-5に制限
            summary = ai_result.get('summary', '')[:200]

            update_article_score(article['id'], score, summary)
            result['scored'] += 1

            print(f"  [{score}] {article['title'][:50]}...")
        else:
            result['errors'] += 1
            # エラー時はスコア3（普通）を設定して次に進む
            update_article_score(article['id'], 3, "スコアリング失敗")

        # レート制限対策
        time.sleep(delay)

    print(f"[INFO] Scored: {result['scored']}/{result['processed']}")
    return result


def score_single_article(article_id: int) -> Optional[int]:
    """単一の記事をスコアリング（API用）"""
    from database import get_article_by_id

    article = get_article_by_id(article_id)
    if not article:
        return None

    prompt = build_scoring_prompt(
        title=article['title'],
        summary=article['summary'] or '',
        feed_name=article['feed_name']
    )

    ai_result = call_api(prompt)

    if ai_result and 'score' in ai_result:
        score = int(ai_result['score'])
        score = max(1, min(5, score))
        summary = ai_result.get('summary', '')[:200]
        update_article_score(article_id, score, summary)
        return score

    return None


if __name__ == "__main__":
    # テスト実行
    print("=" * 50)
    print("AI Scorer Test (API)")
    print("=" * 50)
    result = score_articles(limit=5)
    print(f"\nResult: {result}")