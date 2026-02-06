"""实体识别智能体模块"""
import json
import re
from typing import Dict, Any, List
from src.langgraph_agents.base_agent import BaseAgent
from src.knowledge_base.entities import ENTITY_TYPES, create_entity, normalize_entity_type
from src.utils.logger import logger


class NERAgent(BaseAgent):
    """实体识别智能体"""
    
    def __init__(self, llm=None):
        """
        初始化实体识别智能体
        """
        super().__init__("NERAgent", llm)
        self.entity_types = list(ENTITY_TYPES.keys())
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建实体识别提示词

        Args:
            context: 包含 raw_text 的上下文

        Returns:
            提示词
        """
        text = context.get("raw_text", "")
        qa_report = context.get("quality_report", {})
        issues = qa_report.get("issues", [])
        recommendations = qa_report.get("recommendations", [])
        backtrack_count = context.get("backtrack_count", 0)

        # 如果有QA反馈且正在回溯，添加指导
        qa_guidance = ""
        if (issues or recommendations) and backtrack_count > 0:
            qa_guidance = "\n\n=== 质量检查反馈 ===\n"
            if issues:
                qa_guidance += "上一次识别的问题：\n"
                qa_guidance += "\n".join(f"- {issue}" for issue in issues)
                qa_guidance += "\n\n"
            if recommendations:
                qa_guidance += "改进建议：\n"
                qa_guidance += "\n".join(f"- {rec}" for rec in recommendations)
                qa_guidance += "\n\n"
            qa_guidance += "请根据以上反馈，针对性地改进本次实体识别结果。\n"

        prompt = f"""你是一个专业的法律文书实体识别专家。请从以下香港法律文书中识别所有相关实体。

支持的实体类型：
{json.dumps(self._get_entity_type_descriptions(), indent=2, ensure_ascii=False)}

原文：
{text}

请识别所有实体，以 JSON 格式输出，格式如下：
{{
    "entities": [
        {{
            "type": "实体类型",
            "text": "实体在原文中的表述",
            "start_pos": 起始位置（数字），
            "end_pos": 结束位置（数字），
            "attributes": {{
                "具体属性": "属性值"
            }}
        }}
    ]
}}

注意：
1. 实体类型必须从支持的类型中选择
2. 提取实体在原文中的准确位置（start_pos 和 end_pos）
3. 根据实体类型填写相应的 attributes 字段
4. 保持原文表述的准确性
5. 只输出 JSON，不要包含其他解释文本
{qa_guidance}
开始识别："""
        return prompt
    
    def _get_entity_type_descriptions(self) -> Dict[str, str]:
        """获取实体类型描述"""
        return {
            "Case": "案件信息（案件编号、标题、日期、引证）",
            "Court": "法院（名称、级别、管辖区）",
            "Judge": "法官（姓名、职称）",
            "Party": "当事人（姓名、类型：plaintiff/defendant、角色）",
            "Law": "法律条文（名称、类型、条款）",
            "Evidence": "证据（类型、描述）",
            "LegalTerm": "法律术语（术语、定义）",
            "Date": "日期（日期、类型：filing/hearing/judgment）",
            "Amount": "金额（金额、货币）",
        }
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行实体识别（块级处理）
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        logger.info(f"[{self.name}] 开始执行块级实体识别...")
        
        # 获取文档块
        document_blocks = state.get("document_blocks", [])
        
        if not document_blocks:
            # 如果没有文档块，对全文执行NER（兼容旧逻辑）
            return self._process_full_text(state)
        
        # 块级处理
        all_entities = []
        block_entities = {}  # block_id -> 实体列表
        
        for block in document_blocks:
            block_id = block.get("block_id", "")
            block_type = block.get("block_type", "")
            block_content = block.get("content", "")
            
            if not block_content:
                continue
            
            logger.debug(f"[{self.name}] 处理块 {block_id} ({block_type})")
            
            # 为当前块执行NER
            block_result = self._process_block(block)
            
            # 添加块级信息
            for entity in block_result:
                entity["block_id"] = block_id
                entity["block_type"] = block_type
            
            block_entities[block_id] = block_result
            all_entities.extend(block_result)
        
        # 为所有实体分配唯一ID
        all_entities = self._assign_entity_ids(all_entities)
        
        state["entities"] = all_entities
        state["block_entities"] = block_entities
        state["current_stage"] = "ner_completed"
        
        logger.info(
            f"[{self.name}] 块级实体识别完成，"
            f"共处理 {len(document_blocks)} 个块，"
            f"识别到 {len(all_entities)} 个实体"
        )
        
        return state
    
    def _process_full_text(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        对全文执行实体识别（兼容旧逻辑）
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        logger.info(f"[{self.name}] 对全文执行实体识别...")
        
        # 构建 prompt 并调用 LLM
        prompt = self.build_prompt(state)
        try:
            response = self.invoke_llm(prompt)
            entities = self._parse_response(response)
            
            # 验证和清理实体
            valid_entities = self._validate_entities(entities, state["raw_text"])
            
            # 过滤代词
            valid_entities = self._filter_pronouns(valid_entities)
            
            # 为实体生成唯一 ID
            valid_entities = self._assign_entity_ids(valid_entities)
            
            state["entities"] = valid_entities
            state["block_entities"] = {}
            state["current_stage"] = "ner_completed"
            logger.info(f"[{self.name}] 识别到 {len(valid_entities)} 个实体")
            
        except Exception as e:
            logger.error(f"[{self.name}] 实体识别失败: {e}")
            state["error_messages"].append(f"NER 失败: {str(e)}")
            raise
        
        return state
    
    def _process_block(self, block: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        处理单个文档块的实体识别
        
        Args:
            block: 文档块字典
            
        Returns:
            该块的实体列表
        """
        block_content = block.get("content", "")
        block_type = block.get("block_type", "")
        block_id = block.get("block_id", "")
        
        # 为当前块构建 prompt
        prompt = self._build_block_prompt(block_content, block_type)
        
        try:
            response = self.invoke_llm(prompt)
            entities = self._parse_response(response)
            
            # 验证和清理实体
            valid_entities = self._validate_entities(entities, block_content)
            
            # 过滤代词（约束：不识别代词）
            valid_entities = self._filter_pronouns(valid_entities)
            
            logger.debug(f"块 {block_id} 识别到 {len(valid_entities)} 个实体")
            
            return valid_entities
            
        except Exception as e:
            logger.error(f"块 {block_id} 实体识别失败: {e}")
            return []
    
    def _build_block_prompt(self, block_content: str, block_type: str) -> str:
        """
        为单个块构建实体识别提示词
        
        Args:
            block_content: 块内容
            block_type: 块类型
            
        Returns:
            提示词
        """
        prompt = f"""你是一个专业的法律文书实体识别专家。请从以下文档块中识别所有相关实体。

文档块类型: {block_type}

支持的实体类型：
{self._get_entity_type_descriptions()}

文档块内容：
{block_content}

请识别所有实体，以 JSON 格式输出，格式如下：
{{
    "entities": [
        {{
            "type": "实体类型",
            "text": "实体在原文中的表述",
            "start_pos": 起始位置（数字），
            "end_pos": 结束位置（数字），
            "attributes": {{
                "具体属性": "属性值"
            }}
        }}
    ]
}}

注意：
1. 实体类型必须从支持的类型中选择
2. 提取实体在原文中的准确位置（start_pos 和 end_pos）
3. 根据实体类型填写相应的 attributes 字段
4. 保持原文表述的准确性
5. **不要识别代词**（如"他"、"她"、"该被告"、"其"等）
6. 只输出 JSON，不要包含其他解释文本

开始识别："""
        return prompt
    
    def _filter_pronouns(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤代词实体
        
        Args:
            entities: 实体列表
            
        Returns:
            过滤后的实体列表
        """
        # 常见中文代词
        pronouns = {
            "他", "她", "它", "它们", "他们", "她们", "它们们",
            "其", "该", "此", "本", "上述", "该被告", "该原告",
            "原告", "被告"  # 这些可能在语境中作为代词使用
        }
        
        filtered_entities = []
        
        for entity in entities:
            entity_text = entity.get("text", "").strip()
            
            # 检查是否为代词
            is_pronoun = entity_text in pronouns
            
            if is_pronoun:
                logger.debug(f"过滤代词实体: {entity_text}")
                continue
            
            filtered_entities.append(entity)
        
        filtered_count = len(entities) - len(filtered_entities)
        if filtered_count > 0:
            logger.info(f"过滤了 {filtered_count} 个代词实体")
        
        return filtered_entities
    
    def _parse_response(self, response: str) -> List[Dict[str, Any]]:
        """解析 LLM 响应"""
        try:
            # 尝试直接解析 JSON
            data = json.loads(response.strip())
            if isinstance(data, dict) and "entities" in data:
                return data["entities"]
            elif isinstance(data, list):
                return data
            else:
                logger.warning(f"响应格式不符合预期: {response[:200]}")
                return []
        except json.JSONDecodeError:
            # 尝试从响应中提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    if isinstance(data, dict) and "entities" in data:
                        return data["entities"]
                except:
                    pass
            
            logger.error(f"无法解析 LLM 响应: {response[:500]}")
            return []
    
    def _validate_entities(self, entities: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """验证实体"""
        valid_entities = []
        
        for entity in entities:
            # 验证必需字段
            if not all(key in entity for key in ["type", "text"]):
                logger.warning(f"实体缺少必需字段: {entity}")
                continue
            
            # 归一化实体类型
            entity["type"] = normalize_entity_type(entity["type"])
            
            # 验证实体类型是否支持
            if entity["type"] not in ENTITY_TYPES:
                logger.warning(f"不支持的实体类型: {entity['type']}")
                continue
            
            # 验证文本位置（如果提供了位置）
            if "start_pos" in entity and "end_pos" in entity:
                start = entity["start_pos"]
                end = entity["end_pos"]
                if 0 <= start <= end <= len(text):
                    extracted_text = text[start:end]
                    # 简单匹配检查（允许一些差异）
                    if entity["text"] not in extracted_text and extracted_text not in entity["text"]:
                        logger.warning(f"位置验证失败: {entity['text']}")
            else:
                # 如果没有提供位置，尝试在文本中查找
                if entity["text"] in text:
                    entity["start_pos"] = text.find(entity["text"])
                    entity["end_pos"] = entity["start_pos"] + len(entity["text"])
            
            valid_entities.append(entity)
        
        return valid_entities
    
    def _assign_entity_ids(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为实体分配唯一 ID"""
        type_counters = {}
        
        for entity in entities:
            entity_type = entity["type"]
            
            # 初始化计数器
            if entity_type not in type_counters:
                type_counters[entity_type] = 0
            
            # 生成 ID
            entity["id"] = f"{entity_type.lower()}_{type_counters[entity_type]:03d}"
            entity["confidence"] = entity.get("confidence", 1.0)
            
            type_counters[entity_type] += 1
        
        return entities
