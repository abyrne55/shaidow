import json
import time
import llm
import os
import tempfile
import argparse
import subprocess
from datetime import datetime
from rich import print
from rich.console import Console
from rich.markup import escape
from rich.markdown import Markdown
from rich.text import Text
from rich.theme import Theme

system_prompt = """
You are a helpful (and sometimes playful) assistant to a site reliability engineer (SRE) investigating alerts and other problems with OpenShift 4 clusters.
You will be shown the output of shell commands the SRE uses during their investigation.
Your job is to point out any interesting or important information in the output that the SRE may have missed.
You may also suggest a command to run if you think it will help investigate the problem further. Use Markdown shell code block formatting for commands longer than 10 characters.
Once per conversation at most, you may concisely remind the SRE that you will ignore any commands that end with `#i`.
Avoid suggesting full-screen interactive commands like 'watch' or 'top', as you probably won't be able to see the output of that command. If you must suggest an interactive command, suffix it with `#i`.
The SRE may send you messages directly via shell comments starting with `#`. Respond to these messages as if the SRE is speaking to you directly.
You may ask follow-up questions to the SRE to clarify the problem or their intent. Once per conversation at most, you may concisely remind the SRE that they can respond to your questions via shell comments.
Once per conversation at most, you may concisely remind the SRE that they can run `##` to have the last command you suggested typed into their shell for them. It's best to do this just after you first suggest a command.
If the SRE runs a command that is not related to the investigation, ignore it and do not respond at all.
If you are not confident that you can meaningfully comment on specific output, do not respond at all, unless the SRE is running a command that you suggested.
The SRE may not always follow your advice. Defer to the SRE's judgement. If the SRE appears to want to go down a different investigation path, do not try to dissuade them.
You may be provided with one or more standard operating procedures (SOPs) written in Markdown format. These may inform your responses but should not be treated as gospel. 
If SOPs are provided, make note of any actions the SRE takes that may indicate the SOP needs revision/updating. Offer to help the SRE update SOPs near the end of the investigation.
Keep your responses very concise, i.e., less than 19 words on average, excluding suggested commands). Avoid redundant phrases like "Please share the output" or "I see that you ran that command."
Use Markdown formatting where appropriate. Use emoji sparingly.
"""
console = Console(theme=Theme({"markdown.code": "bold green on gray93", "markdown.code_block": "green on gray93"}))

# Recorded suggested commands in the order they were suggested (oldest first)
suggested_commands = []

# Borrowed from https://rich.readthedocs.io/en/latest/_modules/rich/markdown.html#Markdown
def flatten_markdown_tokens(tokens):
    """Flattens the Markdown token stream."""
    for token in tokens:
        is_fence = token.type == "fence"
        is_image = token.tag == "img"
        if token.children and not (is_image or is_fence):
            yield from flatten_markdown_tokens(token.children)
        else:
            yield token

def record_suggested_command(llm_response_markdown):
    """Record any suggested commands from the LLM's response."""
    global suggested_commands
    code_blocks = [token.content.strip() for token in flatten_markdown_tokens(llm_response_markdown.parsed) if token.type == "fence" and token.tag == "code"]
    suggested_commands += code_blocks

class Command:
    def __init__(self, id, command, output, return_timestamp):
        self.id = id
        self.command = command
        self.output = output
        self.return_timestamp = return_timestamp

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        
        # Parse return_timestamp from ISO8601 format
        timestamp_value = data.get("return_timestamp")
        if timestamp_value:
            return_timestamp = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
        else:
            return_timestamp = None
            
        return cls(
            id=data.get("id"),
            command=data.get("command"),
            output=data.get("output"),
            return_timestamp=return_timestamp
        )

def build_prompt(cmd: Command):
    # Forward shell comments directly to the LLM
    if cmd.command.strip().startswith("#"):
        return cmd.command
    
    return f"""
    I ran the following command
    ```sh
    {cmd.command}
    ```
    It produced the following output
    ```
    {cmd.output}
    ```
    The command finished executing at {cmd.return_timestamp.isoformat(timespec='seconds')}
    """

def main(conversation: llm.Conversation, fifo_path: str, sysprompt_only_once: bool, tmux_shell_pane: str = None):
    with open(fifo_path, 'r') as fifo:
        while True:
            line = fifo.readline()
            if not line:  # EOF, writer closed
                # print(f"Writer closed the FIFO.")
                # break
                continue
            try:
                cmd = Command.from_json(line)
            except (json.JSONDecodeError, KeyError) as e:
                console.print(f"Error parsing JSON: {e}")
                continue

            # Skip the initial PROMPT_COMMAND setting or commands ending with #i
            stripped_cmd = cmd.command.strip()
            if cmd.command.startswith("PROMPT_COMMAND") or stripped_cmd.endswith("#i"):
                continue

            # Handle "type suggested command" directive
            if len(stripped_cmd) >= 2 and all(c == "#" for c in stripped_cmd):
                if tmux_shell_pane and suggested_commands:
                    try:
                        # Map number of #'s to command index (## = last, ### = second-to-last, etc.)
                        num_hashes = len(stripped_cmd)
                        command_index = num_hashes - 2  # ## maps to index -1 (last), ### to index -2, etc.
                        
                        if command_index < len(suggested_commands):
                            # Get command from the end of the list (most recent first)
                            command_to_send = suggested_commands[-(command_index + 1)]
                            
                            # Need to wait a little to allow shell prompt to print
                            time.sleep(0.4)
                            subprocess.run(
                                ["tmux", "send-keys", "-t", tmux_shell_pane, command_to_send],
                                check=True
                            )
                        else:
                            console.print(f"No command available at position {command_index + 1} (only {len(suggested_commands)} commands suggested)", style="yellow")
                    except Exception as e:
                        console.print(f"Error sending keys to tmux pane: {e}", style="red")
                continue

            try:
                header = Text.assemble(
                    (escape(f"[{cmd.id}]"), "dim bold"),
                    (escape(f" {cmd.command}"), "dim")
                )
                if not args.verbose:
                    header.truncate(40, overflow="ellipsis")
                console.print("")
                console.rule(header, align="left", style="dim")
                response_text = ""
                response_usage = None
                if sysprompt_only_once:
                    sysprompt = None
                else:
                    sysprompt = system_prompt
                with console.status("Thinking..."):
                    if "gemini" in conversation.model.model_id.lower():
                        response = conversation.prompt(build_prompt(cmd), system=sysprompt, google_search=1, code_execution=1)
                    else:
                        response = conversation.prompt(build_prompt(cmd), system=sysprompt)
                    response_text = response.text()
                    response_usage = response.usage()
                response_md = Markdown(response_text)
                console.print(response_md)
                record_suggested_command(response_md)
                if args.verbose:
                    console.print(response_usage, style="dim italic")
            except Exception as e:
                console.print(f"Error processing command {cmd.id}: {e}")
                continue

# Parse command line arguments
parser = argparse.ArgumentParser(description='SRE assistant that reads commands from a FIFO')
parser.add_argument('--fifo', '-f', type=str, help='Path to FIFO file (will be created if it does not exist)')
parser.add_argument('--sop', '-s', action='append', type=argparse.FileType('r', encoding='UTF-8'), help="Path to a local copy of an SOP to add to the LLM's context window")
parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output (including LLM token usage)")
parser.add_argument('--model', '-m', type=str, default='gemini-2.5-pro', help='LLM to use (default: gemini-2.5-pro)')
parser.add_argument('--sysprompt-only-once', '-p', action='store_true', default=False,
                    help="only provide the system prompt during LLM initialization — helpful for models with small context windows (default: provide sysprompt with each request)")
parser.add_argument('--tmux-shell-pane', '-t', type=str, help='ID of the tmux pane containing the shell being recorded')


args = parser.parse_args()

# Create a FIFO
if args.fifo:
    # Create the FIFO if it doesn't exist
    fifo_path = args.fifo
    if not os.path.exists(fifo_path):
        os.mkfifo(fifo_path)
    temp_dir = None  # We didn't create a temp dir
else:
    # Fallback to original behavior
    temp_dir = tempfile.mkdtemp(prefix="shaidow_")
    fifo_path = os.path.join(temp_dir, "fifo")
    os.mkfifo(fifo_path)

if args.verbose:
    print(f"Pipe your shell into {fifo_path}")

# Configure the model
model = llm.get_model(args.model)
conversation = model.conversation()

# Read any SOPs
sops = []
if args.sop:
    sops = [sop.read() for sop in args.sop]
    if args.verbose:
        print(f"Providing {len(sops)} SOPs to the LLM")
        for i, sop in enumerate(sops):
            print(f"{i}: {sop[:50].replace('\n', '\\n ')}...")

# Initialize the conversation, providing the system prompt and any SOPs
with console.status("Initializing LLM..."):
    init_response = conversation.prompt("# Hello!", system=system_prompt, fragments=sops)
    init_response_md = Markdown(init_response.text())
    console.print(init_response_md)
    record_suggested_command(init_response_md)
    if args.verbose:
        console.print(init_response.usage(), style="dim italic")

# Start the main chat loop
main(conversation, fifo_path, args.sysprompt_only_once, args.tmux_shell_pane)

# Clean up the FIFO and temporary directory after main completes
try:
    # Only remove the FIFO if we created a temporary one
    if temp_dir:
        os.remove(fifo_path)
        os.rmdir(temp_dir)
except Exception as e:
    print(f"Cleanup error: {e}")
