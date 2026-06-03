"""
每日投研简报生成器
"""
import json
from datetime import datetime
from pathlib import Path
from loguru import logger

class DailyBriefingGenerator:
    def __init__(self, config_path="config/watchlist.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def _format_change(self, pct):
        if pct > 0: return f"🔴 +{pct:.2f}%"
        elif pct < 0: return f"🟢 {pct:.2f}%"
        return f"⚪ {pct:.2f}%"

    def _format_volume(self, volume):
        if volume >= 1e12: return f"{volume/1e12:.1f}万亿"
        elif volume >= 1e8: return f"{volume/1e8:.1f}亿"
        elif volume >= 1e4: return f"{volume/1e4:.1f}万"
        return str(int(volume))

    def generate(self, processed_data, sentiment_summary=None):
        now = datetime.now()
        weekday_map = {0:"一",1:"二",2:"三",3:"四",4:"五",5:"六",6:"日"}
        lines = [
            f"# 每日投研简报",
            f"**{now.strftime('%Y年%m月%d日')} 星期{weekday_map[now.weekday()]}** | 自动生成于 {now.strftime('%H:%M')}",
            "", "---", ""
        ]

        # 行情概览
        market = processed_data.get("market", {})
        stocks = market.get("stocks", [])
        if stocks:
            lines += ["## 持仓行情", "", "| 标的 | 市场 | 现价 | 涨跌幅 | 成交额 |", "|------|------|------|--------|--------|"]
            for s in sorted(stocks, key=lambda x: x.get("change_pct", 0), reverse=True):
                change = self._format_change(s.get("change_pct", 0))
                vol = self._format_volume(s.get("volume", 0)) if s.get("volume") else "N/A"
                lines.append(f"| {s['name']} ({s['code']}) | {s['market']} | {s['price']} | {change} | {vol} |")
            lines.append("")

        # 异动提醒
        threshold = self.config.get("alert_rules", {}).get("price_change_threshold", 0.05)
        anomalies = [s for s in stocks if abs(s.get("change_pct", 0)) >= threshold * 100]
        if anomalies:
            lines += ["## ⚠️ 异动提醒", ""]
            for a in anomalies:
                d = "大涨" if a["change_pct"] > 0 else "大跌"
                lines.append(f"- **{a['name']}**({a['code']}）{d} {abs(a['change_pct']):.2f}%，现价 {a['price']}")
            lines.append("")

        # 宏观指标
        macro = market.get("macro", [])
        if macro:
            lines += ["## 宏观指标", ""]
            for m in macro:
                lines.append(f"- **{m['indicator']}**: {m.get('value', 'N/A')} ({m.get('period', '')})")
            lines.append("")

        # 市场情绪
        if sentiment_summary:
            lines += ["## 市场情绪", ""]
            idx = sentiment_summary.get("sentiment_index", 0)
            dist = sentiment_summary.get("distribution", {})
            mood = "偏乐观 📈" if idx > 20 else ("偏悲观 📉" if idx < -20 else "中性 ➡️")
            lines.append(f"**情绪指数**: {idx} ({mood})")
            lines.append(f"- 正面 {dist.get('positive',0)} 条 | 中性 {dist.get('neutral',0)} 条 | 负面 {dist.get('negative',0)} 条")
            top_kw = sentiment_summary.get("top_keywords", [])
            if top_kw:
                lines.append(f"- 热词: {'、'.join([f'{kw}({c})' for kw,c in top_kw[:10]])}")
            lines.append("")

        # 要闻速递
        news = processed_data.get("news", [])
        if news:
            lines += ["## 要闻速递", ""]
            for i, n in enumerate(news[:15], 1):
                label = n.get("sentiment", {}).get("label", "") if "sentiment" in n else ""
                emoji = {"positive":"🟢","negative":"🔴","neutral":"⚪"}.get(label, "")
                lines.append(f"{i}. {emoji} **{n.get('title','')}** _{n.get('source','')}_")
            lines.append("")

        lines += ["---", "_本简报由投研数据系统自动生成，仅供参考，不构成投资建议。_"]
        return "\n".join(lines)

    def save(self, content, output_dir="reports"):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filename = output_path / f"daily_briefing_{datetime.now().strftime('%Y-%m-%d')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"每日简报已保存: {filename}")
        return str(filename)
