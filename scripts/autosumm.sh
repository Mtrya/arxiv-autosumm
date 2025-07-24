#!/bin/bash

# ArXiv AutoSumm CLI Runner
# This script provides a convenient way to run the ArXiv AutoSumm pipeline

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration file
DEFAULT_CONFIG="config.yaml"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Run the ArXiv AutoSumm pipeline"
    echo ""
    echo "Options:"
    echo "  -c, --config FILE    Configuration file path (default: $DEFAULT_CONFIG)"
    echo "  -v, --verbose        Enable verbose output"
    echo "  -h, --help           Show this help message"
    echo "  --init               Run setup wizard"
    echo "  --test               Test configuration"
    echo ""
    echo "Examples:"
    echo "  $0                   # Run with default config"
    echo "  $0 -c config.yaml    # Run with custom config"
    echo "  $0 --verbose         # Run with verbose output"
    echo "  $0 --init            # Run setup wizard"
}

# Parse command line arguments
CONFIG_FILE="$DEFAULT_CONFIG"
VERBOSE=""
COMMAND="run"

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --init)
            COMMAND="init"
            shift
            ;;
        --test)
            COMMAND="test_config"
            shift
            ;;
        *)
            echo "Error: Unknown option $1"
            usage
            exit 1
            ;;
    esac
done

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH"
    exit 1
fi

# Change to project directory
cd "$SCRIPT_DIR"

# Check if the CLI module exists
if [[ ! -f "autosumm/cli.py" ]]; then
    echo "Error: autosumm/cli.py not found. Make sure you're in the correct directory."
    exit 1
fi

# Run the appropriate command
case $COMMAND in
    "run")
        echo "Starting ArXiv AutoSumm pipeline..."
        python3 -m autosumm.cli run --config "$CONFIG_FILE" $VERBOSE
        ;;
    "init")
        echo "Starting ArXiv AutoSumm setup wizard..."
        python3 -m autosumm.cli init
        ;;
    "test_config")
        echo "Testing configuration..."
        python3 -m autosumm.cli test_config
        ;;
esac