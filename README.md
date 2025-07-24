# ArXiv AutoSumm

Automated research paper summarization from ArXiv with LLM-powered rating and delivery.

## What Works Now

**Core 15-step pipeline**: fetch -> parse -> rate -> summarize -> render -> deliver  
**CLI interface**: `python autosumm/cli.py run` and `python autosumm/cli.py init`  
**Local installation**: Works with git clone, then pip install  
**Multiple formats**: HTML, Markdown (always), PDF (with TeXLive), AZW3 (coming soon)  
**Smart caching**: SQLite-based with TTL and config change detection  
**Multiple LLM providers**: DashScope, SiliconFlow, Ollama, OpenAI, etc.
**VLM powered paper parsing**: Keep table and image structure, but need extra configuration (default disable vlm)

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure
Copy the template and edit:
```bash
cp config.yaml my_own_config.yaml
# Edit my_own_config.yaml with your API keys and email settings
```

### 3. Run
```bash
# Interactive setup (optional but recommended)
python autosumm/cli.py init

# Run the pipeline
python autosumm/cli.py run
```

## Configuration

Use `config.yaml` as your template. **Required changes**:

```yaml
# LLM Configuration
summarize:
  provider: "dashscope"  # or "siliconflow", "openai", or just write anything as long as the base url is correct.
  api_key: "YOUR_API_KEY_HERE"  # Get from your provider
  model: "qwen-turbo"

# Email Configuration  
deliver:
  smtp_server: "smtp.gmail.com"
  sender: "your_email@gmail.com"
  recipient: "your_email@gmail.com"
  password: "YOUR_APP_PASSWORD"  # App password, not regular password
```

See `config.yaml` for all available options and sensible defaults.

## CLI Commands

### `autosumm run`
Run the complete pipeline with your config:
```bash
python autosumm/cli.py run --config my_own_config.yaml --verbose
```

### `autosumm init`
Interactive setup wizard (creates/edits config):
```bash
python autosumm/cli.py init --config my_own_config.yaml
```

## Output Formats

| Format | Status | Requirements |
|--------|--------|--------------|
| **Markdown** | Always available | None |
| **HTML** | Always available | None |
| **PDF** |  Requires TeXLive | Install `texlive-latex-base texlive-latex-extra texlive-xetex pandoc` |
| **AZW3** |  Coming soon | - |

## Known Limitations

- **AZW3 conversion**: Not yet implemented
- **PDF generation**: Requires TeXLive installation (large download)
- **Docker support**: Containerization in progress
- **Testing**: Limited real-world usage, expect some rough edges
- **Config validation**: Basic validation only, will improve

## Troubleshooting

### API Key Setup

**DashScope (Alibaba)**:
```yaml
summarize:
  provider: "dashscope"
  api_key: "sk-your-key-here"
  model: "qwen-turbo"
```

**SiliconFlow**:
```yaml
summarize:
  provider: "siliconflow"
  api_key: "sk-your-key-here"
  model: "deepseek-ai/DeepSeek-V2.5"
```

**Ollama (local)**:
```yaml
summarize:
  provider: "ollama"
  base_url: "http://localhost:11434"
  model: "llama3.1"
  # No API key needed for local
```

### Common Issues

**PDF generation fails**:
```bash
# Ubuntu/Debian
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-xetex pandoc

# macOS
brew install --cask mactex
```

**Email delivery fails**:
- Use app-specific password (not regular email password)
- Check SMTP server settings
- Verify port 465 (SSL) or 587 (TLS)

**API connection issues**:
- Test with: `curl -H "Authorization: Bearer YOUR_KEY" https://api.provider.com/v1/models`
- Check rate limits on your provider
