"""
质量评分模块 - 基于多维度指标对帖子进行质量评分
"""

import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class QualityScorer:
    """质量评分器"""
    
    def __init__(self):
        logger.info("质量评分器初始化完成")
    
    def score_posts(self, posts: List[Dict], 
                   trend_analysis: Dict[str, Any]) -> List[Dict]:
        """
        对帖子列表进行质量评分
        
        Args:
            posts: 去重后的帖子列表
            trend_analysis: 趋势分析结果
        
        Returns:
            带评分的帖子列表
        """
        logger.info(f"开始对 {len(posts)} 个帖子进行质量评分...")
        
        scored_posts = []
        
        for post in posts:
            # 避免重复计算
            if 'quality_score' not in post:
                score = self._calculate_quality_score(post, trend_analysis)
                post['quality_score'] = round(score, 2)
            
            scored_posts.append(post)
        
        # 按评分排序
        scored_posts.sort(key=lambda x: x['quality_score'], reverse=True)
        
        logger.info(f"评分完成，最高分: {scored_posts[0]['quality_score']:.2f}, "
                   f"最低分: {scored_posts[-1]['quality_score']:.2f}")
        
        return scored_posts
    
    def get_top_quality_posts(self, scored_posts: List[Dict], 
                             top_k: int = 5) -> List[Dict]:
        """获取高质量帖子TOP K"""
        return scored_posts[:top_k]
    
    def _calculate_quality_score(self, post: Dict[str, Any], 
                                 trend_analysis: Dict[str, Any]) -> float:
        """
        计算综合质量评分 (0-100)
        
        评分维度:
        1. 互动指标 (40分): 点赞、评论、点赞率
        2. 内容质量 (20分): 标题、内容、标签
        3. 时效性 (15分): 发布时间
        4. 趋势相关性 (25分): 关键词、作者、社区活跃度
        """
        total_score = 0.0
        
        # 1. 互动指标 (40分)
        total_score += self._score_interaction(post)
        
        # 2. 内容质量 (20分)
        total_score += self._score_content(post)
        
        # 3. 时效性 (15分)
        total_score += self._score_freshness(post)
        
        # 4. 趋势相关性 (25分)
        total_score += self._score_trend_relevance(post, trend_analysis)
        
        return min(total_score, 100.0)
    
    def _score_interaction(self, post: Dict[str, Any]) -> float:
        """互动指标评分 (0-40)"""
        score = max(post.get('score', 0), 0)
        comments = max(post.get('num_comments', 0), 0)
        upvote_ratio = max(min(post.get('upvote_ratio', 0.5), 1.0), 0.0)
        
        # 点赞评分 (0-15): 对数缩放
        score_points = min(15, 5 * (1 + 2 * (score ** 0.5) / 100))
        
        # 评论评分 (0-15): 对数缩放
        comment_points = min(15, 5 * (1 + 2 * (comments ** 0.6) / 50))
        
        # 点赞率评分 (0-10)
        if upvote_ratio >= 0.9:
            ratio_points = 10
        elif upvote_ratio >= 0.8:
            ratio_points = 8
        elif upvote_ratio >= 0.7:
            ratio_points = 6
        elif upvote_ratio >= 0.6:
            ratio_points = 4
        else:
            ratio_points = 2
        
        return score_points + comment_points + ratio_points
    
    def _score_content(self, post: Dict[str, Any]) -> float:
        """内容质量评分 (0-20)"""
        title = post.get('title', '')
        content = post.get('selftext_preview', '')
        
        # 标题质量 (0-8)
        title_len = len(title)
        if title_len > 50:
            title_points = 8
        elif title_len > 30:
            title_points = 6
        elif title_len > 15:
            title_points = 4
        else:
            title_points = 2
        
        # 内容丰富度 (0-7)
        content_len = len(content)
        if content_len > 500:
            content_points = 7
        elif content_len > 200:
            content_points = 5
        elif content_len > 100:
            content_points = 3
        elif content_len > 0:
            content_points = 1
        else:
            content_points = 0
        
        # 分类标签 (0-5)
        flair = post.get('flair', '')
        if flair and flair.lower() not in ['general', 'discussion', 'other', '']:
            flair_points = 5
        else:
            flair_points = 0
        
        return title_points + content_points + flair_points
    
    def _score_freshness(self, post: Dict[str, Any]) -> float:
        """时效性评分 (0-15)"""
        try:
            created_utc = post.get('created_utc')
            if isinstance(created_utc, str):
                created_time = datetime.fromisoformat(created_utc.replace('Z', ''))
            else:
                created_time = datetime.fromtimestamp(created_utc)
            
            hours_old = (datetime.now() - created_time).total_seconds() / 3600
            
            if hours_old < 2:
                return 15
            elif hours_old < 6:
                return 12
            elif hours_old < 12:
                return 10
            elif hours_old < 24:
                return 8
            elif hours_old < 48:
                return 6
            elif hours_old < 168:
                return 4
            else:
                return 2
        except:
            return 5
    
    def _score_trend_relevance(self, post: Dict[str, Any], 
                              trend_analysis: Dict[str, Any]) -> float:
        """趋势相关性评分 (0-25)"""
        if not trend_analysis:
            return 12.0
        
        total = 0.0
        
        # 关键词匹配 (0-10)
        total += self._score_keyword_relevance(post, trend_analysis)
        
        # 作者活跃度 (0-8)
        total += self._score_author_activity(post, trend_analysis)
        
        # 社区活跃度 (0-7)
        total += self._score_subreddit_activity(post, trend_analysis)
        
        return total
    
    def _score_keyword_relevance(self, post: Dict[str, Any], 
                                 trend_analysis: Dict[str, Any]) -> float:
        """关键词相关性 (0-10)"""
        trending_keywords = trend_analysis.get('keyword_trends', {}).get('trending_keywords', [])
        
        if not trending_keywords:
            return 0
        
        text = f"{post.get('title', '')} {post.get('selftext_preview', '')}".lower()
        
        matches = sum(1 for kw in trending_keywords[:10] if kw.lower() in text)
        
        if matches >= 3:
            return 10
        elif matches >= 2:
            return 8
        elif matches >= 1:
            return 5
        else:
            return 0
    
    def _score_author_activity(self, post: Dict[str, Any], 
                               trend_analysis: Dict[str, Any]) -> float:
        """作者活跃度 (0-8)"""
        author = post.get('author', '')
        top_authors = trend_analysis.get('author_trends', {}).get('top_authors', [])
        
        for i, author_info in enumerate(top_authors):
            if author_info.get('author') == author:
                rank = i + 1
                if rank <= 3:
                    return 8
                elif rank <= 5:
                    return 6
                elif rank <= 10:
                    return 4
                else:
                    return 2
        
        return 0
    
    def _score_subreddit_activity(self, post: Dict[str, Any], 
                                  trend_analysis: Dict[str, Any]) -> float:
        """社区活跃度 (0-7)"""
        subreddit = post.get('subreddit', '')
        subreddit_perf = trend_analysis.get('subreddit_trends', {}).get('subreddit_performance', {})
        
        if subreddit in subreddit_perf:
            avg_score = subreddit_perf[subreddit].get('avg_score', 0)
            
            if avg_score > 100:
                return 7
            elif avg_score > 50:
                return 5
            elif avg_score > 20:
                return 3
            else:
                return 1
        
        return 2