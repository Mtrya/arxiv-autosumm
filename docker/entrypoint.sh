#!/bin/bash
set -e

# ... existing color definitions ...

# Debug: Show environment and process info
echo "--- ENVIRONMENT ---"
env
echo "--- PROCESS TREE ---"
ps faux
echo "--- PATH ---"
echo $PATH
echo "--- COMMAND LOCATION ---"
which autosumm || echo "autosumm not found in PATH"

command="$1"

# Debug: Show received command
echo "Received command: '$command' with args: '${@:2}'"

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
    # Debug: Show what command will be executed
    echo "Executing: autosumm run $@"
    # Debug: Verify the command exists
    if ! command -v autosumm &> /dev/null; then
      log_error "autosumm command not found in PATH!"
      exit 1
    fi
    # Execute with debug output
    set -x  # Enable command tracing
    autosumm run "$@"
    status=$?
    set +x  # Disable command tracing
    if [ $status -ne 0 ]; then
      log_error "Main application failed with exit code $status"
      log_warning "Container will remain running for debugging"
      sleep infinity
    fi
    ;;
    # Run the main pipeline using:
    # ``` docker run --rm arxiv-autosumm:latest ```
    # Or ``` docker run --rm arxiv-autosumm:latest run-app --verbose --specify-category cs.AI ```
    # With docker-compose, just:
    # ``` docker-compose -f docker/docker-compose.yml up``` (foreground)
    # Add other pipeline arguments normally after `docker-compose up`

  run-tests)
    echo "Running tests..."
    shift
    exec autosumm test-config "$@"
    ;;

  *)
    # If the command is not recognized, show an error.
    echo "Error: Unknown command '$command'"
    echo "Available commands: run-app, run-tests"
    exit 1
    ;;
    # To run the tests:
    # ``` docker run --rm arxiv-autosumm:latest run-tests ```
    # Or ``` docker run --rm arxiv-autosumm:latest run-tests --skip-api-checks```
    # Or with docker-compose:
    # ```docker-compose run --rm autosumm run-tests ```
    # Add other test-config arguments normally after `run-tests`
esac