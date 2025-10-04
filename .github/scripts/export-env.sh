#!/bin/bash

# Universal repository variable and secrets exporter
# This script exports ALL repository variables and common secrets as environment variables

echo "🔧 Starting universal repository variable and secrets export..."

# Export ALL repository variables as environment variables
echo "📋 Exporting repository variables..."

# Check if we have any repository variables
VARS_JSON='${{ toJSON(vars) }}'

if [ -z "$VARS_JSON" ] || [ "$VARS_JSON" = "{}" ]; then
  echo "ℹ️ No repository variables found"
else
  echo "📋 Found repository variables, exporting as environment variables..."

  # Install jq if not present (it's usually available in GitHub runners)
  if ! command -v jq &> /dev/null; then
    echo "📦 Installing jq for JSON processing..."
    sudo apt-get update && sudo apt-get install -y jq
  fi

  # Export ALL repository variables as environment variables
  echo "$VARS_JSON" | jq -r 'to_entries[] |
    "export \(.key)=\(.value)"' > /tmp/vars_exports.sh

  # Source the exports to make them available in current shell
  source /tmp/vars_exports.sh

  # Show what was exported (without revealing values)
  echo "$VARS_JSON" | jq -r 'keys[]' | while read var_name; do
    echo "  ✅ Exported: $var_name"
  done

  # Make the exports available to subsequent steps by adding to GITHUB_ENV
  sed 's/^export //' /tmp/vars_exports.sh >> $GITHUB_ENV

  # Clean up temporary file
  rm -f /tmp/vars_exports.sh
fi

# Export supported secrets
echo "🔐 Processing supported secrets..."

# Group 1: Option A Quick Start secrets (also supported in Option B)
echo "  📋 Exporting Option A secrets (also supported in Option B):"
OPTION_A_SECRETS=(
  "ARXIV_CATEGORIES"
  "MAX_PAPERS"
  "OUTPUT_FORMATS"
  "RATING_STRATEGY"
  "SUMMARIZER_PROVIDER"
  "SUMMARIZER_API_KEY"
  "SUMMARIZER_BASE_URL"
  "SUMMARIZER_MODEL"
  "RATER_PROVIDER"
  "RATER_API_KEY"
  "RATER_BASE_URL"
  "RATER_MODEL"
  "SMTP_SERVER"
  "SMTP_PORT"
  "SENDER_EMAIL"
  "RECIPIENT_EMAIL"
  "SMTP_PASSWORD"
)

# Group A: Option A Quick Start secrets (also supported in Option B)
echo "  📋 Exporting Option A secrets (also supported in Option B):"
echo "ARXIV_CATEGORIES=\${{ secrets.ARXIV_CATEGORIES }}" >> $GITHUB_ENV
echo "MAX_PAPERS=\${{ secrets.MAX_PAPERS }}" >> $GITHUB_ENV
echo "OUTPUT_FORMATS=\${{ secrets.OUTPUT_FORMATS }}" >> $GITHUB_ENV
echo "RATING_STRATEGY=\${{ secrets.RATING_STRATEGY }}" >> $GITHUB_ENV
echo "SUMMARIZER_PROVIDER=\${{ secrets.SUMMARIZER_PROVIDER }}" >> $GITHUB_ENV
echo "SUMMARIZER_API_KEY=\${{ secrets.SUMMARIZER_API_KEY }}" >> $GITHUB_ENV
echo "SUMMARIZER_BASE_URL=\${{ secrets.SUMMARIZER_BASE_URL }}" >> $GITHUB_ENV
echo "SUMMARIZER_MODEL=\${{ secrets.SUMMARIZER_MODEL }}" >> $GITHUB_ENV
echo "RATER_PROVIDER=\${{ secrets.RATER_PROVIDER }}" >> $GITHUB_ENV
echo "RATER_API_KEY=\${{ secrets.RATER_API_KEY }}" >> $GITHUB_ENV
echo "RATER_BASE_URL=\${{ secrets.RATER_BASE_URL }}" >> $GITHUB_ENV
echo "RATER_MODEL=\${{ secrets.RATER_MODEL }}" >> $GITHUB_ENV
echo "SMTP_SERVER=\${{ secrets.SMTP_SERVER }}" >> $GITHUB_ENV
echo "SMTP_PORT=\${{ secrets.SMTP_PORT }}" >> $GITHUB_ENV
echo "SENDER_EMAIL=\${{ secrets.SENDER_EMAIL }}" >> $GITHUB_ENV
echo "RECIPIENT_EMAIL=\${{ secrets.RECIPIENT_EMAIL }}" >> $GITHUB_ENV
echo "SMTP_PASSWORD=\${{ secrets.SMTP_PASSWORD }}" >> $GITHUB_ENV
echo "    ✅ Exported Group A Secrets"

# Group B: Provider API keys (all recognized providers)
echo "  🔑 Exporting provider API keys:"
echo "ANTHROPIC_API_KEY=\${{ secrets.ANTHROPIC_API_KEY }}" >> $GITHUB_ENV
echo "COHERE_API_KEY=\${{ secrets.COHERE_API_KEY }}" >> $GITHUB_ENV
echo "DASHSCOPE_API_KEY=\${{ secrets.DASHSCOPE_API_KEY }}" >> $GITHUB_ENV
echo "DEEPSEEK_API_KEY=\${{ secrets.DEEPSEEK_API_KEY }}" >> $GITHUB_ENV
echo "GEMINI_API_KEY=\${{ secrets.GEMINI_API_KEY }}" >> $GITHUB_ENV
echo "GROQ_API_KEY=\${{ secrets.GROQ_API_KEY }}" >> $GITHUB_ENV
echo "MINIMAX_API_KEY=\${{ secrets.MINIMAX_API_KEY }}" >> $GITHUB_ENV
echo "MODELSCOPE_API_KEY=\${{ secrets.MODELSCOPE_API_KEY }}" >> $GITHUB_ENV
echo "MOONSHOT_API_KEY=\${{ secrets.MOONSHOT_API_KEY }}" >> $GITHUB_ENV
echo "OLLAMA_API_KEY=\${{ secrets.OLLAMA_API_KEY }}" >> $GITHUB_ENV
echo "OPENAI_API_KEY=\${{ secrets.OPENAI_API_KEY }}" >> $GITHUB_ENV
echo "OPENROUTER_API_KEY=\${{ secrets.OPENROUTER_API_KEY }}" >> $GITHUB_ENV
echo "SILICONFLOW_API_KEY=\${{ secrets.SILICONFLOW_API_KEY }}" >> $GITHUB_ENV
echo "TOGETHER_API_KEY=\${{ secrets.TOGETHER_API_KEY }}" >> $GITHUB_ENV
echo "ARK_API_KEY=\${{ secrets.ARK_API_KEY }}" >> $GITHUB_ENV
echo "ZHIPU_API_KEY=\${{ secrets.ZHIPU_API_KEY }}" >> $GITHUB_ENV
echo "    ✅ Exported Group B Secrets"

echo ""
echo "💡 Note: To use additional secret names, add them to the workflow env blocks manually"