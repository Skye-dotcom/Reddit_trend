"""报告生成模块 - 负责调用大模型分析和生成最终报告"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI

from config import LLM_CONFIG, LLM_ANALYSIS_CONFIG


logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器"""

    def __init__(self) -> None:
        self.llm_client = OpenAI(
            api_key=LLM_CONFIG.get("api_key"),
            base_url=LLM_CONFIG.get("base_url"),
        )
        logger.info("报告生成器初始化完成")

    def generate_report(
        self,
        report_data: Dict[str, Any],
        output_dir: str = "reports",
    ) -> Dict[str, str]:
        """生成完整报告并按日期目录存储"""

        logger.info("开始生成最终报告...")

        now = datetime.now()
        base_dir = Path(output_dir)
        date_dir = base_dir / f"{now:%Y}" / f"{now:%m}" / f"{now:%d}"
        date_dir.mkdir(parents=True, exist_ok=True)

        timestamp = now.strftime("%Y%m%d_%H%M%S")
        md_path = date_dir / f"report_{timestamp}.md"

        markdown_content = self._create_markdown_report(report_data)
        md_path.write_text(markdown_content, encoding="utf-8")

        latest_path = base_dir / "latest_report.md"
        latest_path.write_text(markdown_content, encoding="utf-8")

        logger.info("报告已生成: %s", md_path)

        return {
            "markdown": str(md_path),
            "latest": str(latest_path),
        }

    def analyze_with_llm(
        self,
        hot_ranking: List[Dict],
        trend_analysis: Dict[str, Any],
        detailed_posts: List[Dict],
    ) -> str:
        """使用大模型进行综合分析（步骤8专用qwen3-max）"""
        
        logger.info("开始大模型综合分析（使用%s）...", LLM_ANALYSIS_CONFIG.get("model"))
        
        # 检查并记录None值
        original_hot_count = len(hot_ranking)
        original_detailed_count = len(detailed_posts)
        
        none_in_hot = [i for i, post in enumerate(hot_ranking) if post is None]
        none_in_detailed = [i for i, post in enumerate(detailed_posts) if post is None]
        
        if none_in_hot or none_in_detailed:
            logger.error(f"\n{'='*60}")
            logger.error(f"⚠️ 发现None值！")
            if none_in_hot:
                logger.error(f"hot_ranking中有 {len(none_in_hot)} 个None值，位置: {none_in_hot}")
                logger.error(f"hot_ranking总长度: {original_hot_count}")
            if none_in_detailed:
                logger.error(f"detailed_posts中有 {len(none_in_detailed)} 个None值，位置: {none_in_detailed}")
                logger.error(f"detailed_posts总长度: {original_detailed_count}")
            logger.error(f"{'='*60}\n")
        
        # 过滤None值并记录被过滤的帖子信息
        hot_ranking_filtered = []
        for i, post in enumerate(hot_ranking):
            if post is None:
                logger.error(f"❌ hot_ranking[{i}] 是 None，已被过滤")
            else:
                hot_ranking_filtered.append(post)
        
        detailed_posts_filtered = []
        for i, post in enumerate(detailed_posts):
            if post is None:
                logger.error(f"❌ detailed_posts[{i}] 是 None，已被过滤")
            else:
                detailed_posts_filtered.append(post)
        
        hot_ranking = hot_ranking_filtered
        detailed_posts = detailed_posts_filtered
        
        if not hot_ranking:
            logger.warning("热门帖子列表为空，无法进行分析")
            return "数据不足：没有可分析的热门帖子"
        
        prompt = self._build_llm_prompt(hot_ranking, trend_analysis, detailed_posts)
        
        # 如果LLM_ANALYSIS_CONFIG的api_key为空，使用LLM_CONFIG的api_key
        api_key = LLM_ANALYSIS_CONFIG.get("api_key") or LLM_CONFIG.get("api_key")
        
        try:
            # 为步骤8创建专用的客户端
            analysis_client = OpenAI(
                api_key=api_key,
                base_url=LLM_ANALYSIS_CONFIG.get("base_url"),
            )
            
            response = analysis_client.chat.completions.create(
                model=LLM_ANALYSIS_CONFIG.get("model"),
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的AI趋势分析师，擅长从Reddit数据中洞察技术趋势。",
                    },
                    {"role": "user", "content": prompt},
                ],
                stream=True,
                temperature=LLM_ANALYSIS_CONFIG.get("temperature", 0.3),
                max_tokens=LLM_ANALYSIS_CONFIG.get("max_tokens", 10000),
            )
            
            content = ""
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    content += delta
            
            logger.info("大模型分析完成")
            return content
        
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("大模型分析失败: %s", exc)
            return f"分析失败: {exc}"
    
    def _build_llm_prompt(self, hot_ranking: List[Dict],
                         trend_analysis: Dict[str, Any],
                         detailed_posts: List[Dict]) -> str:
        """构建大模型分析提示"""
        
        # 二次检查None值（理论上不应该有，因为analyze_with_llm已经过滤了）
        none_count_hot = sum(1 for post in hot_ranking if post is None)
        none_count_detailed = sum(1 for post in detailed_posts if post is None)
        
        if none_count_hot > 0 or none_count_detailed > 0:
            logger.error(f"⚠️ _build_llm_prompt中仍然发现None值！")
            logger.error(f"   hot_ranking: {none_count_hot}个None / {len(hot_ranking)}个总数")
            logger.error(f"   detailed_posts: {none_count_detailed}个None / {len(detailed_posts)}个总数")
            
            # 记录None值的具体位置
            for i, post in enumerate(hot_ranking):
                if post is None:
                    logger.error(f"   hot_ranking[{i}] = None")
            for i, post in enumerate(detailed_posts):
                if post is None:
                    logger.error(f"   detailed_posts[{i}] = None")
        
        # 过滤掉None值（防御性编程）
        hot_ranking = [post for post in hot_ranking if post is not None]
        detailed_posts = [post for post in detailed_posts if post is not None]
        
        # 提取热门帖子摘要
        hot_summary = []
        for i, post in enumerate(hot_ranking[:10], 1):
            # 优先使用摘要，如果没有或生成失败则使用标题
            if post.get('summary'):
                summary_text = post['summary'][:80]
            else:
                summary_text = post.get('title', '')[:80]
            hot_summary.append(f"{i}. [{summary_text}] - r/{post['subreddit']} - {post['score']}分 - {post['num_comments']}评论")
        
        # 提取TOP5详细内容
        detailed_summary = []
        for i, post in enumerate(detailed_posts, 1):
            content_preview = post.get('content', '')[:500] if post.get('content') else "无内容"
            detailed_summary.append(f"""
### 高质量帖子 {i}: {post['title']}
- 社区: r/{post['subreddit']}
- 分数: {post['score']} | 评论: {post['num_comments']}
- 质量评分: {post.get('quality_score', 'N/A')}
- 内容摘要: {content_preview}
- 评论数: {len(post.get('comments', []))}
""")
        
        prompt = f"""
当前日期: {datetime.now().strftime("%Y-%m-%d")}

# Reddit AI社区趋势分析任务

你需要基于以下Reddit社区数据，进行深入的趋势分析并生成专业报告。

## 数据概览

### 热门帖子TOP10
{chr(10).join(hot_summary)}

### 趋势关键词
{json.dumps(trend_analysis.get('keyword_trends', {}), ensure_ascii=False, indent=2)}

### 社区表现
{json.dumps(trend_analysis.get('subreddit_trends', {}), ensure_ascii=False, indent=2)}

### 活跃作者
{json.dumps(trend_analysis.get('author_trends', {}), ensure_ascii=False, indent=2)}

### 互动趋势
{json.dumps(trend_analysis.get('engagement_trends', {}), ensure_ascii=False, indent=2)}

## 高质量帖子详细内容

{chr(10).join(detailed_summary)}

---

## 分析要求

请基于以上数据，撰写一份专业的趋势分析报告，包含以下部分：

### 1. 核心热点话题识别（3-5个）
- 每个热点的详细描述
- 相关帖子统计和趋势
- 社区讨论热度
- 技术或应用层面的重要性

### 2. 新兴趋势发现（2-3个）
- 新出现的技术趋势或讨论主题
- 增长潜力分析
- 可能的未来发展

### 3. 技术深度洞察
- 基于高质量帖子的深度分析
- 技术发展的瓶颈和机遇
- 对未来发展的预测

### 4. 社区生态观察
- 不同社区的特点和专长
- 跨社区的共同关注点
- 社区间的差异和特色

### 5. 行动建议
- 对开发者/研究者的建议
- 值得关注的方向
- 潜在的机会点

## 输出格式

请使用清晰的Markdown格式，用具体的数据和实例支持你的分析。确保分析深入、数据驱动，并提供可操作的洞察。
"""
        
        return prompt
    
    def _create_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """创建Markdown报告"""
    
        metadata = report_data.get('metadata', {})
        timeframe_rankings = report_data.get('timeframe_rankings', {})
        quality_ranking = report_data.get('quality_ranking', [])
        trend_analysis = report_data.get('trend_analysis', {})
        llm_analysis = report_data.get('llm_analysis', '')
        
        # 过滤None值
        timeframe_rankings = {
            key: [post for post in posts if post is not None]
            for key, posts in timeframe_rankings.items()
        }
        quality_ranking = [post for post in quality_ranking if post is not None]
    
        report = f"""# Reddit AI社区深度分析报告

    **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
    **数据收集时间**: {metadata.get('start_time', 'N/A')}  
    **分析耗时**: {metadata.get('duration', 0):.1f}秒

---

## 📊 数据概览

- **当天热门帖子**: {len(timeframe_rankings.get('hot', []))} 条
- **本周热门帖子**: {len(timeframe_rankings.get('week', []))} 条  
- **本月热门帖子**: {len(timeframe_rankings.get('month', []))} 条
- **高质量深度分析**: {len(quality_ranking)} 条
- **覆盖社区**: {trend_analysis.get('subreddit_trends', {}).get('total_subreddits', 0)} 个
- **活跃作者**: {trend_analysis.get('author_trends', {}).get('active_authors', 0)} 位

---

## 🔥 当天热门帖子排行榜 (实时热度)

| 排名 | 标题 | 社区 | 分数 | 评论数 |
|------|------|------|------|--------|
"""
    
        # 添加当天热门排行
        for i, post in enumerate(timeframe_rankings.get('hot', [])[:20], 1):
            post_url = post.get('permalink', f"https://reddit.com/comments/{post['id']}")
            title = self._escape_markdown(post['title'][:60])
            if len(post['title']) > 60:
                title += "..."
        
            report += f"| {i} | [{title}]({post_url}) | "
            report += f"r/{post['subreddit']} | {post['score']} | "
            report += f"{post['num_comments']} |\n"
            # 添加摘要或错误信息
            if post.get('summary_error'):
                error_msg = f"⚠️ 摘要生成错误：{post.get('summary_error')}"
                error_escaped = self._escape_markdown(error_msg)
                report += f"| | {error_escaped} | | | |\n"
            elif post.get('summary'):
                summary_escaped = self._escape_markdown(post['summary'])
                report += f"| | {summary_escaped} | | | |\n"
    
        report += "\n---\n\n## 📈 本周热门帖子排行榜 (按分数排序)\n\n"
        report += "| 排名 | 标题 | 社区 | 分数 | 评论数 |\n"
        report += "|------|------|------|------|--------|\n"
    
        for i, post in enumerate(timeframe_rankings.get('week', [])[:20], 1):
            post_url = post.get('permalink', f"https://reddit.com/comments/{post['id']}")
            title = self._escape_markdown(post['title'][:60])
            if len(post['title']) > 60:
                title += "..."
        
            report += f"| {i} | [{title}]({post_url}) | "
            report += f"r/{post['subreddit']} | {post['score']} | "
            report += f"{post['num_comments']} |\n"
            # 添加摘要或错误信息
            if post.get('summary_error'):
                error_msg = f"⚠️ 摘要生成错误：{post.get('summary_error')}"
                error_escaped = self._escape_markdown(error_msg)
                report += f"| | {error_escaped} | | | |\n"
            elif post.get('summary'):
                summary_escaped = self._escape_markdown(post['summary'])
                report += f"| | {summary_escaped} | | | |\n"
    
        report += "\n---\n\n## 🗓️ 本月热门帖子排行榜 (按分数排序)\n\n"
        report += "| 排名 | 标题 | 社区 | 分数 | 评论数 |\n"
        report += "|------|------|------|------|--------|\n"
    
        for i, post in enumerate(timeframe_rankings.get('month', [])[:20], 1):
            post_url = post.get('permalink', f"https://reddit.com/comments/{post['id']}")
            title = self._escape_markdown(post['title'][:60])
            if len(post['title']) > 60:
                title += "..."
        
            report += f"| {i} | [{title}]({post_url}) | "
            report += f"r/{post['subreddit']} | {post['score']} | "
            report += f"{post['num_comments']} |\n"
            # 添加摘要或错误信息
            if post.get('summary_error'):
                error_msg = f"⚠️ 摘要生成错误：{post.get('summary_error')}"
                error_escaped = self._escape_markdown(error_msg)
                report += f"| | {error_escaped} | | | |\n"
            elif post.get('summary'):
                summary_escaped = self._escape_markdown(post['summary'])
                report += f"| | {summary_escaped} | | | |\n"

        # ... 其余报告内容保持不变
        
        # 添加高质量排行
        report += "\n---\n\n## ⭐ 高质量帖子深度分析\n\n"
        report += "| 排名 | 标题 | 社区 | 质量评分 | 分数 | 评论数 |\n"
        report += "|------|------|------|----------|------|--------|\n"
        
        for i, post in enumerate(quality_ranking, 1):
            post_url = post.get('permalink', f"https://reddit.com/comments/{post['id']}")
            title = self._escape_markdown(post['title'][:50])
            if len(post['title']) > 50:
                title += "..."
            
            report += f"| {i} | [{title}]({post_url}) | "
            report += f"r/{post['subreddit']} | {post.get('quality_score', 0):.2f} | "
            report += f"{post['score']} | {post['num_comments']} |\n"
            # 添加摘要或错误信息
            if post.get('summary_error'):
                error_msg = f"⚠️ 摘要生成错误：{post.get('summary_error')}"
                error_escaped = self._escape_markdown(error_msg)
                report += f"| | {error_escaped} | | | | |\n"
            elif post.get('summary'):
                summary_escaped = self._escape_markdown(post['summary'])
                report += f"| | {summary_escaped} | | | | |\n"
        
        # 添加趋势关键词
        keyword_freq = trend_analysis.get('keyword_trends', {}).get('keyword_frequency', {})
        trending_kw = trend_analysis.get('keyword_trends', {}).get('trending_keywords', [])
        
        report += "\n---\n\n## 🔍 趋势关键词\n\n"
        report += "| 关键词 | 出现频率 | 趋势级别 |\n"
        report += "|--------|----------|----------|\n"
        
        for keyword, freq in list(keyword_freq.items())[:15]:
            trend_label = "🔥 热门" if keyword in trending_kw[:5] else "📈 上升" if keyword in trending_kw else "➡️ 一般"
            report += f"| {keyword} | {freq} | {trend_label} |\n"
        
        # 添加大模型分析
        report += "\n---\n\n# 🤖 AI智能深度分析\n\n"
        report += llm_analysis
        
        # 添加附录
        report += "\n\n---\n\n## 📌 附录\n\n"
        report += "### 社区表现统计\n\n"
        
        subreddit_perf = trend_analysis.get('subreddit_trends', {}).get('subreddit_performance', {})
        for sub, stats in list(subreddit_perf.items())[:10]:
            report += f"- **r/{sub}**: {stats['posts']}个帖子, 平均分数 {stats['avg_score']:.1f}\n"
        
        report += f"\n\n---\n\n*报告由Reddit智能分析系统生成*  \n*数据来源: Reddit API*"
        
        return report
    
    def _escape_markdown(self, text: str) -> str:
        """转义Markdown特殊字符"""
        if not text:
            return ""
        
        escape_chars = ['|', '[', ']', '(', ')', '*', '_', '`']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        return text
