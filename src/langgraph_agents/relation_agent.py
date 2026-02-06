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
        执行关系抽取
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        logger.info(f"[{self.name}] 开始执行关系抽取...")
        
        if not state.get("normalized_entities"):
            logger.warning(f"[{self.name}] 没有实体，无法抽取关系")
            state["relations"] = []
            return state
        
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
