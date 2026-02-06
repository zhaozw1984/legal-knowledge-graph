"""指代消解智能体模块"""
import json
from typing import Dict, Any, List
from src.langgraph_agents.base_agent import BaseAgent
from src.utils.logger import logger


class CorefAgent(BaseAgent):
    """指代消解智能体"""
    
    def __init__(self, llm=None):
        """初始化指代消解智能体"""
        super().__init__("CorefAgent", llm)
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建指代消解提示词

        Args:
            context: 包含 raw_text 和 entities 的上下文

        Returns:
            提示词
        """
        text = context.get("raw_text", "")
        entities = context.get("entities", [])
        qa_report = context.get("quality_report", {})
        issues = qa_report.get("issues", [])
        recommendations = qa_report.get("recommendations", [])
        backtrack_count = context.get("backtrack_count", 0)

        # 构建实体列表字符串
        entity_list = "\n".join([
            f"- {e['id']}: {e['type']} - {e['text']}"
            for e in entities
        ])

        # 如果有QA反馈且正在回溯，添加指导
        qa_guidance = ""
        if (issues or recommendations) and backtrack_count > 0:
            qa_guidance = "\n\n=== 质量检查反馈 ===\n"
            if issues:
                qa_guidance += "上一次消解的问题：\n"
                qa_guidance += "\n".join(f"- {issue}" for issue in issues)
                qa_guidance += "\n\n"
            if recommendations:
                qa_guidance += "改进建议：\n"
                qa_guidance += "\n".join(f"- {rec}" for rec in recommendations)
                qa_guidance += "\n\n"
            qa_guidance += "请根据以上反馈，针对性地改进本次指代消解结果。\n"

        prompt = f"""你是一个专业的指代消解专家。请解决以下法律文本中的指代问题。

原文：
{text}

已识别的实体：
{entity_list}

任务：
1. 找出文本中所有指代词（如"他"、"该原告"、"被告方"等）
2. 将这些指代词映射到对应的实体
3. 更新实体的文本表述，消除歧义

输出格式（JSON）：
{{
    "resolved_entities": [
        {{
            "id": "原实体ID",
            "text": "消解后的完整表述",
            "coref_chains": ["指代词1", "指代词2"]
        }}
    ]
}}

注意：
1. 实体 ID 必须与已识别实体列表一致
2. 保持实体的其他属性不变
3. 只输出 JSON，不要包含其他文本
{qa_guidance}
开始消解："""
        return prompt
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行指代消解
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        logger.info(f"[{self.name}] 开始执行指代消解...")
        
        #跳过当前agent
        #state["resolved_entities"] = state.get("entities", [])
        #return state

        if not state.get("entities"):
            logger.warning(f"[{self.name}] 没有实体需要消解")
            state["resolved_entities"] = state.get("entities", [])
            return state
        
        # 构建 prompt 并调用 LLM
        prompt = self.build_prompt(state)
        try:
            response = self.invoke_llm(prompt)
            resolved_entities = self._parse_and_merge(response, state["entities"])
            
            state["resolved_entities"] = resolved_entities
            state["current_stage"] = "coref_completed"
            logger.info(f"[{self.name}] 消解完成，处理了 {len(resolved_entities)} 个实体")
            
        except Exception as e:
            logger.error(f"[{self.name}] 指代消解失败: {e}")
            state["error_messages"].append(f"指代消解失败: {str(e)}")
            # 如果消解失败，使用原始实体
            state["resolved_entities"] = state.get("entities", [])
            raise
        
        return state
    
    def _parse_and_merge(self, response: str, original_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析响应并合并到原始实体
        
        Args:
            response: LLM 响应
            original_entities: 原始实体列表
            
        Returns:
            合并后的实体列表
        """
        try:
            # 清理响应
            response = response.strip()
            
            # 检查响应是否为空
            if not response:
                logger.warning("指代消解响应为空")
                return original_entities
            
            # 尝试解析 JSON
            data = json.loads(response)
            resolved_list = data.get("resolved_entities", [])
            
            if not resolved_list:
                logger.warning("指代消解响应中没有 resolved_entities")
                return original_entities
            
            # 创建映射
            entity_map = {e["id"]: e for e in original_entities}
            
            # 更新实体
            for resolved in resolved_list:
                entity_id = resolved.get("id")
                if entity_id in entity_map:
                    # 更新文本表述
                    entity_map[entity_id]["text"] = resolved.get("text", entity_map[entity_id]["text"])
                    # 保存指代链
                    entity_map[entity_id]["attributes"]["coref_chains"] = resolved.get("coref_chains", [])
            
            return list(entity_map.values())
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}, 响应内容: {response[:500]}")
            return original_entities
        except Exception as e:
            logger.error(f"解析指代消解响应失败: {e}")
            return original_entities
