# ArXiv AutoSumm

Automated research paper summarization from ArXiv with LLM-powered rating, multi-format delivery, and comprehensive configuration management.

## 🚀 What Works Now

**✅ Complete 15-step pipeline**: fetch → parse → rate → summarize → render → deliver  
**✅ CLI**: Interactive setup, configuration testing, and summarization pipeline running
**✅ Multi-format output**: Markdown, HTML, PDF, AZW3 (Kindle)  
**✅ Smart caching**: SQLite-based with TTL, config change detection, and rate limiting  
**✅ VLM-powered parsing**: Vision Language Model OCR for enhanced PDF processing  
**✅ Comprehensive validation**: API connectivity, dependency checks, and error handling  
**✅ Environment variables**: Full .env support with secure credential management

## 📦 Installation

### Method 1: Development Installation

Create and activate an virtual environment (optional but recommended)

```bash
# python3 -m venv arxiv-env
# source arxiv-env/bin/activate
# Or using conda
# conda create -n arxiv-env
# conda activate arxiv-env
```

Then install in the virtual environment

```bash
git clone https://github.com/Mtrya/arxiv-autosumm.git
cd arxiv-autosumm
pip install -e .
```

### Method 2: Using Docker

#### **Not Implemented, Coming Soon**

## ⚡ Quick Start

### 1. Interactive Setup (Recommended)

```bash
autosumm init
```

This will guide you through:

- LLM provider selection and API key setup
- ArXiv categories configuration
- Email delivery setup
- Validation and testing

### 2. Manual Configuration

```bash
cp config.yaml my_config.yaml
# Edit my_config.yaml with your custom settings
autosumm test-config --config my_config.yaml # test if config is valid
autosumm run --config my_config.yaml # run pipeline
```

### 3. Environment Variables *(Optional)*

Use `.env` file or environment variables for sensitive data:

```bash
# .env file
DASHSCOPE_API_KEY=your-key-here
SMTP_PASSWORD=your-app-password
```

### 4. Start with CLI Commands

```bash
# Run the complete pipeline
autosumm run [--config path/to/config.yaml] [--verbose] [--category an_arxiv_category]

# Or simply:
autosumm run

# Get help
autosumm --help
autosumm [command] --help
```

## Recommended Usage

### Automated Daily Summaries with Cron

Set up automated daily paper summaries using cron:

```bash
# Add to crontab (crontab -e)
# Run daily at 8 AM
0 8 * * * cd /path/to/arxiv-autosumm && autosumm run --config my_config.yaml

# Run weekly on Monday at 9 AM
0 9 * * 1 cd /path/to/arxiv-autosumm && autosumm run --config my_config.yaml
```

### Systemd Timer (Modern Alternative)

Create a systemd service for more reliable scheduling.

#### Method 1: Direct Python Path (Universal - Works with any environment manager)

```bash
# First, activate your environment using your preferred method:
# conda activate myenv
# source venv/bin/activate  
# poetry shell
# pipenv shell
# etc.

# Then find your Python path
which python

# Use that exact path in your service file
```bash
# Create service file: ~/.config/systemd/user/arxiv-autosumm.service
[Unit]
Description=ArXiv AutoSumm Daily Pipeline
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/arxiv-autosumm
ExecStart=/your/env/python/path -m autosumm.cli run --config my_config.yaml

[Install]
WantedBy=default.target
```

#### Method 2: Environment Activation (If Method 1 doesn't work)

```bash
# For most virtual environments (adjust activation command for your setup):
[Unit]
Description=ArXiv AutoSumm Daily Pipeline
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/arxiv-autosumm
ExecStart=/bin/bash -c 'source /path/to/activate-script && python -m autosumm.cli run --config my_config.yaml'

[Install]
WantedBy=default.target
```

Common activation scripts by environment type:

- venv/virtualenv: `source /path/to/venv/bin/activate`
- conda: `source /path/to/conda/etc/profile.d/conda.sh && conda activate env-name`
- poetry: `cd /project/dir && poetry run python -m autosumm.cli run --config my_config.yaml`

#### Timer Configuration

```bash
# Create timer file: ~/.config/systemd/user/arxiv-autosumm.timer
[Unit]
Description=Run ArXiv AutoSumm daily

[Timer]
OnCalendar=*-*-* 2:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

#### Testing Your Setup

```bash
# Test the exact command from your service file
/your/env/python/path -m autosumm.cli run --config my_config.yaml

# Then proceed with systemd setup
systemctl --user daemon-reload
systemctl --user enable arxiv-autosumm.timer
systemctl --user start arxiv-autosumm.timer
systemctl --user list-timers # should see arxiv-autosumm
```

### Manual CLI Usage

**Daily workflow:**

```bash
# Run pipeline with one of the categories 
autosumm run

# Run pipeline with specified category
autosumm run --category cs.AI

# Debug mode with verbose output
autosumm run --verbose
```

## Pipeline Description

The complete chronological pipeline processes research papers in the exact order of execution:

- **1. Fetch**: Downloads paper metadata from ArXiv using configured categories or date ranges
- **2. Deduplication**: Uses SQLite cache to skip already-processed papers, preventing redundant work
- **3. Rate Limiting**: Respects ArXiv API limits with exponential backoff to avoid being blocked
- **4. PDF Download**: Retrieves full PDFs for newly discovered papers
- **5. Fast Parse**: Extracts text using PyPDF2 for quick initial processing
- **6. Embedder Rate** *(Optional)*: Uses embedding similarity to select top-k papers based on relevance to your interests
- **7. LLM Rate** *(Optional)*: Uses language models to score papers on configured criteria (novelty, methodology, clarity... based on your configuration)
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

## 📊 Output Formats

| Format | Dependencies | Notes |
|--------|--------------|--------|
| **Markdown** | None | Primary format, always available |
| **HTML** | pandoc | MathJax support for equations |
| **PDF** | TeXLive + pandoc | Uses XeLaTeX engine, includes bibliography |
| **AZW3** | Calibre (ebook-convert) + pandoc | Kindle format with table of contents |

### Format Requirements

```bash
# Ubuntu/Debian
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-xetex pandoc calibre
```

## Basic Configuration

### Run

```yaml
run:
  categories: ["cs.AI", "cs.RO"] # arxiv categories you're interested in.
  send_log: false # whether to deliver logfile as well as summaries
  log_dir: ./logs # where to store logfiles  
```

### Fetch

```yaml
fetch:
  days: 8
  max_results: 200
  max_retries: 10
```

### Summarizer Config

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

### Paper Rating

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

**Parameter Flow:**

- **fetch:max_results** → initial paper limit from ArXiv
- **rate:top_k** → papers passed to LLM for rating (after optional embedder filtering)
- **rate:max_selected** → final papers selected for optional vlm parsing and summarization (after rating)

### Render Config

```yaml
render:
  formats: ["pdf", "md"] # summaries' formats, default setting gives you .pdf and .md files
  output_dir: ./output # autosumm will output these summaries to output_dir, then deliver to you via email
  base_filename: null # default to "summary". Summary naming is {base_filename}_{category}_{year&week}.{extension_name}
```

### Deliver and Email

```yaml
deliver:
  smtp_server
  port: 465
  sender: env:SENDER
  recipient: env:RECIPIENT
  password: env:SMTP_PASSWORD
```

### Default LLM Providers

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

## Common Issues

### **API Connection Problems**

```bash
# Test API connectivity
curl -H "Authorization: Bearer YOUR_KEY" \
  https://api.provider.com/v1/models

# Check provider configuration
autosumm test-config # check connectiviy, authentication, batch/vision support (if configured) and completion_options validity
```

### **Email Delivery Issues**

```bash
# Test SMTP connection
autosumm test-config --skip-api-checks
```

### **PDF Generation Fails**

```bash
# Check TeXLive installation
which xelatex
which pandoc

# Install missing packages
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-xetex pandoc

# Then test again with autosumm test-config --skip-api-checks
autosumm test-config --skip-api-checks
```

### **AZW3 Conversion Issues**

```bash
# Check Calibre installation
which ebook-convert

# Test conversion manually
ebook-convert input.html output.azw3

# Specify calibre_path in config.yaml if necessary
# Then test again with autosumm test-config --skip-api-checks
autosumm test-config --skip-api-checks
```

## Environment Setup

### **Setting up .env file**

```bash
# Create .env file
cat > .env << EOF
DASHSCOPE_API_KEY=your-dashscope-key
OPENAI_API_KEY=your-openai-key
SMTP_PASSWORD=your-app-password
EMAIL_SENDER=your-email@gmail.com
EMAIL_RECIPIENT=your-email@gmail.com
EOF

# Make sure .env is in your working directory
autosumm run --config my_config.yaml
```

You can also set these variables in ~/.bashrc, ~/.zshrc, etc. Using your API keys directly without hiding it is also totally fine, as long as you're sure about the safety issue.

## 🚨 Known Limitations

- **Docker support**: Not yet implemented (planned)
- **Unit tests**: Limited test coverage (project is stable (in my use case) but needs more tests)
- **Linux native**: Not tested on Windows or MacOS yet
- **Rate limiting**: Some providers may have aggressive rate limits
- **VLM Parsing**: Enabling VLM parsing may require significant time and tokens, especially for large PDFs, and the parsing quality is not guaranteed (rely on the specific model and prompts)

## Future Plan

- **Docker**: Add docker support. Will probably add a setup.sh for local build while also preparing an docker image for immediate use
- **Convenient Tests**: Add cli commands to do unit tests, enabling users to quickly find the prompt best tailored to their model
- **Cross Platform**: Add Window support. I don't have a Mac and have never used MacOS before, so I'm afraid I can't test it on MacOS. Welcome contributions.
- **More Providers**: Support Anthropic/Gemini/Zhipu/Volc/... compatible SDK
- **Audio Formats**: Use TTS models to convert summaries to speech

## 🔧 Advanced Configuration

### Coming soon

## 📄 License

MIT License - see LICENSE file for details.
