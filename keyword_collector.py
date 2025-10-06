"""
基于关键词搜索的Reddit数据收集器
支持全站搜索、指定社区搜索、多关键词组合搜索
"""

import os
import json
import praw
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from collections import defaultdict
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KeywordRedditCollector:
    """基于关键词搜索的Reddit数据收集器"""
    
    def __init__(self):
        """初始化收集器"""
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "python:keyword-reddit-collector:1.0 (by /u/developer)")
        )
        
        # 验证连接
        try:
            self.reddit.user.me()
            logger.info("Reddit API连接成功（已认证用户）")
        except:
            logger.info("Reddit API连接成功（只读模式）")
        
        logger.info("关键词Reddit数据收集器初始化完成")
    
    def search_by_keywords(self, 
                          keywords: Union[str, List[str]],
                          subreddits: Optional[List[str]] = None,
                          sort: str = "top",
                          time_filter: str = "week", 
                          limit: int = 100,
                          min_score: int = 5,
                          min_comments: int = 3) -> List[Dict[str, Any]]:
        """
        根据关键词搜索帖子
        
        Args:
            keywords: 关键词字符串或关键词列表
            subreddits: 要搜索的subreddit列表，None表示全站搜索
            sort: 排序方式 (relevance, hot, top, new, comments)
            time_filter: 时间过滤器 (hour, day, week, month, year, all)
            limit: 最大结果数量
            min_score: 最小分数过滤
            min_comments: 最小评论数过滤
            
        Returns:
            搜索结果列表
        """
        # 处理关键词
        if isinstance(keywords, list):
            query = " ".join(keywords)
        else:
            query = keywords
        
        logger.info(f"开始搜索关键词: '{query}', 限制: {limit}, 排序: {sort}, 时间: {time_filter}")
        
        # 确定搜索范围
        if subreddits:
            # 在指定社区中搜索
            subreddit_str = "+".join(subreddits)
            search_subreddit = self.reddit.subreddit(subreddit_str)
            scope_info = f"社区: {subreddit_str}"
        else:
            # 全站搜索
            search_subreddit = self.reddit.subreddit("all")
            scope_info = "全站"
        
        logger.info(f"搜索范围: {scope_info}")
        
        try:
            # 执行搜索
            search_results = search_subreddit.search(
                query=query,
                sort=sort,
                time_filter=time_filter,
                limit=limit
            )
            
            # 提取并过滤结果
            posts = []
            for post in search_results:
                post_data = self._extract_post_data(post)
                
                # 应用过滤条件
                if (post_data['score'] >= min_score and 
                    post_data['num_comments'] >= min_comments):
                    posts.append(post_data)
            
            logger.info(f"搜索完成: 找到 {len(posts)} 个符合条件的帖子")
            
            # 按分数排序
            posts.sort(key=lambda x: x['score'], reverse=True)
            
            return posts
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    def multi_keyword_search(self, 
                           keyword_groups: Dict[str, List[str]],
                           subreddits: Optional[List[str]] = None,
                           **search_params) -> Dict[str, List[Dict[str, Any]]]:
        """
        多关键词组合搜索
        
        Args:
            keyword_groups: 关键词组字典，格式: {"组名": ["关键词1", "关键词2"]}
            subreddits: 搜索的subreddit列表
            **search_params: 其他搜索参数
            
        Returns:
            按关键词组分类的搜索结果
        """
        logger.info(f"开始多关键词组合搜索: {list(keyword_groups.keys())}")
        
        results = {}
        
        for group_name, keywords in keyword_groups.items():
            logger.info(f"搜索关键词组: {group_name} - {keywords}")
            
            # 对每组关键词进行搜索
            group_results = self.search_by_keywords(
                keywords=keywords,
                subreddits=subreddits,
                **search_params
            )
            
            results[group_name] = group_results
            
            # API限制控制
            time.sleep(1)
        
        return results
    
    def trending_topics_search(self, 
                             ai_categories: Optional[Dict[str, List[str]]] = None,
                             subreddits: Optional[List[str]] = None,
                             limit_per_category: int = 50) -> Dict[str, Any]:
        """
        AI热门话题搜索
        
        Args:
            ai_categories: AI类别关键词字典
            subreddits: 搜索的subreddit列表  
            limit_per_category: 每个类别的结果限制
            
        Returns:
            按类别分组的搜索结果
        """
        # 默认AI类别关键词
        if ai_categories is None:
            ai_categories = {
                "大语言模型": ["LLM", "GPT", "transformer", "language model", "ChatGPT", "Claude"],
                "机器学习": ["machine learning", "deep learning", "neural network", "ML", "DL"],
                "AI工具": ["AI tools", "automation", "AI agent", "prompt engineering"],
                "模型训练": ["training", "fine-tuning", "dataset", "model training", "LoRA", "RLHF"],
                "AI应用": ["AI application", "use case", "implementation", "real world"],
                "技术讨论": ["algorithm", "architecture", "optimization", "performance"],
                "开源项目": ["open source", "GitHub", "repository", "code", "implementation"],
                "研究论文": ["paper", "research", "arxiv", "study", "experiment"]
            }
        
        logger.info(f"开始AI热门话题搜索: {list(ai_categories.keys())}")
        
        # 默认搜索的AI相关subreddit
        if subreddits is None:
            subreddits = [
                "MachineLearning", "LocalLLaMA", "OpenAI", "artificial", 
                "singularity", "LangChain", "ChatGPT", "deeplearning"
            ]
        
        results = {
            'search_metadata': {
                'timestamp': datetime.now().isoformat(),
                'categories_searched': list(ai_categories.keys()),
                'subreddits_searched': subreddits,
                'limit_per_category': limit_per_category
            },
            'category_results': {},
            'summary': {}
        }
        
        # 按类别搜索
        all_posts = []
        
        for category, keywords in ai_categories.items():
            category_posts = self.search_by_keywords(
                keywords=keywords,
                subreddits=subreddits,
                sort="top",
                time_filter="week",
                limit=limit_per_category,
                min_score=10,
                min_comments=5
            )
            
            results['category_results'][category] = category_posts
            all_posts.extend(category_posts)
            
            logger.info(f"类别 '{category}' 找到 {len(category_posts)} 个帖子")
            
            # API限制控制
            time.sleep(1)
        
        # 生成摘要统计
        results['summary'] = self._generate_search_summary(results['category_results'])
        
        logger.info(f"AI热门话题搜索完成，总计 {len(all_posts)} 个帖子")
        
        return results
    
    def advanced_search(self, 
                       query: str,
                       subreddits: Optional[List[str]] = None,
                       exclude_subreddits: Optional[List[str]] = None,
                       author: Optional[str] = None,
                       site: Optional[str] = None,
                       title_only: bool = False,
                       **search_params) -> List[Dict[str, Any]]:
        """
        高级搜索功能
        
        Args:
            query: 基础查询字符串
            subreddits: 包含的subreddit列表
            exclude_subreddits: 排除的subreddit列表
            author: 指定作者
            site: 指定网站域名
            title_only: 是否只搜索标题
            **search_params: 其他搜索参数
            
        Returns:
            搜索结果列表
        """
        # 构建高级查询字符串
        advanced_query = query
        
        if exclude_subreddits:
            for sub in exclude_subreddits:
                advanced_query += f" -subreddit:{sub}"
        
        if author:
            advanced_query += f" author:{author}"
            
        if site:
            advanced_query += f" site:{site}"
            
        if title_only:
            advanced_query = f"title:{advanced_query}"
        
        logger.info(f"高级搜索查询: {advanced_query}")
        
        return self.search_by_keywords(
            keywords=advanced_query,
            subreddits=subreddits,
            **search_params
        )
    
    def _extract_post_data(self, post) -> Dict[str, Any]:
        """提取帖子数据"""
        return {
            'id': post.id,
            'title': post.title,
            'author': str(post.author) if post.author else "[deleted]",
            'subreddit': post.subreddit.display_name,
            'score': post.score,
            'upvote_ratio': post.upvote_ratio,
            'num_comments': post.num_comments,
            'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
            'url': post.url,
            'permalink': f"https://reddit.com{post.permalink}",
            'is_self': post.is_self,
            'selftext': post.selftext if post.is_self else "",
            'selftext_preview': post.selftext[:300] if post.is_self else "",
            'flair': post.link_flair_text,
            'domain': post.domain,
            'stickied': post.stickied,
            'locked': post.locked,
            'nsfw': post.over_18,
            'spoiler': post.spoiler,
            'collected_at': datetime.now().isoformat()
        }
    
    def _generate_search_summary(self, category_results: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """生成搜索结果摘要"""
        total_posts = sum(len(posts) for posts in category_results.values())
        
        if total_posts == 0:
            return {'total_posts': 0}
        
        # 统计各维度
        all_posts = []
        for posts in category_results.values():
            all_posts.extend(posts)
        
        # 按社区统计
        subreddit_stats = defaultdict(int)
        author_stats = defaultdict(int)
        domain_stats = defaultdict(int)
        
        total_score = 0
        total_comments = 0
        
        for post in all_posts:
            subreddit_stats[post['subreddit']] += 1
            author_stats[post['author']] += 1
            domain_stats[post['domain']] += 1
            total_score += post['score']
            total_comments += post['num_comments']
        
        # 排序统计
        top_subreddits = sorted(subreddit_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        top_authors = sorted(author_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        top_domains = sorted(domain_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 找出最热门的帖子
        top_post = max(all_posts, key=lambda x: x['score'])
        
        return {
            'total_posts': total_posts,
            'categories_count': len(category_results),
            'avg_score': total_score / total_posts,
            'avg_comments': total_comments / total_posts,
            'top_subreddits': top_subreddits,
            'top_authors': top_authors,
            'top_domains': top_domains,
            'hottest_post': {
                'title': top_post['title'],
                'score': top_post['score'],
                'subreddit': top_post['subreddit'],
                'url': top_post['permalink']
            },
            'posts_by_category': {cat: len(posts) for cat, posts in category_results.items()}
        }
    
    def save_search_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """保存搜索结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"keyword_search_results_{timestamp}.json"
        
        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"搜索结果已保存到: {filepath}")
        return filepath

def main():
    """演示关键词搜索功能"""
    collector = KeywordRedditCollector()
    
    print("=== Reddit关键词搜索演示 ===\n")
    
    # 演示1: 基础关键词搜索
    print("1. 基础关键词搜索...")
    basic_results = collector.search_by_keywords(
        keywords=["ai", "agent", "deep learning"],       
        # subreddits=["MachineLearning", "OpenAI", "ChatGPT"],    # None表示搜索全站
        sort="top",
        time_filter="week",
        limit=20,
        min_score=10
    )
    
    print(f"   找到 {len(basic_results)} 个相关帖子")
    if basic_results:
        top_post = basic_results[0]
        print(f"   最热帖子: {top_post['title'][:60]}... (分数: {top_post['score']})")

    filepath = collector.save_search_results(basic_results)
    print(f"   基础关键词搜索结果已保存到: {filepath}")
    
    # # 演示2: AI热门话题搜索
    # print("\n2. AI热门话题搜索...")
    # trending_results = collector.trending_topics_search(
    #     limit_per_category=15
    # )
    
    # summary = trending_results['summary']
    # print(f"   搜索了 {summary['categories_count']} 个AI类别")
    # print(f"   总计找到 {summary['total_posts']} 个帖子")
    # print(f"   平均分数: {summary['avg_score']:.1f}")
    
    # if summary.get('hottest_post'):
    #     hottest = summary['hottest_post']
    #     print(f"   最热帖子: {hottest['title'][:60]}... (r/{hottest['subreddit']}, 分数: {hottest['score']})")
    
    # # 演示3: 高级搜索
    # print("\n3. 高级搜索...")
    # advanced_results = collector.advanced_search(
    #     query="fine tuning",
    #     subreddits=["LocalLLaMA", "MachineLearning"],
    #     exclude_subreddits=["memes", "funny"],
    #     title_only=False,
    #     sort="top",
    #     time_filter="month",
    #     limit=15
    # )
    
    # print(f"   高级搜索找到 {len(advanced_results)} 个帖子")
    
    # # 保存结果
    # print("\n4. 保存搜索结果...")
    
    # # 合并所有结果
    # all_results = {
    #     'basic_search': {
    #         'query': "ChatGPT GPT-4 OpenAI",
    #         'results': basic_results
    #     },
    #     'trending_topics': trending_results,
    #     'advanced_search': {
    #         'query': "fine tuning (advanced)",
    #         'results': advanced_results
    #     }
    # }
    
    # filepath = collector.save_search_results(all_results)
    # print(f"   所有搜索结果已保存到: {filepath}")
    
    # print("\n=== 演示完成 ===")
    
    # # 显示各类别统计
    # if trending_results['summary'].get('posts_by_category'):
    #     print(f"\n各AI类别帖子数量:")
    #     for category, count in trending_results['summary']['posts_by_category'].items():
    #         print(f"  {category}: {count}个")

if __name__ == "__main__":
    main()