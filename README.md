# 香港法律文书知识图谱构建系统

基于 LangGraph 和 DeepSeek-V3.2 的香港法律文书知识图谱自动构建工具。

## 功能特性

- 📄 **PDF 文本提取**：自动从法律文书中提取文本内容
- 🤖 **多智能体协作**：5个专业智能体分工协作（实体识别、指代消解、归一化、关系抽取、质量检查）
- 🔄 **智能回溯机制**：质量检查不通过时自动回溯到对应阶段
- 🗺️ **知识图谱存储**：自动构建并存储到 Neo4j 图数据库
- 📊 **质量评估**：自动评估抽取结果质量，给出改进建议

## 系统架构

```
PDF 文件 → 文本提取 → NER 智能体 → 指代消解 → 实体归一化 → 关系抽取 → 质量检查 → Neo4j
                     ↑                                    ↓
                     └────────── 回溯机制 ────────────────┘
```

## 安装步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下参数：

```env
# DeepSeek API
DASHSCOPE_API_KEY=your-api-key-here

# Neo4j（可选）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here
```

### 3. 准备 Neo4j 数据库（可选）

如果需要将结果存储到 Neo4j：

```bash
# 使用 Docker 启动 Neo4j
docker run -d \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/your-password \
    neo4j:latest
```

## 使用方法

### 基础使用

处理 `input` 目录中的所有 PDF 文件：

```bash
python main.py
```

处理单个文件：

```bash
python main.py --input path/to/file.pdf
```

处理指定目录：

```bash
python main.py --input path/to/directory
```

### 高级选项

不使用 Neo4j 存储：

```bash
python main.py --no-neo4j
```

导出知识图谱为 JSON：

```bash
python main.py --export output/knowledge_graph.json
```

### 完整示例

```bash
# 处理 input 目录并导出结果
python main.py -i input -e output/result.json

# 处理单个文件并存储到 Neo4j
python main.py -i input/CACC000510_2005.pdf
```

## 模块说明

### 核心模块

- `src/pdf_processor/`：PDF 文本提取
- `src/langgraph_agents/`：LangGraph 智能体和状态机
- `src/neo4j/`：Neo4j 数据库集成
- `src/knowledge_base/`：实体类型和模式定义
- `src/llm/`：LLM 客户端（DeepSeek-V3.2）

### 智能体说明

1. **NERAgent**：实体识别
   - 识别 Case、Court、Judge、Party、Law 等法律实体
   - 使用 LLM 进行精准识别

2. **CorefAgent**：指代消解
   - 解决文本中的代词和实体引用歧义
   - 统一实体表述

3. **NormalizationAgent**：实体归一化
   - 合并相同或相似的实体
   - 确保知识一致性

4. **RelationAgent**：关系抽取
   - 识别实体之间的语义关系
   - 构建三元组知识

5. **QualityCheckAgent**：质量检查
   - 评估抽取结果质量
   - 决定是否触发回溯

## 输出结果

### 知识图谱节点类型

- `Case`：案件信息
- `Court`：法院
- `Judge`：法官
- `Party`：当事人（原告/被告）
- `Law`：法律条文
- `Evidence`：证据
- `LegalTerm`：法律术语
- `Date`：日期
- `Amount`：金额

### 关系类型

- `case_in_court`：案件所在法院
- `case_judged_by`：案件法官
- `case_involved_party`：案件当事人
- `case_applied_law`：案件适用的法律
- 等等...

## 配置说明

### LLM 配置

在 `config/settings.py` 中配置：

```python
llm_model = "deepseek-v3.2"
llm_temperature = 0.7
llm_max_tokens = 4000
```

### 质量检查配置

```python
quality_threshold = 0.8  # 质量阈值
max_backtrack_attempts = 3  # 最大回溯次数
```

## 日志

日志文件位置：`output/logs/app.log`

日志级别可在 `.env` 中配置：

```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## 故障排除

### 1. PDF 提取失败

确保 PDF 文件格式正确，尝试使用不同的 PDF 提取工具。

### 2. LLM 调用失败

- 检查 API Key 是否正确
- 确认网络连接正常
- 检查 API 额度是否充足

### 3. Neo4j 连接失败

- 确认 Neo4j 服务正在运行
- 检查连接配置是否正确
- 验证用户名和密码

### 4. 抽取质量不佳

- 调整 LLM temperature 参数
- 增加回溯次数
- 检查文本质量

## 开发指南

### 添加新的实体类型

1. 在 `src/knowledge_base/entities.py` 中定义实体类
2. 在 `NERAgent` 中添加实体类型描述
3. 更新 Neo4j 约束

### 添加新的关系类型

1. 在 `src/knowledge_base/schemas.py` 中定义关系
2. 在 `RelationAgent` 中添加关系描述

### 自定义智能体

继承 `BaseAgent` 并实现 `process` 和 `build_prompt` 方法：

```python
class CustomAgent(BaseAgent):
    def process(self, state):
        # 实现处理逻辑
        return state
    
    def build_prompt(self, context):
        # 构建提示词
        return "Your prompt"
```

## 项目结构

```
hk-legal-knowledge-graph-langgraph/
├── config/                   # 配置
│   └── settings.py
├── src/
│   ├── pdf_processor/        # PDF 处理
│   ├── langgraph_agents/     # LangGraph 智能体
│   ├── neo4j/                # Neo4j 集成
│   ├── knowledge_base/       # 知识库定义
│   ├── llm/                  # LLM 客户端
│   └── utils/                # 工具
├── input/                    # 输入 PDF 文件
├── output/                   # 输出结果
├── main.py                   # 主程序入口
├── requirements.txt          # 依赖包
└── .env                     # 环境变量
```

## 许可证

MIT License

## 技术栈

- Python 3.10+
- LangGraph
- LangChain
- DeepSeek-V3.2
- Neo4j
- PyMuPDF
