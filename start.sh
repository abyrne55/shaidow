#!/bin/bash
# Shaidow tmux startup script
# Creates a tmux session with shell.sh on the left and shaidow.py on the right,
# connected via a secure FIFO
# Generated-by: Claude 4 Sonnet

set -eo pipefail

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Creates a tmux session with shell.sh (left) and shaidow.py (right) connected via FIFO"
    echo ""
    echo "All options are passed through to shaidow.py, except:"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "Common shaidow.py options:"
    echo "  -m, --model MODEL     LLM to use (default: gemini-2.5-pro) (run 'llm models list' for choices)"
    echo "  -s, --sop FILE        Path to SOP file to include"
    echo "  -v, --verbose         Verbose output"
    echo ""
    echo "Example: $0 -m gemini-2.5-flash -v"
}

# Check for help flag
for arg in "$@"; do
    if [[ "$arg" == "-h" || "$arg" == "--help" ]]; then
        usage
        exit 0
    fi
done

# Generate a unique session name
SESSION_NAME="shaidow_$(date +%s)_$$"

# Create a secure temporary directory
TEMP_DIR=$(mktemp -d -t shaidow_XXXXXX)
if [[ ! -d "$TEMP_DIR" ]]; then
    echo "Error: Failed to create temporary directory"
    exit 1
fi

# Set secure permissions (only owner can read/write/execute)
chmod 700 "$TEMP_DIR"

# Create FIFO with secure permissions
FIFO_PATH="$TEMP_DIR/fifo"
mkfifo "$FIFO_PATH"
chmod 600 "$FIFO_PATH"  # Only owner can read/write


# Function to cleanup on exit
cleanup() {
    # Kill the tmux session if it exists
    tmux has-session -t "$SESSION_NAME" 2>/dev/null && tmux kill-session -t "$SESSION_NAME"
    
    # Clean up FIFO and temp directory
    [[ -p "$FIFO_PATH" ]] && rm -f "$FIFO_PATH"
    [[ -d "$TEMP_DIR" ]] && rmdir "$TEMP_DIR" 2>/dev/null
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Get the absolute path to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if for required dependencies
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is required but not installed"
    echo "Please install tmux: sudo dnf install tmux (Fedora/RHEL) or brew install tmux (macOS)"
    exit 1
fi
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed."
    echo "Please install jq: sudo dnf install jq (Fedora/RHEL) or brew install jq (macOS)"
    exit 1
fi
if ! command -v script &> /dev/null; then
    echo "Error: script is required but not installed."
    echo "Please install script: sudo dnf install script (Fedora/RHEL) or brew install script (macOS)"
    exit 1
fi
if ! command -v llm &> /dev/null; then
    echo "Error: llm is required but not installed. If you are using a virtual environment, make sure it is activated."
    echo "Otherwise, please install all required Python packages: pip3 install -r $SCRIPT_DIR/requirements.txt"
    exit 1
fi

# Check if llm is configured
if ! [[ $(llm keys list) ]] && [[ "$SKIP_KEY_CHECK" != "1" ]]; then
    echo "⚠️  llm may not be configured with any remote model API keys. Run 'llm keys set gemini' to configure an API key for the default Gemini model."
    if ! [[ $(llm models list | grep gpt4all) ]]; then
        echo "⚠️  llm may not be configured for local models. Run 'llm install llm-gpt4all' to install a local model management plugin"
    else
        echo "💡 Use the --model flag to specify a model. Run 'llm models list | grep gpt4all' to view available local models."
    fi
    echo "See https://llm.datasette.io/en/stable/setup.html#installing-plugins for more information on configuring llm."
    echo "Set SKIP_KEY_CHECK=1 to skip this check."
fi

# Check if required files exist
if [[ ! -f "$SCRIPT_DIR/shell.sh" ]]; then
    echo "Error: shell.sh not found in $SCRIPT_DIR"
    exit 1
fi

if [[ ! -f "$SCRIPT_DIR/shaidow.py" ]]; then
    echo "Error: shaidow.py not found in $SCRIPT_DIR"
    exit 1
fi

# Make sure shell.sh is executable
chmod +x "$SCRIPT_DIR/shell.sh"

echo "Starting Shaidow tmux session ($SESSION_NAME via $FIFO_PATH)..."

# Create a new tmux session with shell.sh running in the first pane
tmux new-session -d -s "$SESSION_NAME" -c "$SCRIPT_DIR" "$SCRIPT_DIR/shell.sh" "$FIFO_PATH"

# Split the window vertically and run shaidow.py in the right pane
tmux split-window -h -t "$SESSION_NAME:0" -c "$SCRIPT_DIR" "python3 $SCRIPT_DIR/shaidow.py --fifo '$FIFO_PATH' $*"

# Configure the session to exit when the left pane (shell.sh) exits
# This ensures that when the user exits the shell, the entire session terminates
tmux set-hook -t "$SESSION_NAME" pane-exited "if-shell -F '#{==:#{pane_index},0}' 'kill-session'"

# Set the left pane as the active pane
tmux select-pane -t "$SESSION_NAME:0.0"

# Attach to the session, noting duration in case of early exit
START_TIME=$(date +%s)
tmux attach-session -t "$SESSION_NAME"
END_TIME=$(date +%s)

# Calculate duration and show warning for quick exits
DURATION=$((END_TIME - START_TIME))
if [[ "$DURATION" -lt 5 && "$DURATION" -ge 0 ]]; then
    echo "⁉️  Session ended after ${DURATION}s. If this was unexpected, check for any llm configuration issues noted above, or try testing llm directly:"
    echo "llm -m MODEL_NAME 'hello'"
fi


# After tmux session ends, cleanup will be called automatically due to trap
