# Interactive Shell Logger (JSONL Format)
Generated-by: Claude 4 Sonnet

A bash script that creates an interactive shell where all commands and their outputs are logged in JSONL format.

## Features

- Logs each command and output as a JSON object per line (JSONL)
- Each JSON object contains: `id`, `command`, and `output` fields
- Proper JSON escaping of all strings using jq
- Captures entire command output (multi-line supported)
- Includes command exit status when non-zero
- Easy to use interactive interface

## Requirements

- `jq` - JSON processor (install with: `sudo apt-get install jq` or `brew install jq`)

## Usage

```bash
./shell.sh [logfile]
```

If no logfile is specified, it defaults to `shell_session.log`.

## Example

Start the logger:
```bash
./shell.sh my_session.jsonl
```

In the interactive shell, run some commands:
```
$ echo "Hello World"
Hello World
$ ls -la
total 8
drwxr-xr-x 2 user user 4096 Sep 10 10:30 .
drwxr-xr-x 3 user user 4096 Sep 10 10:29 ..
$ exit
```

The log file will contain proper JSONL format (one JSON object per line):
```json
{"id":"1","command":"echo \"Hello World\"","output":"Hello World"}
{"id":"2","command":"ls -la","output":"total 8\ndrwxr-xr-x 2 user user 4096 Sep 10 10:30 .\ndrwxr-xr-x 3 user user 4096 Sep 10 10:29 .."}
```

## Notes

- Type `exit` to quit the logged shell session
- Empty commands are ignored
- Command exit status is included in output when non-zero
- All strings are properly JSON-escaped using jq
- Each JSON object is on a single line (JSONL format)
- Multi-line output is captured with `\n` escape sequences

## Processing JSONL Output

You can easily process the JSONL output using jq:

```bash
# Pretty print all entries
cat session.jsonl | jq '.'

# Get only commands
cat session.jsonl | jq -r '.command'

# Get only outputs
cat session.jsonl | jq -r '.output'

# Filter by command pattern
cat session.jsonl | jq 'select(.command | contains("ls"))'

# Count total commands
cat session.jsonl | jq -s 'length'
```

## Testing

A test script is provided:
```bash
./test_jsonl.sh
```

This will run the logger with simulated input and show the resulting JSONL log file.
