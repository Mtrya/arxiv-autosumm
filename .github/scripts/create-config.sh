#!/bin/bash

# Generate config.yaml and .env from environment variables
# This script creates the configuration when not using repository config.yaml

echo "🔧 Generating configuration from environment variables..."

# Set default values
CATEGORIES=${ARXIV_CATEGORIES:-'cs.AI,cs.CV,cs.RO'}
MAX_PAPERS_CONFIG=${MAX_PAPERS:-'5'}
OUTPUT_FORMATS_CONFIG=${OUTPUT_FORMATS:-'pdf,md'}
RATING_STRATEGY_CONFIG=${RATING_STRATEGY:-'llm'}

# Determine provider defaults
if [ -z "$SUMMARIZER_PROVIDER" ]; then
  SUMMARIZER_PROVIDER="modelscope"
  echo "🤖 Default summarizer provider: modelscope"
fi

if [ -z "$RATER_PROVIDER" ]; then
  RATER_PROVIDER="$SUMMARIZER_PROVIDER"
  echo "🎯 Default rater provider: $RATER_PROVIDER"
fi

# Create config.yaml from environment variables
echo "📝 Creating config.yaml..."
cat > config.yaml << EOF
run:
  categories: [$(echo $CATEGORIES | sed 's/,/, /g')]
  send_log: true
  log_dir: ./logs

fetch:
  days: 3
  max_results: 100
  max_retries: 10

summarize:
  provider: $SUMMARIZER_PROVIDER
  api_key: env:SUMMARIZER_API_KEY
  base_url: ${SUMMARIZER_BASE_URL:-'https://api-inference.modelscope.cn/v1/'}
  model: ${SUMMARIZER_MODEL:-'Qwen/Qwen2.5-7B-Instruct'}
  batch: false
  system_prompt: file:./prompts/summ_lm/system.md
  user_prompt_template: file:./prompts/summ_lm/user.md
  completion_options:
    temperature: 0.7
  context_length: 200000

rate:
  strategy: $RATING_STRATEGY_CONFIG
  top_k: 80
  max_selected: $MAX_PAPERS_CONFIG
  embedder: null
  llm:
    provider: $RATER_PROVIDER
    api_key: env:RATER_API_KEY
    base_url: ${RATER_BASE_URL:-'https://api-inference.modelscope.cn/v1/'}
    model: ${RATER_MODEL:-'Qwen/Qwen2.5-7B-Instruct'}
    batch: false
    system_prompt: file:./prompts/rate_lm/system.md
    user_prompt_template: file:./prompts/rate_lm/user.md
    completion_options:
      temperature: 0.2
      max_tokens: 1024
    context_length: 100000
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

render:
  formats: [$(echo $OUTPUT_FORMATS_CONFIG | sed 's/,/, /g')]
  output_dir: ./output
  base_filename: null

cache:
  dir: ~/.cache/arxiv-autosumm/
  ttl_days: 16

deliver:
  smtp_server: $SMTP_SERVER
  port: ${SMTP_PORT:-'465'}
  sender: $SENDER_EMAIL
  recipient: $RECIPIENT_EMAIL
  password: env:SMTP_PASSWORD
EOF

echo ""
echo "✅ Configuration generated successfully"
echo "📊 Configuration summary:"
echo "  📚 Categories: $CATEGORIES"
echo "  📄 Max papers: $MAX_PAPERS_CONFIG"
echo "  📋 Output formats: $OUTPUT_FORMATS_CONFIG"
echo "  🎯 Rating strategy: $RATING_STRATEGY_CONFIG"
echo "  🤖 Summarizer: $SUMMARIZER_PROVIDER ($SUMMARIZER_MODEL)"
echo "  🎯 Rater: $RATER_PROVIDER ($RATER_MODEL)"
echo "  📧 Email: $SENDER_EMAIL → $RECIPIENT_EMAIL"