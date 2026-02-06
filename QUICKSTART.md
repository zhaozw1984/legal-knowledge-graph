# 快速开始指南

## 项目完成情况 ✓

已成功实现基于 **LangGraph + DeepSeek-V3.2** 的香港法律文书知识图谱构建系统。

### 实现的功能模块

✅ **PDF 文本提取** - 从 PDF 文件中提取文本内容  
✅ **实体识别智能体** - 识别法律实体（Case、Court、Judge、Party、Law 等）  
✅ **指代消解智能体** - 解决文本中的代词和实体引用歧义  
✅ **实体归一化智能体** - 合并相同实体，确保知识一致性  
✅ **关系抽取智能体** - 抽取实体间的语义关系  
✅ **质量检查智能体** - 评估抽取质量，触发智能回溯  
✅ **LangGraph 状态机** - 多智能体协作和流程控制  
✅ **Neo4j 知识图谱存储** - 将抽取结果持久化到图数据库  
✅ **主程序入口** - 批量处理和完整流水线  

### 项目结构

```
hk-legal-knowledge-graph-langgraph/
├── config/                     # 配置管理
│   └── settings.py             # 环境配置（DeepSeek API、Neo4j）
├── src/
│   ├── pdf_processor/          # PDF 提取
│   │   └── extractor.py        # PDF 文本提取器
│   ├── langgraph_agents/       # LangGraph 智能体
│   │   ├── base_agent.py       # 智能体基类
│   │   ├── ner_agent.py        # 实体识别
│   │   ├── coref_agent.py      # 指代消解
│   │   ├── normalization_agent.py  # 实体归一化
│   │   ├── relation_agent.py   # 关系抽取
│   │   ├── qa_agent.py         # 质量检查
│   │   ├── state.py            # 状态定义
│   │   └── graph.py            # 状态机
│   ├── neo4j/                  # Neo4j 集成
│   │   ├── client.py           # Neo4j 客户端
│   │   ├── models.py           # 图数据模型
│   │   └── storage.py          # 存储管理器
│   ├── knowledge_base/         # 知识库定义
│   │   ├── entities.py         # 实体类型
│   │   └── schemas.py          # 关系类型
│   ├── llm/                    # LLM 客户端
│   │   └── client.py           # DeepSeek-V3.2 客户端
│   └── utils/                  # 工具
│       └── logger.py           # 日志工具
├── input/                      # 输入 PDF 文件（6个）
├── output/                     # 输出目录（自动创建）
├── main.py                     # 主程序入口
├── test_pipeline.py            # 完整测试脚本
├── requirements.txt            # 依赖包
├── .env.example                # 环境变量示例
├── README.md                   # 项目文档
└── USAGE.md                    # 使用指南
```

## 立即开始使用

### 1. 安装依赖

```bash
cd d:/AISource/hk-zzw
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
copy .env.example .env

# 编辑 .env 文件，填入你的 DeepSeek API Key
# DASHSCOPE_API_KEY=your-api-key-here
```

### 3. 运行测试（可选）

```bash
python test_pipeline.py
```

### 4. 处理 PDF 文件

**处理所有 PDF（不需要 Neo4j）：**
```bash
python main.py --no-neo4j
```

**处理单个文件：**
```bash
python main.py --input input/CACC000510_2005.pdf --no-neo4j
```

**处理目录：**
```bash
python main.py --input input --no-neo4j
```

## 核心特性

### 1. 多智能体协作

5个专业智能体分工协作，每个智能体专注于特定任务：

```
NER智能体 → 指代消解智能体 → 归一化智能体 → 关系抽取智能体 → 质量检查智能体
                                    ↑
                            回溯机制（质量不达标时）
```

### 2. 智能回溯机制

- 质量检查智能体评估抽取结果
- 如果质量评分 < 0.8，自动回溯到对应阶段
- 最多回溯 3 次，超过则停止
- 支持回溯到 NER、指代消解、归一化、关系抽取任一阶段

### 3. 深度 LLM 集成

- 使用 DeepSeek-V3.2 进行实体和关系抽取
- 精心设计的提示词工程
- 支持上下文理解（全文抽取，非分段）

### 4. 灵活的存储

- 可选 Neo4j 图数据库存储
- 支持 JSON 导出
- 批量写入优化

## 输出示例

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

文件 2: input/CACC000531_2005.pdf
  状态: 成功
  实体数: 12
  关系数: 18
  质量评分: 0.88

------------------------------------------------------------
总计: 成功 6/6
总实体数: 78
总关系数: 102
============================================================
```

### 知识图谱节点

系统会识别以下类型的实体：

- **Case** - 案件信息（案件编号、标题、日期、引证）
- **Court** - 法院（名称、级别、管辖区）
- **Judge** - 法官（姓名、职称）
- **Party** - 当事人（原告/被告）
- **Law** - 法律条文（名称、类型、条款）
- **Evidence** - 证据（类型、描述）
- **LegalTerm** - 法律术语
- **Date** - 日期（立案/开庭/判决）
- **Amount** - 金额

### 知识图谱关系

系统会抽取实体间的关系，例如：

- `case_in_court` - 案件所在法院
- `case_judged_by` - 案件法官
- `case_involved_party` - 案件当事人
- `case_applied_law` - 案件适用的法律
- `case_evidence` - 案件证据
- 等等...

## 下一步

### 使用 Neo4j（推荐）

如果需要将结果存储到 Neo4j：

1. **启动 Neo4j**（使用 Docker）：
   ```bash
   docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/your-password neo4j:latest
   ```

2. **配置 .env 文件**：
   ```env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your-password
   ```

3. **运行主程序**：
   ```bash
   python main.py
   ```

4. **访问 Neo4j 浏览器**：
   - 打开浏览器访问 http://localhost:7474
   - 执行 Cypher 查询查看结果

### 自定义和扩展

- **添加新的实体类型**：编辑 `src/knowledge_base/entities.py`
- **添加新的关系类型**：编辑 `src/knowledge_base/schemas.py`
- **调整提示词**：编辑各智能体的 `build_prompt` 方法
- **修改质量阈值**：编辑 `.env` 中的 `QUALITY_THRESHOLD`

## 重要提示

1. **全文抽取**：系统采用全文抽取方式，不是分段抽取，确保全局一致性
2. **智能回溯**：质量检查不达标时会自动回溯，无需人工干预
3. **LangGraph 架构**：使用 LangGraph 而非 LangChain，支持复杂的状态管理和回溯
4. **DeepSeek-V3.2**：使用你提供的 LLM 配置，无需额外设置

## 技术亮点

✨ **LangGraph 状态机** - 支持循环、分支、回溯  
✨ **多智能体协作** - 每个智能体专注于特定任务  
✨ **智能质量检查** - 自动评估并决定是否回溯  
✨ **全文实体抽取** - 确保指代消解的准确性  
✨ **灵活配置** - 支持多种使用场景  

## 故障排除

### LLM 调用失败

- 检查 `.env` 中的 `DASHSCOPE_API_KEY`
- 确认网络连接
- 检查 API 额度

### Python 命令无法执行

如果遇到 Python 命令执行问题，请确保：
- Python 已安装并添加到 PATH
- 依赖已正确安装

### 查看详细日志

所有运行日志保存在 `output/logs/app.log`，可用于调试。

## 获取帮助

- 查看 `README.md` 了解完整项目信息
- 查看 `USAGE.md` 了解详细使用指南
- 查看 `output/logs/app.log` 查看运行日志

---

**项目已完成！** 🎉

开始使用：`python main.py --no-neo4j`
