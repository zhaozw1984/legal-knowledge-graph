"""
规则实体标准化模块

基于 pkuseg + 规则 + 词典进行实体标准化，完全替代现有 LLM 归一化方法。
"""

from .normalizer import EntityNormalizer
from .segmenter import PKUSegmenter
from .dictionary import EntityDictionary

__all__ = [
    "EntityNormalizer",
    "PKUSegmenter",
    "EntityDictionary"
]
