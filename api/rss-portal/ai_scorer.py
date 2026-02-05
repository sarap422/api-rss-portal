"""
RSS Portal AIスコアリングモジュール
OpenRouter APIを使用して記事の関連度をスコアリング
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
# OpenRouter 設定
# ============================================================
# config.py に以下を追加してください:
# OPENROUTER_API_KEY = "sk-or-v1-..."
# OPENROUTER_MODEL = "google/gemini-2.0-flash-001"

try:
    from config import OPENROUTER_API_KEY, OPENROUTER_MODEL
except ImportError:
    OPENROUTER_API_KEY = None
    OPENROUTER_MODEL = "google/gemini-2.0-flash-001"

# OpenRouter API エンドポイント
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def build_scoring_prompt(title: str, summary: str, feed_name: str) -> str:
    """スコアリング用のプロンプトを構築"""
    
    # 過去のフィードバックを取得
    liked = get_liked_articles(5)
    disliked = get_disliked_articles(5)
    clicked = get_clicked_articles(10)
    
    liked_text = ""
    if liked:
        liked_text = "\n【過去に高評価した記事】\n"
        for a in liked:
            liked_text += f"- {a['title']}\n"
    
    # クリック記事（暗黙のLike）
    clicked_text = ""
    if clicked:
        clicked_text = "\n【クリックして読んだ記事】\n"
        for a in clicked:
            clicked_text += f"- {a['title']}\n"
    
    disliked_text = ""
    if disliked:
        disliked_text = "\n【過去に低評価した記事】\n"
        for a in disliked:
            disliked_text += f"- {a['title']}\n"
    
    prompt = f"""以下の記事を、ユーザーの興味に基づいて1〜5でスコアリングしてください。

【ユーザーの興味分野】
{USER_INTERESTS}

【興味がない分野】
{USER_DISLIKES}
{liked_text}{clicked_text}{disliked_text}
【スコア基準】
5: 非常に興味深い、すぐ読みたい
4: 興味あり、時間があれば読みたい
3: 普通、特に興味を引かない
2: あまり興味がない
1: 全く興味がない、読む必要なし

【記事情報】
フィード: {feed_name}
タイトル: {title}
要約: {summary[:300] if summary else '（要約なし）'}

【出力形式】
必ず以下のJSON形式のみで出力してください。それ以外のテキストは不要です。
{{"score": 数字, "summary": "この記事の内容を130文字以内で要約"}}
"""
    return prompt


def extract_json_from_response(text: str) -> Optional[dict]:
    """レスポンスからJSONを抽出"""
    
    # 1. 前後の空白を除去
    text = text.strip()
    
    # 2. Markdownコードブロックを除去 (```json ... ``` or ``` ... ```)
    if '```' in text:
        # コードブロック内の内容を抽出
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block_match:
            text = code_block_match.group(1).strip()
    
    # 3. JSONとして直接パースを試みる
    if text.startswith('{'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    
    # 4. { から } までを抽出（ネストされた括弧に対応、文字列内のブレースを無視）
    brace_count = 0
    start_idx = -1
    in_string = False
    escape = False
    for i, char in enumerate(text):
        if escape:
            escape = False
            continue
        if char == '\\' and in_string:
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == '{':
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                json_str = text[start_idx:i+1]
                try:
                    return json.loads(json_str)
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


def call_openrouter_api(prompt: str) -> Optional[dict]:
    """OpenRouter APIを呼び出してスコアを取得"""
    
    if not OPENROUTER_API_KEY:
        print("[ERROR] OpenRouter API key not configured")
        print("[INFO] Add to config.py: OPENROUTER_API_KEY = 'sk-or-v1-...'")
        return None
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": SITE_URL,
        "X-Title": "RSS Portal"
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 500,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 429:
            print("[WARN] Rate limited. Waiting 60 seconds...")
            time.sleep(60)
            return None
        
        if response.status_code == 402:
            print("[ERROR] Insufficient credits. Please add credits at https://openrouter.ai/credits")
            return None
        
        response.raise_for_status()
        data = response.json()
        
        # レスポンスからテキストを抽出
        text = data['choices'][0]['message']['content']
        
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
    print(f"[INFO] Using model: {OPENROUTER_MODEL}")
    
    for article in articles:
        result['processed'] += 1
        
        prompt = build_scoring_prompt(
            title=article['title'],
            summary=article['summary'] or '',
            feed_name=article['feed_name']
        )
        
        ai_result = call_openrouter_api(prompt)
        
        if ai_result and 'score' in ai_result:
            score = int(ai_result['score'])
            score = max(1, min(5, score))  # 1-5に制限
            summary = ai_result.get('summary', '')[:130]
            
            update_article_score(article['id'], score, summary)
            result['scored'] += 1
            
            print(f"  [{score}] {article['title'][:40]}...")
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
    
    ai_result = call_openrouter_api(prompt)
    
    if ai_result and 'score' in ai_result:
        score = int(ai_result['score'])
        score = max(1, min(5, score))
        summary = ai_result.get('summary', '')[:130]
        update_article_score(article_id, score, summary)
        return score
    
    return None


if __name__ == "__main__":
    # テスト実行
    print("=" * 50)
    print("AI Scorer Test (OpenRouter)")
    print("=" * 50)
    result = score_articles(limit=5)
    print(f"\nResult: {result}")