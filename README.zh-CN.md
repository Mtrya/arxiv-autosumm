# ArXiv AutoSumm

ArXiv论文自动摘要系统

[English](README.md) | [中文](README.zh-CN.md)

## 📦 安装

### 方法一：GitHub Actions（推荐）

GitHub Actions 提供自动化定时执行，无需维护本地基础设施。提供两种配置方式：

#### 选项 A：动态配置（快速启动）

此方式通过仓库密钥自动生成配置，无需提交配置文件。

**先决条件：**

- GitHub 账户
- 大语言模型供应商的 API 密钥
- SMTP 邮箱和密码

**步骤：**

1. **Fork（请顺便 Star）仓库**

   - 点击右上角的 "Fork" 按钮
   - 选择您的 GitHub 账户

2. **配置仓库密钥**

   - 进入您的 fork → Settings → Secrets and variables → Actions
   - 添加以下密钥：

   | 密钥名称              | 必填 | 类型 | 允许值                                   | 作用                           | 默认值             | 示例                                   |
   | --------------------- | ---- | ---- | ---------------------------------------- | ------------------------------ | ------------------ | -------------------------------------- |
   | `SUMMARIZER_PROVIDER` | ❌    | str  | 供应商名称                               | 用于摘要的大语言模型供应商     | `modelscope`       | `deepseek`                             |
   | `RATER_PROVIDER`      | ❌    | str  | 供应商名称                               | 用于论文评分的大语言模型供应商 | `modelscope`       | `zhipu`                                |
   | `SUMMARIZER_API_KEY`  | ✅    | str  | 有效的 API 密钥                           | 摘要大语言模型的 API 密钥      | -                  | `sk-xxx`                               |
   | `RATER_API_KEY`       | ✅    | str  | 有效的 API 密钥                           | 评分大语言模型的 API 密钥      | -                  | `sk-xxx`                               |
   | `SMTP_SERVER`         | ✅    | str  | 有效的 SMTP 服务器                        | 邮件发送的 SMTP 服务器         | -                  | `smtp.gmail.com`                       |
   | `SENDER_EMAIL`        | ✅    | str  | 有效的邮箱地址                           | 发件人邮箱地址                 | -                  | `your-email@gmail.com`                 |
   | `RECIPIENT_EMAIL`     | ✅    | str  | 有效的邮箱地址                           | 收件人邮箱地址                 | -                  | `recipient@email.com`                  |
   | `SMTP_PASSWORD`       | ✅    | str  | 有效的密码                               | SMTP 密码或应用密码            | -                  | `ASqfdvaer123456`                      |
   | `SUMMARIZER_BASE_URL` | ❌    | str  | 有效的 URL                               | 摘要 API 的基础 URL            | 提供商特定         | `https://api.deepseek.com/v1`          |
   | `SUMMARIZER_MODEL`    | ❌    | str  | 模型名称                                 | 用于摘要的模型名称             | 提供商特定         | `deepseek-reasoner`                    |
   | `RATER_BASE_URL`      | ❌    | str  | 有效的 URL                               | 评分 API 的基础 URL            | 提供商特定         | `https://open.bigmodel.cn/api/paas/v4` |
   | `RATER_MODEL`         | ❌    | str  | 模型名称                                 | 用于论文评分的模型名称         | 提供商特定         | `glm-4.5-flash`                        |
   | `ARXIV_CATEGORIES`    | ❌    | str  | 真实的 ArXiv 分类                        | 要监控的 ArXiv 分类            | `cs.AI,cs.CV,cs.RO` | `cs.AI,cs.LG,cs.RO`                    |
   | `MAX_PAPERS`          | ❌    | int  | 1-1000                                   | 最大摘要数量                   | `5`                | `10`                                   |
   | `OUTPUT_FORMATS`      | ❌    | str  | pdf, html, md，用逗号分隔                | 输出格式                       | `pdf,md`           | `pdf,html,md`                          |
   | `SMTP_PORT`           | ❌    | int  | 有效的端口号                             | SMTP 端口号                   | `465`              | `587`                                  |

   **注意**：系统会根据识别的提供商名称自动检测基础 URL 和默认模型。如果您指定了识别的提供商（如 `deepseek`、`openai`、`dashscope`），基础 URL 和默认模型将自动配置。对于自定义提供商或未指定提供商名称时，您必须手动提供基础 URL 和模型名称。

3. **启用 GitHub Actions**

   - 进入您 fork 仓库的 Actions 标签页
   - 如果提示，启用 Actions
   - 选择选项："我了解我的工作流，继续启用它们"

4. **运行工作流**

   - **手动运行**：进入 Actions → "ArXiv AutoSumm Daily" → "Run workflow"
   - **定时运行**：每天 22:00 UTC 自动运行
   - **测试模式**：勾选 "Run in test mode" 进行有限处理

#### 选项 B：仓库配置（高级）

如需对 VLM 解析、Embedder 评分和自定义配置进行完全控制，建议使用仓库中的配置文件。

**前置要求：**

- 与选项 A 相同

**步骤：**

1. **Fork 并设置仓库变量**

   - Fork 仓库（与选项 A 相同）
   - 进入 Settings → Variables → Actions
   - 添加仓库变量：`USE_REPO_CONFIG = true`

2. **配置并提交 config.yaml**

   - 将 `config.advanced.yaml` 复制为 `config.yaml`
   - **将所有设置直接写入 config.yaml**：分类、模型、输出格式等
   - **仅对敏感数据使用密钥引用**：`api_key: sec:API_KEY`
   - 将 `config.yaml` 提交到您的仓库

3. **自定义提示词（可选）**

   - 编辑 `prompts/` 目录中的提示词文件以自定义行为
   - **保留提示词中的所有 `{...}` 模板占位符**
   - 常见自定义：
     - `prompts/summ_lm/` - 摘要风格和重点
     - `prompts/rate_lm/` - 评分标准重点
     - `prompts/rate_emb/` - 相关性过滤的嵌入查询
     - `prompts/parse_vlm/` - VLM 解析指令

4. **配置所需密钥**

   - 仅为您 `config.yaml` 中引用的敏感数据设置密钥
   - 使用工作流中允许的任何密钥名称

**允许的密钥名称**（来自 main.yml 环境）：

```secrets
# LLM 提供商密钥
OPENAI_API_KEY, DEEPSEEK_API_KEY, MODELSCOPE_API_KEY, DASHSCOPE_API_KEY
SILICONFLOW_API_KEY, ZHIPU_API_KEY, MOONSHOT_API_KEY, MINIMAX_API_KEY
ANTHROCIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, VOLCENGINE_API_KEY

# 自定义功能密钥
SUMMARIZER_API_KEY, RATER_API_KEY, EMBEDDER_API_KEY, VLM_API_KEY, LLM_API_KEY, API_KEY

# 邮件配置
SMTP_PASSWORD, SENDER_EMAIL, RECIPIENT_EMAIL, SMTP_SERVER, SMTP_PORT

# 配置变量
ARXIV_CATEGORIES, MAX_PAPERS, OUTPUT_FORMATS, RATING_STRATEGY
```

### 方法二：本地 Git 克隆安装

完全本地控制执行时机和配置。

#### 前置要求

**系统要求：**

- Git
- 系统依赖（根据所需输出格式）

**可选系统依赖：**

```bash
# PDF 输出
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-xetex

# HTML 输出
sudo apt-get install pandoc

# AZW3（Kindle）输出
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

3. **配置应用**

   **基础配置：**

   ```bash
   cp config.basic.yaml config.yaml
   # 编辑 config.yaml 设置您的配置
   ```

   **高级配置：**

   ```bash
   cp config.advanced.yaml config.yaml
   # 编辑 config.yaml 设置高级功能
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

5. **运行管道**

   ```bash
   # 正常执行
   autosumm run

   # 详细输出
   autosumm run --verbose

   # 仅单个分类
   autosumm run --specify-category cs.AI
   ```

#### 本地定时任务

对于自动化执行，您可以使用 systemd（推荐）或 crontab。

##### Systemd 计时器（推荐）

创建 systemd 服务和计时器，实现现代化可靠的定时任务：

```bash
# 创建 systemd 服务文件
sudo tee /etc/systemd/system/arxiv-autosumm.service > /dev/null << 'EOF'
[Unit]
Description=ArXiv AutoSumm Service
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/arxiv-autosumm
ExecStart=/usr/bin/python -m autosumm.cli run
StandardOutput=journal
StandardError=journal
EOF

# 创建 systemd 计时器文件
sudo tee /etc/systemd/system/arxiv-autosumm.timer > /dev/null << 'EOF'
[Unit]
Description=ArXiv AutoSumm Timer
Requires=arxiv-autosumm.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 重新加载 systemd 并启用计时器
sudo systemctl daemon-reload
sudo systemctl enable arxiv-autosumm.timer
sudo systemctl start arxiv-autosumm.timer

# 检查计时器状态
systemctl list-timers --all
```

##### Crontab（备选方案）

对于没有 systemd 的系统，使用传统的 crontab：

```bash
# 编辑 crontab
crontab -e

# 每天上午 9 点运行
0 9 * * * cd /path/to/arxiv-autosumm && autosumm run

# 每 6 小时运行一次
0 */6 * * * cd /path/to/arxiv-autosumm && autosumm run
```

### 功能特性

**共同功能：**

- **自动化论文处理**：从 ArXiv 获取到邮件投递的完整管道
- **15+ LLM 供应商**：OpenAI、DeepSeek、ModelScope、Zhipu 等
- **多种输出格式**：PDF、HTML、Markdown、AZW3（Kindle）
- **智能论文评分**：可选 LLM、Embedder 或混合策略
- **高级缓存**：基于 SQLite 的去重，避免重复处理
- **自定义提示词**：根据需求定制摘要和评分标准
- **邮件投递**：支持附件的 SMTP 配置
- **视觉语言模型**：可选 VLM 解析，增强 PDF 提取

**GitHub Actions 特有：**

- **无需基础设施管理**：GitHub 提供所有计算资源
- **高可靠性**：99.9%+ 运行时间，自动故障转移
- **免费额度**：公共仓库每月 2000 分钟
- **内置监控**：自动记录日志和执行历史
- **简单部署**：Fork 仓库，配置密钥即可运行
- **两种配置选项**：动态（基于密钥）或基于仓库

**本地安装特有：**

- **完全控制**：完全自定义所有组件
- **无限执行**：无时间或资源限制
- **灵活调度**：systemd 计时器或 crontab 自动化
- **本地调试**：完整的开发环境访问
- **数据隐私**：所有处理和存储保持本地
- **离线功能**：初始化后可在无网络连接情况下工作
