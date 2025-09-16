#!/bin/bash
# Shaidow tmux startup script
# Creates a tmux session with shell.sh on the left and shaidow.py on the right,
# connected via a secure FIFO
# Generated-by: Claude 4 Sonnet

set -euo pipefail

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Creates a tmux session with shell.sh (left) and shaidow.py (right) connected via FIFO"
    echo ""
    echo "All options are passed through to shaidow.py, except:"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "Common shaidow.py options:"
    echo "  -m, --model MODEL     LLM model to use (default: gemini-2.5-flash)"
    echo "  -s, --sop FILE        Path to SOP file to include"
    echo "  -v, --verbose         Verbose output"
    echo ""
    echo "Example: $0 -m claude-3-5-sonnet -v"
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
FIFO_PATH="$TEMP_DIR/shaidow_fifo"
mkfifo "$FIFO_PATH"
chmod 600 "$FIFO_PATH"  # Only owner can read/write


# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    # Kill the tmux session if it exists
    tmux has-session -t "$SESSION_NAME" 2>/dev/null && tmux kill-session -t "$SESSION_NAME"
    
    # Clean up FIFO and temp directory
    [[ -p "$FIFO_PATH" ]] && rm -f "$FIFO_PATH"
    [[ -d "$TEMP_DIR" ]] && rmdir "$TEMP_DIR" 2>/dev/null
    echo "Cleanup complete"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Check if tmux is available
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is required but not installed"
    echo "Please install tmux: sudo apt-get install tmux (Ubuntu/Debian) or brew install tmux (macOS)"
    exit 1
fi

# Get the absolute path to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

echo "Starting Shaidow tmux session..."
echo "FIFO path: $FIFO_PATH"
echo "Session name: $SESSION_NAME"
echo "Temp directory: $TEMP_DIR"

# Create a new tmux session with shell.sh running in the first pane
tmux new-session -d -s "$SESSION_NAME" -c "$SCRIPT_DIR" "$SCRIPT_DIR/shell.sh" "$FIFO_PATH"

# Split the window vertically and run shaidow.py in the right pane
tmux split-window -h -t "$SESSION_NAME:0" -c "$SCRIPT_DIR" "python3 $SCRIPT_DIR/shaidow.py --fifo '$FIFO_PATH' $*"

# Set the left pane as the active pane
tmux select-pane -t "$SESSION_NAME:0.0"

# Attach to the session
echo "Attaching to tmux session. Use Ctrl+B then arrow keys to switch panes."
echo "Use Ctrl+B then 'd' to detach, or 'exit' in the left pane to end the session."

# Attach to the session
tmux attach-session -t "$SESSION_NAME"

# After tmux session ends, cleanup will be called automatically due to trap
