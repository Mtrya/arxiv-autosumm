# ArXiv AutoSumm

Automated research paper summarization from ArXiv with LLM-powered rating, multi-format delivery, and comprehensive configuration management.

[English](README.md) | [中文](README.zh-CN.md)

## 📦 Installation

### Method 1: GitHub Actions (Recommended)

GitHub Actions provides automated, scheduled execution without maintaining local infrastructure. Choose from two configuration approaches:

#### Option A: Dynamic Configuration (Quick Start)

This approach automatically generates configuration from repository secrets - no config file commits needed.

**Prerequisites:**

- GitHub account
- API keys for LLM providers
- SMTP Email and password

**Steps:**

1. **Fork (and star please) the Repository**

   - Click "Fork" in the top-right corner
   - Choose your GitHub account

2. **Configure Repository Secrets**

   - Navigate to your fork → Settings → Secrets and variables → Actions
   - Add the following secrets:

   | Secret                | Required | Type | Allowed Values                            | Role                           | Default             | Example                                |
   | --------------------- | -------- | ---- | ----------------------------------------- | ------------------------------ | ------------------- | -------------------------------------- |
   | `SUMMARIZER_PROVIDER` | ❌        | str  | Provider name                             | LLM provider for summarization | `modelscope`        | `deepseek`                             |
   | `RATER_PROVIDER`      | ❌        | str  | Provider name                             | LLM provider for paper rating  | `modelscope`        | `zhipu`                                |
   | `SUMMARIZER_API_KEY`  | ✅        | str  | Valid API key                             | API key for summarizer LLM     | -                   | `sk-xxx`                               |
   | `RATER_API_KEY`       | ✅        | str  | Valid API key                             | API key for rater LLM          | -                   | `sk-xxx`                               |
   | `SMTP_SERVER`         | ✅        | str  | Valid SMTP server                         | SMTP server for email delivery | -                   | `smtp.gmail.com`                       |
   | `SENDER_EMAIL`        | ✅        | str  | Valid email                               | Sender email address           | -                   | `your-email@gmail.com`                 |
   | `RECIPIENT_EMAIL`     | ✅        | str  | Valid email                               | Recipient email address        | -                   | `recipient@email.com`                  |
   | `SMTP_PASSWORD`       | ✅        | str  | Valid password                            | SMTP password or app password  | -                   | `ASqfdvaer123456`                      |
   | `SUMMARIZER_BASE_URL` | ❌        | str  | Valid URL                                 | Base URL for summarizer API    | Provider-specific   | `https://api.deepseek.com/v1`          |
   | `SUMMARIZER_MODEL`    | ❌        | str  | Model name                                | Model name for summarization   | Provider-specific   | `deepseek-reasoner`                    |
   | `RATER_BASE_URL`      | ❌        | str  | Valid URL                                 | Base URL for rater API         | Provider-specific   | `https://open.bigmodel.cn/api/paas/v4` |
   | `RATER_MODEL`         | ❌        | str  | Model name                                | Model name for paper rating    | Provider specific   | `glm-4.5-flash`                        |
   | `ARXIV_CATEGORIES`    | ❌        | str  | Real ArXiv categories                     | ArXiv categories to monitor    | `cs.AI,cs.CV,cs.RO` | `cs.AI,cs.LG,cs.RO`                    |
   | `MAX_PAPERS`          | ❌        | int  | 1-1000                                    | Maximum number of summaries    | `5`                 | `10`                                   |
   | `OUTPUT_FORMATS`      | ❌        | str  | pdf, html, md and pdf, separated by comma | Output formats                 | `pdf,md`            | `pdf,html,md`                          |
   | `SMTP_PORT`           | ❌        | int  | Valid port number                         | SMTP port number               | `465`               | `587`                                  |

   **Note**: The system auto-detects base URLs and default models from recognized provider names. If you specify a recognized provider (e.g., `deepseek`, `openai`, `dashscope`), the base URL and default model will be automatically configured. For custom providers or when not specifying a provider name, you must provide the base URL and model name manually.

3. **Enable GitHub Actions**

   - Navigate to Actions tab in your fork
   - Enable Actions if prompted
   - Choose option: "I understand my workflows, go ahead and enable them"

4. **Run the Workflow**

   - **Manual**: Go to Actions → "ArXiv AutoSumm Daily" → "Run workflow"
   - **Scheduled**: Runs automatically daily at 22:00 UTC
   - **Test Mode**: Check "Run in test mode" for limited processing

#### Option B: Repository Configuration (Advanced)

For full control over advanced settings like VLM parsing, embedder rating and custom configurations, we recommend using `config.py` in the repository.

**Prerequisites:**

- Same as Option A

**Steps:**

1. **Fork and Set Repository Variable**

   - Fork the repository (same as Option A)
   - Navigate to Settings → Variables → Actions
   - Add repository variable: `USE_REPO_CONFIG = true`

2. **Configure and Commit config.yaml**

   - Copy `config.advanced.yaml` to `config.yaml`
   - **Put all settings directly in config.yaml**: categories, models, output formats, etc.
   - **Only use secret references for sensitive data**: `api_key: sec:API_KEY`
   - Commit `config.yaml` to your repository

3. **Customize Prompts (Optional)**

   - Edit prompt files in `prompts/` directory to customize behavior
   - **Preserve all `{...}` template placeholders** in the prompts
   - Common customizations:
     - `prompts/summ_lm/` - Summarization style and focus
     - `prompts/rate_lm/` - Rating criteria emphasis
     - `prompts/rate_emb/` - Embedding query for relevance filtering
     - `prompts/parse_vlm/` - VLM parsing instructions

4. **Configure Required Secrets**

   - Only set secrets for sensitive data referenced in your `config.yaml`
   - Use any of the allowed secret names from the workflow

**Allowed Secret Names** (from main.yml environment):

```secrets
# LLM Provider Keys
OPENAI_API_KEY, DEEPSEEK_API_KEY, MODELSCOPE_API_KEY, DASHSCOPE_API_KEY
SILICONFLOW_API_KEY, ZHIPU_API_KEY, MOONSHOT_API_KEY, MINIMAX_API_KEY
ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, VOLCENGINE_API_KEY

# Custom Function Keys
SUMMARIZER_API_KEY, RATER_API_KEY, EMBEDDER_API_KEY, VLM_API_KEY, LLM_API_KEY, API_KEY

# Email Configuration
SMTP_PASSWORD, SENDER_EMAIL, RECIPIENT_EMAIL, SMTP_SERVER, SMTP_PORT

# Configuration Variables
ARXIV_CATEGORIES, MAX_PAPERS, OUTPUT_FORMATS, RATING_STRATEGY
```

### Method 2: Local Setup with Git Clone

Full local control over execution timing and configuration.

#### Prerequisites

**System Requirements:**

- Git
- System dependencies (based on desired output formats)

**Optional System Dependencies:**

```bash
# For PDF output
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-xetex

# For HTML output
sudo apt-get install pandoc

# For AZW3 (Kindle) output
sudo apt-get install calibre

# Install all at once
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-xetex pandoc calibre
```

#### Installation Steps

1. **Clone Repository**

   ```bash
   git clone https://github.com/your-username/arxiv-autosumm.git
   cd arxiv-autosumm
   ```

2. **Install Python Dependencies**

   ```bash
   pip install -e .
   ```

3. **Configure Application**

   **Basic Configuration:**

   ```bash
   cp config.basic.yaml config.yaml
   # Edit config.yaml with your settings
   ```

   **Advanced Configuration:**

   ```bash
   cp config.advanced.yaml config.yaml
   # Edit config.yaml for advanced features
   ```

   **Environment Variables** (alternative to config file):

   ```bash
   # Create .env file
   echo "SUMMARIZER_API_KEY=your_key" > .env
   echo "RATER_API_KEY=your_key" >> .env
   echo "SMTP_PASSWORD=your_password" >> .env
   ```

4. **Test Configuration**

   ```bash
   autosumm run --test
   ```

5. **Run Pipeline**

   ```bash
   # Normal execution
   autosumm run
   
   # Verbose output
   autosumm run --verbose
   
   # Single category only
   autosumm run --specify-category cs.AI
   ```

#### Local Scheduling

For automated execution, you can use either systemd (recommended) or crontab.

##### Systemd Timer (Recommended)

Create a systemd service and timer for modern, reliable scheduling:

```bash
# Create systemd service file
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

# Create systemd timer file
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

# Reload systemd and enable timer
sudo systemctl daemon-reload
sudo systemctl enable arxiv-autosumm.timer
sudo systemctl start arxiv-autosumm.timer

# Check timer status
systemctl list-timers --all
```

##### Crontab (Alternative)

For systems without systemd, use traditional crontab:

```bash
# Edit crontab
crontab -e

# Run daily at 9 AM
0 9 * * * cd /path/to/arxiv-autosumm && autosumm run

# Run every 6 hours
0 */6 * * * cd /path/to/arxiv-autosumm && autosumm run
```

### Features

**Common Features:**

- **Automated Paper Processing**: Complete pipeline from ArXiv fetching to email delivery on a daily schedule
- **Multiple Output Formats**: PDF, HTML, Markdown, AZW3 (Kindle)
- **Advanced Caching**: SQLite-based deduplication to avoid redundant processing
- **Email Delivery**: SMTP configuration with attachment support

**GitHub Actions Specific:**

- **No Infrastructure Management**: GitHub provides all computing resources
- **Built-in Monitoring**: Automatic logging and execution history
- **Easy Deployment**: Fork repository, configure secrets, and run
- **Two Configuration Options**: Dynamic (secrets-based) or repository-based

**Local Setup Specific:**

- **Full Control**: Complete customization of all components
- **Unlimited Execution**: No time or resource constraints (2000mins/month for GitHub Actions)
- **Local Debugging**: Complete development environment access
- **Data Privacy**: All processing and storage remains local (if you use local models)

## Pipeline Description

The complete chronological pipeline processes research papers in the exact order of execution:

- **1. Fetch**: Downloads paper metadata from ArXiv using configured categories or date ranges
- **2. Deduplication**: Uses SQLite cache to skip already-processed papers, preventing redundant work
- **3. Rate Limiting**: Respects ArXiv API limits with exponential backoff to avoid being blocked
- **4. PDF Download**: Retrieves full PDFs for newly discovered papers
- **5. Fast Parse**: Extracts text using PyPDF2 for quick initial processing
- **6. Embedder Rate** *(Optional)*: Uses embedding similarity to select top-k papers based on relevance to your interests
- **7. LLM Rate** *(Optional)*: Uses language models to score papers on configured criteria (novelty, methodology, clarity, etc. Based on your configuration)
- **8. VLM Parse** *(Optional)*: Uses Vision Language Models for enhanced OCR on complex layouts and figures
- **9. Summarize**: Generates concise technical summaries using your configured LLM
- **10. Render**: Creates outputs in PDF, HTML, Markdown, or AZW3 formats
- **11. Deliver**: Sends formatted summaries via email

### Rating Strategies

You can configure three different rating approaches based on your needs:

- **llm**: Uses only LLM rating (most accurate, higher cost)
- **embedder**: Uses only embedding similarity (faster, lower cost)
- **hybrid**: Uses embedder -> LLM hierarchical rating (balanced approach)

Configure in `config.yaml`:

```yaml
rate:
  strategy: llm  # llm, embedder or hybrid
  top_k: 80 # if strategy is hybrid, set this parameter
```

**Parameter Flow:**

- **fetch:max_results** → initial paper limit from ArXiv
- **rate:top_k** → papers passed to LLM for rating (after optional embedder filtering)
- **rate:max_selected** → final papers selected for optional vlm parsing and summarization (after rating)

## Configuration

### Basic Configuration

#### Run

```yaml
run:
  categories: ["cs.AI", "cs.RO"] # arxiv categories you're interested in.
  send_log: false # whether to deliver logfile as well as summaries
  log_dir: ./logs # where to store logfiles  
```

#### Fetch

```yaml
fetch:
  days: 8
  max_results: 200
  max_retries: 10
```

#### Summarizer Config

```yaml
summarize:
  provider: deepseek
  api_key: env:DEEPSEEK_API_KEY # use environmental variable
  base_url: https://api.deepseek.com/v1
  model: deepseek-reasoner # use a powerful reasoner model as summarizer
  batch: False # disable batch processing
  system_prompt: null # it's ok to use empty system prompt
  user_prompt_template: file:./prompts/summ_lm/user.md # user prompt template for summarizer, must contain {paper_content} placeholder
  completion_options:
    temperature: 0.6
    # can add other completion options such as top_k, top_p, etc.
  context_length: 131072 # default to 131072, this parameter decides how paper content will be truncated to fit in model's context length
```

#### Paper Rating

```yaml
rate:
  strategy: llm # llm, embedder or hybrid
  top_k: 80    # maximum papers to pass to LLM for rating (after embedder filtering)
  max_selected: 10  # final papers to summarize (after LLM rating)
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
        description: How original and innovative are the contributions?
        weight: 0.3
      methodology:
        description: How rigorous is the experimental design and evaluation?
        weight: 0.25
      clarity:
        description: How well-written and understandable is the paper?
        weight: 0.2
```

#### Render Config

```yaml
render:
  formats: ["pdf", "md"] # summaries' formats, default setting gives you .pdf and .md files
  output_dir: ./output # autosumm will output these summaries to output_dir, then deliver to you via email
  base_filename: null # default to "summary". Summary naming is {base_filename}_{category}_{year&week}.{extension_name}
```

#### Deliver and Email

```yaml
deliver:
  smtp_server
  port: 465
  sender: env:SENDER
  recipient: env:RECIPIENT
  password: env:SMTP_PASSWORD
```

#### Default LLM Providers

| Provider | Example Model | Notes |
|----------|---------------|--------|
| **OpenAI** | gpt-4o, gpt-4o-mini | Requires OPENAI_API_KEY |
| **DeepSeek** | deepseek-reasoner | Requires DEEPSEEK_API_KEY |
| **DashScope** | qwen-plus, qwen-turbo | Requires DASHSCOPE_API_KEY |
| **SiliconFlow** | deepseek-ai/DeepSeek-R1 | Requires SILICONFLOW_API_KEY |
| **Ollama** | qwen3:32b, llama3.1:8b | Requires Local Installation |
| **Moonshot** | kimi-k2-0711-preview | Requires MOONSHOT_API_KEY |
| **Minimax** | MiniMax-Text-01 | Requires MINIMAX_API_KEY |
| **ModelScope** | Qwen/Qwen3-235B-A22B-Thinking-2507 | Requires MODELSCOPE_API_KEY |
| **Zhipu** | glm-4.5, glm-4.5-flash | Requires ZHIPU_API_KEY |
| **VolcEngine** | doubao-1.6-seed-thinking | Requires ARK_API_KEY |

### Advanced Configuration

#### Coming soon

## 🚨 Known Limitations

- **Rate limiting**: Some providers may have aggressive rate limits
- **VLM Parsing**: Enabling VLM parsing may require significant time and tokens, especially for large PDFs, and the parsing quality is not guaranteed (rely on the specific model and prompts)

## Future Plan

- **More Providers**: Anthropic API format for Claude
- **Update README**: Update README with more user-friendly illustrations and configuration instruction
- **Tune Prompts**: Provide clear and simple entrance for users to tune their custom prompts

## 📄 License

MIT License - see LICENSE file for details.
