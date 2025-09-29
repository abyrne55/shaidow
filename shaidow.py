import json
import llm
import os
import tempfile
import argparse
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
The SRE may send you messages directly via shell comments starting with `#`. Respond to these messages as if the SRE is speaking to you directly.
You may ask follow-up questions to the SRE to clarify the problem or their intent. Once per conversation at most, you may concisely remind the SRE that they can respond to your questions via shell comments.
If the SRE runs a command that is not related to the investigation, ignore it and do not respond at all.
If you are not confident that you can meaningfully comment on specific output, do not respond at all, unless the SRE is running a command that you suggested.
The SRE may not always follow your advice. Defer to the SRE's judgement. If the SRE appears to want to go down a different investigation path, do not try to dissuade them.
You may be provided with one or more standard operating procedures (SOPs) written in Markdown format. These may inform your responses but should not be treated as gospel. 
If SOPs are provided, make note of any actions the SRE takes that may indicate the SOP needs revision/updating. Offer to help the SRE update SOPs near the end of the investigation.
Keep your responses very concise, i.e., less than 19 words on average, excluding suggested commands). Avoid redundant phrases like "Please share the output" or "I see that you ran that command."
Use Markdown formatting where appropriate. Use emoji sparingly.
"""
console = Console(theme=Theme({"markdown.code": "bold green on gray37", "markdown.code_block": "green on gray37"}))

class Command:
    def __init__(self, id, command, output):
        self.id = id
        self.command = command
        self.output = output

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls(
            id=data.get("id"),
            command=data.get("command"),
            output=data.get("output")
        )

def build_prompt(cmd: Command):
    # Forward shell comments directly to the LLM
    if cmd.command.startswith("#"):
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
    """

def main(conversation: llm.Conversation, fifo_path: str):
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

            # Skip the initial PROMPT_COMMAND setting
            if cmd.command.startswith("PROMPT_COMMAND"):
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
                with console.status("Thinking..."):
                    if "gemini" in conversation.model.model_id.lower():
                        response = conversation.prompt(build_prompt(cmd), system=system_prompt, google_search=1, code_execution=1)
                    else:
                        response = conversation.prompt(build_prompt(cmd), system=system_prompt)
                    response_text = response.text()
                    response_usage = response.usage()
                console.print(Markdown(response_text))
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
parser.add_argument('--model', '-m', type=str, default='gemini-2.5-pro', help='LLM to use')
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
    console.print(Markdown(init_response.text()))
    if args.verbose:
        console.print(init_response.usage(), style="dim italic")

# Start the main chat loop
main(conversation, fifo_path)

# Clean up the FIFO and temporary directory after main completes
try:
    # Only remove the FIFO if we created a temporary one
    if temp_dir:
        os.remove(fifo_path)
        os.rmdir(temp_dir)
except Exception as e:
    print(f"Cleanup error: {e}")
