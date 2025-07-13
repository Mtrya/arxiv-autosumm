# ArXiv AutoSumm

Automated research paper summarization from ArXiv with LLM-powered rating and delivery.

## What's Working
-  **Core pipeline**: fetch ’ parse ’ rate ’ summarize ’ render ’ deliver
-  **CLI interface**: `autosumm run|init|test-config`
-  **Caching**: SQLite-based with TTL
-  **Multiple formats**: markdown, PDF, HTML, AZW3
-  **Docker containerization**: multi-stage Dockerfile + docker-compose
-  **Configuration**: YAML-based with environment variables

## Quick Start
```bash
# Local
python autosumm/main.py

# Docker
docker-compose up arxiv-autosumm
```

## Configuration
Set up `my_own_config.yaml` (see `config.yaml` template):
- ArXiv categories to monitor
- LLM provider settings (OpenAI, DashScope, etc.)
- Email delivery settings
- Output formats

## What's Next
- = **Setup wizard** (`autosumm init`) - CLI stub exists
- = **Config validation** (`autosumm test-config`) - stub exists
- = **Docker functions** - container ready, need to test runtime
- = **Scheduled execution** - docker-compose includes cron profile
- = **Setup documentation** - comprehensive guide needed

## Docker Usage
```bash
# Build
docker build -t arxiv-autosumm -f docker/Dockerfile .

# Run with volumes
docker run -v $(pwd)/config:/data/config arxiv-autosumm
```

## Project Structure
```
autosumm/           # Core Python package
docker/            # Container files
config.yaml        # Configuration template
autosumm.sh        # CLI wrapper script
```