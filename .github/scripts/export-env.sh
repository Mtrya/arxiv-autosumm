#!/bin/bash

# Repository variables exporter
# This script exports ALL repository variables as environment variables
# Usage: export-env.sh "${{ toJSON(vars) }}"

echo "🔧 Starting repository variable export..."

# Get repository variables JSON from first argument
VARS_JSON="$1"

# Debug: Show what we got
echo "🐛 Debug: VARS_JSON content: '$VARS_JSON'"
echo "🐛 Debug: VARS_JSON length: ${#VARS_JSON}"

if [ -z "$VARS_JSON" ] || [ "$VARS_JSON" = "{}" ] || [ "$VARS_JSON" = "null" ]; then
  echo "ℹ️ No repository variables found"
  echo "🐛 Debug: VARS_JSON was empty, null, or {}"
else
  echo "📋 Found repository variables, exporting as environment variables..."

  # Install jq if not present (it's usually available in GitHub runners)
  if ! command -v jq &> /dev/null; then
    echo "📦 Installing jq for JSON processing..."
    sudo apt-get update && sudo apt-get install -y jq
  fi

  # Debug: Test jq with our JSON
  echo "🐛 Debug: Testing jq with JSON..."
  echo "$VARS_JSON" | jq . || echo "🐛 Debug: jq failed with our JSON"

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

echo "✅ Repository variable export completed"