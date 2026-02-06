# 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

复制并编辑 `.env` 文件：

```bash
cp .env.example .env
```

必需配置项：

```env
# DeepSeek API Key（必需）
DASHSCOPE_API_KEY=your-api-key-here

# Neo4j（可选，如果不使用可以留空或运行时加 --no-neo4j）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

### 3. 运行测试

运行完整测试验证安装：

```bash
python test_pipeline.py
```

### 4. 处理 PDF 文件

处理 `input` 目录中的所有 PDF：

```bash
python main.py
```

## 使用场景

### 场景 1：处理单个文件

```bash
python main.py --input input/CACC000510_2005.pdf
```

### 场景 2：处理整个目录

```bash
python main.py --input input/
```

### 场景 3：不使用 Neo4j（仅抽取）

```bash
python main.py --no-neo4j
```

### 场景 4：导出为 JSON

```bash
python main.py --export output/result.json
```

## 输出说明

### 控制台输出

```
============================================================
处理结果摘要
============================================================

文件 1: input/CACC000510_2005.pdf
  状态: 成功
  实体数: 15
  关系数: 20
  质量评分: 0.85

------------------------------------------------------------
总计: 成功 3/6
总实体数: 42
总关系数: 56
============================================================
```

### 文件输出

- **中间文本文件**：`output/*.txt`（从 PDF 提取的纯文本）
- **日志文件**：`output/logs/app.log`（详细运行日志）
- **JSON 导出**：`output/knowledge_graph.json`（如果使用了 `--export`）

## Neo4j 查询示例

连接到 Neo4j 后，可以执行以下查询：

### 查看所有案件

```cypher
MATCH (c:Case)
RETURN c
LIMIT 10
```

### 查看案件关系图

```cypher
MATCH (case:Case)-[r]->(other)
RETURN case, r, other
LIMIT 20
```

### 查找特定法官的所有案件

```cypher
MATCH (j:Judge)-[:case_judged_by]->(c:Case)
WHERE j.name = "法官姓名"
RETURN j, c
```

### 统计实体数量

```cypher
MATCH (n)
RETURN labels(n) as type, count(n) as count
```

## 故障排除

### 问题 1：ModuleNotFoundError

**错误信息**：
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案**：
```bash
pip install -r requirements.txt
```

### 问题 2：API 调用失败

**错误信息**：
```
Error: Failed to call LLM: ...
```

**解决方案**：
1. 检查 `.env` 中的 `DASHSCOPE_API_KEY` 是否正确
2. 确认网络连接正常
3. 检查 API 额度是否充足

### 问题 3：Neo4j 连接失败

**错误信息**：
```
Unable to connect to Neo4j database
```

**解决方案**：
1. 确认 Neo4j 服务正在运行
2. 检查连接配置是否正确
3. 使用 `--no-neo4j` 跳过 Neo4j 存储

### 问题 4：PDF 提取为空

**问题**：PDF 文件提取成功，但文本为空

**解决方案**：
1. 检查 PDF 文件是否是扫描版（需要 OCR）
2. 尝试使用其他 PDF 提取工具
3. 确认 PDF 文件没有密码保护

## 性能优化

### 1. 调整 LLM 温度

较低的温度（如 0.3）会得到更确定的结果，较高温度（如 0.9）会增加多样性。

在 `.env` 中配置：
```env
LLM_TEMPERATURE=0.5
```

### 2. 调整最大回溯次数

增加回溯次数可以提高质量，但会增加处理时间。

在 `.env` 中配置：
```env
MAX_BACKTRACK_ATTEMPTS=3
```

### 3. 批量处理

批量处理比逐个文件处理更高效。

## 常见问题

### Q1: 可以使用其他 LLM 吗？

A: 可以。修改 `src/llm/client.py` 中的 `get_llm()` 函数，使用其他兼容 OpenAI API 的模型。

### Q2: 如何添加新的实体类型？

A:
1. 在 `src/knowledge_base/entities.py` 中定义新的实体类
2. 在 `src/langgraph_agents/ner_agent.py` 的 `_get_entity_type_descriptions()` 中添加描述
3. 在 `src/neo4j/client.py` 的 `create_constraints()` 中添加新类型的约束

### Q3: 如何提高抽取准确率？

A:
- 降低 LLM 温度（如 0.3）
- 增加最大回溯次数
- 为 NER 提供更丰富的示例
- 使用高质量的 PDF 文本

### Q4: 可以处理英文法律文书吗？

A: 可以，但需要调整提示词为英文，并确保 LLM 支持英文处理。

### Q5: 导出的 JSON 格式是什么？

A:
```json
{
  "export_time": "2024-01-15T10:30:00",
  "stats": {"Case": 5, "Court": 2, ...},
  "nodes": [
    {
      "id": "case_000",
      "labels": ["Case"],
      "properties": {"case_id": "...", ...}
    }
  ],
  "relationships": [
    {
      "source": "case_000",
      "target": "court_000",
      "type": "case_in_court",
      "properties": {}
    }
  ]
}
```

## 高级用法

### 自定义智能体

创建新的智能体：

```python
from src.langgraph_agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def process(self, state):
        # 实现处理逻辑
        return state
    
    def build_prompt(self, context):
        # 构建提示词
        return "Your prompt here"
```

### 可视化状态机

```python
from src.langgraph_agents.graph import LegalExtractionGraph

graph = LegalExtractionGraph()
graph.visualize_graph("output/graph.png")
```

### 批量导入已有知识

如果已有结构化数据，可以直接导入 Neo4j：

```python
from src.neo4j.storage import KnowledgeGraphStorage

storage = KnowledgeGraphStorage()
storage.connect()
storage.batch_save_results(your_data_list)
storage.close()
```

## 技术支持

如遇到问题，请查看：
1. 日志文件：`output/logs/app.log`
2. 错误堆栈信息
3. 本文档的故障排除部分
