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

#### Option B: Repository Configuration (Advanced)

For full control over advanced settings like VLM parsing, embedder rating and custom configurations, we recommend using `config.yaml` in the repository.

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
   - **Use environment variables for sensitive data**: `api_key: env:API_KEY`
   - Commit `config.yaml` to your repository

3. **Customize Prompts (Optional)**

   - Edit prompt files in `prompts/` directory to customize behavior
   - **Preserve all `{...}` template placeholders** in the prompts
   - Common customizations:
     - `prompts/summ_lm/` - Summarization style and focus
     - `prompts/rate_lm/` - Rating criteria emphasis
     - `prompts/rate_emb/` - Embedding query for relevance filtering
     - `prompts/parse_vlm/` - VLM parsing instructions

4. **Configure Secrets and Variables**

   Configure your repository with secrets for safety concerns and variables for maximum flexibility:

   **Environment Variables** (for all configuration):
     - Use for API keys, passwords, and any settings
     - Reference in config.yaml with `env:` prefix: `api_key: env:API_KEY`

   Two types of environment variables are supported:

   Use **Repository Secrets** for sensitive data:
     - Save API keys, passwords, and sensitive information to repository secrets
     - Reference with `env:` prefix: `api_key: env:MY_API_KEY` in `config.yaml`
     - GitHub Actions automatically masks secrets in logs

   Use **Repository Variables** for flexible configuration:
     - Support any variable name you choose
     - Use for settings you want to change without committing `config.yaml`
     - Also reference with `env:` prefix: `max_results: env:FETCH_RESULTS`

**Example Usage:**

```yaml
fetch:
  max_results: env:FETCH_RESULTS    # Repository variable (any name)
  days: env:CUSTOM_DAYS           # Repository variable (any name)

summarize:
  model: env:MY_SUMMARIZER_MODEL  # Repository variable (any name)
  api_key: env:SUMMARIZER_API_KEY # Pre-defined secret name

rate:
  max_selected: env:MAX_PAPERS    # Repository variable (any name)
```

**Secret Naming Constraints:**

GitHub Actions has technical limitations that prevent truly unlimited custom secret names. Here's what's actually supported:

**✅ What Works:**

1. **Repository Variables**: Any name you want (these are not secrets)
   - Example: `MY_MODEL`, `CUSTOM_DAYS`, `FETCH_RESULTS`

2. **Pre-defined Secret Names** (Option A): Fixed names for quick setup

   ```yaml
   # These specific names work:
   SUMMARIZER_API_KEY, RATER_API_KEY, SMTP_PASSWORD
   SUMMARIZER_PROVIDER, SUMMARIZER_MODEL, MAX_PAPERS
   # ... and more (see .github/scripts/export-env.sh lines 49-67)
   ```

3. **Provider API Keys** (Option B): Standard `{PROVIDER}_API_KEY` pattern

   ```yaml
   # These provider-specific names work:
   ANTHROPIC_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY
   MODELSCOPE_API_KEY, ZHIPU_API_KEY, SILICONFLOW_API_KEY
   # ... and all recognized providers (lines 92-107)
   ```

**❌ Why Unlimited Custom Names Don't Work:**

1. **Technical Limitation**: GitHub Actions cannot dynamically access secret names at runtime
   - Secrets must be explicitly referenced in workflow files using `${{ secrets.SECRET_NAME }}`
   - No programmatic way to list or access arbitrary secret names

2. **Security Design**: GitHub intentionally restricts secret access
   - Prevents accidental exposure of all repository secrets
   - Requires explicit declaration of which secrets a workflow can access
   - Auditing and security boundaries depend on this limitation

**🔧 Adding Additional Secret Names:**

If you need secret names beyond the supported patterns, you must manually add them to `.github/workflows/main.yml` after line 113:

```bash
# Add your custom secrets after line 113
echo "MY_CUSTOM_API_KEY=\${{ secrets.MY_CUSTOM_API_KEY }}" >> $GITHUB_ENV
echo "COMPANY_EMAIL=\${{ secrets.COMPANY_EMAIL }}" >> $GITHUB_ENV
```

**Example Configuration:**

```yaml
# Using pre-defined Option A secrets
summarize:
  api_key: env:SUMMARIZER_API_KEY     # Works out of the box
  model: env:SUMMARIZER_MODEL        # Works out of the box

# Using provider API keys
summarize:
  provider: openai
  api_key: env:OPENAI_API_KEY        # Works out of the box

# Using repository variables (not secrets)
summarize:
  model: env:MY_CHOSEN_MODEL         # Repository variable, any name
  temperature: env:MY_TEMP_SETTING   # Repository variable, any name
```

### Method 2: Local Setup with Git Clone

Full local control over execution timing and configuration.

#### Prerequisites

**System Requirements:**

- Git
- Python 3.11+
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
sudo tee ~/.config/systemd/user/arxiv-autosumm.service > /dev/null << 'EOF'
[Unit]
Description=ArXiv AutoSumm Service
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/arxiv-autosumm # replace with real directory
ExecStart=/usr/bin/python -m autosumm.cli run # replace with your python path
StandardOutput=journal
StandardError=journal
EOF

# Create systemd timer file
sudo tee ~/.config/systemd/user/arxiv-autosumm.timer > /dev/null << 'EOF'
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
- **Multiple Rating Strategies**: LLM-based, embedding-based, or hybrid approach
- **VLM Parsing**: Optional Vision Language Model support for enhanced PDF parsing

**GitHub Actions Specific:**

- **No Infrastructure Management**: GitHub provides all resources
- **Built-in Monitoring**: Automatic logging and execution history
- **Easy Deployment**: Fork repository, configure secrets, and run
- **Two Configuration Options**: Dynamic (secrets-based) or repository-based
- **Universal Repository Variables**: Flexible configuration without code changes

**Local Setup Specific:**

- **Full Control**: Complete customization of all components
- **Unlimited Execution**: No time or resource constraints
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
- **hybrid**: Uses embedder → LLM hierarchical rating (balanced approach)

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
  sender: env:SENDER_EMAIL
  recipient: env:RECIPIENT_EMAIL
  password: env:SMTP_PASSWORD
```

#### Default LLM Providers

| Provider | Example Model | Requirements |
|----------|---------------|--------|
| **Anthropic** | claude-sonnet-4-5-20250929 | ANTHROPIC_API_KEY |
| **Cohere** | command-r-plus, command | COHERE_API_KEY |
| **DashScope** | qwen-max, qwen-turbo | DASHSCOPE_API_KEY |
| **DeepSeek** | deepseek-reasoner, deepseek-chat | DEEPSEEK_API_KEY |
| **Gemini** | gemini-1.5-pro, gemini-1.5-flash | GEMINI_API_KEY |
| **Groq** | llama-3.1-70b-versatile, mixtral-8x7b-32768 | GROQ_API_KEY |
| **MinerU** | *for pdf parsing, no specific models* | MINERU_API_TOKEN |
| **Minimax** | MiniMax-Text-01 | MINIMAX_API_KEY |
| **Mistral** | mistral-large-latest | MISTRAL_API_KEY |
| **ModelScope** | Qwen/Qwen2.5-7B-Instruct, Qwen/Qwen2.5-32B-Instruct | MODELSCOPE_API_KEY |
| **Moonshot** | kimi-k2-0711-preview, moonshot-v1-8k | MOONSHOT_API_KEY |
| **Ollama** | qwen2.5:7b, llama3.1:8b, deepseek-coder-v2:16b | Local Installation |
| **OpenAI** | gpt-4o, gpt-4o-mini, text-embedding-3-small | OPENAI_API_KEY |
| **OpenRouter** | anthropic/claude-3.5-sonnet, meta-llama/llama-3.1-70b-instruct | OPENROUTER_API_KEY |
| **SiliconFlow** | deepseek-ai/DeepSeek-R1, Qwen/Qwen2.5-7B-Instruct | SILICONFLOW_API_KEY |
| **Together** | meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo, Qwen/Qwen2.5-72B-Instruct-Turbo | TOGETHER_API_KEY |
| **VolcEngine** | doubao-1.6-seed-thinking, doubao-pro-32k | ARK_API_KEY |
| **Zhipu** | glm-4.6, glm-4.5-flash, glm-4v-plus | ZHIPU_API_KEY |

### Advanced Configuration

#### VLM Parsing

For enhanced PDF parsing using Vision Language Models:

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

#### Embedder Configuration

For similarity-based paper filtering:

```yaml
rate:
  strategy: hybrid
  embedder:
    provider: modelscope
    model: BAAI/bge-large-en-v1.5
    api_key: env:EMBEDDER_API_KEY
    query_prompt: file:./prompts/rate_emb/query.md
```

## CLI Commands

The `autosumm` CLI provides commands for pipeline management:

```bash
# Run the complete pipeline
autosumm run [--config path/to/config.yaml] [--verbose] [--test] [--specify-category CATEGORY]

# Test configuration and dependencies
autosumm run --test [--config path/to/config.yaml] [--verbose]

# Prompt tuning interface (coming soon)
autosumm tune [--config path/to/config.yaml] [--category CATEGORY]

# Show help
autosumm --help
autosumm [command] --help
```

### Command Options

- `--config, -c`: Path to configuration file (default: `config.yaml`)
- `--verbose, -v`: Enable verbose output with detailed logging
- `--test, -t`: Test configuration and dependencies only (no pipeline execution)
- `--specify-category, -s`: Process only specified ArXiv category (single category only)

## 🚨 Known Limitations

- **Rate limiting**: Some providers may have aggressive rate limits
- **VLM Parsing**: Enabling VLM parsing may require significant time and tokens, especially for large PDFs, and the parsing quality is not guaranteed (rely on the specific model and prompts)
- **Processing Time**: Large paper collections may take considerable time to process depending on chosen models and strategies

## 📄 License

MIT License - see LICENSE file for details.
