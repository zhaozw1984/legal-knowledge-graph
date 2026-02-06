"""
关系归一化智能体

使用纯规则方法对抽取的关系进行归一化处理和Schema校验。
"""

from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass
from loguru import logger
from src.langgraph_agents.state import ExtractionState


@dataclass
class NormalizedRelation:
    """归一化后的关系"""
    subject_entity_id: str
    predicate: str
    object_entity_id: str
    confidence: float
    evidence: Optional[str]
    source_block_id: Optional[str]
    need_coref: bool  # 是否需要指代消解
    validation_passed: bool  # 是否通过Schema校验


class RelationNormalizationAgent:
    """关系归一化智能体"""
    
    def __init__(self):
        """初始化智能体"""
        self.relation_types = self._load_relation_types()
        self.entity_type_schemas = self._load_entity_type_schemas()
    
    def _load_relation_types(self) -> Dict[str, Tuple[str, str]]:
        """
        加载关系类型定义
        
        Returns:
            关系类型 -> (主语实体类型, 宾语实体类型)
        """
        return {
            # Case 相关
            "case_in_court": ("Case", "Court"),
            "case_judged_by": ("Case", "Judge"),
            "case_involved_party": ("Case", "Party"),
            "case_applied_law": ("Case", "Law"),
            "case_evidence": ("Case", "Evidence"),
            
            # Party 相关
            "party_represented_by": ("Party", "Party"),
            "party_against_party": ("Party", "Party"),
            
            # Law 相关
            "law_cited_by_case": ("Law", "Case"),
            "law_interpreted_by_case": ("Law", "Case"),
            
            # 时间相关
            "case_filed_date": ("Case", "Date"),
            "case_hearing_date": ("Case", "Date"),
            "case_judgment_date": ("Case", "Date"),
            
            # 金额相关
            "case_amount": ("Case", "Amount"),
            "party_awarded_amount": ("Party", "Amount"),
        }
    
    def _load_entity_type_schemas(self) -> Dict[str, str]:
        """
        加载实体类型Schema
        
        Returns:
            实体ID -> 实体类型
        """
        return {
            # 实体类型映射
            "Case": "Case",
            "Court": "Court",
            "Judge": "Judge",
            "Party": "Party",
            "Law": "Law",
            "Evidence": "Evidence",
            "LegalTerm": "LegalTerm",
            "Date": "Date",
            "Amount": "Amount"
        }
    
    def normalize(self, state: ExtractionState) -> ExtractionState:
        """
        归一化关系
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始关系归一化和Schema校验")
        
        raw_relations = state.get("relations", [])
        entities = state.get("normalized_entities", [])
        
        if not raw_relations:
            logger.warning("没有需要归一化的关系")
            state["normalized_relations"] = []
            return state
        
        # 构建实体ID到实体类型的映射
        entity_type_map = self._build_entity_type_map(entities)
        
        # 归一化每个关系
        normalized_relations = []
        for relation in raw_relations:
            norm_relation = self._normalize_relation(
                relation, 
                entity_type_map
            )
            normalized_relations.append(norm_relation)
        
        # 去重关系
        normalized_relations = self._deduplicate_relations(normalized_relations)
        
        state["normalized_relations"] = [
            norm_relation.__dict__ 
            for norm_relation in normalized_relations
        ]
        
        logger.info(
            f"关系归一化完成，"
            f"原始关系数: {len(raw_relations)}, "
            f"归一化后: {len(normalized_relations)}, "
            f"需要消解: {sum(1 for r in normalized_relations if r.need_coref)}"
        )
        
        return state
    
    def _build_entity_type_map(
        self, 
        entities: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        构建实体ID到实体类型的映射
        
        Args:
            entities: 实体列表
            
        Returns:
            实体ID -> 实体类型
        """
        entity_type_map = {}
        for entity in entities:
            entity_id = entity.get("entity_id", "")
            entity_type = entity.get("entity_type", "")
            if entity_id and entity_type:
                entity_type_map[entity_id] = entity_type
        
        return entity_type_map
    
    def _normalize_relation(
        self, 
        relation: Dict[str, Any], 
        entity_type_map: Dict[str, str]
    ) -> NormalizedRelation:
        """
        归一化单个关系
        
        Args:
            relation: 原始关系
            entity_type_map: 实体类型映射
            
        Returns:
            归一化后的关系
        """
        subject_id = relation.get("subject", "")
        predicate = relation.get("predicate", "")
        object_id = relation.get("object", "")
        confidence = relation.get("confidence", 1.0)
        evidence = relation.get("evidence", "")
        source_block_id = relation.get("block_id", "")
        
        # 归一化谓词
        normalized_predicate = self._normalize_predicate(predicate)
        
        # Schema校验
        validation_passed = self._validate_schema(
            normalized_predicate,
            subject_id,
            object_id,
            entity_type_map
        )
        
        # 标记是否需要指代消解
        need_coref = self._check_need_coref(
            subject_id,
            object_id,
            entity_type_map
        )
        
        return NormalizedRelation(
            subject_entity_id=subject_id,
            predicate=normalized_predicate,
            object_entity_id=object_id,
            confidence=confidence,
            evidence=evidence,
            source_block_id=source_block_id,
            need_coref=need_coref,
            validation_passed=validation_passed
        )
    
    def _normalize_predicate(self, predicate: str) -> str:
        """
        归一化谓词
        
        Args:
            predicate: 原始谓词
            
        Returns:
            标准化的谓词
        """
        # 谓词别名映射
        predicate_aliases = {
            # 同义词映射
            "在...法院": "case_in_court",
            "由...法官审理": "case_judged_by",
            "涉及当事人": "case_involved_party",
            "适用法律": "case_applied_law",
            "证据": "case_evidence",
            "当事人代表": "party_represented_by",
            "当事人对抗": "party_against_party",
            "引用法律": "law_cited_by_case",
            "解释法律": "law_interpreted_by_case",
            "立案日期": "case_filed_date",
            "开庭日期": "case_hearing_date",
            "判决日期": "case_judgment_date",
            "案件金额": "case_amount",
            "获得金额": "party_awarded_amount"
        }
        
        # 检查是否在别名中
        if predicate in predicate_aliases:
            return predicate_aliases[predicate]
        
        # 检查是否已经标准化
        if predicate in self.relation_types:
            return predicate
        
        # 尝试模糊匹配
        for alias, normalized in predicate_aliases.items():
            if alias in predicate or predicate in alias:
                return normalized
        
        # 无法归一化，返回原始谓词
        logger.warning(f"无法归一化谓词: {predicate}")
        return predicate
    
    def _validate_schema(
        self,
        predicate: str,
        subject_id: str,
        object_id: str,
        entity_type_map: Dict[str, str]
    ) -> bool:
        """
        Schema校验
        
        Args:
            predicate: 谓词
            subject_id: 主语实体ID
            object_id: 宾语实体ID
            entity_type_map: 实体类型映射
            
        Returns:
            是否通过校验
        """
        # 如果谓词不在已知类型中，无法验证
        if predicate not in self.relation_types:
            logger.debug(f"未知谓词类型: {predicate}")
            return False
        
        expected_subject_type, expected_object_type = self.relation_types[predicate]
        
        # 获取实际实体类型
        actual_subject_type = entity_type_map.get(subject_id, "")
        actual_object_type = entity_type_map.get(object_id, "")
        
        # 验证类型匹配
        subject_match = (actual_subject_type == expected_subject_type)
        object_match = (actual_object_type == expected_object_type)
        
        validation_passed = subject_match and object_match
        
        if not validation_passed:
            logger.warning(
                f"Schema校验失败: {predicate} "
                f"预期({expected_subject_type}, {expected_object_type}) "
                f"实际({actual_subject_type}, {actual_object_type})"
            )
        
        return validation_passed
    
    def _check_need_coref(
        self,
        subject_id: str,
        object_id: str,
        entity_type_map: Dict[str, str]
    ) -> bool:
        """
        检查关系是否需要指代消解
        
        Args:
            subject_id: 主语实体ID
            object_id: 宾语实体ID
            entity_type_map: 实体类型映射
            
        Returns:
            是否需要指代消解
        """
        # 如果实体ID不在映射中（可能是代词或临时ID），需要消解
        need_coref = False
        
        if subject_id and subject_id not in entity_type_map:
            need_coref = True
        
        if object_id and object_id not in entity_type_map:
            need_coref = True
        
        return need_coref
    
    def _deduplicate_relations(
        self, 
        relations: List[NormalizedRelation]
    ) -> List[NormalizedRelation]:
        """
        去重关系
        
        Args:
            relations: 关系列表
            
        Returns:
            去重后的关系列表
        """
        seen = set()
        unique_relations = []
        
        for relation in relations:
            # 创建唯一键 (subject, predicate, object)
            key = (
                relation.subject_entity_id,
                relation.predicate,
                relation.object_entity_id
            )
            
            if key not in seen:
                seen.add(key)
                unique_relations.append(relation)
            else:
                logger.debug(f"去重关系: {key}")
        
        logger.info(f"去重前: {len(relations)}, 去重后: {len(unique_relations)}")
        
        return unique_relations
    
    def get_statistics(self, state: ExtractionState) -> Dict[str, Any]:
        """
        获取归一化统计信息
        
        Args:
            state: 当前状态
            
        Returns:
            统计信息字典
        """
        normalized_relations = state.get("normalized_relations", [])
        
        return {
            "total_relations": len(normalized_relations),
            "need_coref_count": sum(
                1 for r in normalized_relations 
                if r.get("need_coref", False)
            ),
            "validation_passed_count": sum(
                1 for r in normalized_relations 
                if r.get("validation_passed", False)
            ),
            "validation_failed_count": sum(
                1 for r in normalized_relations 
                if not r.get("validation_passed", True)
            )
        }
