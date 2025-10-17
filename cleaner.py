"""
数据清洗模块 - 负责验证、清洗和去重数据
"""

import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class DataCleaner:
    """数据清洗器"""
    
    def __init__(self):
        self.stats = {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'filtered': 0
        }
        logger.info("数据清洗器初始化完成")
    
    def clean_posts(self, posts_dict: Dict[str, List[Dict]], 
                   remove_duplicates: bool = False) -> Dict[str, List[Dict]]:
        """
        清洗帖子数据
        
        Args:
            posts_dict: {"timeframe_sub": [posts]}
            remove_duplicates: 是否去重
        
        Returns:
            清洗后的数据
        """
        logger.info("开始数据清洗...")
        self.stats['total'] = sum(len(posts) for posts in posts_dict.values())
        
        cleaned_dict = {}
        
        for key, posts in posts_dict.items():
            cleaned_posts = []
            
            for post in posts:
                # 首先检查post是否为None
                if post is None:
                    logger.error(f"⚠️ 在 {key} 中发现None帖子，已跳过")
                    self.stats['invalid'] += 1
                    continue
                
                # 验证数据完整性
                if not self._validate_post(post):
                    self.stats['invalid'] += 1
                    logger.debug(f"帖子验证失败: {post.get('id', 'unknown')}")
                    continue
                
                # 质量过滤
                if not self._quality_filter(post):
                    self.stats['filtered'] += 1
                    logger.debug(f"帖子质量过滤: {post.get('id', 'unknown')} - {post.get('title', '')[:30]}")
                    continue
                
                # 数据清洗
                cleaned_post = self._clean_post_data(post)
                
                # 二次验证清洗后的数据不是None
                if cleaned_post is None:
                    logger.error(f"⚠️ 清洗后帖子变成None: {post.get('id', 'unknown')}")
                    self.stats['invalid'] += 1
                    continue
                
                cleaned_posts.append(cleaned_post)
                self.stats['valid'] += 1
            
            cleaned_dict[key] = cleaned_posts
        
        logger.info(f"清洗完成: {self.stats['valid']}/{self.stats['total']} 有效, "
                   f"{self.stats['invalid']} 无效, {self.stats['filtered']} 过滤")
        
        return cleaned_dict
    
    def deduplicate_posts(self, posts_dict: Dict[str, List[Dict]], 
                         keep: str = 'highest_hot') -> List[Dict]:
        """
        去重帖子（保留hot分数最高的）
        
        Args:
            posts_dict: 清洗后的数据
            keep: 保留策略 ('highest_hot', 'first', 'last')
        
        Returns:
            去重后的帖子列表
        """
        logger.info("开始数据去重...")
        
        # 收集所有帖子
        all_posts = []
        for timeframe_key, posts in posts_dict.items():
            for post in posts:
                # 标记来源时间维度
                post['source_timeframe'] = timeframe_key.split('_')[0]
                all_posts.append(post)
        
        # 按ID分组
        post_groups = {}
        for post in all_posts:
            post_id = post['id']
            if post_id not in post_groups:
                post_groups[post_id] = []
            post_groups[post_id].append(post)
        
        # 去重策略
        unique_posts = []
        for post_id, group in post_groups.items():
            if keep == 'highest_hot':
                # 保留来自hot时间维度且分数最高的
                hot_posts = [p for p in group if p['source_timeframe'] == 'hot']
                if hot_posts:
                    selected = max(hot_posts, key=lambda x: x['score'])
                else:
                    selected = max(group, key=lambda x: x['score'])
            elif keep == 'first':
                selected = group[0]
            elif keep == 'last':
                selected = group[-1]
            else:
                selected = max(group, key=lambda x: x['score'])
            
            unique_posts.append(selected)
        
        logger.info(f"去重完成: {len(all_posts)} -> {len(unique_posts)}")
        return unique_posts
    
    def _validate_post(self, post: Dict[str, Any]) -> bool:
        """验证帖子数据完整性"""
        required_fields = ['id', 'title', 'subreddit', 'created_utc']
        
        for field in required_fields:
            if field not in post or not post[field]:
                return False
        
        # 验证时间格式
        try:
            if isinstance(post['created_utc'], str):
                datetime.fromisoformat(post['created_utc'].replace('Z', ''))
        except:
            return False
        
        # 验证数值字段
        numeric_fields = ['score', 'num_comments']
        for field in numeric_fields:
            if field in post:
                try:
                    float(post[field])
                except:
                    return False
        
        return True
    
    def _quality_filter(self, post: Dict[str, Any]) -> bool:
        """质量过滤"""
        # 过滤删除的帖子
        if post.get('author') == '[deleted]' and not post.get('title'):
            return False
        
        # 过滤负分帖子
        if post.get('score', 0) < 0:
            return False
        
        # 过滤标题过短
        title = post.get('title', '')
        if len(title.strip()) < 10:
            return False
        
        return True
    
    def _clean_post_data(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """清洗单个帖子数据"""
        cleaned = post.copy()
        
        # 清理文本字段
        text_fields = ['title', 'selftext_preview']
        for field in text_fields:
            if field in cleaned and cleaned[field]:
                cleaned[field] = ' '.join(cleaned[field].split())
                if field == 'title':
                    cleaned[field] = cleaned[field][:300]
                else:
                    cleaned[field] = cleaned[field][:500]
        
        # 标准化数值
        if 'score' in cleaned:
            cleaned['score'] = max(0, int(cleaned['score']))
        if 'num_comments' in cleaned:
            cleaned['num_comments'] = max(0, int(cleaned['num_comments']))
        if 'upvote_ratio' in cleaned:
            cleaned['upvote_ratio'] = max(0.0, min(1.0, float(cleaned['upvote_ratio'])))
        
        return cleaned
    
    def get_stats(self) -> Dict[str, Any]:
        """获取清洗统计"""
        total = self.stats['total']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'valid_rate': (self.stats['valid'] / total) * 100,
            'invalid_rate': (self.stats['invalid'] / total) * 100,
            'filter_rate': (self.stats['filtered'] / total) * 100
        }
