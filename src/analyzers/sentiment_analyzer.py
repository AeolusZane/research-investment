"""
舆情情绪分析器 - 情绪词典 + 异常检测
"""
import re
from collections import Counter
from datetime import datetime
from loguru import logger

POSITIVE_WORDS = [
    "利好", "上涨", "涨停", "突破", "新高", "增长", "超预期", "盈利",
    "买入", "推荐", "看多", "反弹", "回暖", "复苏", "景气", "扩张",
    "强势", "看好", "乐观", "放量", "主力", "加仓", "北向流入",
]
NEGATIVE_WORDS = [
    "利空", "下跌", "跌停", "暴跌", "新低", "下滑", "不及预期", "亏损",
    "卖出", "减持", "看空", "回调", "恶化", "衰退", "萎缩", "收缩",
    "弱势", "悲观", "恐慌", "缩量", "出逃", "清仓", "北向流出",
    "暴雷", "违规", "处罚", "退市", "风险", "警告",
]
NEUTRAL_WORDS = ["震荡", "横盘", "观望", "分歧", "博弈", "整理", "盘整"]

class SentimentAnalyzer:
    def analyze_text(self, text):
        if not text:
            return {"score": 0, "label": "neutral", "keywords": []}
        pos = sum(1 for w in POSITIVE_WORDS if w in text)
        neg = sum(1 for w in NEGATIVE_WORDS if w in text)
        neu = sum(1 for w in NEUTRAL_WORDS if w in text)
        total = pos + neg + neu
        score = (pos - neg) / total if total > 0 else 0
        label = "positive" if score > 0.2 else ("negative" if score < -0.2 else "neutral")
        keywords = [w for w in POSITIVE_WORDS + NEGATIVE_WORDS + NEUTRAL_WORDS if w in text]
        return {"score": round(score, 2), "label": label, "positive_hits": pos, "negative_hits": neg, "keywords": keywords}

    def analyze_batch(self, items):
        results = []
        all_keywords = Counter()
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        for item in items:
            text = f"{item.get('title', '')} {item.get('summary', '')}"
            analysis = self.analyze_text(text)
            results.append({**item, "sentiment": analysis})
            counts[analysis["label"]] += 1
            for kw in analysis["keywords"]:
                all_keywords[kw] += 1
        total = len(results)
        sentiment_index = round((counts["positive"] - counts["negative"]) / total * 100, 1) if total > 0 else 0
        summary = {
            "analyzed_at": datetime.now().isoformat(), "total_items": total,
            "sentiment_index": sentiment_index, "distribution": counts,
            "top_keywords": all_keywords.most_common(15), "items": results,
        }
        logger.info(f"情绪分析完成: 指数={sentiment_index}, 正面={counts['positive']}, 中性={counts['neutral']}, 负面={counts['negative']}")
        return summary

    def detect_anomalies(self, sentiment_summary, threshold=2.0):
        anomalies = []
        index = sentiment_summary.get("sentiment_index", 0)
        if abs(index) > threshold * 20:
            anomalies.append({"type": "sentiment_extreme", "description": f"市场情绪指数极端: {index}",
                              "severity": "high" if abs(index) > threshold * 30 else "medium"})
        top_kw = sentiment_summary.get("top_keywords", [])
        neg_kw = [kw for kw, count in top_kw if kw in NEGATIVE_WORDS and count >= 3]
        if neg_kw:
            anomalies.append({"type": "negative_cluster", "description": f"负面关键词集中: {', '.join(neg_kw)}", "severity": "medium"})
        return anomalies
