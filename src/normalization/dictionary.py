"""
实体词典管理

管理实体标准化用的词典数据。
"""

from typing import Dict, List, Set
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class EntityEntry:
    """实体词典条目"""
    canonical_name: str        # 标准名称
    aliases: List[str] = field(default_factory=list)  # 别名列表
    entity_type: str = ""       # 实体类型
    confidence: float = 1.0    # 置信度


class EntityDictionary:
    """实体词典管理器"""
    
    def __init__(self):
        """初始化词典"""
        self.entries: Dict[str, EntityEntry] = {}  # 标准名称 -> 实体条目
        self.alias_map: Dict[str, str] = {}        # 别名 -> 标准名称
        
        # 加载默认词典
        self._load_default_dictionary()
    
    def _load_default_dictionary(self):
        """加载默认词典数据"""
        # 常见法律术语词典
        self.add_entry(
            canonical_name="中华人民共和国",
            aliases=["中国", "我国"],
            entity_type="Case"
        )
        
        self.add_entry(
            canonical_name="被告",
            aliases=["被告人", "被申请人"],
            entity_type="Party"
        )
        
        self.add_entry(
            canonical_name="原告",
            aliases=["申请人", "上诉人"],
            entity_type="Party"
        )
        
        logger.info(f"加载默认词典完成，共 {len(self.entries)} 条")
    
    def add_entry(self, canonical_name: str, aliases: List[str], 
                  entity_type: str, confidence: float = 1.0):
        """
        添加实体条目
        
        Args:
            canonical_name: 标准名称
            aliases: 别名列表
            entity_type: 实体类型
            confidence: 置信度
        """
        entry = EntityEntry(
            canonical_name=canonical_name,
            aliases=aliases,
            entity_type=entity_type,
            confidence=confidence
        )
        
        self.entries[canonical_name] = entry
        
        # 建立别名映射
        for alias in aliases:
            self.alias_map[alias] = canonical_name
        
        logger.debug(f"添加实体: {canonical_name} (别名: {aliases})")
    
    def lookup(self, name: str) -> Optional[EntityEntry]:
        """
        查找实体
        
        Args:
            name: 实体名称
            
        Returns:
            实体条目，如果未找到返回None
        """
        # 直接查找标准名称
        if name in self.entries:
            return self.entries[name]
        
        # 通过别名查找
        if name in self.alias_map:
            canonical_name = self.alias_map[name]
            return self.entries[canonical_name]
        
        return None
    
    def get_canonical_name(self, name: str) -> str:
        """
        获取标准名称
        
        Args:
            name: 实体名称
            
        Returns:
            标准名称，如果未找到返回原名称
        """
        entry = self.lookup(name)
        if entry:
            return entry.canonical_name
        return name
    
    def find_similar_entities(self, name: str, 
                            threshold: float = 0.8) -> List[EntityEntry]:
        """
        查找相似实体
        
        Args:
            name: 实体名称
            threshold: 相似度阈值
            
        Returns:
            相似实体列表
        """
        # 简化实现：基于字符串相似度
        similar = []
        
        for entry in self.entries.values():
            # 包含关系
            if name in entry.canonical_name or entry.canonical_name in name:
                similar.append(entry)
                continue
            
            # 别名匹配
            for alias in entry.aliases:
                if name in alias or alias in name:
                    similar.append(entry)
                    break
        
        return similar
    
    def batch_lookup(self, names: List[str]) -> Dict[str, EntityEntry]:
        """
        批量查找实体
        
        Args:
            names: 实体名称列表
            
        Returns:
            实体名称 -> 实体条目的映射
        """
        results = {}
        for name in names:
            entry = self.lookup(name)
            if entry:
                results[name] = entry
        return results
    
    def export(self) -> Dict:
        """
        导出词典为字典格式
        
        Returns:
            词典数据
        """
        return {
            "entries": [
                {
                    "canonical_name": entry.canonical_name,
                    "aliases": entry.aliases,
                    "entity_type": entry.entity_type,
                    "confidence": entry.confidence
                }
                for entry in self.entries.values()
            ]
        }
