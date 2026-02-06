"""
pkuseg 分词封装

提供中文分词功能，用于实体标准化中的关键词提取。
"""

from typing import List, Optional
import pkuseg
from loguru import logger


class PKUSegmenter:
    """pkuseg 分词器封装"""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        初始化分词器
        
        Args:
            model_name: 模型名称，默认使用 pkuseg 的默认模型
        """
        try:
            self.seg = pkuseg.pkuseg(model_name=model_name)
            logger.info(f"pkuseg 分词器初始化成功")
        except Exception as e:
            logger.error(f"pkuseg 初始化失败: {e}")
            raise
    
    def cut(self, text: str) -> List[str]:
        """
        分词
        
        Args:
            text: 待分词文本
            
        Returns:
            分词结果列表
        """
        return self.seg.cut(text)
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        提取关键词（基于词频）
        
        Args:
            text: 待提取文本
            top_k: 返回前k个关键词
            
        Returns:
            关键词列表
        """
        words = self.cut(text)
        
        # 统计词频
        word_freq = {}
        for word in words:
            # 过滤停用词和短词
            if len(word) < 2:
                continue
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按词频排序
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, _ in sorted_words[:top_k]]
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度（基于关键词重叠）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数（0-1）
        """
        keywords1 = set(self.extract_keywords(text1, top_k=20))
        keywords2 = set(self.extract_keywords(text2, top_k=20))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2
        
        return len(intersection) / len(union) if union else 0.0
