# ArXiv AutoSumm

Automated research paper summarization from ArXiv with LLM-powered rating, multi-format delivery, and comprehensive configuration management.

## 🚀 What Works Now

**✅ Complete pipeline**: fetch → parse → rate → summarize → render → deliver  
**✅ Multi-format output**: Markdown, HTML, PDF, AZW3 (Kindle)  

## 📦 Installation

### Quick Start

Use GitHub Actions workflow. Detailed documentation coming soon.

### Local Setup

Clone and use locally. Detailed documentation coming soon.

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
| **Zhipu** | glm-4.5, glm-4.5-flash | Requires ZHIPU_API_KEY |
| **VolcEngine** | doubao-1.6-seed-thinking | Requires ARK_API_KEY |

## 🚨 Known Limitations

- **Rate limiting**: Some providers may have aggressive rate limits
- **VLM Parsing**: Enabling VLM parsing may require significant time and tokens, especially for large PDFs, and the parsing quality is not guaranteed (rely on the specific model and prompts)

## Future Plan

- **More Providers**: Anthropic API format for Claude
- **Update README**: Will update README to include convenient use of GitHub Actions workflow after testing
- **Tune Prompts**: Provide clear and simple entrance for users to tune their custom prompts

## 🔧 Advanced Configuration

### Coming soon

## 📄 License

MIT License - see LICENSE file for details.
