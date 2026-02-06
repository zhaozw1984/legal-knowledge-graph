---
name: github-initial-push
overview: 将当前项目初始化 Git 仓库并推送到 GitHub，仓库名称为 legal-knowledge-graph
todos:
  - id: check-git
    content: 检查系统是否安装 Git 并验证版本
    status: completed
  - id: init-git
    content: 初始化 Git 仓库（git init）
    status: completed
    dependencies:
      - check-git
  - id: config-git
    content: 配置 Git 用户信息（邮箱和用户名）
    status: completed
    dependencies:
      - init-git
  - id: create-gitignore
    content: 创建 .gitignore 文件配置忽略规则
    status: completed
    dependencies:
      - config-git
  - id: add-files
    content: 添加项目文件到 Git 暂存区
    status: completed
    dependencies:
      - create-gitignore
  - id: initial-commit
    content: 创建初始 Git 提交
    status: completed
    dependencies:
      - add-files
  - id: create-github-repo
    content: 在 GitHub 网页端创建 legal-knowledge-graph 仓库
    status: completed
    dependencies:
      - initial-commit
  - id: push-to-github
    content: 连接远程仓库并推送代码到 GitHub
    status: completed
    dependencies:
      - create-github-repo
---

## Product Overview

将当前法律知识图谱项目（legal-knowledge-graph）初始化 Git 仓库并推送到 GitHub，作为项目重构前的备份。

## Core Features

- 初始化 Git 仓库
- 配置 Git 用户信息（用户名和邮箱）
- 创建 .gitignore 文件，排除不必要的文件
- 提交当前项目代码
- 在 GitHub 上创建仓库 legal-knowledge-graph
- 将本地代码推送到远程 GitHub 仓库

## Tech Stack

- 版本控制：Git
- 代码托管：GitHub
- 操作系统：Windows (PowerShell)

## Tech Architecture

### 实现流程

```mermaid
flowchart LR
    A[检查当前目录] --> B[初始化 Git 仓库]
    B --> C[配置 Git 用户信息]
    C --> D[创建 .gitignore]
    D --> E[添加文件到暂存区]
    E --> F[创建初始提交]
    F --> G[在 GitHub 创建远程仓库]
    G --> H[添加远程仓库地址]
    H --> I[推送代码到 GitHub]
```

## Implementation Details

### 核心目录结构

```
d:\AISource\hk-zzw\
├── .git/                    # 新增：Git 仓库目录
├── .gitignore               # 新增：Git 忽略文件配置
├── config/                  # 配置文件
├── input/                   # 输入文件（PDF等）
├── output/                  # 输出文件（处理结果）
├── src/                     # 源代码
│   └── langgraph_agents/    # LangGraph 代理
├── main.py                  # 主程序入口
├── requirements.txt         # Python 依赖
├── README.md                # 项目说明
├── QUICKSTART.md            # 快速开始指南
└── USAGE.md                 # 使用说明
```

### .gitignore 配置

需要排除以下内容：

- Python 字节码文件（*.pyc, **pycache**/）
- 虚拟环境（venv/, env/）
- IDE 配置（.vscode/, .idea/）
- 敏感信息（.env, 凭证文件）
- 临时输出文件（output/ 目录内容）
- 日志文件（*.log）

### Git 配置

- 用户邮箱：274426532@qq.com
- 远程仓库名：legal-knowledge-graph
- 分支名称：main

### 技术实现步骤

1. **检查 Git 安装状态**：验证系统是否已安装 Git
2. **初始化 Git 仓库**：执行 `git init` 命令
3. **配置用户信息**：设置 `git config user.email` 和 `user.name`
4. **创建 .gitignore**：编写忽略规则，排除不必要的文件
5. **添加文件**：使用 `git add .` 添加所有文件到暂存区
6. **创建提交**：执行 `git commit -m "Initial commit: Legal Knowledge Graph project"`
7. **创建 GitHub 仓库**：通过 GitHub 网页界面创建远程仓库
8. **连接远程仓库**：使用 `git remote add origin` 添加远程仓库地址
9. **推送代码**：执行 `git push -u origin main` 推送到 GitHub

## Technical Considerations

### 安全注意事项

- 不应在 .gitignore 或代码中提交敏感信息（密码、API密钥等）
- 提供的 GitHub 密码应妥善保管，建议使用 Personal Access Token
- 注意检查是否存在 .env 或其他配置文件包含敏感信息

### 文件排除策略

- 排除大文件和二进制文件以避免仓库过大
- 保留源代码、配置文件和文档
- 考虑是否将 input/ 和 output/ 目录纳入版本控制

### 分支管理

- 初始推送到 main 分支
- 建议后续使用 feature 分支进行开发
- 可考虑创建 develop 分支用于日常开发