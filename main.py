"""
投研数据系统 - 主入口

用法:
    python main.py                  # 运行完整每日简报流程
    python main.py --collect-only   # 仅采集数据
    python main.py --report-only    # 仅生成报告（使用已有数据）
    python main.py --source news    # 仅采集新闻
    python main.py --source market  # 仅采集行情
    python main.py --source sentiment  # 仅采集舆情
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

def collect_news(config_path, output_dir):
    from src.collectors.news_collector import NewsCollector
    c = NewsCollector(config_path); data = c.collect_all(); c.save(data, output_dir); return data

def collect_market(config_path, output_dir):
    from src.collectors.market_data_collector import MarketDataCollector
    c = MarketDataCollector(config_path); data = c.collect_all(); c.save(data, output_dir); return data

def collect_sentiment(config_path, output_dir):
    from src.collectors.sentiment_collector import SentimentCollector
    c = SentimentCollector(config_path); data = c.collect_all(); c.save(data, output_dir); return data

def process_data(news_data, market_data, sentiment_data):
    from src.processors.data_cleaner import DataCleaner
    from src.analyzers.sentiment_analyzer import SentimentAnalyzer
    cleaner = DataCleaner()
    processed = cleaner.process_all(news_data, market_data, sentiment_data)
    analyzer = SentimentAnalyzer()
    all_items = processed.get("news", []) + processed.get("sentiment", [])
    sentiment_summary = analyzer.analyze_batch(all_items)
    anomalies = analyzer.detect_anomalies(sentiment_summary)
    if anomalies:
        logger.warning(f"检测到 {len(anomalies)} 个情绪异常")
        for a in anomalies:
            logger.warning(f"  {a['description']}")
    return processed, sentiment_summary

def generate_report(processed_data, sentiment_summary, config_path, output_dir):
    from src.reporters.daily_briefing import DailyBriefingGenerator
    gen = DailyBriefingGenerator(config_path)
    content = gen.generate(processed_data, sentiment_summary)
    filepath = gen.save(content, output_dir)
    print("\n" + "=" * 60)
    print(content)
    print("=" * 60 + "\n")
    return filepath

def load_latest_data(data_dir):
    date_str = datetime.now().strftime("%Y-%m-%d")
    dp = Path(data_dir)
    news_data = market_data = sentiment_data = None
    for name, var in [("news", "news_data"), ("market", "market_data"), ("sentiment", "sentiment_data")]:
        f = dp / f"{name}_{date_str}.json"
        if f.exists():
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            logger.info(f"加载{name}数据: {f}")
            if name == "news": news_data = data
            elif name == "market": market_data = data
            else: sentiment_data = data
    return news_data, market_data, sentiment_data

def main():
    parser = argparse.ArgumentParser(description="投研数据系统")
    parser.add_argument("--config", default="config/watchlist.json")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--source", choices=["news", "market", "sentiment"])
    args = parser.parse_args()

    logger.info("投研数据系统启动")
    news_data = market_data = sentiment_data = None

    if not args.report_only:
        logger.info("开始数据采集...")
        if args.source == "news": news_data = collect_news(args.config, args.data_dir)
        elif args.source == "market": market_data = collect_market(args.config, args.data_dir)
        elif args.source == "sentiment": sentiment_data = collect_sentiment(args.config, args.data_dir)
        else:
            news_data = collect_news(args.config, args.data_dir)
            market_data = collect_market(args.config, args.data_dir)
            sentiment_data = collect_sentiment(args.config, args.data_dir)
        if args.collect_only:
            logger.info("数据采集完成（仅采集模式）"); return

    if args.report_only:
        news_data, market_data, sentiment_data = load_latest_data(args.data_dir)
        if not any([news_data, market_data, sentiment_data]):
            logger.error("未找到今日数据"); sys.exit(1)

    logger.info("开始数据处理...")
    processed, sentiment_summary = process_data(news_data, market_data, sentiment_data)
    logger.info("生成每日简报...")
    filepath = generate_report(processed, sentiment_summary, args.config, args.reports_dir)
    logger.info(f"完成！简报已保存: {filepath}")

if __name__ == "__main__":
    main()
