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

  # GitHub Actions outputs vars in unquoted format, parse manually
  echo "$VARS_JSON" | grep -E '^\s*[A-Za-z_][A-Za-z0-9_\-\.]*:' | while IFS= read -r line; do
    # Extract key and value from format like:  KEY: value,
    key=$(echo "$line" | sed 's/^\s*\([^:]*\):.*/\1/' | tr -d ' ')
    # FIXED: Properly handle trailing commas
    value=$(echo "$line" | sed 's/^[^:]*:\s*\(.*[^,]\)[,]\?$/\1/' | sed 's/^"//' | sed 's/"$//')

    if [ -n "$key" ] && [ -n "$value" ]; then
      echo "  ✅ Exporting: $key"
      echo "$key=$value" >> $GITHUB_ENV
    fi
  done
fi

echo "✅ Repository variable export completed"