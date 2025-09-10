import json
import llm
import os
import tempfile
import argparse
from dotenv import load_dotenv

system_prompt = """
You are a helpful (and sometimes playful) assistant to a site reliability engineer (SRE) investigating alerts and other problems with OpenShift 4 clusters.
You will be shown the output of shell commands the SRE uses during their investigation. 
Your job is to point out any interesting or important information in the output that the SRE may have missed.
You may also suggest a command to run if you think it will help investigate the problem further. Do not wrap the command in backticks or other formatting.
The SRE may send you messages directly via shell comments starting with `#`. Respond to these messages as if the SRE is speaking to you directly.
You may ask follow-up questions to the SRE to clarify the problem or their intent. Once per conversation at most, you may concisely remind the SRE that they can respond to your questions via shell comments.
If the SRE runs a command that is not related to the investigation, ignore it and do not respond at all.
If you are not confident that you can meaningfully comment on specific output, do not respond at all, unless the SRE is running a command that you suggested.
Keep your responses very concise (ideally 20 words or fewer, excluding suggested commands).
Do not use markdown formatting. You may use emojis and POSIX-safe ANSI escape codes for formatting/coloring where appropriate.
"""


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
                print(f"Error parsing JSON: {e}", flush=True)
                continue
                
            try:
                print("\n---", flush=True)
                for chunk in conversation.prompt(build_prompt(cmd), system=system_prompt):
                   # Replace literal \x1b with actual escape character for ANSI codes
                   decoded_chunk = chunk.replace('\\x1b', '\x1b')
                   print(decoded_chunk, end="", flush=True)
            except Exception as e:
                print(f"Error processing command {cmd.id}: {e}", flush=True)
                continue

load_dotenv()

# Parse command line arguments
parser = argparse.ArgumentParser(description='SRE assistant that reads commands from a FIFO')
parser.add_argument('--fifo', '-f', type=str, help='Path to FIFO file (will be created if it does not exist)')
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

print(f"Run: Write JSONL to FIFO at {fifo_path}")

# Initialize the conversation
model = llm.get_model("gemini-2.5-flash")
api_key = os.getenv("LLM_GEMINI_KEY")
if not api_key:
    print("Warning: LLM_GEMINI_KEY environment variable not set")
model.key = api_key
conversation = model.conversation()

main(conversation, fifo_path)

# Clean up the FIFO and temporary directory after main completes
try:
    # Only remove the FIFO if we created a temporary one
    if temp_dir:
        os.remove(fifo_path)
        os.rmdir(temp_dir)
except Exception as e:
    print(f"Cleanup error: {e}")
