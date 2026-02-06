# 测试启动指南

## 📋 快速开始

### 方式一：完整流水线测试（推荐）

运行主程序处理真实的 PDF 文件：

```bash
# 处理单个 PDF 文件
python main.py --input input/你的文件.pdf

# 处理整个 input 目录
python main.py

# 不使用 Neo4j 存储（仅抽取）
python main.py --no-neo4j

# 导出到 JSON 文件
python main.py --export output/knowledge_graph.json
```

**参数说明**：
- `--input` 或 `-i`: 指定输入文件或目录路径
- `--no-neo4j`: 跳过 Neo4j 存储（适合测试）
- `--export` 或 `-e`: 导出知识图谱到 JSON 文件

---

### 方式二：7步架构单元测试

测试新7步架构的完整流程：

```bash
python test_7_step_pipeline.py
```

**测试内容**：
1. 文档结构解析
2. 块级NER识别
3. 规则实体标准化
4. 循环关系抽取
5. 关系归一化
6. Relation-guided指代消解
7. 质量检查

**预期输出**：
- 文档块数量
- 实体数量和详情
- 关系数量和详情
- 质量评分
- 回溯次数

---

### 方式三：依赖检查

验证所有依赖是否正确安装：

```bash
python test_dependencies.py
```

---

## 🚀 完整测试流程

### 步骤1：检查依赖

```bash
python test_dependencies.py
```

确保所有依赖都显示 ✅ 已安装。

---

### 步骤2：运行7步单元测试

```bash
python test_7_step_pipeline.py
```

观察输出，确认7个步骤都正常执行。

---

### 步骤3：处理真实PDF

确保 `input/` 目录中有 PDF 文件，然后：

```bash
# 先不连接 Neo4j 测试抽取功能
python main.py --no-neo4j

# 如果正常，再连接 Neo4j
python main.py
```

---

## 📦 测试数据

项目包含6个测试PDF文件，位于 `input/` 目录：

```
input/
├── 文件1.pdf
├── 文件2.pdf
├── 文件3.pdf
├── 文件4.pdf
├── 文件5.pdf
└── 文件6.pdf
```

---

## 🔧 配置说明

### 环境变量（.env 文件）

```env
# DeepSeek API 配置
DASHSCOPE_API_KEY=your_api_key_here
LLM_MODEL=deepseek-v3.2
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4000

# Neo4j 配置（可选）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 配置文件（config/settings.py）

```python
# 7步架构配置
document_parser_enabled = True          # 启用文档结构解析
entity_normalization_enabled = True     # 启用规则实体标准化
relation_normalization_enabled = True    # 启用关系归一化
coref_max_hops = 3                   # 指代消解最大跳数
```

---

## 📊 输出说明

### 处理结果

```json
{
  "text": "原始文本",
  "pdf_path": "PDF文件路径",
  "document_blocks": [...],      // 文档块列表
  "entities": [...],              // 实体列表
  "relations": [...],             // 关系列表
  "quality_report": {...},         // 质量报告
  "backtrack_count": 0,           // 回溯次数
  "success": true
}
```

### 质量评分

- `1.0 - 0.8`: 优秀，无需回溯
- `0.8 - 0.6`: 良好，可能需要少量调整
- `0.6 - 0.4`: 一般，建议回溯改进
- `< 0.4`: 较差，必须回溯

---

## ⚠️ 常见问题

### 问题1：API密钥错误

**错误信息**：`API key is invalid`

**解决方案**：
1. 检查 `.env` 文件中的 `DASHSCOPE_API_KEY`
2. 确保密钥有效且未过期

---

### 问题2：Neo4j 连接失败

**错误信息**：`无法连接到 Neo4j 数据库`

**解决方案**：
1. 使用 `--no-neo4j` 参数跳过 Neo4j
2. 或者先启动 Neo4j 服务：
   ```bash
   # Docker 方式
   docker run -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/password \
     neo4j:latest
   ```

---

### 问题3：PDF解析失败

**错误信息**：`PDF 提取失败`

**解决方案**：
1. 确认 PDF 文件未损坏
2. 检查 PDF 是否有密码保护
3. 尝试使用其他 PDF 文件测试

---

## 🎯 快速验证

### 最小化测试（5分钟）

```bash
# 1. 检查依赖
python test_dependencies.py

# 2. 运行7步测试（使用内置测试文本）
python test_7_step_pipeline.py

# 3. 如果都通过，系统就正常工作了！
```

---

## 📝 日志和调试

### 查看详细日志

日志文件：`output/logs/app.log`

实时查看日志（Linux/Mac）：
```bash
tail -f output/logs/app.log
```

### 启用调试模式

修改 `config/settings.py`：
```python
log_level = "DEBUG"
```

---

## ✅ 成功标准

测试成功标志：

- [x] 所有依赖检查通过
- [x] 7步测试输出完整
- [x] 至少识别到实体
- [x] 质量评分 > 0.7
- [x] 无致命错误

---

## 🚀 开始测试

现在就绪！选择一个测试方式开始：

**推荐顺序**：
```bash
python test_dependencies.py           # 先检查依赖
python test_7_step_pipeline.py         # 测试7步流程
python main.py --no-neo4j            # 处理真实PDF
```

祝测试顺利！🎉
