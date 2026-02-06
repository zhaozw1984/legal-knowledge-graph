"""关系抽取智能体模块"""
import json
from typing import Dict, Any, List
from src.langgraph_agents.base_agent import BaseAgent
from src.knowledge_base.schemas import RELATION_TYPES
from src.utils.logger import logger


class RelationAgent(BaseAgent):
    """关系抽取智能体"""
    
    def __init__(self, llm=None):
        """初始化关系抽取智能体"""
        super().__init__("RelationAgent", llm)
        self.relation_types = RELATION_TYPES
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建关系抽取提示词

        Args:
            context: 包含 raw_text 和 normalized_entities 的上下文

        Returns:
            提示词
        """
        text = context.get("raw_text", "")
        entities = context.get("normalized_entities", [])
        qa_report = context.get("quality_report", {})
        issues = qa_report.get("issues", [])
        recommendations = qa_report.get("recommendations", [])
        backtrack_count = context.get("backtrack_count", 0)

        # 构建实体列表
        entity_list = "\n".join([
            f"- {e['id']}: {e['type']} - {e['text']}"
            for e in entities
        ])

        # 构建关系类型描述
        relation_desc = "\n".join([
            f"- {rtype}: {description}"
            for rtype, description in self.relation_types.items()
        ])

        # 如果有QA反馈且正在回溯，添加指导
        qa_guidance = ""
        if (issues or recommendations) and backtrack_count > 0:
            qa_guidance = "\n\n=== 质量检查反馈 ===\n"
            if issues:
                qa_guidance += "上一次关系抽取的问题：\n"
                qa_guidance += "\n".join(f"- {issue}" for issue in issues)
                qa_guidance += "\n\n"
            if recommendations:
                qa_guidance += "改进建议：\n"
                qa_guidance += "\n".join(f"- {rec}" for rec in recommendations)
                qa_guidance += "\n\n"
            qa_guidance += "请根据以上反馈，针对性地改进本次关系抽取结果。\n"

        prompt = f"""你是一个专业的法律关系抽取专家。请从文本中识别实体之间的关系。

实体列表：
{entity_list}

支持的关系类型：
{relation_desc}

原文：
{text}

任务：
1. 识别实体之间的语义关系
2. 确定关系类型（从支持的关系类型中选择）
3. 标记关系证据（在原文中的位置或句子）

输出格式（JSON）：
{{
    "relations": [
        {{
            "subject": "主语实体ID",
            "predicate": "关系类型",
            "object": "宾语实体ID",
            "confidence": "关系置信度",
            "evidence": "支持该关系的原文片段"
        }}
    ]
}}

注意：
1. subject 和 object 必须是实体列表中存在的 ID
2. predicate 必须是支持的关系类型
3. confidence 范围为 0-1
4. 只抽取明确表达的关系，不要猜测
5. 只输出 JSON
{qa_guidance}
开始抽取："""
        return prompt
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行关系抽取（块级循环抽取）
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        logger.info(f"[{self.name}] 开始执行块级循环关系抽取...")
        
        if not state.get("normalized_entities"):
            logger.warning(f"[{self.name}] 没有实体，无法抽取关系")
            state["relations"] = []
            return state
        
        # 获取文档块
        document_blocks = state.get("document_blocks", [])
        
        if not document_blocks:
            # 如果没有文档块，对全文执行关系抽取（兼容旧逻辑）
            return self._process_full_text(state)
        
        # 块级循环抽取
        all_relations = []
        
        for block in document_blocks:
            block_id = block.get("block_id", "")
            block_type = block.get("block_type", "")
            block_content = block.get("content", "")
            
            if not block_content:
                continue
            
            logger.debug(f"[{self.name}] 处理块 {block_id} ({block_type})")
            
            # 为当前块抽取关系
            block_relations = self._process_block(block, state)
            
            # 添加块级信息
            for relation in block_relations:
                relation["block_id"] = block_id
            
            all_relations.extend(block_relations)
        
        # 去重关系
        all_relations = self._deduplicate_relations(all_relations)
        
        state["relations"] = all_relations
        state["current_stage"] = "relation_completed"
        
        logger.info(
            f"[{self.name}] 块级关系抽取完成，"
            f"共处理 {len(document_blocks)} 个块，"
            f"抽取到 {len(all_relations)} 个关系"
        )
        
        return state
    
    def _process_full_text(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        对全文执行关系抽取（兼容旧逻辑）
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        logger.info(f"[{self.name}] 对全文执行关系抽取...")
        
        # 构建 prompt 并调用 LLM
        prompt = self.build_prompt(state)
        try:
            response = self.invoke_llm(prompt)
            relations = self._parse_and_validate(response, state["normalized_entities"])
            
            state["relations"] = relations
            state["current_stage"] = "relation_completed"
            logger.info(f"[{self.name}] 抽取到 {len(relations)} 个关系")
            
        except Exception as e:
            logger.error(f"[{self.name}] 关系抽取失败: {e}")
            state["error_messages"].append(f"关系抽取失败: {str(e)}")
            state["relations"] = []
            raise
        
        return state
    
    def _process_block(self, block: Dict[str, Any], state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        处理单个文档块的关系抽取
        
        Args:
            block: 文档块字典
            state: 当前状态
            
        Returns:
            该块的关系列表
        """
        block_content = block.get("content", "")
        block_type = block.get("block_type", "")
        block_id = block.get("block_id", "")
        
        # 获取该块的实体
        block_entities = state.get("block_entities", {}).get(block_id, [])
        all_entities = state.get("normalized_entities", [])
        
        if not block_entities:
            logger.debug(f"块 {block_id} 没有实体，跳过")
            return []
        
        # 为当前块构建 prompt
        prompt = self._build_block_prompt(
            block_content, 
            block_entities, 
            all_entities,
            block_type
        )
        
        try:
            response = self.invoke_llm(prompt)
            relations = self._parse_and_validate(response, all_entities)
            
            logger.debug(f"块 {block_id} 抽取到 {len(relations)} 个关系")
            
            return relations
            
        except Exception as e:
            logger.error(f"块 {block_id} 关系抽取失败: {e}")
            return []
    
    def _build_block_prompt(
        self, 
        block_content: str, 
        block_entities: List[Dict[str, Any]],
        all_entities: List[Dict[str, Any]],
        block_type: str
    ) -> str:
        """
        为单个块构建关系抽取提示词
        
        Args:
            block_content: 块内容
            block_entities: 该块的实体列表
            all_entities: 所有标准化实体列表
            block_type: 块类型
            
        Returns:
            提示词
        """
        # 构建块实体列表
        block_entity_list = "\n".join([
            f"- {e.get('entity_id', '')}: {e.get('entity_type', '')} - {e.get('canonical_name', '')}"
            for e in block_entities
        ])
        
        # 构建全局实体列表（用于跨块引用）
        all_entity_list = "\n".join([
            f"- {e.get('entity_id', '')}: {e.get('entity_type', '')} - {e.get('canonical_name', '')}"
            for e in all_entities[:20]  # 限制数量避免prompt过长
        ])
        
        # 构建关系类型描述
        relation_desc = "\n".join([
            f"- {rtype}: {description}"
            for rtype, description in self.relation_types.items()
        ])
        
        prompt = f"""你是一个专业的法律关系抽取专家。请从文档块中识别实体之间的关系。

文档块类型: {block_type}

当前块的实体列表：
{block_entity_list}

全局实体列表（前20个）：
{all_entity_list}

支持的关系类型：
{relation_desc}

文档块内容：
{block_content}

任务：
1. 识别实体之间的语义关系
2. 确定关系类型（从支持的关系类型中选择）
3. 标记关系证据（在原文中的位置或句子）

输出格式（JSON）：
{{
    "relations": [
        {{
            "subject": "主语实体ID或原始文本",
            "predicate": "关系类型",
            "object": "宾语实体ID或原始文本",
            "confidence": "关系置信度（0-1）",
            "evidence": "支持该关系的原文片段"
        }}
    ]
}}

重要约束：
1. **如果实体在全局实体列表中存在，必须使用实体ID**（如 "entity_001"）
2. **如果实体是代词或未识别的实体，必须保留原始文本**（如 "该被告"、"其"）
3. predicate 必须是支持的关系类型
4. confidence 范围为 0-1
5. 只抽取明确表达的关系，不要猜测
6. 只输出 JSON，不要包含其他解释文本

开始抽取："""
        return prompt
    
    def _deduplicate_relations(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            # 创建唯一键
            key = (
                relation.get("subject", ""),
                relation.get("predicate", ""),
                relation.get("object", "")
            )
            
            if key not in seen:
                seen.add(key)
                unique_relations.append(relation)
            else:
                logger.debug(f"去重关系: {key}")
        
        logger.info(f"去重前: {len(relations)}, 去重后: {len(unique_relations)}")
        
        return unique_relations
    
    def _parse_and_validate(self, response: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析并验证关系
        
        Args:
            response: LLM 响应
            entities: 实体列表（用于验证）
            
        Returns:
            验证通过的关系列表
        """
        try:
            # 清理响应
            response = response.strip()
            
            # 检查响应是否为空
            if not response:
                logger.warning("关系抽取响应为空")
                return []
            
            # 尝试解析 JSON
            data = json.loads(response)
            relation_list = data.get("relations", [])
            
            # 创建实体 ID 集合用于验证
            entity_ids = {e["id"] for e in entities}
            valid_relations = []
            
            for relation in relation_list:
                # 验证必需字段
                if not all(key in relation for key in ["subject", "predicate", "object"]):
                    logger.warning(f"关系缺少必需字段: {relation}")
                    continue
                
                # 验证实体 ID 存在
                if relation["subject"] not in entity_ids:
                    logger.warning(f"主语实体不存在: {relation['subject']}")
                    continue
                
                if relation["object"] not in entity_ids:
                    logger.warning(f"宾语实体不存在: {relation['object']}")
                    continue
                
                # 验证关系类型
                if relation["predicate"] not in self.relation_types:
                    logger.warning(f"不支持的关系类型: {relation['predicate']}")
                    continue
                
                # 验证置信度
                relation["confidence"] = relation.get("confidence", 0.5)
                if not 0 <= relation["confidence"] <= 1:
                    relation["confidence"] = 0.5
                
                valid_relations.append(relation)
            
            return valid_relations
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}, 响应内容: {response[:500]}")
            return []
        except Exception as e:
            logger.error(f"解析关系响应失败: {e}")
            return []
