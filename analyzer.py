"""
趋势分析模块 - 负责生成热门排行和趋势分析
"""

import logging
from collections import defaultdict, Counter
from typing import Dict, List, Any
import statistics

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """趋势分析器"""
    
    def __init__(self):
        logger.info("趋势分析器初始化完成")
    
    def create_hot_ranking(self, posts_dict: Dict[str, List[Dict]], 
                          top_k: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """
        创建三个时间维度的热门帖子排行榜
        
        Args:
            posts_dict: 清洗后的数据
            top_k: 每个排行榜返回前K个
        
        Returns:
            包含三个时间维度排行榜的字典:
            {
                'hot': [...],      # 当天热门帖子，按hot排序
                'week': [...],     # 本周热门帖子，按score排序  
                'month': [...]     # 本月热门帖子，按score排序
            }
        """
        logger.info(f"生成三个时间维度热门排行榜 TOP{top_k}...")
        
        # 按时间维度分类帖子
        hot_posts = []
        week_posts = []
        month_posts = []
        
        for timeframe_key, posts in posts_dict.items():
            timeframe = timeframe_key.split('_')[0]
            
            for post in posts:
                post_copy = post.copy()
                post_copy['source_key'] = timeframe_key
                
                if timeframe == 'hot':
                    hot_posts.append(post_copy)
                elif timeframe == 'day':
                    # 将day时间维度也归入hot，因为都是当天内容
                    hot_posts.append(post_copy)
                elif timeframe == 'week':
                    week_posts.append(post_copy)
                elif timeframe == 'month':
                    month_posts.append(post_copy)
        
        # 对每个时间维度的帖子进行排序
        # hot维度：保持原有的hot排序（按热度实时排序）
        hot_ranking = hot_posts[:top_k]
        
        # week维度：按score降序排序
        week_ranking = sorted(week_posts, key=lambda x: x.get('score', 0), reverse=True)[:top_k]
        
        # month维度：按score降序排序
        month_ranking = sorted(month_posts, key=lambda x: x.get('score', 0), reverse=True)[:top_k]
        
        return {
            'hot': hot_ranking,
            'week': week_ranking,
            'month': month_ranking
        }
    
    def analyze_trends(self, posts_dict: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        综合趋势分析
        
        Args:
            posts_dict: 清洗后的数据
        
        Returns:
            趋势分析结果
        """
        logger.info("开始趋势分析...")
        
        # 收集所有帖子
        all_posts = []
        for posts in posts_dict.values():
            all_posts.extend(posts)
        
        if not all_posts:
            return {}
        
        analysis = {
            'keyword_trends': self._analyze_keywords(all_posts),
            'author_trends': self._analyze_authors(all_posts),
            'subreddit_trends': self._analyze_subreddits(all_posts),
            'engagement_trends': self._analyze_engagement(all_posts),
            'time_distribution': self._analyze_time_distribution(posts_dict)
        }
        
        logger.info("趋势分析完成")
        return analysis
    
    def _analyze_keywords(self, posts: List[Dict]) -> Dict[str, Any]:
        """关键词趋势分析"""
        ai_keywords = [
            'llm', 'gpt', 'ai', 'machine learning', 'deep learning',
            'transformer', 'model', 'training', 'fine-tune', 'finetune',
            'langchain', 'openai', 'anthropic', 'claude', 'chatgpt',
            'rag', 'vector', 'embedding', 'prompt', 'agent', 'ollama',
            'local', 'inference', 'quantization', 'lora', 'rlhf'
        ]
        
        keyword_counts = defaultdict(int)
        
        for post in posts:
            text = f"{post.get('title', '')} {post.get('selftext_preview', '')}".lower()
            
            for keyword in ai_keywords:
                if keyword in text:
                    keyword_counts[keyword] += 1
        
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_keywords_found': len(keyword_counts),
            'keyword_frequency': dict(sorted_keywords[:20]),
            'trending_keywords': [kw for kw, count in sorted_keywords[:10] if count > 1]
        }
    
    def _analyze_authors(self, posts: List[Dict]) -> Dict[str, Any]:
        """作者趋势分析"""
        author_stats = defaultdict(lambda: {'posts': 0, 'total_score': 0, 'total_comments': 0})
        
        for post in posts:
            author = post.get('author')
            if author and author != '[deleted]':
                author_stats[author]['posts'] += 1
                author_stats[author]['total_score'] += post.get('score', 0)
                author_stats[author]['total_comments'] += post.get('num_comments', 0)
        
        top_authors = []
        for author, stats in author_stats.items():
            if stats['posts'] > 1:
                top_authors.append({
                    'author': author,
                    'posts_count': stats['posts'],
                    'avg_score': stats['total_score'] / stats['posts'],
                    'total_engagement': stats['total_score'] + stats['total_comments']
                })
        
        top_authors.sort(key=lambda x: x['total_engagement'], reverse=True)
        
        return {
            'total_unique_authors': len(author_stats),
            'active_authors': len([a for a in author_stats.values() if a['posts'] > 1]),
            'top_authors': top_authors[:10]
        }
    
    def _analyze_subreddits(self, posts: List[Dict]) -> Dict[str, Any]:
        """Subreddit趋势分析"""
        subreddit_stats = defaultdict(lambda: {'posts': 0, 'total_score': 0, 'avg_score': 0})
        
        for post in posts:
            subreddit = post.get('subreddit')
            if subreddit:
                subreddit_stats[subreddit]['posts'] += 1
                subreddit_stats[subreddit]['total_score'] += post.get('score', 0)
        
        for stats in subreddit_stats.values():
            if stats['posts'] > 0:
                stats['avg_score'] = stats['total_score'] / stats['posts']
        
        sorted_subs = sorted(
            subreddit_stats.items(),
            key=lambda x: x[1]['total_score'],
            reverse=True
        )
        
        return {
            'total_subreddits': len(subreddit_stats),
            'subreddit_performance': {name: stats for name, stats in sorted_subs[:10]}
        }
    
    def _analyze_engagement(self, posts: List[Dict]) -> Dict[str, Any]:
        """互动趋势分析"""
        engagement_ratios = []
        high_engagement_posts = []
        
        for post in posts:
            score = post.get('score', 0)
            comments = post.get('num_comments', 0)
            
            if score > 0:
                ratio = comments / score
                engagement_ratios.append(ratio)
                
                if ratio > 0.1:  # 评论率超过10%
                    high_engagement_posts.append(post)
        
        high_engagement_posts.sort(key=lambda x: x['num_comments'], reverse=True)
        
        return {
            'avg_engagement_ratio': statistics.mean(engagement_ratios) if engagement_ratios else 0,
            'median_engagement_ratio': statistics.median(engagement_ratios) if engagement_ratios else 0,
            'high_engagement_count': len(high_engagement_posts),
            'top_engagement_posts': high_engagement_posts[:5]
        }
    
    def _analyze_time_distribution(self, posts_dict: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """时间分布分析"""
        timeframe_stats = {}
        
        for timeframe_key, posts in posts_dict.items():
            timeframe = timeframe_key.split('_')[0]
            
            if timeframe not in timeframe_stats:
                timeframe_stats[timeframe] = {
                    'total_posts': 0,
                    'avg_score': 0,
                    'avg_comments': 0
                }
            
            timeframe_stats[timeframe]['total_posts'] += len(posts)
            
            if posts:
                scores = [p.get('score', 0) for p in posts]
                comments = [p.get('num_comments', 0) for p in posts]
                timeframe_stats[timeframe]['avg_score'] += sum(scores) / len(posts)
                timeframe_stats[timeframe]['avg_comments'] += sum(comments) / len(posts)
        
        return timeframe_stats