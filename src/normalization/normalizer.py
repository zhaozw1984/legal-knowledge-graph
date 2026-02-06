"""
规则实体标准化引擎

基于 pkuseg 分词、规则匹配和词典查询进行实体标准化。
"""

from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass
from loguru import logger

from .segmenter import PKUSegmenter
from .dictionary import EntityDictionary, EntityEntry


@dataclass
class NormalizedEntity:
    """标准化后的实体"""
    entity_id: str
    canonical_name: str          # 标准名称
    aliases: List[str]           # 别名列表
    entity_type: str
    original_names: List[str]    # 原始名称列表
    block_type: str              # 来源块类型
    confidence: float            # 置信度
    source_block_ids: List[str]  # 来源块ID列表


class EntityNormalizer:
    """实体标准化器"""
    
    def __init__(self):
        """初始化标准化器"""
        self.segmenter = PKUSegmenter()
        self.dictionary = EntityDictionary()
        self.entity_counter = 0
    
    def normalize(
        self, 
        entities: List[Dict[str, Any]]
    ) -> List[NormalizedEntity]:
        """
        标准化实体列表
        
        Args:
            entities: 原始实体列表，每个实体包含 text, entity_type, block_id 等字段
            
        Returns:
            标准化后的实体列表
        """
        logger.info(f"开始实体标准化，共 {len(entities)} 个实体")
        
        # 第一步：基于词典的预匹配
        pre_matched = self._pre_match_dictionary(entities)
        
        # 第二步：基于相似度的聚类
        clusters = self._cluster_by_similarity(pre_matched)
        
        # 第三步：构建标准化实体
        normalized_entities = self._build_normalized_entities(clusters)
        
        logger.info(f"实体标准化完成，合并后共 {len(normalized_entities)} 个实体")
        
        return normalized_entities
    
    def _pre_match_dictionary(
        self, 
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        基于词典进行预匹配
        
        Args:
            entities: 原始实体列表
            
        Returns:
            预匹配后的实体列表（添加了 canonical_name 字段）
        """
        matched = []
        
        for entity in entities:
            text = entity.get("text", "")
            canonical_name = self.dictionary.get_canonical_name(text)
            
            # 标记是否从词典匹配
            is_dict_matched = (canonical_name != text)
            
            matched.append({
                **entity,
                "canonical_name": canonical_name,
                "is_dict_matched": is_dict_matched
            })
        
        logger.debug(f"词典预匹配完成，{sum(1 for e in matched if e['is_dict_matched'])} 个实体匹配到词典")
        
        return matched
    
    def _cluster_by_similarity(
        self, 
        entities: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        基于相似度聚类实体
        
        Args:
            entities: 预匹配后的实体列表
            
        Returns:
            实体簇列表，每个簇包含相似度高的实体
        """
        # 按实体类型分组
        type_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for entity in entities:
            entity_type = entity.get("entity_type", "UNKNOWN")
            type_groups[entity_type].append(entity)
        
        clusters = []
        
        for entity_type, group_entities in type_groups.items():
            # 对每种实体类型进行聚类
            type_clusters = self._cluster_same_type(group_entities)
            clusters.extend(type_clusters)
        
        logger.debug(f"相似度聚类完成，共 {len(clusters)} 个簇")
        
        return clusters
    
    def _cluster_same_type(
        self, 
        entities: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        对同类型实体进行聚类
        
        Args:
            entities: 同类型实体列表
            
        Returns:
            实体簇列表
        """
        clusters = []
        used = set()
        
        similarity_threshold = 0.6  # 相似度阈值
        
        for i, entity1 in enumerate(entities):
            if i in used:
                continue
            
            cluster = [entity1]
            used.add(i)
            
            for j, entity2 in enumerate(entities):
                if j <= i or j in used:
                    continue
                
                # 计算相似度
                similarity = self._compute_entity_similarity(entity1, entity2)
                
                if similarity >= similarity_threshold:
                    cluster.append(entity2)
                    used.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _compute_entity_similarity(
        self, 
        entity1: Dict[str, Any], 
        entity2: Dict[str, Any]
    ) -> float:
        """
        计算两个实体的相似度
        
        Args:
            entity1: 实体1
            entity2: 实体2
            
        Returns:
            相似度分数（0-1）
        """
        text1 = entity1.get("text", "")
        text2 = entity2.get("text", "")
        
        # 文本包含关系
        if text1 in text2 or text2 in text1:
            return 0.9
        
        # 使用 pkuseg 计算关键词相似度
        text_similarity = self.segmenter.compute_similarity(text1, text2)
        
        # 如果都有 canonical_name 且相同，给予高权重
        if (entity1.get("canonical_name") == entity2.get("canonical_name") and
            entity1.get("canonical_name") != text1 and 
            entity1.get("canonical_name") != text2):
            return 0.95
        
        return text_similarity
    
    def _build_normalized_entities(
        self, 
        clusters: List[List[Dict[str, Any]]]
    ) -> List[NormalizedEntity]:
        """
        从实体簇构建标准化实体
        
        Args:
            clusters: 实体簇列表
            
        Returns:
            标准化实体列表
        """
        normalized_entities = []
        
        for cluster in clusters:
            if not cluster:
                continue
            
            # 选择代表性名称（最长或词典匹配的）
            representative = self._select_representative(cluster)
            
            # 收集所有别名
            all_names = list(set([e.get("text", "") for e in cluster]))
            all_names = [name for name in all_names if name and name != representative]
            
            # 收集来源块ID
            source_block_ids = list(set([
                e.get("block_id", "") 
                for e in cluster 
                if e.get("block_id")
            ]))
            
            # 获取块类型
            block_types = set([e.get("block_type", "") for e in cluster])
            block_type = block_types.pop() if block_types else ""
            
            # 计算置信度
            confidence = self._compute_cluster_confidence(cluster)
            
            # 生成标准化实体
            normalized_entity = NormalizedEntity(
                entity_id=self._generate_entity_id(),
                canonical_name=representative,
                aliases=all_names,
                entity_type=cluster[0].get("entity_type", "UNKNOWN"),
                original_names=[e.get("text", "") for e in cluster],
                block_type=block_type,
                confidence=confidence,
                source_block_ids=source_block_ids
            )
            
            normalized_entities.append(normalized_entity)
        
        return normalized_entities
    
    def _select_representative(
        self, 
        cluster: List[Dict[str, Any]]
    ) -> str:
        """
        选择代表性名称
        
        Args:
            cluster: 实体簇
            
        Returns:
            代表性名称
        """
        # 优先选择词典匹配的 canonical_name
        for entity in cluster:
            if entity.get("is_dict_matched"):
                return entity.get("canonical_name", entity.get("text", ""))
        
        # 选择最长的名称
        names = [e.get("text", "") for e in cluster]
        return max(names, key=len) if names else ""
    
    def _compute_cluster_confidence(
        self, 
        cluster: List[Dict[str, Any]]
    ) -> float:
        """
        计算簇的置信度
        
        Args:
            cluster: 实体簇
            
        Returns:
            置信度分数（0-1）
        """
        if not cluster:
            return 0.0
        
        # 如果簇中有词典匹配的实体，置信度高
        dict_matched_count = sum(
            1 for e in cluster if e.get("is_dict_matched")
        )
        
        if dict_matched_count > 0:
            return min(0.9, 0.7 + 0.2 * (dict_matched_count / len(cluster)))
        
        # 基于簇大小和一致性
        size_factor = min(1.0, len(cluster) / 3.0)  # 簇越大置信度越高
        return 0.5 + 0.3 * size_factor
    
    def _generate_entity_id(self) -> str:
        """生成唯一的实体ID"""
        self.entity_counter += 1
        return f"entity_{self.entity_counter:04d}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取标准化统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "total_entities": self.entity_counter,
            "dictionary_entries": len(self.dictionary.entries),
            "alias_map_size": len(self.dictionary.alias_map)
        }
