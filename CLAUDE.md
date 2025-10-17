# Shaidow - Project Overview for Claude

## What is Shaidow?

Shaidow is a **terminal companion tool** that provides real-time AI assistance for SRE (Site Reliability Engineer) work. It splits your terminal into two panes: one where you work normally, and another where an LLM observes your commands and provides live feedback, suggestions, and troubleshooting help.

## Core Architecture

### Main Components

1. **shaidow.py** (Main application)
   - Processes shell commands via FIFO pipes
   - Integrates with LLM providers via the `llm` Python package
   - Manages conversation context and tool invocations
   - Displays formatted responses using Rich library

2. **start.sh** (Session manager)
   - Creates tmux session with two panes
   - Sets up FIFO communication between panes
   - Configures shell instrumentation (PROMPT_COMMAND, DEBUG trap)
   - Launches both the shell recording and AI assistant

3. **Tools Directory** (`tools/`)
   - `clock.py` - Time management tools (local_time, utc_time, stopwatch)
   - `web.py` - Internet access (search via ddgs, read_url via trafilatura)
   - `knowledgebase.py` - Local document search using llm embeddings
   - `__init__.py` - Shared utilities for tool status messages

### Key Technical Details

- **Communication**: Uses named pipes (FIFOs) for inter-process communication
- **Command Capture**: Leverages `script` + `script2json` + Bash traps to record commands/outputs
- **LLM Integration**: Model-agnostic via the `llm` package (supports Gemini, ChatGPT, Claude, local models)
- **Context Management**: Maintains conversation history with optional system prompt injection
- **UI**: Rich library for formatted markdown output

## File Structure

```
shaidow/
├── shaidow.py           # Main AI assistant application
├── start.sh             # Session setup and launcher
├── shell.sh             # Shell configuration script
├── README.md            # User documentation
├── SHELL_README.md      # Shell-specific docs
├── requirements.txt     # Python dependencies
├── constraints.txt      # Dependency version constraints
├── .env                 # Environment variables (API keys, etc.)
└── tools/
    ├── __init__.py      # Tool utilities and status messages
    ├── clock.py         # Time-related tools
    ├── web.py           # Web search and fetching
    └── knowledgebase.py # Local document search
```

## Key Features & Implementation

### 1. Real-time Command Analysis
- Commands are captured via Bash DEBUG trap
- Output captured by `script` utility
- Parsed by `script2json` into JSONL format
- Fed to LLM with timestamp and context

### 2. Direct Messaging (`# comments`)
- Shell comments starting with `#` are forwarded directly to the LLM
- Enables conversational interaction without running commands

### 3. Command Suggestion & Pasting
- LLM suggests commands in markdown code blocks
- User types `##` to paste the last suggested command
- `###` for second-to-last, etc.
- Implemented via tmux send-keys

### 4. Ignored Commands (`#i`)
- Commands ending with `#i` are not sent to the LLM
- Useful for interactive programs (watch, top, vim)

### 5. Tool System
- LLM can invoke tools to enhance responses
- **Clock**: Get timestamps, manage stopwatch
- **Web**: Search internet, fetch/parse web pages
- **KnowledgeBase**: Search local SOP documents via embeddings

### 6. SOP Integration
- Standard Operating Procedures loaded as LLM "fragments"
- Can be injected at startup via `-s` flag
- LLM references SOPs when providing guidance

## System Prompt Summary

The AI assistant is configured to:
- Point out interesting/important information in command outputs
- Suggest investigative commands when helpful
- Respond to direct messages via `#` comments
- Use tools (KnowledgeBase, Web, Clock) to ground responses
- Keep responses concise (avg <19 words, excluding commands)
- Track SOP deviation and offer to help update procedures
- Defer to SRE's judgment, not be prescriptive
- Ignore unrelated commands

## Known Limitations

1. **Race Conditions**: Signals (SIGUSR1/SIGUSR2) can arrive out-of-order under heavy system load
2. **Interactive Commands**: Full-screen programs (watch, top, vim) don't work well
3. **Subshells**: Commands in ssh/oc debug sessions may not be captured
4. **Ctrl-C Bug**: Pressing Ctrl-C at prompt causes last command to be re-sent to LLM

## Dependencies

### System
- Python 3.10+
- tmux, sed, script (util-linux)
- Go (for script2json)

### Python Packages
- `llm` - LLM provider abstraction
- `rich` - Terminal formatting
- `ddgs` - DuckDuckGo search
- `trafilatura` - Web page extraction

### External Tools
- `script2json` - Golang tool for converting script output to JSON

## Configuration

- **Model Selection**: `--model` / `-m` flag (default: gemini-2.5-pro)
- **FIFO Path**: `--fifo` / `-f` flag
- **SOPs**: `--sop` / `-s` flag (repeatable)
- **Knowledge Base**: `--kb-collection` / `-k` and `--kb-database` / `-d` flags
- **Verbosity**: `--verbose` / `-v` flag
- **System Prompt**: `--sysprompt-only-once` / `-p` for small context windows

## Development Notes

### Adding New Tools
1. Create a new file in `tools/` directory
2. Implement a class with `__init__` that registers tool methods
3. Use `@llm.hookimpl` decorators (follow existing tool patterns)
4. Import and register in `shaidow.py` main function

### Modifying System Prompt
- Edit `system_prompt` variable in `shaidow.py` (line 20)
- Keep instructions concise and behavior-focused
- Test with multiple LLM providers for compatibility

### Testing Tool Calls
- Use `--verbose` flag to see tool invocations
- Test with direct messages: `# Search for "disk pressure"`
- Verify status messages appear during tool execution

## Common Workflows

### Starting a Session
```bash
./start.sh -m gemini-2.5-flash
```

### Using with SOPs
```bash
./start.sh -s /path/to/sop1.md -s /path/to/sop2.md
```

### Setting up Knowledge Base
```bash
llm embed-models default text-embedding-004
cd /path/to/docs
llm embed-multi --files ./ '**/*.md' --store ops-sop
```

### Debugging
```bash
python3 shaidow.py -f /tmp/test.fifo -v -m claude-4-sonnet
```

## Integration Points

- **OpenShift/Kubernetes**: Optimized for `oc` commands and cluster troubleshooting
- **tmux**: Essential for split-pane UI
- **LLM Providers**: Any provider supported by `llm` package works
- **Embeddings**: Any embedding model supported by `llm` for knowledge base

## Future Enhancement Ideas

- Better handling of subshells
- Improved race condition mitigation
- Support for other shells (zsh, fish)
- Web UI alternative to tmux
- Streaming responses for slower models
- Persistent conversation history across sessions
