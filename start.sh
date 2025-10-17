#!/bin/bash
# Shaidow tmux startup script
# Creates a tmux session with a script2json-recorded shell on the left and shaidow.py on the right,
# connected via a secure FIFO
# Generated-by: Claude 4 Sonnet

set -eo pipefail

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Creates a tmux session with a shell recorded by script2json(left) and shaidow.py (right) connected via FIFO"
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

# Quit if already in a tmux session
if [[ -n "$TMUX" ]]; then
    echo "Error: existing tmux/byobu session detected. Please start Shaidow in a new terminal window or run 'unset TMUX' to override."
    exit 1
fi

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

# Create FIFOs with secure permissions
SCRIPT2JSON_PID_FILE="$TEMP_DIR/script2json.pid"
SCRIPT_FIFO_PATH="$TEMP_DIR/script.fifo"
COMMAND_FIFO_PATH="$TEMP_DIR/command.fifo"
SHAIDOW_FIFO_PATH="$TEMP_DIR/shaidow.fifo"
mkfifo "$SCRIPT_FIFO_PATH" "$COMMAND_FIFO_PATH" "$SHAIDOW_FIFO_PATH"
chmod 600 "$SCRIPT_FIFO_PATH" "$COMMAND_FIFO_PATH" "$SHAIDOW_FIFO_PATH"  # Only owner can read/write


# Function to cleanup on exit
cleanup() {
    # Kill the tmux session if it exists
    tmux has-session -t "$SESSION_NAME" 2>/dev/null && tmux kill-session -t "$SESSION_NAME"
    
    # Clean up temp files and kill script2json
    [[ -p "$SCRIPT_FIFO_PATH" ]] && rm -f "$SCRIPT_FIFO_PATH"
    [[ -p "$COMMAND_FIFO_PATH" ]] && rm -f "$COMMAND_FIFO_PATH"
    [[ -p "$SHAIDOW_FIFO_PATH" ]] && rm -f "$SHAIDOW_FIFO_PATH"
    [[ -s "$SCRIPT2JSON_PID_FILE" ]] && kill $(cat "$SCRIPT2JSON_PID_FILE")
    [[ -f "$SCRIPT2JSON_PID_FILE" ]] && rm -f "$SCRIPT2JSON_PID_FILE"
    [[ -d "$TEMP_DIR" ]] && rmdir "$TEMP_DIR"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Get the absolute path to the script directory
SHAIDOW_SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# If llm is missing and the virtual environment is not activated, ask user if they want to activate it
if ! command -v llm &> /dev/null && ! [[ "$VIRTUAL_ENV" ]]; then
    read -p "Virtual environment not activated. Would you like to activate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        source $SHAIDOW_SRC_DIR/.venv/bin/activate
    fi
fi

# Check if for required dependencies
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is required but not installed"
    echo "Please install tmux: sudo dnf install tmux (Fedora/RHEL) or brew install tmux (macOS)"
    exit 1
fi
if ! command -v script &> /dev/null; then
    echo "Error: script is required but not installed."
    echo "Please install script: sudo dnf install script (Fedora/RHEL) or brew install script (macOS)"
    exit 1
fi
if ! command -v script2json &> /dev/null; then
    echo "Error: script2json is required but not installed."
    echo "Please install script2json: git clone https://github.com/abyrne55/script2json.git && cd script2json && go build && go install"
    exit 1
fi
if ! command -v llm &> /dev/null; then
    echo "Error: llm is required but not installed"
    echo "Please install all required Python packages: pip3 install -r $SHAIDOW_SRC_DIR/requirements.txt"
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
if [[ ! -f "$SHAIDOW_SRC_DIR/shaidow.py" ]]; then
    echo "Error: shaidow.py not found in $SHAIDOW_SRC_DIR"
    exit 1
fi

echo "Starting script2json (TODO remove tee to log file)..."
script2json -log-level error -pid-file "$SCRIPT2JSON_PID_FILE" -script-fifo "$SCRIPT_FIFO_PATH" -command-fifo "$COMMAND_FIFO_PATH" | tee $SHAIDOW_FIFO_PATH >/tmp/script2json.log 2>&1 &

echo "Starting Shaidow tmux session ($SESSION_NAME via $TEMP_DIR)..."

# Create a new tmux session with recorded shell session running in the first pane
tmux new-session -d -s "$SESSION_NAME" -c "$HOME" "script -qf $SCRIPT_FIFO_PATH"

# Initialize recorded shell with a simpler variable assignment
S2J_PID=$(cat "$SCRIPT2JSON_PID_FILE")
TMUX_SHELL_PANE_ID="$SESSION_NAME:0.0"
INIT_SHELL_CMD="PROMPT_COMMAND='echo \"\$(fc -ln -1 2>/dev/null | sed \"s/^[[:space:]]*//\")\" > $COMMAND_FIFO_PATH 2>/dev/null; kill -USR2 $S2J_PID 2>/dev/null; ' ; trap '[[ ! \"\$BASH_COMMAND\" =~ kill\\ -USR[1-2]+\\ $S2J_PID ]] && { kill -USR1 $S2J_PID 2>/dev/null; }' DEBUG"
tmux send-keys -t "$TMUX_SHELL_PANE_ID" "$INIT_SHELL_CMD" Enter

# Split the window vertically and run shaidow.py in the right pane
tmux split-window -h -t "$SESSION_NAME:0" -c "$SHAIDOW_SRC_DIR" "python3 $SHAIDOW_SRC_DIR/shaidow.py --fifo '$SHAIDOW_FIFO_PATH' --tmux-shell-pane '$TMUX_SHELL_PANE_ID' --script2json-pid '$S2J_PID' $*"

# Disable the status bar
tmux set-option -t "$SESSION_NAME" status off

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
