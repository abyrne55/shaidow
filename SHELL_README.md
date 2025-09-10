# Interactive Shell Logger

A bash script that creates an interactive shell where all commands and their outputs are logged with unique identifiers.

## Features

- Logs each command with a unique identifier: `RAN [X]: command`
- Logs command output with matching identifier: `GOT [X]: output`
- Filters out shell prompts (PS1) from the log file
- Simple and clean log format
- Easy to use interactive interface

## Usage

```bash
./interactive_logger.sh [logfile]
```

If no logfile is specified, it defaults to `shell_session.log`.

## Example

Start the logger:
```bash
./interactive_logger.sh my_session.log
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

The log file will contain:
```
RAN [1]: echo "Hello World"
GOT [1]: Hello World
RAN [2]: ls -la
GOT [2]: total 8
GOT [2]: drwxr-xr-x 2 user user 4096 Sep 10 10:30 .
GOT [2]: drwxr-xr-x 3 user user 4096 Sep 10 10:29 ..
```

## Notes

- Type `exit` to quit the logged shell session
- Empty commands are ignored
- Command exit status is logged if non-zero
- PS1 prompts are filtered out of the log file
- Each command-output pair gets a unique identifier for easy matching

## Testing

A test script is provided:
```bash
./test_logger.sh
```

This will run the logger with simulated input and show the resulting log file.
