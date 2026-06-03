"""
行情数据采集器 - AKShare(A股) + yfinance(美股/港股)
"""
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from loguru import logger

class MarketDataCollector:
    def __init__(self, config_path="config/watchlist.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.watchlist = self.config.get("watchlist", {})

    def collect_a_shares(self):
        try:
            import akshare as ak
        except ImportError:
            logger.warning("akshare 未安装，跳过 A 股数据采集")
            return []
        items = []
        for code, name in self.watchlist.get("A股", {}).items():
            try:
                pure_code = code.split(".")[0]
                df = ak.stock_zh_a_spot_em()
                row = df[df["代码"] == pure_code]
                if not row.empty:
                    row = row.iloc[0]
                    items.append({
                        "code": code, "name": name, "market": "A股",
                        "price": float(row.get("最新价", 0)),
                        "change_pct": float(row.get("涨跌幅", 0)),
                        "volume": float(row.get("成交量", 0)),
                        "turnover": float(row.get("成交额", 0)),
                        "high": float(row.get("最高", 0)),
                        "low": float(row.get("最低", 0)),
                        "open": float(row.get("今开", 0)),
                        "prev_close": float(row.get("昨收", 0)),
                        "pe_ratio": float(row.get("市盈率-动态", 0)) if pd.notna(row.get("市盈率-动态")) else None,
                        "pb_ratio": float(row.get("市净率", 0)) if pd.notna(row.get("市净率")) else None,
                        "market_cap": float(row.get("总市值", 0)),
                        "collected_at": datetime.now().isoformat(),
                    })
                    logger.info(f"A股 {name}({code}): {row.get('最新价', 'N/A')}")
            except Exception as e:
                logger.warning(f"A股 {name}({code}) 采集失败: {e}")
        return items

    def collect_us_hk_shares(self):
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance 未安装，跳过美股/港股数据采集")
            return []
        items = []
        for market_key, market_name in [("美股", "美股"), ("港股", "港股")]:
            for code, name in self.watchlist.get(market_key, {}).items():
                try:
                    ticker = yf.Ticker(code)
                    hist = ticker.history(period="5d")
                    if not hist.empty:
                        latest = hist.iloc[-1]
                        prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1]
                        change_pct = ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100
                        items.append({
                            "code": code, "name": name, "market": market_name,
                            "price": round(float(latest["Close"]), 2),
                            "change_pct": round(change_pct, 2),
                            "volume": int(latest["Volume"]),
                            "high": round(float(latest["High"]), 2),
                            "low": round(float(latest["Low"]), 2),
                            "collected_at": datetime.now().isoformat(),
                        })
                        logger.info(f"{market_name} {name}({code}): {latest['Close']:.2f}")
                except Exception as e:
                    logger.warning(f"{market_name} {name}({code}) 采集失败: {e}")
        return items

    def collect_macro_indicators(self):
        items = []
        try:
            import akshare as ak
            try:
                cpi_df = ak.macro_china_cpi()
                if not cpi_df.empty:
                    latest = cpi_df.iloc[-1]
                    items.append({"indicator": "CPI", "value": float(latest.iloc[-1]) if len(latest) > 1 else None,
                                  "period": str(latest.iloc[0]), "source": "akshare", "collected_at": datetime.now().isoformat()})
            except Exception as e:
                logger.warning(f"CPI 采集失败: {e}")
            try:
                pmi_df = ak.macro_china_pmi()
                if not pmi_df.empty:
                    latest = pmi_df.iloc[-1]
                    items.append({"indicator": "PMI", "value": float(latest.iloc[-1]) if len(latest) > 1 else None,
                                  "period": str(latest.iloc[0]), "source": "akshare", "collected_at": datetime.now().isoformat()})
            except Exception as e:
                logger.warning(f"PMI 采集失败: {e}")
        except ImportError:
            logger.warning("akshare 未安装，跳过宏观数据采集")
        return items

    def collect_all(self):
        result = {
            "collected_at": datetime.now().isoformat(),
            "a_shares": self.collect_a_shares(),
            "us_hk_shares": self.collect_us_hk_shares(),
            "macro": self.collect_macro_indicators(),
        }
        result["total_items"] = len(result["a_shares"]) + len(result["us_hk_shares"]) + len(result["macro"])
        logger.info(f"行情数据采集完成: 共 {result['total_items']} 条")
        return result

    def save(self, data, output_dir="data"):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filename = output_path / f"market_{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"行情数据已保存: {filename}")
        return str(filename)
