"""指代消解智能体模块"""
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict
from src.langgraph_agents.base_agent import BaseAgent
from src.utils.logger import logger


class CorefAgent(BaseAgent):
    """指代消解智能体（Relation-guided图推理）"""
    
    def __init__(self, llm=None):
        """初始化指代消解智能体"""
        super().__init__("CorefAgent", llm)
        self.max_hops = 3  # 最大推理跳数
        self.similarity_threshold = 0.5  # 相似度阈值
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建指代消解提示词（已废弃，使用图推理替代）
        
        保留此方法以兼容BaseAgent接口
        """
        return ""
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Relation-guided指代消解
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        logger.info(f"[{self.name}] 开始执行Relation-guided指代消解...")
        
        # 获取归一化后的关系
        normalized_relations = state.get("normalized_relations", [])
        entities = state.get("normalized_entities", [])
        
        if not normalized_relations or not entities:
            logger.warning(f"[{self.name}] 没有关系或实体，跳过消解")
            state["resolved_entities"] = entities
            return state
        
        # 构建实体关系图
        entity_graph = self._build_entity_graph(normalized_relations)
        
        # 构建实体ID到实体的映射
        entity_map = {e.get("entity_id", ""): e for e in entities}
        
        # 消解关系中的代词引用
        resolved_relations = []
        coref_count = 0
        
        for relation in normalized_relations:
            resolved_relation = self._resolve_relation(
                relation, 
                entity_graph, 
                entity_map
            )
            
            if resolved_relation.get("was_resolved", False):
                coref_count += 1
            
            resolved_relations.append(resolved_relation)
        
        # 更新状态
        state["normalized_relations"] = resolved_relations
        state["resolved_entities"] = entities  # 实体本身不变，只是关系中的引用被消解
        state["current_stage"] = "coref_completed"
        
        logger.info(
            f"[{self.name}] 指代消解完成，"
            f"共 {len(normalized_relations)} 个关系，"
            f"消解了 {coref_count} 个代词引用"
        )
        
        return state
    
    def _build_entity_graph(self, relations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        构建实体关系图
        
        Args:
            relations: 关系列表
            
        Returns:
            实体ID -> 邻接关系列表
        """
        graph = defaultdict(list)
        
        for relation in relations:
            subject = relation.get("subject_entity_id", "")
            object_id = relation.get("object_entity_id", "")
            predicate = relation.get("predicate", "")
            
            if subject and object_id:
                # 双向添加边
                graph[subject].append({
                    "target": object_id,
                    "predicate": predicate,
                    "direction": "out"
                })
                graph[object_id].append({
                    "target": subject,
                    "predicate": predicate,
                    "direction": "in"
                })
        
        logger.debug(f"构建实体图，共 {len(graph)} 个节点")
        return dict(graph)
    
    def _resolve_relation(
        self,
        relation: Dict[str, Any],
        entity_graph: Dict[str, List[Dict[str, Any]]],
        entity_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        消解单个关系中的代词引用
        
        Args:
            relation: 原始关系
            entity_graph: 实体关系图
            entity_map: 实体映射
            
        Returns:
            消解后的关系
        """
        resolved_relation = relation.copy()
        was_resolved = False
        
        # 消解主语
        subject = relation.get("subject_entity_id", "")
        resolved_subject = self._resolve_pronoun(
            subject, 
            relation, 
            entity_graph, 
            entity_map
        )
        
        if resolved_subject != subject:
            resolved_relation["subject_entity_id"] = resolved_subject
            resolved_relation["original_subject"] = subject
            was_resolved = True
            logger.debug(f"消解主语: {subject} -> {resolved_subject}")
        
        # 消解宾语
        object_id = relation.get("object_entity_id", "")
        resolved_object = self._resolve_pronoun(
            object_id, 
            relation, 
            entity_graph, 
            entity_map
        )
        
        if resolved_object != object_id:
            resolved_relation["object_entity_id"] = resolved_object
            resolved_relation["original_object"] = object_id
            was_resolved = True
            logger.debug(f"消解宾语: {object_id} -> {resolved_object}")
        
        resolved_relation["was_resolved"] = was_resolved
        return resolved_relation
    
    def _resolve_pronoun(
        self,
        pronoun: str,
        relation: Dict[str, Any],
        entity_graph: Dict[str, List[Dict[str, Any]]],
        entity_map: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        使用图推理消解代词
        
        Args:
            pronoun: 代词文本
            relation: 包含代词的关系
            entity_graph: 实体关系图
            entity_map: 实体映射
            
        Returns:
            消解后的实体ID
        """
        # 如果已经是实体ID，直接返回
        if pronoun in entity_map:
            return pronoun
        
        # 提取代词的语义线索（如"该被告" -> Party类型）
        pronoun_clues = self._extract_pronoun_clues(pronoun)
        
        # 在图中查找候选实体
        candidates = self._find_candidate_entities(
            pronoun_clues,
            entity_graph,
            entity_map,
            relation
        )
        
        # 如果没有候选，返回原代词
        if not candidates:
            logger.debug(f"未找到代词 '{pronoun}' 的候选实体")
            return pronoun
        
        # 选择最佳匹配
        best_match = self._select_best_candidate(
            pronoun,
            candidates,
            relation
        )
        
        return best_match
    
    def _extract_pronoun_clues(self, pronoun: str) -> Dict[str, Any]:
        """
        从代词中提取语义线索
        
        Args:
            pronoun: 代词文本
            
        Returns:
            线索字典
        """
        clues = {
            "text": pronoun,
            "entity_types": [],
            "keywords": []
        }
        
        # 常见代词模式
        if "被告" in pronoun:
            clues["entity_types"].append("Party")
            clues["keywords"].append("defendant")
        elif "原告" in pronoun:
            clues["entity_types"].append("Party")
            clues["keywords"].append("plaintiff")
        elif "法院" in pronoun:
            clues["entity_types"].append("Court")
        elif "法官" in pronoun:
            clues["entity_types"].append("Judge")
        elif "证据" in pronoun:
            clues["entity_types"].append("Evidence")
        
        # 代词类型
        if pronoun in ["他", "她", "它", "其", "该", "此"]:
            clues["is_pure_pronoun"] = True
        else:
            clues["is_pure_pronoun"] = False
        
        return clues
    
    def _find_candidate_entities(
        self,
        clues: Dict[str, Any],
        entity_graph: Dict[str, List[Dict[str, Any]]],
        entity_map: Dict[str, Dict[str, Any]],
        relation: Dict[str, Any]
    ) -> List[Tuple[str, float]]:
        """
        在图中查找候选实体
        
        Args:
            clues: 代词线索
            entity_graph: 实体关系图
            entity_map: 实体映射
            relation: 包含代词的关系
            
        Returns:
            [(实体ID, 相似度分数), ...]
        """
        candidates = []
        
        # 确定搜索起点：使用关系中的另一个端点
        subject = relation.get("subject_entity_id", "")
        object_id = relation.get("object_entity_id", "")
        
        # 找到关系中的已知实体端点
        known_entity = None
        if subject and subject in entity_map and object_id and object_id not in entity_map:
            known_entity = subject
        elif object_id and object_id in entity_map and subject and subject not in entity_map:
            known_entity = object_id
        
        if not known_entity:
            # 如果两个端点都是代词，无法消解
            return candidates
        
        # 从已知实体开始进行多跳推理
        candidates = self._graph_bfs(
            known_entity,
            clues,
            entity_graph,
            entity_map,
            max_hops=self.max_hops
        )
        
        # 按相似度排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates
    
    def _graph_bfs(
        self,
        start_entity: str,
        clues: Dict[str, Any],
        entity_graph: Dict[str, List[Dict[str, Any]]],
        entity_map: Dict[str, Dict[str, Any]],
        max_hops: int
    ) -> List[Tuple[str, float]]:
        """
        广度优先搜索查找候选实体
        
        Args:
            start_entity: 起始实体ID
            clues: 代词线索
            entity_graph: 实体关系图
            entity_map: 实体映射
            max_hops: 最大跳数
            
        Returns:
            [(实体ID, 相似度分数), ...]
        """
        candidates = []
        visited = set([start_entity])
        
        # 队列：(实体ID, 当前跳数, 路径相似度)
        queue = [(start_entity, 0, 1.0)]
        
        while queue:
            current_entity, hops, path_similarity = queue.pop(0)
            
            # 跳过起始点
            if current_entity == start_entity:
                pass
            else:
                # 计算该实体的匹配分数
                entity_data = entity_map.get(current_entity, {})
                entity_type = entity_data.get("entity_type", "")
                
                # 计算类型匹配度
                type_score = 0.0
                if clues["entity_types"]:
                    type_score = 1.0 if entity_type in clues["entity_types"] else 0.5
                
                # 计算整体分数（路径相似度 * 类型匹配度）
                score = path_similarity * (0.3 + 0.7 * type_score)
                
                candidates.append((current_entity, score))
            
            # 扩展到邻居节点
            if hops < max_hops and current_entity in entity_graph:
                for edge in entity_graph[current_entity]:
                    neighbor = edge["target"]
                    if neighbor not in visited:
                        visited.add(neighbor)
                        # 根据关系类型调整相似度衰减
                        decay = 0.8 if edge["predicate"] in ["case_involved_party", "party_against_party"] else 0.6
                        new_similarity = path_similarity * decay
                        queue.append((neighbor, hops + 1, new_similarity))
        
        return candidates
    
    def _select_best_candidate(
        self,
        pronoun: str,
        candidates: List[Tuple[str, float]],
        relation: Dict[str, Any]
    ) -> str:
        """
        选择最佳候选实体
        
        Args:
            pronoun: 代词
            candidates: 候选列表 [(实体ID, 相似度), ...]
            relation: 关系上下文
            
        Returns:
            最佳实体ID
        """
        if not candidates:
            return pronoun
        
        # 过滤掉相似度过低的候选
        filtered = [
            (entity_id, score) 
            for entity_id, score in candidates 
            if score >= self.similarity_threshold
        ]
        
        if not filtered:
            # 如果没有通过阈值的，返回最高分的
            return candidates[0][0]
        
        # 返回最高分的候选
        return filtered[0][0]
