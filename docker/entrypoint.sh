#!/bin/bash
# ./docker/entrypoint.sh

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[ArXiv AutoSumm]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# The first argument passed to the container is treated as the command
command="$1"

# If no command is provided, default to 'run_app'
if [ -z "$command" ]; then
    command="run-app"
fi

# Use a case statement to execute the correct logic.
case "$command" in
  run-app)
    echo "Starting the main application..."
    shift
    exec autosumm run "$@"
    ;;
    # Run the main pipeline using:
    # ``` docker run --rm arxiv-autosumm:latest ```
    # Or ``` docker run --rm arxiv-autosumm:latest run-app --verbose --specify-category cs.AI ```
    # With docker-compose, just:
    # ``` docker-compose up``` (foreground) or ``` docker-compose up -d``` (background)
    # Add other pipeline arguments normally after `docker-compose up`

  run_tests)
    echo "Running tests..."
    shift
    exec autosumm test-config "$@"
    ;;

  *)
    # If the command is not recognized, show an error.
    echo "Error: Unknown command '$command'"
    echo "Available commands: run_app, run_tests"
    exit 1
    ;;
    # To run the tests:
    # ``` docker run --rm arxiv-autosumm:latest run-tests ```
    # Or ``` docker run --rm arxiv-autosumm:latest run-tests --skip-api-checks```
    # Or with docker-compose:
    # ```docker-compose run --rm autosumm run-tests ```
    # Add other test-config arguments normally after `run-tests`
esac