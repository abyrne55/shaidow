#!/usr/bin/env python3
"""
Script to JSONL Parser

This script parses output files from the 'script' command and converts them
to JSONL (JSON Lines) format. Each line in the output contains:
- id: Unique identifier for each command
- command: The command that was executed  
- output: The output produced by the command (without shell prompts)

Usage:
    python3 script_to_jsonl.py input_file output_file

The script handles:
- Commands with no output
- Commands that "take over the TTY" like man, vi, etc.
- Multi-line output
- ANSI escape sequences and terminal control codes
- Various shell prompt formats
- Mixed line endings (\r\n, \n, \r)

Example:
    # Create a script session
    script -q session.txt
    # ... run some commands ...
    # exit
    
    # Convert to JSONL
    python3 script_to_jsonl.py session.txt commands.jsonl

Author: Generated for parsing script command outputs
"""

import re
import json
import sys
import argparse
from typing import List, Dict


class ScriptParser:
    """Parser for script command output files."""
    
    def __init__(self):
        # Comprehensive ANSI escape sequence patterns
        self.ansi_escape = re.compile(r'''
            \x1B                # ESC
            (?:                 # 7-bit C1 Fe (except CSI)
                [@-Z\\-_]
            |                   # or CSI + parameter bytes + intermediate bytes + final byte
                \[              # CSI
                [0-?]*          # parameter bytes
                [ -/]*          # intermediate bytes  
                [@-~]           # final byte
            )
        ''', re.VERBOSE)
        
        # Terminal control sequences
        self.terminal_controls = [
            re.compile(r'\]0;[^\x07]*\x07'),    # Set window title
            re.compile(r'\[?\?2004[hl]'),       # Bracketed paste mode
            re.compile(r'\x0e'),                # Shift out
            re.compile(r'\x0f'),                # Shift in
        ]
        
        # Pattern to detect start/end of script session
        self.script_start = re.compile(r'^Script started on.*?\[.*?\]$')
        self.script_end = re.compile(r'^Script done on.*?\[.*?\]$')
        
        # Shell prompt pattern - very flexible
        self.prompt_pattern = re.compile(r'^(.+?)[\$#%>]\s*(.*)$')
    
    def clean_line(self, line: str) -> str:
        """Thoroughly clean ANSI sequences and control characters."""
        cleaned = line
        
        # Remove terminal control sequences
        for pattern in self.terminal_controls:
            cleaned = pattern.sub('', cleaned)
        
        # Remove ANSI escape sequences
        cleaned = self.ansi_escape.sub('', cleaned)
        
        # Remove any remaining control characters except \t
        cleaned = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', cleaned)
        
        return cleaned
    
    def normalize_content(self, content: str) -> str:
        """Normalize line endings and clean up the content."""
        # Handle various line ending combinations
        content = content.replace('\r\n', '\n')
        content = content.replace('\r', '\n')
        
        # Remove null bytes and other problematic characters
        content = content.replace('\x00', '')
        
        return content
    
    def parse_script_output(self, content: str) -> List[Dict[str, str]]:
        """Parse script output and return list of command/output pairs."""
        content = self.normalize_content(content)
        lines = content.split('\n')
        
        commands = []
        command_id = 1
        
        # State tracking
        in_session = False
        current_command = None
        current_output = []
        
        for line in lines:
            # Check for session boundaries
            if self.script_start.match(line):
                in_session = True
                continue
            elif self.script_end.match(line):
                break
            
            if not in_session:
                continue
            
            # Clean the line thoroughly
            cleaned = self.clean_line(line)
            
            # Try to match as a prompt line
            prompt_match = self.prompt_pattern.match(cleaned)
            
            if prompt_match:
                command_part = prompt_match.group(2).strip()
                
                # Finalize previous command
                if current_command is not None:
                    output_text = '\n'.join(current_output).strip()
                    commands.append({
                        'id': str(command_id),
                        'command': current_command,
                        'output': output_text
                    })
                    command_id += 1
                
                # Start new command
                current_command = command_part if command_part else None
                current_output = []
                
            else:
                # This is potentially command input or output
                stripped = cleaned.strip()
                
                # If no current command and this looks like input
                if current_command is None and stripped:
                    # Heuristic: command lines usually don't start with whitespace
                    if not cleaned.startswith((' ', '\t')):
                        current_command = stripped
                        current_output = []
                        continue
                
                # Collect output for current command
                if current_command is not None:
                    # Skip command echo back
                    if stripped != current_command:
                        current_output.append(cleaned.rstrip())
        
        # Handle final command
        if current_command is not None:
            output_text = '\n'.join(current_output).strip()
            commands.append({
                'id': str(command_id),
                'command': current_command,
                'output': output_text
            })
        
        return commands
    
    def script_to_jsonl(self, input_file: str, output_file: str) -> None:
        """Convert script output file to JSONL format."""
        try:
            with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            commands = self.parse_script_output(content)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for cmd in commands:
                    f.write(json.dumps(cmd, ensure_ascii=False) + '\n')
            
            print(f"Successfully converted {len(commands)} commands from {input_file} to {output_file}")
            
            # Show first few commands for verification
            if commands:
                print("\nFirst few commands:")
                for cmd in commands[:3]:
                    print(f"  {cmd['id']}: {cmd['command']} -> {cmd['output'][:50]}{'...' if len(cmd['output']) > 50 else ''}")
            
        except FileNotFoundError:
            print(f"Error: Input file '{input_file}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error processing file: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert script command output to JSONL format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 script_to_jsonl.py typescript output.jsonl
    python3 script_to_jsonl.py session.log commands.jsonl

Output format:
Each line contains a JSON object with:
- id: Sequential command identifier (string)
- command: The command that was executed
- output: The command's output (cleaned of prompts and ANSI sequences)

Example output:
{"id":"1","command":"echo hello","output":"hello"}
{"id":"2","command":"ls","output":"file1.txt\\nfile2.txt"}

Features:
- Removes ANSI escape sequences and terminal control codes
- Handles various shell prompt formats  
- Groups multi-line output correctly
- Handles commands with no output
- Works with commands that manipulate the terminal (man, vi, etc.)
- Supports mixed line endings from script command output

Requirements:
- Python 3.6+ (uses f-strings in error messages)
- Input must be output from the 'script' command

Note: For best results, use 'script -q' to reduce extra output.
        """
    )
    
    parser.add_argument('input_file', help='Input script output file')
    parser.add_argument('output_file', help='Output JSONL file')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"Converting {args.input_file} to {args.output_file}")
    
    parser_instance = ScriptParser()
    parser_instance.script_to_jsonl(args.input_file, args.output_file)


if __name__ == '__main__':
    main()