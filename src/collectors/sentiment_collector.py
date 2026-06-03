"""
社区舆情采集器 - 雪球、东方财富股吧
"""
import json, re
from datetime import datetime
from pathlib import Path
import requests
from loguru import logger

class SentimentCollector:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def __init__(self, config_path="config/watchlist.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def collect_xueqiu_hot(self, max_items=20):
        url = "https://xueqiu.com/statuses/hot/listV2.json"
        params = {"since_id": -1, "max_id": -1, "size": max_items}
        items = []
        try:
            session = requests.Session()
            session.get("https://xueqiu.com", headers=self.HEADERS, timeout=10)
            resp = session.get(url, params=params, headers=self.HEADERS, timeout=10)
            data = resp.json()
            for item in data.get("data", {}).get("items", [])[:max_items]:
                original = item.get("original_status", item)
                items.append({
                    "title": original.get("title", "") or original.get("description", "")[:80],
                    "summary": original.get("description", "")[:200],
                    "url": f"https://xueqiu.com{original.get('target', '')}",
                    "source": "xueqiu",
                    "user": original.get("user", {}).get("screen_name", ""),
                    "reply_count": original.get("reply_count", 0),
                    "retweet_count": original.get("retweet_count", 0),
                    "like_count": original.get("like_count", 0),
                    "collected_at": datetime.now().isoformat(),
                })
            logger.info(f"雪球: 采集到 {len(items)} 条热帖")
        except Exception as e:
            logger.warning(f"雪球采集失败: {e}")
        return items

    def collect_all(self, max_items=20):
        result = {"collected_at": datetime.now().isoformat(), "sources": {}}
        xueqiu = self.collect_xueqiu_hot(max_items)
        if xueqiu:
            result["sources"]["xueqiu"] = xueqiu
        result["total_items"] = sum(len(v) for v in result["sources"].values())
        logger.info(f"舆情采集完成: 共 {result['total_items']} 条")
        return result

    def save(self, data, output_dir="data"):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filename = output_path / f"sentiment_{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"舆情数据已保存: {filename}")
        return str(filename)
