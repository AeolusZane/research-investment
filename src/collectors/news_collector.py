"""
财经新闻采集器 - 东方财富、财联社
"""
import json, re
from datetime import datetime
from pathlib import Path
import requests
from loguru import logger

class NewsCollector:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def __init__(self, config_path="config/watchlist.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def collect_eastmoney_news(self, max_items=20):
        url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
        items = []
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            resp.encoding = "utf-8"
            match = re.search(r'ajaxResult\((.*)\)', resp.text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                for item in data.get("LivesList", [])[:max_items]:
                    items.append({
                        "title": item.get("title", ""),
                        "summary": item.get("digest", ""),
                        "url": item.get("url", ""),
                        "source": "eastmoney",
                        "published_at": item.get("showtime", ""),
                        "collected_at": datetime.now().isoformat(),
                    })
            logger.info(f"东方财富: 采集到 {len(items)} 条新闻")
        except Exception as e:
            logger.warning(f"东方财富采集失败: {e}")
        return items

    def collect_cls_telegraph(self, max_items=20):
        url = "https://www.cls.cn/nodeapi/updateTelegraph"
        params = {"app": "CailianpressWeb", "os": "web", "sv": "8.4.6", "rn": max_items}
        items = []
        try:
            resp = requests.get(url, params=params, headers=self.HEADERS, timeout=10)
            data = resp.json()
            for item in data.get("data", {}).get("roll_data", [])[:max_items]:
                items.append({
                    "title": item.get("title", "") or item.get("content", "")[:50],
                    "summary": item.get("content", ""),
                    "url": f"https://www.cls.cn/detail/{item.get('id', '')}",
                    "source": "cls",
                    "published_at": datetime.fromtimestamp(item.get("ctime", 0)).isoformat() if item.get("ctime") else "",
                    "collected_at": datetime.now().isoformat(),
                })
            logger.info(f"财联社: 采集到 {len(items)} 条电报")
        except Exception as e:
            logger.warning(f"财联社采集失败: {e}")
        return items

    def collect_all(self, max_items=20):
        result = {"collected_at": datetime.now().isoformat(), "sources": {}}
        eastmoney = self.collect_eastmoney_news(max_items)
        if eastmoney:
            result["sources"]["eastmoney"] = eastmoney
        cls_news = self.collect_cls_telegraph(max_items)
        if cls_news:
            result["sources"]["cls"] = cls_news
        result["total_items"] = sum(len(v) for v in result["sources"].values())
        logger.info(f"新闻采集完成: 共 {result['total_items']} 条")
        return result

    def save(self, data, output_dir="data"):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filename = output_path / f"news_{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"新闻数据已保存: {filename}")
        return str(filename)
