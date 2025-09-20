# AI Shell Quick Start Guide

## Installation

```bash
# From the project directory
./setup_ai_shell.sh
```

## Usage

Start AI Shell from anywhere:
```bash
aida-shell
```

## Examples

### Natural Language Examples
These will be routed to the AI assistant:

```bash
# File operations
$ list the files in the current folder
$ what files are here?
$ show me large files
$ find Python files modified today

# Help requests  
$ how do I compress a folder?
$ what's the command to check disk space?
$ explain the last error

# Context-aware assistance
$ git push origin main
(error occurs)
$ what went wrong?
$ fix it
```

### Command Examples
These will execute directly:

```bash
# Standard commands
$ ls -la
$ pwd
$ cd /tmp
$ git status
$ python3 script.py

# Pipes and operators
$ ls | grep ".py"
$ cat file.txt | wc -l
$ echo "hello" > output.txt
```

## How It Works

1. **Heuristic Classification** (90% of cases):
   - Obvious commands: `ls`, `git`, `cd`, etc.
   - Obvious natural language: Questions, "show me", "list the", etc.

2. **AI Classification** (10% of ambiguous cases):
   - Uses OpenAI to determine intent
   - Examples: "restart server", "check status"

3. **Execution**:
   - Commands: SSH to localhost (or local fallback)
   - Natural Language: Routes to AI agent with context

## Tips

- The AI remembers your last 10 commands and their output
- After errors, ask "what went wrong?" or just say "fix"
- Tab completion and history (Ctrl-R) work as expected
- Use `--debug` flag to see classification decisions

## Troubleshooting

### "Command not found" for natural language
The classifier thought it was a command. Try rephrasing with:
- Question words: "what", "how", "where"
- Action phrases: "show me", "list the", "find"

### SSH not working
The shell will automatically fall back to local execution. To enable SSH:
```bash
sudo systemctl start ssh
./setup_ai_shell.sh
```

### No tools loaded
Make sure you're using the `aida-shell` command, not running the Python script directly from another directory.
