"""
数据获取模块 - 负责从Reddit获取帖子数据
"""

import os
import praw
import logging
import time
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class RedditDataFetcher:
    """Reddit数据获取器"""
    
    def __init__(self):
        """初始化Reddit客户端"""
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "python:reddit-analyzer:1.0")
        )
        
        try:
            self.reddit.user.me()
            logger.info("Reddit API连接成功（已认证）")
        except:
            logger.info("Reddit API连接成功（只读模式）")
    
    def fetch_posts_from_subreddits(self, subreddit_config: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        从多个subreddit获取帖子
        
        Args:
            subreddit_config: {"priority": [{"name": "xxx", "limit": 50}]}
        
        Returns:
            {"timeframe_subreddit": [post1, post2, ...]}
        """
        all_posts = {}
        
        for priority, subreddits in subreddit_config.items():
            logger.info(f"正在获取 {priority} 优先级社区...")
            
            for sub_info in subreddits:
                name = sub_info['name']
                limit = sub_info['limit']
                
                try:
                    subreddit = self.reddit.subreddit(name)
                    
                    # 获取多个时间维度的帖子
                    for timeframe, method in [
                        ('hot', lambda: subreddit.hot(limit=limit)),
                        ('day', lambda: subreddit.top(time_filter='day', limit=max(10, limit//2))),
                        ('week', lambda: subreddit.top(time_filter='week', limit=max(15, limit//2))),
                        ('month', lambda: subreddit.top(time_filter='month', limit=limit))
                    ]:
                        key = f"{timeframe}_{name}"
                        posts = list(method())
                        all_posts[key] = [self._extract_basic_post(post) for post in posts]
                        logger.info(f"  r/{name} [{timeframe}]: {len(all_posts[key])} 个帖子")
                        time.sleep(0.5)  # API限流
                
                except Exception as e:
                    logger.error(f"获取 r/{name} 失败: {e}")
                    continue
        
        return all_posts
    
    def fetch_detailed_posts(self, post_ids: List[str], 
                           comment_depth: int = 2,
                           max_workers: int = 3) -> List[Dict[str, Any]]:
        """
        批量获取帖子详细信息（包括评论）
        
        Args:
            post_ids: 帖子ID列表
            comment_depth: 评论深度
            max_workers: 并发线程数
        
        Returns:
            详细帖子列表
        """
        logger.info(f"开始获取 {len(post_ids)} 个帖子的详细信息...")
        
        detailed_posts = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {
                executor.submit(self._fetch_single_detail, post_id, comment_depth): post_id
                for post_id in post_ids
            }
            
            for future in as_completed(future_to_id):
                post_id = future_to_id[future]
                try:
                    result = future.result()
                    if result:
                        detailed_posts.append(result)
                        logger.debug(f"成功获取帖子 {post_id}")
                except Exception as e:
                    logger.error(f"获取帖子 {post_id} 详情失败: {e}")
                
                time.sleep(0.2)  # 限流
        
        logger.info(f"成功获取 {len(detailed_posts)}/{len(post_ids)} 个详细帖子")
        return detailed_posts
    
    def _fetch_single_detail(self, post_id: str, comment_depth: int) -> Dict[str, Any]:
        """获取单个帖子的详细信息"""
        try:
            submission = self.reddit.submission(id=post_id)
            
            return {
                'id': submission.id,
                'title': submission.title,
                'author': str(submission.author) if submission.author else "[deleted]",
                'subreddit': submission.subreddit.display_name,
                'content': submission.selftext,
                'url': submission.url,
                'permalink': f"https://reddit.com{submission.permalink}",
                'score': submission.score,
                'upvote_ratio': submission.upvote_ratio,
                'num_comments': submission.num_comments,
                'created_utc': datetime.fromtimestamp(submission.created_utc).isoformat(),
                'flair': submission.link_flair_text,
                'is_self': submission.is_self,
                'comments': self._extract_comments(submission, comment_depth),
                'collected_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"提取帖子 {post_id} 详情失败: {e}")
            return None
    
    def _extract_basic_post(self, post) -> Dict[str, Any]:
        """提取基础帖子信息"""
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
            'is_self': post.is_self,
            'selftext_preview': post.selftext[:200] if post.selftext else "",
            'flair': post.link_flair_text,
            'permalink': f"https://reddit.com{post.permalink}",
            'stickied': post.stickied,
            'locked': post.locked
        }
    
    def _extract_comments(self, submission, depth: int) -> List[Dict[str, Any]]:
        """提取评论"""
        comments = []
        
        try:
            submission.comments.replace_more(limit=5)
            
            for comment in submission.comments[:20]:
                if hasattr(comment, 'body') and comment.body != '[deleted]':
                    comment_data = {
                        'id': comment.id,
                        'author': str(comment.author) if comment.author else "[deleted]",
                        'body': comment.body[:500],
                        'score': comment.score,
                        'created_utc': datetime.fromtimestamp(comment.created_utc).isoformat(),
                        'is_submitter': comment.is_submitter
                    }
                    
                    if depth > 1 and hasattr(comment, 'replies'):
                        comment_data['replies'] = self._extract_replies(comment.replies, depth - 1)
                    
                    comments.append(comment_data)
        
        except Exception as e:
            logger.error(f"提取评论失败: {e}")
        
        return comments
    
    def _extract_replies(self, replies, depth: int) -> List[Dict[str, Any]]:
        """提取回复"""
        reply_list = []
        
        try:
            for reply in replies[:5]:
                if hasattr(reply, 'body') and reply.body != '[deleted]':
                    reply_list.append({
                        'id': reply.id,
                        'author': str(reply.author) if reply.author else "[deleted]",
                        'body': reply.body[:300],
                        'score': reply.score
                    })
        except:
            pass
        
        return reply_list