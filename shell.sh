#!/bin/bash
# Generated-by: Claude 4 Sonnet

# Interactive Shell Logger
# Logs commands and outputs with unique identifiers
# Usage: ./interactive_logger.sh [logfile]

# Set default log file if not provided
LOGFILE="${1:-shell_session.log}"

# Initialize command counter
COMMAND_COUNTER=1

# Create a temporary directory for our named pipes
TEMP_DIR=$(mktemp -d -t shell_logger_XXXXXX)
COMMAND_PIPE="$TEMP_DIR/commands"
OUTPUT_PIPE="$TEMP_DIR/output"

# Create named pipes
mkfifo "$COMMAND_PIPE"
mkfifo "$OUTPUT_PIPE"

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    rm -f "$COMMAND_PIPE" "$OUTPUT_PIPE"
    rmdir "$TEMP_DIR" 2>/dev/null
    exit 0
}

# Set trap for cleanup on script exit
trap cleanup EXIT INT TERM

# Function to log commands and outputs
log_processor() {
    local log_file="$1"
    local cmd_id=""
    local in_command=false
    
    # Use script command to capture the interactive session
    # The -q flag suppresses the "Script started/done" messages
    # The -f flag flushes output immediately
    script -q -f -c "
        # Custom PS1 that signals when a command starts
        export PS1='\\[\\033]0;CMD_START_\$BASHPID\\007\\]\\$ '
        
        # Function to handle command execution
        handle_command() {
            local cmd=\$1
            echo \"CMD_START_\$BASHPID:\$cmd\" >&2
        }
        
        # Set up command logging
        set -o functrace
        trap 'handle_command \"\$BASH_COMMAND\"' DEBUG
        
        # Start bash with history expansion disabled to avoid issues
        exec bash --norc --noprofile -i
    " /dev/null 2> >(
        while IFS= read -r line; do
            if [[ \$line =~ ^CMD_START_[0-9]+:(.*)$ ]]; then
                cmd_id=\$COMMAND_COUNTER
                ((COMMAND_COUNTER++))
                command=\"\${BASH_REMATCH[1]}\"
                echo \"RAN [\$cmd_id]: \$command\" >> \"\$log_file\"
                in_command=true
            fi
        done
    ) | while IFS= read -r line; do
        # Filter out PS1 escape sequences and prompts
        if [[ \$line =~ ^\\\$ ]]; then
            continue  # Skip prompt lines
        fi
        
        if [[ \$in_command == true && -n \$cmd_id ]]; then
            echo \"GOT [\$cmd_id]: \$line\" >> \"\$log_file\"
        fi
    done
}

# Alternative simpler approach using expect-like behavior with bash
interactive_shell() {
    local log_file="$1"
    
    echo "Starting interactive shell with logging to: $log_file"
    echo "Type 'exit' to quit the logged shell session."
    echo "----------------------------------------"
    
    # Clear the log file
    > "$log_file"
    
    while true; do
        # Read command from user
        read -r -p "$ " user_command
        
        # Check for exit
        if [[ "$user_command" == "exit" ]]; then
            echo "Exiting logged shell session."
            break
        fi
        
        # Skip empty commands
        if [[ -z "$user_command" ]]; then
            continue
        fi
        
        # Log the command
        echo "RAN [$COMMAND_COUNTER]: $user_command" >> "$log_file"
        
        # Execute the command and capture output
        {
            eval "$user_command" 2>&1
        } | while IFS= read -r output_line; do
            echo "GOT [$COMMAND_COUNTER]: $output_line" >> "$log_file"
            echo "$output_line"
        done
        
        # Handle the case where command produces no output
        if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
            echo "GOT [$COMMAND_COUNTER]: (command exited with status ${PIPESTATUS[0]})" >> "$log_file"
        fi
        
        ((COMMAND_COUNTER++))
    done
}

# Main execution
echo "Interactive Shell Logger"
echo "Log file: $LOGFILE"
echo "========================"

# Start the interactive shell with logging
interactive_shell "$LOGFILE"
