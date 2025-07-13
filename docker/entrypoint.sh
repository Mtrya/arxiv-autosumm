#!/bin/bash

# ArXiv AutoSumm Docker Entrypoint
# Handles configuration and runs the appropriate command

set -e

# Function to display usage
usage() {
    echo "Usage: docker run [OPTIONS] IMAGE [COMMAND] [ARGS...]"
    echo ""
    echo "Commands:"
    echo "  run              Run the summarization pipeline"
    echo "  init             Run setup wizard"
    echo "  test-config      Test configuration"
    echo "  shell            Start interactive shell"
    echo ""
    echo "Environment variables:"
    echo "  ARXIV_AUTOSUMM_CONFIG     Path to config file"
    echo "  ARXIV_AUTOSUMM_CACHE_DIR  Cache directory"
    echo "  ARXIV_AUTOSUMM_OUTPUT_DIR Output directory"
    echo ""
    echo "Volume mounts:"
    echo "  /data/config      Configuration files"
    echo "  /data/cache       Cache directory"
    echo "  /data/output      Output directory"
}

# Default configuration
CONFIG_FILE="${ARXIV_AUTOSUMM_CONFIG:-/data/config/config.yaml}"
CACHE_DIR="${ARXIV_AUTOSUMM_CACHE_DIR:-/data/cache}"
OUTPUT_DIR="${ARXIV_AUTOSUMM_OUTPUT_DIR:-/data/output}"

# Ensure directories exist
mkdir -p "$CACHE_DIR" "$OUTPUT_DIR"

# If config file doesn't exist, create a default one
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Creating default configuration file..."
    cp /app/config.yaml "$CONFIG_FILE"
    echo "Please edit $CONFIG_FILE to configure your settings"
fi

# Handle different commands
case "${1:-run}" in
    run)
        echo "Starting ArXiv AutoSumm pipeline..."
        echo "Config: $CONFIG_FILE"
        echo "Cache: $CACHE_DIR"
        echo "Output: $OUTPUT_DIR"
        
        # Run the pipeline
        python -m autosumm.cli run --config "$CONFIG_FILE"
        ;;
        
    init)
        echo "Running setup wizard..."
        python -m autosumm.cli init
        ;;
        
    test-config)
        echo "Testing configuration..."
        python -m autosumm.cli test_config
        ;;
        
    shell)
        echo "Starting interactive shell..."
        exec /bin/bash
        ;;
        
    --help|help|-h)
        usage
        ;;
        
    *)
        # Pass through to the CLI
        python -m autosumm.cli "$@"
        ;;
esac