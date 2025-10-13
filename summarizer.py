"""
摘要生成模块 - 负责为帖子生成摘要
"""

import logging
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from config import LLM_CONFIG

logger = logging.getLogger(__name__)


class PostSummarizer:
    """帖子摘要生成器"""
    
    def __init__(self, model: str = None, api_key: str = None, base_url: str = None):
        """
        初始化摘要生成器
        
        Args:
            model: LLM模型名称，默认从config读取
            api_key: API密钥，默认从config读取
            base_url: API基础URL，默认从config读取
        """
        self.model = model or LLM_CONFIG.get("model")
        self.api_key = api_key or LLM_CONFIG.get("api_key")
        self.base_url = base_url or LLM_CONFIG.get("base_url")
        
        self.llm_client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        logger.info(f"摘要生成器初始化完成 - 模型: {self.model}")
    
    def generate_summaries_for_posts(
        self, 
        posts: List[Dict[str, Any]], 
        fetcher,
        max_workers: int = 5,
        max_comments: int = 5
    ) -> List[Dict[str, Any]]:
        """
        为帖子列表批量生成摘要
        
        Args:
            posts: 帖子列表
            fetcher: RedditDataFetcher实例，用于获取评论
            max_workers: 最大并发数
            max_comments: 当selftext较短时，获取的评论数量
        
        Returns:
            添加了summary字段的帖子列表
        """
        logger.info(f"开始为 {len(posts)} 个帖子生成摘要...")
        
        posts_with_summary = []
        
        # 使用线程池并发生成摘要
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_post = {
                executor.submit(
                    self._generate_single_summary, 
                    post, 
                    fetcher,
                    max_comments
                ): post
                for post in posts
            }
            
            completed = 0
            for future in as_completed(future_to_post):
                post = future_to_post[future]
                try:
                    post_with_summary = future.result()
                    posts_with_summary.append(post_with_summary)
                    completed += 1
                    if completed % 10 == 0:
                        logger.info(f"摘要生成进度: {completed}/{len(posts)}")
                except Exception as e:
                    logger.error(f"生成帖子 {post.get('id')} 摘要失败: {e}")
                    # 失败时标记错误信息
                    post['summary_error'] = str(e)
                    post['summary'] = None
                    posts_with_summary.append(post)
        
        logger.info(f"摘要生成完成: {len(posts_with_summary)}/{len(posts)}")
        return posts_with_summary
    
    def _generate_single_summary(
        self, 
        post: Dict[str, Any], 
        fetcher,
        max_comments: int
    ) -> Dict[str, Any]:
        """
        为单个帖子生成摘要
        
        Args:
            post: 帖子数据
            fetcher: RedditDataFetcher实例
            max_comments: 当selftext较短时，获取的评论数量
        
        Returns:
            添加了summary字段的帖子
        """
        post_copy = post.copy()
        
        # 获取正文内容
        selftext = post.get('selftext_preview', '') or post.get('content', '')
        title = post.get('title', '')
        
        # 判断是否需要获取评论
        if len(selftext) < 50:
            # 正文较短，需要获取评论
            comments_text = self._fetch_comments_for_summary(post.get('id'), fetcher, max_comments)
            prompt_content = f"标题: {title}\n\n正文: {selftext}\n\n评论:\n{comments_text}"
        else:
            # 正文足够长，直接使用正文
            prompt_content = f"标题: {title}\n\n正文: {selftext}"
        
        # 调用LLM生成摘要
        summary = self._call_llm_for_summary(prompt_content)
        post_copy['summary'] = summary
        
        return post_copy
    
    def _fetch_comments_for_summary(
        self, 
        post_id: str, 
        fetcher, 
        max_comments: int
    ) -> str:
        """
        获取帖子的评论用于生成摘要
        
        Args:
            post_id: 帖子ID
            fetcher: RedditDataFetcher实例
            max_comments: 最大评论数
        
        Returns:
            评论文本
        """
        try:
            submission = fetcher.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)
            
            comments = []
            for comment in submission.comments[:max_comments]:
                if hasattr(comment, 'body') and comment.body != '[deleted]':
                    # 限制每条评论长度
                    comment_text = comment.body[:200]
                    comments.append(f"- {comment_text}")
            
            return "\n".join(comments) if comments else "无有效评论"
        
        except Exception as e:
            logger.warning(f"获取帖子 {post_id} 评论失败: {e}")
            return "无法获取评论"
    
    def _call_llm_for_summary(self, content: str) -> str:
        """调用LLM生成摘要
        
        Args:
            content: 需要摘要的内容
        
        Returns:
            摘要文本（100字以内）
        
        Raises:
            Exception: 如果LLM调用失败
        """
        prompt = f"""请为以下Reddit帖子生成一个简洁的摘要，要求：
1. 摘要字数控制在100字以内
2. 突出帖子的核心内容和要点
3. 使用中文
4. 直接输出摘要，不要添加任何前缀或说明

帖子内容：
{content}

摘要："""
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的内容摘要助手，擅长提取核心信息并生成简洁的摘要。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=200,
            )
            
            summary = response.choices[0].message.content.strip()
            # 确保摘要不超过100字
            if len(summary) > 100:
                summary = summary[:100]
            
            return summary
        
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            # 失败时抛出异常，让上层处理
            raise Exception(f"LLM调用失败: {str(e)}")
