"""
仮説エンジン（全チャネル共通）

8つの事業仮説を管理し、各チャネルのデータから仮説スコアを算出する。
Threads / Instagram / Web のクロス分析に使用。
"""
import json
import os
from datetime import datetime

HYPOTHESES = {
    "hygiene": {
        "name": "清潔感",
        "insight": "清潔感は顔じゃなくて手入れで決まる",
        "target_emotion": "気づき",
        "keywords": ["清潔感", "手入れ", "身だしなみ", "整える", "清潔"],
        "seo_keywords": ["清潔感 男 作り方", "男 清潔感 出し方", "清潔感のある男"],
        "confidence": 0.0,
    },
    "aging_anxiety": {
        "name": "加齢不安",
        "insight": "30代で肌が変わる。気づいた時がスタート",
        "target_emotion": "焦りと安心",
        "keywords": ["老化", "肌", "30代", "エイジング", "シワ", "たるみ"],
        "seo_keywords": ["男 肌 老化 30代", "男 エイジングケア", "30代 男 肌 変化"],
        "confidence": 0.0,
    },
    "confidence": {
        "name": "自信",
        "insight": "自信は整えた先にある",
        "target_emotion": "共感と希望",
        "keywords": ["自信", "自己肯定", "変わりたい", "整える", "コンプレックス"],
        "seo_keywords": ["男 自信 ない 整える", "自己肯定感 男 上げ方"],
        "confidence": 0.0,
    },
    "presence": {
        "name": "第一印象",
        "insight": "印象は3秒で決まる。整え方で変わる",
        "target_emotion": "危機感",
        "keywords": ["第一印象", "印象", "見た目", "3秒", "面接", "デート"],
        "seo_keywords": ["第一印象 男 変える", "男 見た目 印象"],
        "confidence": 0.0,
    },
    "recovery_story": {
        "name": "回復体験",
        "insight": "過去の自分と向き合った記録",
        "target_emotion": "共感と勇気",
        "keywords": ["体験談", "回復", "過去", "変化", "汗", "多汗症"],
        "seo_keywords": ["多汗症 体験談 男", "男 コンプレックス 克服"],
        "confidence": 0.0,
    },
    "loneliness": {
        "name": "孤独",
        "insight": "誰にも言えない悩みがある。それでいい",
        "target_emotion": "深い共感",
        "keywords": ["孤独", "悩み", "相談", "一人", "誰にも言えない"],
        "seo_keywords": ["男 悩み 相談できない", "男 孤独 対処"],
        "confidence": 0.0,
    },
    "self_investment": {
        "name": "自己投資",
        "insight": "毎朝5分の投資が、1年後の自分を変える",
        "target_emotion": "納得と行動",
        "keywords": ["自己投資", "習慣", "毎朝", "5分", "ルーティン"],
        "seo_keywords": ["男 自己投資 美容", "朝 ルーティン 男"],
        "confidence": 0.0,
    },
    "conditioning": {
        "name": "コンディション",
        "insight": "整えるのは見た目じゃなくて、体調から",
        "target_emotion": "ハッとする気づき",
        "keywords": ["体調", "睡眠", "疲労", "回復", "サウナ", "運動"],
        "seo_keywords": ["男 疲労 回復 方法", "男 コンディション 管理"],
        "confidence": 0.0,
    },
}


def get_hypothesis(hypothesis_id):
    return HYPOTHESES.get(hypothesis_id)


def list_hypotheses():
    return HYPOTHESES


def detect_hypothesis(text):
    """テキストからどの仮説に該当するか推定"""
    scores = {}
    text_lower = text.lower()
    for hid, hyp in HYPOTHESES.items():
        score = sum(1 for kw in hyp["keywords"] if kw in text_lower)
        if score > 0:
            scores[hid] = score
    if not scores:
        return None
    return max(scores, key=scores.get)


def calculate_hypothesis_scores(posts_data):
    """投稿データから仮説スコアを算出

    posts_data: [{"hypothesis": "hygiene", "impressions": 100, "saves": 5, "comments": 2, ...}]
    """
    scores = {}
    for hid in HYPOTHESES:
        relevant = [p for p in posts_data if p.get("hypothesis") == hid]
        if not relevant:
            scores[hid] = {"score": 0, "posts": 0, "avg_save_rate": 0, "avg_engagement": 0}
            continue

        total_imp = sum(p.get("impressions", 0) for p in relevant)
        total_saves = sum(p.get("saves", 0) for p in relevant)
        total_comments = sum(p.get("comments", 0) for p in relevant)
        total_likes = sum(p.get("likes", 0) for p in relevant)

        save_rate = (total_saves / total_imp * 100) if total_imp > 0 else 0
        engagement = ((total_likes + total_comments + total_saves) / total_imp * 100) if total_imp > 0 else 0

        # スコア算出: 保存率重視（アルゴリズムで最も重要）
        score = save_rate * 3 + engagement * 2 + len(relevant) * 0.5

        scores[hid] = {
            "score": round(score, 2),
            "posts": len(relevant),
            "avg_save_rate": round(save_rate, 2),
            "avg_engagement": round(engagement, 2),
            "total_impressions": total_imp,
        }

    return scores


def rank_hypotheses(scores):
    """スコア順にランキング"""
    ranked = sorted(scores.items(), key=lambda x: -x[1]["score"])
    for i, (hid, data) in enumerate(ranked):
        stars = min(5, int(data["score"] / 2) + 1) if data["score"] > 0 else 0
        data["rank"] = i + 1
        data["stars"] = "★" * stars + "☆" * (5 - stars)
        data["confidence_pct"] = min(100, int(data["score"] * 5))
    return ranked
