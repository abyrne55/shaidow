# Shaidow

**Terminal companion that "shadows" your CLI work with real-time AI assistance.**

Shaidow splits your terminal in half, allowing you to work like you normally would on one pane and receive live AI feedback in the other. The LLM assistant watches your commands and their outputs and provides contextual insights, suggestions, and troubleshooting help. Optimized for SREs working on OpenShift clusters.

## Features

- **Real-time Command Analysis**: LLM observes your shell commands and provides immediate feedback
- **Intelligent Suggestions**: Get relevant follow-up commands and investigation paths
- **Inline DMs**: Use `# comments` to directly communicate with the LLM
- **SOP Integration**: Load Standard Operating Procedures to guide AI responses
- **Tools**: Clock, KnowledgeBase, and Web search integrate external information for grounded responses
- **LLM Agnostic**: Works with any model supported by the [`llm` Python package](https://llm.datasette.io/en/stable/) (e.g., Gemini, ChatGPT, and local models)

## Setup

Shaidow relies on the following dependencies:

- Python 3.10+
- `tmux`, `sed`, and `script` (probably pre-installed, otherwise available via your friendly package manager)
  - Note that `script` might be hidden within a package named something like `util-linux`
- A handful of Python packages (`pip3 install -r requirements.txt -c constraints.txt`)
   - [`llm`](https://llm.datasette.io/en/stable/) for vendor-neutral access to LLMs
   - [`rich`](https://rich.readthedocs.io/en/stable/) for output formatting
   - [`ddgs`](https://github.com/deedy5/ddgs) for web search
   - [`trafilatura`](https://github.com/adbar/trafilatura) for web page distillation
- [`script2json` Golang tool](https://github.com/abyrne55/script2json) for converting `script`'s output into JSON

Use the following steps to install and configure these dependencies (excluding Python; you're on your own for that).

1. Clone this repo and `cd` into it
2. (optional) Create and activate a Python virtual environment
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install required dependencies
   ```sh
   pip3 install -r requirements.txt
   # replace dnf with apt, brew, etc. as needed
   sudo dnf install tmux script sed
   go get github.com/abyrne55/script2json
   ```

4. Configure `llm` for use with a remote model provider (e.g., Google Gemini, OpenAI ChatGPT) or local model manager (e.g., gpt4all). See [the `llm` docs](https://llm.datasette.io/en/stable/setup.html#installing-plugins) for more details
   ```bash
   # ChatGPT (no llm plugin needed)
   llm keys set openai
   llm -m o3 "Hello World"

   # Gemini
   llm install llm-gemini
   llm keys set gemini
   llm -m gemini-2.5-flash "Hello World"

   # Claude
   llm install llm-anthropic
   llm keys set anthropic
   llm -m claude-4-sonnet "Hello World"
   
   # Or download and run local models
   llm install llm-gpt4all
   llm -m orca-mini-3b-gguf2-q4_0 "Hello World"
   ```

### Knowledge Base Setup (optional)
You can give your LLM assistant on-demand access to a "knowledge base" of local documents (e.g., a Git repo full of SOPs in Markdown format). This feature relies on [`llm`'s embeddings-related functionality](https://llm.datasette.io/en/stable/embeddings/index.html). If configured, the LLM will search the knowledge base for most SRE-specific questions before performing a wider web search. 

After activating your virtual environment (if applicable; see above), use the following steps to set this up:

1. Set `llm`'s default embeddings model. See [the llm docs](https://llm.datasette.io/en/stable/plugins/directory.html#embedding-models) for some embedding-specific plugins you can install if your existing models don't work for you.
   ```bash
   # List available embeddings models
   llm embed-models list

   # Set the default model (e.g., Gemini's "text-embedding" model)
   llm embed-models default text-embedding-004
   ```
2. `cd` into the root of your cache of documents, and create a collection of embeddings. The example below creates a collection called "ops-sop" out of all of the Markdown files within the current directory and its subdirectories (recursively). The `--store` flag is important, as it tells `llm` to store a copy of each document alongside its embedding. Shaidow will use the resulting embeddings database to find and read documents similar to the query term
   ```bash
   llm embed-multi --files ./ '**/*.md' --store ops-sop
   # This will take a few minutes
   ```
3. Once embeddings have been generated, you can do a test search using `llm similar`
   ```bash
   llm similar ops-sop -c "disk pressure" --plain | less
   # v4/alerts/KubePersistentVolumeFullInFourDaysLayeredProduct.md (0.5438262299243574)
   #
   ## KubePersistentVolumeFullInFourDaysLayeredProduct
   #**Table of Contents**
   #- [Check Description](#check-description)
   #- [Troubleshooting](#troubleshooting)
   # ...
   #
   #v4/alerts/etcdHighFsyncDurations.md (0.5436313728466821)
   #
   ## etcdHighFsyncDurations
   #
   #The alert `etcdHighFsyncDurations` is fired when 99 percentile fsync duration for an etcd instance exceeds 1 second for 10 minutes. A `wal_fsync` is called when etcd persists its log entries to disk before applying them. High disk operation latencies  often indicate disk issues. It may cause high request latency or make the cluster unstable.
   # ...
   ```
And that's it! Shaidow will automatically use any collection named "ops-sop" that's stored in `llm`'s default embeddings database (see `llm collections path`). If you'd prefer to store your embeddings elsewhere or name your collections differently, make sure you use the `--kb-collection` and/or `--kb-database` flags when starting Shaidow (see *[Other Options](#other-options)*).

## Usage

Run `./start.sh -m $MODEL_NAME`, specifying any of the LLM names/aliases shown by `llm list models`. Running start.sh without any arguments will default to using Google's Gemini 2.5 Pro. Note that start.sh will emit some warnings if `llm` hasn't been pre-configured with any remote model API keys. If you're only using local models, you can silence these warnings by setting `SKIP_KEY_CHECK=1` before running start.sh. 

This script will spawn a two-pane tmux session that works something like the following:
```
┌─────────────────┬─────────────────┐
│------Shell------│--AI Assistant---│
│                 │                 │
│ $ oc get pods   │                 │
│                 │ xyz pod looks   │
│                 │  unhealthy, no? │
│ $ # How should  |                 │
│    I debug xyz? │ Let's start with│
│                 │  oc logs xyz    │
│ $ oc logs xyz   │                 │
└─────────────────┴─────────────────┘
```
In other words, type into the left pane as you would a normal shell (see _Technical Details > Shell_ below). Each time you run a command, the command and its output will be sent to the LLM. Any response/feedback generated by the LLM will be displayed in the right pane. You can also type `# shell comments` into the right pane to chat directly with the LLM.

To return to your normal shell, run `exit` or press Ctrl-D.

### `#` Commands
#### Direct Messaging the Assistant (`# DMs`)
You can communicate directly with the LLM by typing `#` followed by your message. These comments are forwarded straight to the assistant without being executed as shell commands. Use this to ask questions, provide context, or respond to the assistant's queries. Remember that some LLMs (e.g., Gemini) have the ability to search the web or execute Python code on your behalf.

#### Paste Suggested Commands (`##`)
Type `##` to automatically paste the last command suggested by the LLM into your shell prompt. Use `###` for the second-to-last suggested command, `####` for the third-to-last, and so on. This feature requires the `--tmux-shell-pane` flag to be  set to the ID of your tmux shell pane (`start.sh` does this for you).

#### Reset Pipeline State (`#reset`)
Type `#reset` to clear the command/output processing pipeline when you notice desynchronization (commands paired with wrong outputs, missing outputs, or corrupted output). This sends a reset signal to `script2json`, clearing all internal buffers and channel queues without requiring a full restart. The assistant may also suggest running `#reset` if it detects signs of desynchronization.

#### Ignored Commands (`#i`)
Append `#i` to any command to prevent the assistant from seeing or analyzing it. This is useful for running unrelated commands or interactive programs (like `watch` or `top`) that would clutter the assistant's context. The command still executes normally in your shell.

### Tools
Shaidow gives your AI assistant access to a few [tools](https://llm.datasette.io/en/stable/tools.html) (technically [toolboxes](https://llm.datasette.io/en/stable/python-api.html#toolbox-classes)) that it can use to inform its responses. The LLM will automatically invoke these tools as needed to provide more accurate and contextual assistance. You can also explicitly instruct the LLM to use a tool (e.g., `# Start the stopwatch`) 
 * **Web**: basic internet access tools
   * `search`: get a list of URLs and content snippets related to a search query (uses `ddgs`)
   * `read_url`: fetch a web page and distill it to Markdown format (uses `trafilatura`)
 * **Clock**: simple time management tools
   * `local_time` and `utc_time`: get current local/UTC time in ISO 8601 format (useful when looking at timestamped logs)
   * `start_stopwatch` and `check_stopwatch`: simple elapsed time counter that LLM can use to get a sense of how long to wait, e.g., for a node to restart
 * **KnowledgeBase**: search local documents (see _[Knowledge Base Setup](#knowledge-base-setup-optional)_)
   * `search`: search the knowledgebase for documents relevant to a query
   * `read_id`: read the content of a document by its ID

### Injecting SOPs
Use the `-s` flag to provide local copies of Markdown-formatted standard operating procedure (SOP) documents to the LLM. You can provide as many SOPs as you'd like; just keep in mind the context window size of whichever model you're using.
```bash
./start.sh -s /path/to/incident-response.md -s /path/to/NodeNotReady.md
```
Once inside Shaidow, you can query the LLM about any SOPs you've provided.
```
$ oc get nodes
NAME           STATUS     ROLES    AGE   VERSION
node1          Ready      worker   10d   v1.28.2
node2          NotReady   worker   10d   v1.28.2
node3          Ready      master   10d   v1.28.2

[LLM Response] Looks like node2 is having trouble. The SOP suggests running `oc debug no/node2` next

$ # I just checked the AWS console, and it looks like node2 has been terminated. Does the SOP say anything about that?

[LLM Response] Ah, that would explain why it's NotReady! Yes, the SOP says to contact the cluster administrator and ask them to...
```

Note that you can also just ask the LLM to pull up a specific SOP using the [KnowledgeBase](#knowledge-base-setup-optional) toolbox

### Other Options
Any flags passed to start.sh are passed along to shaidow.py (a.k.a. what runs in the "right pane"). Run `python3 shaidow.py -h` for more information about the flags it accepts
```
$ python3 shaidow.py -h
usage: shaidow.py [-h] [--fifo FIFO] [--sop SOP] [--verbose] [--model MODEL] [--sysprompt-only-once]
                  [--tmux-shell-pane TMUX_SHELL_PANE] [--kb-collection KB_COLLECTION] [--kb-database KB_DATABASE]

SRE assistant that reads commands from a FIFO

options:
  -h, --help            show this help message and exit
  --fifo, -f FIFO       Path to FIFO file (will be created if it does not exist)
  --sop, -s SOP         Path to a local copy of an SOP to add to the LLM's context window
  --verbose, -v         Verbose output (including LLM token usage)
  --model, -m MODEL     LLM to use (default: gemini-2.5-pro)
  --sysprompt-only-once, -p
                        only provide the system prompt during LLM initialization — helpful for models with small context
                        windows (default: provide sysprompt with each request)
  --tmux-shell-pane, -t TMUX_SHELL_PANE
                        ID of the tmux pane containing the shell being recorded
  --kb-collection, -k KB_COLLECTION
                        Name of the knowledgebase collection to use (default: ops-sop)
  --kb-database, -d KB_DATABASE
                        Path to the SQLite database containing the knowledgebase collection (default: llm's default
                        embeddings database)
```

## Technical Details

### Overview
1. **Session Setup**: `start.sh` creates a secure tmux session with a "shell pane" running `script` on the left and an "assistant pane" running `shaidow.py` on the right
2. **FIFO Communication**: A few named pipes (FIFOs) created within a temporary directory connects the shell and assistant panes, with [script2json](https://github.com/abyrne55/script2json) as the middle man
3. **Command Logging**: The shell pane gets configured with Bash debugging "traps" that enable script2json to capture your commands/outputs and write them into Shaidow's input FIFO in JSONL format
4. **AI Processing**: `shaidow.py` analyzes each command/output using your chosen LLM
5. **Real-time Feedback**: The AI provides contextual insights and suggestions

### Shell
It turns out that live-recording shell commands and their outputs in a structured format is not a use case well-served by a single widely-available tool. Shaidow relies on `script`, `script2json`, FIFOs, and Bash features (specifically `$PROMPT_COMMAND`, the `DEBUG` trap, and the `fc` built-in) in order to satisfy this use case while still providing users with a fully-functional Bash shell. This approach carries some limitations.
* **Race Conditions**: `script2json` relies on the shell to send signals (i.e., SIGUSR1 and SIGUSR2) at precise moments in order to differentiate between user input and command output. While not frequently encountered during testing, these signals can arrive late or out-of-order when your system is under heavy load, causing commands/outputs to be missed, corrupted, or desynchronized. If this happens, type `#reset` to clear the pipeline state without restarting. Consider also `renice`ing the `script` and `script2json` processes.
* **Interactive Commands**: Full-screen interactive programs like `watch`, `top`, `vim`, or `htop` don't work well with Shaidow's recording mechanism. Their dynamic output isn't captured in a structured format, so the LLM won't see meaningful updates. Append `#i` to these commands to prevent the assistant from trying to analyze them.
* **Subshells (e.g., `ssh`, `oc debug`)**: Commands run inside subshells (like `ssh host` or `oc debug node/xyz`) may not be captured and sent to the assistant until the subshell exits (if at all). The new shell lacks the Bash instrumentation (DEBUG trap, PROMPT_COMMAND, signal handlers) that enables command recording. Consider running individual commands with `-c` flags (e.g., `ssh host "command"`) instead of entering interactive subshells.
* **Ctrl-C**: There's a known bug where pressing Ctrl-C at the prompt causes `script2json` to send the most recently-executed command to Shaidow, making the LLM think that said recent command was run (again) and produced no output. This doesn't affect pressing Ctrl-C while a program is running.

### System Prompt
The AI is optimized for SRE workflows but can be customized by editing `system_prompt.txt`. The prompt emphasizes:
- Concise responses (average <19 words, excluding commands)
- Silent tool use (no commentary between tool calls)
- Practical command suggestions (single-line, no backslash continuations)
- Deference to SRE judgment and investigation path
- SOP awareness with suggestions for updates when needed

### SOPs
SOPs provided by the user are given to `llm` as ["fragments"](https://llm.datasette.io/en/stable/fragments.html) attached to the "Hello" query that's used to initialize the model. Every LLM plugin handles fragments a little differently, but in practice, it doesn't seem all that much different from just running `cat /path/to/sop.md` in Shaidow's left pane.

## Development
Run tests with `source .venv/bin/activate && python -m pytest test_shaidow.py tools/test_init.py tools/test_knowledgebase.py -v`
