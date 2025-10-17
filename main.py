"""
Reddit社区数据分析系统 - 主程序
流程：获取 -> 清洗 -> 分析 -> 评分 -> 深度抓取 -> 综合报告
"""

import logging
from datetime import datetime
from fetcher import RedditDataFetcher
from cleaner import DataCleaner
from analyzer import TrendAnalyzer
from scorer import QualityScorer
from reporter import ReportGenerator
from summarizer import PostSummarizer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 社区优先级配置
SUBREDDIT_CONFIG = {
    "high": [
        {"name": "LocalLLaMA", "limit": 50},
        {"name": "MachineLearning", "limit": 50},
        {"name": "singularity", "limit": 40},
        {"name": "OpenAI", "limit": 40},
    ],
    "medium": [
        {"name": "LangChain", "limit": 30},
        {"name": "artificial", "limit": 25},
    ]
}

def main():
    """主流程"""
    print("=" * 60)
    print("Reddit AI社区深度分析系统")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # 初始化各模块
    fetcher = RedditDataFetcher()
    cleaner = DataCleaner()
    summarizer = PostSummarizer()  # 初始化摘要生成器
    analyzer = TrendAnalyzer(summarizer=summarizer)  # 传入summarizer
    scorer = QualityScorer()
    reporter = ReportGenerator()
    
    # ========== 步骤1: 获取基础帖子信息 ==========
    logger.info("步骤1: 获取基础帖子信息")
    raw_posts = fetcher.fetch_posts_from_subreddits(SUBREDDIT_CONFIG)
    logger.info(f"共获取 {sum(len(posts) for posts in raw_posts.values())} 个帖子")
    
    # ========== 步骤2: 数据清洗（不去重）==========
    logger.info("步骤2: 数据清洗")
    cleaned_posts = cleaner.clean_posts(raw_posts, remove_duplicates=False)
    logger.info(f"清洗后保留 {sum(len(posts) for posts in cleaned_posts.values())} 个帖子")
    
    # ========== 步骤3: 制作三个时间维度的热门排行表 + 趋势分析 + 生成摘要 ==========
    logger.info("步骤3: 三个时间维度热门排行 + 趋势分析 + 摘要生成")
    timeframe_rankings = analyzer.create_hot_ranking(
        cleaned_posts, 
        top_k=20, 
        fetcher=fetcher,  # 传入fetcher用于获取评论
        generate_summaries=True  # 启用摘要生成
    )
    trend_analysis = analyzer.analyze_trends(cleaned_posts)
    logger.info(f"生成热门排行榜: hot-{len(timeframe_rankings['hot'])}, week-{len(timeframe_rankings['week'])}, month-{len(timeframe_rankings['month'])}")
    logger.info("摘要生成已完成")
    
    # ========== 步骤4: 去重（保留hot最高）==========
    logger.info("步骤4: 数据去重")
    unique_posts = cleaner.deduplicate_posts(cleaned_posts, keep='highest_hot')
    logger.info(f"去重后保留 {len(unique_posts)} 个唯一帖子")
    
    # ========== 步骤5: 质量评分排序 ==========
    logger.info("步骤5: 质量评分")
    scored_posts = scorer.score_posts(unique_posts, trend_analysis)
    quality_ranking = scorer.get_top_quality_posts(scored_posts, top_k=5)
    logger.info(f"高质量帖子TOP5已选出")
    
    # 为高质量帖子生成摘要（如果还没有）
    logger.info("为高质量帖子生成摘要...")
    quality_ranking = summarizer.generate_summaries_for_posts(
        quality_ranking, 
        fetcher,
        max_workers=3,  # TOP5数量少，减少并发
        max_comments=5
    )
    logger.info("高质量帖子摘要生成完成")
    
    # ========== 步骤6: 深度信息获取（TOP5）==========
    logger.info("步骤6: 深度信息获取")
    top5_ids = [post['id'] for post in quality_ranking]
    detailed_posts = fetcher.fetch_detailed_posts(top5_ids, comment_depth=2)
    logger.info(f"成功获取 {len(detailed_posts)} 个帖子的详细信息")
    
    # ========== 步骤7: 大模型综合分析 ==========
    logger.info("步骤7: 大模型综合分析")
    
    # 数据完整性验证
    logger.info(f"\n{'='*60}")
    logger.info("📊 数据完整性验证...")
    logger.info(f"  hot排行榜: {len(timeframe_rankings['hot'])} 个帖子")
    logger.info(f"  week排行榜: {len(timeframe_rankings['week'])} 个帖子")
    logger.info(f"  month排行榜: {len(timeframe_rankings['month'])} 个帖子")
    logger.info(f"  详细帖子: {len(detailed_posts)} 个帖子")
    
    # 检查None值
    none_in_hot = []
    for i, post in enumerate(timeframe_rankings['hot']):
        if post is None:
            none_in_hot.append(i)
            logger.error(f"❌ hot排行榜[{i}] 是 None")
    
    none_in_week = []
    for i, post in enumerate(timeframe_rankings['week']):
        if post is None:
            none_in_week.append(i)
            logger.error(f"❌ week排行榜[{i}] 是 None")
    
    none_in_month = []
    for i, post in enumerate(timeframe_rankings['month']):
        if post is None:
            none_in_month.append(i)
            logger.error(f"❌ month排行榜[{i}] 是 None")
    
    none_in_detailed = []
    for i, post in enumerate(detailed_posts):
        if post is None:
            none_in_detailed.append(i)
            logger.error(f"❌ detailed_posts[{i}] 是 None")
    
    total_none = len(none_in_hot) + len(none_in_week) + len(none_in_month) + len(none_in_detailed)
    
    if total_none > 0:
        logger.error(f"\n⚠️ 发现 {total_none} 个None值！")
        if none_in_hot:
            logger.error(f"  hot排行榜中有 {len(none_in_hot)} 个None，位置: {none_in_hot}")
        if none_in_week:
            logger.error(f"  week排行榜中有 {len(none_in_week)} 个None，位置: {none_in_week}")
        if none_in_month:
            logger.error(f"  month排行榜中有 {len(none_in_month)} 个None，位置: {none_in_month}")
        if none_in_detailed:
            logger.error(f"  detailed_posts中有 {len(none_in_detailed)} 个None，位置: {none_in_detailed}")
    else:
        logger.info("✅ 数据验证通过，没有None值")
    
    logger.info(f"{'='*60}\n")

    # 创建一个合并的排行榜，包含所有三个时间维度的帖子
    combined_ranking = (
        timeframe_rankings['hot'] + 
        timeframe_rankings['week'] + 
        timeframe_rankings['month']
    )
    
    logger.info(f"合并后排行榜总数: {len(combined_ranking)} 个帖子")

    llm_analysis = reporter.analyze_with_llm(
        hot_ranking=combined_ranking,  # 传递合并后的排行榜
        trend_analysis=trend_analysis,
        detailed_posts=detailed_posts
    )
    
    # ========== 步骤8: 生成最终报告 ==========
    logger.info("步骤8: 生成最终报告")
    report_data = {
        'timeframe_rankings': timeframe_rankings,  # 这里改为timeframe_rankings
        'quality_ranking': quality_ranking,
        'trend_analysis': trend_analysis,
        'detailed_posts': detailed_posts,
        'llm_analysis': llm_analysis,
        'metadata': {
            'start_time': start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration': (datetime.now() - start_time).total_seconds()
        }
    }   
    
    report_files = reporter.generate_report(report_data)
    
    # ========== 完成 ==========
    duration = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 60)
    print("分析完成!")
    print(f"耗时: {duration:.1f}秒")
    print(f"Markdown报告: {report_files.get('markdown', 'N/A')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
