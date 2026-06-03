"""
数据清洗器 - 去重、去噪、标准化
"""
import json, re, hashlib
from datetime import datetime
from loguru import logger

class DataCleaner:
    def __init__(self):
        self._seen_hashes = set()

    def _content_hash(self, item):
        key = f"{item.get('title', '')}{item.get('summary', '')[:100]}"
        return hashlib.md5(key.encode()).hexdigest()

    def deduplicate(self, items):
        result = []
        for item in items:
            h = self._content_hash(item)
            if h not in self._seen_hashes:
                self._seen_hashes.add(h)
                result.append(item)
        removed = len(items) - len(result)
        if removed > 0:
            logger.info(f"去重: 移除 {removed} 条重复内容")
        return result

    def clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        return text

    def normalize_news(self, items):
        normalized = []
        for item in items:
            cleaned = {
                "title": self.clean_text(item.get("title", "")),
                "summary": self.clean_text(item.get("summary", "")),
                "url": item.get("url", ""),
                "source": item.get("source", "unknown"),
                "published_at": item.get("published_at", ""),
                "collected_at": item.get("collected_at", ""),
            }
            if cleaned["title"]:
                normalized.append(cleaned)
        return normalized

    def normalize_market_data(self, data):
        normalized = {"collected_at": data.get("collected_at", ""), "stocks": [], "macro": []}
        for stock in data.get("a_shares", []) + data.get("us_hk_shares", []):
            normalized["stocks"].append({
                "code": stock.get("code", ""), "name": stock.get("name", ""),
                "market": stock.get("market", ""), "price": stock.get("price", 0),
                "change_pct": round(stock.get("change_pct", 0), 2),
                "volume": stock.get("volume", 0),
                "pe_ratio": stock.get("pe_ratio"), "pb_ratio": stock.get("pb_ratio"),
                "market_cap": stock.get("market_cap"),
            })
        normalized["macro"] = data.get("macro", [])
        return normalized

    def process_all(self, news_data=None, market_data=None, sentiment_data=None):
        result = {"processed_at": datetime.now().isoformat(), "news": [], "market": {}, "sentiment": []}
        if news_data:
            all_news = []
            for source_items in news_data.get("sources", {}).values():
                all_news.extend(source_items)
            all_news = self.deduplicate(all_news)
            result["news"] = self.normalize_news(all_news)
            logger.info(f"新闻处理完成: {len(result['news'])} 条")
        if market_data:
            result["market"] = self.normalize_market_data(market_data)
            logger.info(f"行情处理完成: {len(result['market'].get('stocks', []))} 只标的")
        if sentiment_data:
            all_sentiment = []
            for source_items in sentiment_data.get("sources", {}).values():
                all_sentiment.extend(source_items)
            all_sentiment = self.deduplicate(all_sentiment)
            result["sentiment"] = all_sentiment
            logger.info(f"舆情处理完成: {len(result['sentiment'])} 条")
        return result
