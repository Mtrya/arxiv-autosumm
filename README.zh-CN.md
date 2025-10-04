# ArXiv AutoSumm

基于 LLM 的 ArXiv 自动化研究论文摘要工具，提供智能评分、多格式输出和全面的配置管理功能。

[English](README.md) | [中文](README.zh-CN.md)

## 📦 安装

### 方法 1：GitHub Actions（推荐）

GitHub Actions 提供自动化的定时执行，无需维护本地基础设施。提供两种配置方式：

#### 选项 A：动态配置（快速开始）

此方式通过仓库密钥自动生成配置 - 无需提交配置文件。

**前置条件：**

- GitHub 账号
- LLM 提供商的 API 密钥
- SMTP 邮箱和密码

**步骤：**

1. **Fork 仓库（欢迎点 Star）**

   - 点击右上角的 "Fork"
   - 选择您的 GitHub 账号

2. **配置仓库密钥**

   - 导航到您的 fork → Settings → Secrets and variables → Actions
   - 添加以下密钥：

   | 配置项                  | 必需 | 类型 | 允许值                                 | 功能描述                       | 默认值             | 示例                                  |
   | --------------------- | ---- | ---- | -------------------------------------- | ------------------------------ | ------------------- | ------------------------------------- |
   | `SUMMARIZER_PROVIDER` | ❌   | str  | 提供商名称                             | 摘要生成的 LLM 提供商         | `modelscope`        | `deepseek`                             |
   | `RATER_PROVIDER`      | ❌   | str  | 提供商名称                             | 论文评分的 LLM 提供商         | `modelscope`        | `zhipu`                                |
   | `SUMMARIZER_API_KEY`  | ✅   | str  | 有效 API 密钥                          | 摘要 LLM 的 API 密钥          | -                   | `sk-xxx`                               |
   | `RATER_API_KEY`       | ✅   | str  | 有效 API 密钥                          | 评分 LLM 的 API 密钥          | -                   | `sk-xxx`                               |
   | `SMTP_SERVER`         | ✅   | str  | 有效 SMTP 服务器                       | 邮件发送的 SMTP 服务器        | -                   | `smtp.gmail.com`                       |
   | `SENDER_EMAIL`        | ✅   | str  | 有效邮箱                               | 发送者邮箱地址                | -                   | `your-email@gmail.com`                 |
   | `RECIPIENT_EMAIL`     | ✅   | str  | 有效邮箱                               | 接收者邮箱地址                | -                   | `recipient@email.com`                  |
   | `SMTP_PASSWORD`       | ✅   | str  | 有效密码                               | SMTP 密码或应用密码           | -                   | `ASqfdvaer123456`                      |
   | `SUMMARIZER_BASE_URL` | ❌   | str  | 有效 URL                               | 摘要 API 的基础 URL           | 提供商特定          | `https://api.deepseek.com/v1`          |
   | `SUMMARIZER_MODEL`    | ❌   | str  | 模型名称                              | 摘要生成的模型名称            | 提供商特定          | `deepseek-reasoner`                    |
   | `RATER_BASE_URL`      | ❌   | str  | 有效 URL                               | 评分 API 的基础 URL           | 提供商特定          | `https://open.bigmodel.cn/api/paas/v4` |
   | `RATER_MODEL`         | ❌   | str  | 模型名称                              | 论文评分的模型名称            | 提供商特定          | `glm-4.5-flash`                        |
   | `ARXIV_CATEGORIES`    | ❌   | str  | 真实的 ArXiv 分类                      | 要监控的 ArXiv 分类           | `cs.AI,cs.CV,cs.RO` | `cs.AI,cs.LG,cs.RO`                    |
   | `MAX_PAPERS`          | ❌   | int  | 1-1000                                 | 最大摘要数量                  | `5`                 | `10`                                   |
   | `OUTPUT_FORMATS`      | ❌   | str  | pdf, html, md, azw3 格式，用逗号分隔   | 输出格式                      | `pdf,md`            | `pdf,html,md`                          |
   | `SMTP_PORT`           | ❌   | int  | 有效端口号                            | SMTP 端口号                   | `465`               | `587`                                  |

   **注意**：系统会从受支持的提供商名称自动检测基础 URL 和默认模型。如果指定了受支持的提供商（如 `deepseek`、`openai`、`dashscope`），基础 URL 和默认模型将自动配置。对于自定义提供商或不指定提供商名称时，您必须手动提供基础 URL 和模型名称。

3. **启用 GitHub Actions**

   - 导航到您 fork 仓库的 Actions 标签页
   - 如果提示，启用 Actions
   - 选择选项："I understand my workflows, go ahead and enable them"

4. **运行工作流**

   - **手动运行**：前往 Actions → "ArXiv AutoSumm Daily" → "Run workflow"
   - **定时运行**：每天 UTC 时间 22:00 自动运行

#### 选项 B：仓库配置（高级）

为了完全控制 VLM 解析、嵌入评分和自定义配置等高级设置，我们建议在仓库中使用 `config.yaml`。

**前置条件：**

- 与选项 A 相同

**步骤：**

1. **Fork 并设置仓库变量**

   - Fork 仓库（同选项 A）
   - 导航到 Settings → Variables → Actions
   - 添加仓库变量：`USE_REPO_CONFIG = true`

2. **配置并提交 config.yaml**

   - 将 `config.advanced.yaml` 复制为 `config.yaml`
   - **将所有设置直接放在 config.yaml 中**：分类、模型、输出格式等
   - **仅对敏感数据使用环境变量**：`api_key: env:API_KEY`
   - 将 `config.yaml` 提交到您的仓库

3. **自定义提示词（可选）**

   - 编辑 `prompts/` 目录中的提示词文件以自定义行为
   - **在提示词中保留所有 `{...}` 模板占位符**
   - 常见自定义：
     - `prompts/summ_lm/` - 摘要风格和重点
     - `prompts/rate_lm/` - 评分标准重点
     - `prompts/rate_emb/` - 相关性过滤的嵌入查询
     - `prompts/parse_vlm/` - VLM 解析指令

4. **配置密钥和变量**

   使用密钥和变量配置您的仓库以获得最大灵活性：

   **环境变量**（适用于所有配置）：
   - 用于 API 密钥、密码和任何设置
   - 在 config.yaml 中使用 `env:` 前缀引用：`api_key: env:API_KEY`

   支持两种类型的环境变量：

   **仓库密钥**（敏感数据）：
   - **命名规则**：使用大写字母和下划线（例如：`MY_API_KEY`、`COMPANY_EMAIL`）
   - 用于 API 密钥、密码和敏感信息
   - 使用 `env:` 前缀引用：`api_key: env:MY_API_KEY`
   - GitHub Actions 会自动在日志中屏蔽密钥，无论名称如何

   **仓库变量**（灵活配置）：
   - 支持您选择的任何变量名称
   - 用于无需提交代码即可更改的设置
   - 同样使用 `env:` 前缀引用：`max_results: env:FETCH_RESULTS`

**使用示例：**

```yaml
fetch:
  max_results: env:FETCH_RESULTS    # 仓库变量（任意名称）
  days: env:CUSTOM_DAYS           # 仓库变量（任意名称）

summarize:
  model: env:MY_SUMMARIZER_MODEL  # 仓库变量（任意名称）
  api_key: env:MY_API_KEY         # 仓库密钥（任意名称）

rate:
  max_selected: env:MAX_PAPERS    # 仓库变量（任意名称）
```

**密钥命名：**

- **对于密钥**（API 密钥、密码）：使用大写字母和下划线（例如：`MY_OPENAI_KEY`、`COMPANY_API_KEY`）
- **对于变量**（设置、偏好）：使用任何您想要的名称
- 两者在 config.yaml 中都使用相同的 `env:` 前缀引用
- 有效密钥示例：`OPENAI_API_KEY`、`MY_COMPANY_KEY`、`SECRET_EMAIL`、`API_KEY_V2`

### 方法 2：本地 Git 克隆安装

完全控制执行时机和配置。

#### 前置条件

**系统要求：**

- Git
- Python 3.11+
- 系统依赖项（基于所需的输出格式）

**可选系统依赖项：**

```bash
# 用于 PDF 输出
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-xetex

# 用于 HTML 输出
sudo apt-get install pandoc

# 用于 AZW3 (Kindle) 输出
sudo apt-get install calibre

# 一次性安装所有依赖
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-xetex pandoc calibre
```

#### 安装步骤

1. **克隆仓库**

   ```bash
   git clone https://github.com/your-username/arxiv-autosumm.git
   cd arxiv-autosumm
   ```

2. **安装 Python 依赖**

   ```bash
   pip install -e .
   ```

3. **配置应用程序**

   **基础配置：**

   ```bash
   cp config.basic.yaml config.yaml
   # 编辑 config.yaml 设置您的配置参数
   ```

   **高级配置：**

   ```bash
   cp config.advanced.yaml config.yaml
   # 编辑 config.yaml 进行高级功能配置
   ```

   **环境变量**（配置文件的替代方案）：

   ```bash
   # 创建 .env 文件
   echo "SUMMARIZER_API_KEY=your_key" > .env
   echo "RATER_API_KEY=your_key" >> .env
   echo "SMTP_PASSWORD=your_password" >> .env
   ```

4. **测试配置**

   ```bash
   autosumm run --test
   ```

5. **运行处理流程**

   ```bash
   # 正常执行处理流程
   autosumm run

   # 详细输出模式执行
   autosumm run --verbose

   # 仅处理指定分类
   autosumm run --specify-category cs.AI
   ```

#### 本地定时任务

对于自动化执行，您可以使用 systemd（推荐）或 crontab。

##### Systemd 定时器（推荐）

创建 systemd 服务和定时器以实现现代化、可靠的定时执行：

```bash
# 创建 systemd 服务文件
sudo tee ~/.config/systemd/user/arxiv-autosumm.service > /dev/null << 'EOF'
[Unit]
Description=ArXiv AutoSumm 服务
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/arxiv-autosumm # 替换为实际安装目录
ExecStart=/usr/bin/python -m autosumm.cli run # 替换为您的 Python 可执行文件路径
StandardOutput=journal
StandardError=journal
EOF

# 创建 systemd 定时器文件
sudo tee ~/.config/systemd/user/arxiv-autosumm.timer > /dev/null << 'EOF'
[Unit]
Description=ArXiv AutoSumm 定时器
Requires=arxiv-autosumm.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 重新加载 systemd 并启用定时器
sudo systemctl daemon-reload
sudo systemctl enable arxiv-autosumm.timer
sudo systemctl start arxiv-autosumm.timer

# 检查定时器状态
systemctl list-timers --all
```

##### Crontab（替代方案）

对于没有 systemd 的系统，使用传统的 crontab：

```bash
# 编辑 crontab
crontab -e

# 每天上午 9 点运行处理流程
0 9 * * * cd /path/to/arxiv-autosumm && autosumm run

# 每 6 小时运行一次处理流程
0 */6 * * * cd /path/to/arxiv-autosumm && autosumm run
```

### 功能特性

**通用功能：**

- **自动化论文处理**：从 ArXiv 获取到邮件投递的完整工作流，按日常计划运行
- **多种输出格式**：PDF、HTML、Markdown、AZW3（Kindle）
- **高级缓存**：基于 SQLite 的缓存去重，避免重复处理
- **邮件投递**：支持附件的 SMTP 配置
- **多种评分策略**：基于语言模型、基于嵌入或混合方法
- **VLM 解析**：可选的视觉语言模型支持，增强 PDF 解析

**GitHub Actions 特有功能：**

- **无需服务器资源管理**：GitHub 提供所有计算资源
- **内置监控**：自动日志记录和执行历史
- **轻松部署**：Fork 仓库、配置密钥并运行
- **两种配置选项**：动态（基于密钥）或基于仓库
- **通用仓库变量**：无需代码更改的灵活配置

**本地安装特有功能：**

- **完全控制**：所有组件的完全自定义
- **无限制执行**：无时间或资源约束
- **本地调试**：完整的开发环境访问
- **数据隐私**：所有处理和存储保持本地（如果您使用本地模型）

## 工作流说明

完整的论文处理工作流按以下执行顺序处理研究论文：

- **1. 获取**：使用配置的分类或日期范围从 ArXiv 下载论文元数据
- **2. 缓存去重**：使用 SQLite 缓存跳过已处理的论文，防止重复工作
- **3. 速率限制**：遵守 ArXiv API 限制，使用指数退避避免被阻止
- **4. PDF 下载**：为新发现的论文检索完整 PDF
- **5. 快速解析**：使用 PyPDF2 提取文本进行快速初始处理
- **6. 嵌入相似度评分** *（可选）*：使用嵌入相似性根据与您兴趣的相关性选择 top-k 论文
- **7. 语言模型评分** *（可选）*：使用语言模型根据配置的标准（新颖性、方法论、清晰度等，基于您的配置）对论文评分
- **8. VLM 解析** *（可选）*：使用视觉语言模型对复杂布局和图表进行增强 OCR
- **9. 摘要**：使用您配置的语言模型生成简洁的技术摘要
- **10. 格式生成**：创建 PDF、HTML、Markdown 或 AZW3 格式的输出
- **11. 邮件投递**：通过邮件发送格式化的摘要

### 评分策略

您可以根据需求配置三种不同的评分方法：

- **llm**：仅使用语言模型评分（最准确，成本较高）
- **embedder**：仅使用嵌入相似性（更快，成本较低）
- **hybrid**：使用嵌入 → 语言模型分层评分（平衡方法）

在 `config.yaml` 中配置：

```yaml
rate:
  strategy: llm  # llm、embedder 或 hybrid
  top_k: 80 # 如果策略是 hybrid，设置此参数
```

**参数流程：**

- **fetch:max_results** → 从 ArXiv 获取的初始论文数量
- **rate:top_k** → 传递给语言模型进行评分的论文数量（经过可选的嵌入过滤后）
- **rate:max_selected** → 最终选择用于可选 VLM 解析和摘要的论文数量（评分后）

## 配置

### 基础配置

#### 运行配置

```yaml
run:
  categories: ["cs.AI", "cs.RO"] # 您感兴趣的 arxiv 分类
  send_log: false # 是否同时发送日志文件和摘要
  log_dir: ./logs # 存储日志文件的位置
```

#### 获取配置

```yaml
fetch:
  days: 8
  max_results: 200
  max_retries: 10
```

#### 摘要器配置

```yaml
summarize:
  provider: deepseek
  api_key: env:DEEPSEEK_API_KEY # 使用环境变量
  base_url: https://api.deepseek.com/v1
  model: deepseek-reasoner # 使用强大的推理模型作为摘要器
  batch: False # 禁用批处理
  system_prompt: null # 使用空的系统提示词也可以
  user_prompt_template: file:./prompts/summ_lm/user.md # 摘要器的用户提示词模板，必须包含 {paper_content} 占位符
  completion_options:
    temperature: 0.6
    # 可以添加其他完成选项，如 top_k、top_p 等
  context_length: 131072 # 默认为 131072，此参数决定论文内容将如何截断以适应模型的上下文长度
```

#### 论文评分

```yaml
rate:
  strategy: llm # llm、embedder 或 hybrid
  top_k: 80    # 传递给 LLM 进行评分的最大论文数（嵌入过滤后）
  max_selected: 10  # 最终摘要的论文数（LLM 评分后）
  embedder: null
  llm:
    provider: modelscope
    api_key: env:MODELSCOPE_API_KEY
    base_url: https://api-inference.modelscope.cn/v1/
    model: Qwen/Qwen2.5-7B-Instruct
    system_prompt: file:./prompts/rate_lm/system.md
    user_prompt_template: file:./prompts/rate_lm/user.md
    completion_options:
      temperature: 0.2
      max_tokens: 1024
    context_length: 32768
    criteria:
      novelty:
        description: 贡献的原创性和创新性如何？
        weight: 0.3
      methodology:
        description: 实验设计和评估的严谨性如何？
        weight: 0.25
      clarity:
        description: 论文的写作和可理解性如何？
        weight: 0.2
```

#### 渲染配置

```yaml
render:
  formats: ["pdf", "md"] # 摘要格式，默认设置为您提供 .pdf 和 .md 文件
  output_dir: ./output # autosumm 将把这些摘要输出到 output_dir，然后通过邮件发送给您
  base_filename: null # 默认为 "summary"。摘要命名为 {base_filename}_{category}_{year&week}.{extension_name}
```

#### 发送和邮件配置

```yaml
deliver:
  smtp_server: smtp.gmail.com  # SMTP 服务器地址
  port: 465                    # SMTP 端口（465 用于 SSL，587 用于 TLS）
  sender: env:SENDER_EMAIL     # 发送者邮箱地址
  recipient: env:RECIPIENT_EMAIL # 接收者邮箱地址
  password: env:SMTP_PASSWORD  # SMTP 密码或应用密码
```

#### 默认 LLM 提供商

| 提供商 | 示例模型 | 备注 |
|--------|----------|------|
| **OpenAI** | gpt-5, gpt-4.1 | 需要 OPENAI_API_KEY |
| **DeepSeek** | deepseek-reasoner | 需要 DEEPSEEK_API_KEY |
| **DashScope** | qwen-max, qwen-turbo | 需要 DASHSCOPE_API_KEY |
| **SiliconFlow** | deepseek-ai/DeepSeek-R1 | 需要 SILICONFLOW_API_KEY |
| **Ollama** | qwen3:32b, llama3.1:8b | 需要本地安装 |
| **Moonshot** | kimi-k2-0711-preview | 需要 MOONSHOT_API_KEY |
| **Minimax** | MiniMax-Text-01 | 需要 MINIMAX_API_KEY |
| **ModelScope** | Qwen/Qwen3-235B-A22B-Thinking-2507 | 需要 MODELSCOPE_API_KEY |
| **Zhipu** | glm-4.6, glm-4.5-flash | 需要 ZHIPU_API_KEY |
| **VolcEngine** | doubao-1.6-seed-thinking | 需要 ARK_API_KEY |
| **Anthropic** | claude-3.5-sonnet | 需要 ANTHROPIC_API_KEY |

### 高级配置

#### VLM 解析

使用视觉语言模型进行增强的 PDF 解析：

```yaml
parse:
  vlm:
    enabled: true
    provider: modelscope
    model: Qwen/Qwen2-VL-72B-Instruct
    api_key: env:VLM_API_KEY
    system_prompt: file:./prompts/parse_vlm/system.md
    user_prompt_template: file:./prompts/parse_vlm/user.md
```

#### 嵌入器配置

用于基于相似性的论文过滤：

```yaml
rate:
  strategy: hybrid
  embedder:
    provider: modelscope
    model: BAAI/bge-large-en-v1.5
    api_key: env:EMBEDDER_API_KEY
    query_prompt: file:./prompts/rate_emb/query.md
```

## CLI 命令

`autosumm` CLI 提供流水线管理命令：

```bash
# 运行完整流水线
autosumm run [--config path/to/config.yaml] [--verbose] [--test] [--specify-category CATEGORY]

# 测试配置和依赖
autosumm run --test [--config path/to/config.yaml] [--verbose]

# 提示词调整界面（即将推出）
autosumm tune [--config path/to/config.yaml] [--category CATEGORY]

# 显示帮助
autosumm --help
autosumm [command] --help
```

### 命令选项

- `--config, -c`：配置文件路径（默认：`config.yaml`）
- `--verbose, -v`：启用详细输出和详细日志
- `--test, -t`：仅测试配置和依赖（不执行流水线）
- `--specify-category, -s`：仅处理指定的 ArXiv 分类（仅单个分类）

## 🚨 已知限制

- **速率限制**：某些提供商可能有激进的速率限制
- **VLM 解析**：启用 VLM 解析可能需要大量时间和token（而且是昂贵的输出token），特别是对于大型 PDF，并且解析质量无法保证（依赖于特定模型和提示词）
- **处理时间**：大型论文集合可能需要相当长的处理时间，具体取决于选择的模型和策略

## 📄 许可证

MIT 许可证 - 详见 LICENSE 文件。
