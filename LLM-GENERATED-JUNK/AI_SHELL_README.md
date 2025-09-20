# AI Shell - Intelligent Command Line Interface

An AI-enhanced shell that seamlessly integrates natural language understanding with traditional command execution.

## Quick Start

```bash
# Run from anywhere
aida-shell

# Or with debug mode
aida-shell --debug
```

## Features

- **Dual Mode Operation**: Handles both Linux commands and natural language seamlessly
- **Intelligent Classification**: Uses OpenAI to distinguish between commands and questions
- **State Preservation**: `cd`, `export`, and other stateful commands work correctly
- **Full Shell Experience**: Arrow keys, tab completion, Ctrl-R history search
- **Context Awareness**: Remembers recent commands and their output
- **SSH Execution**: Uses SSH-to-localhost for proper environment access

## Examples

### Regular Commands
```bash
$ ls -la
$ git status
$ cd /tmp
$ python3 script.py
```

### Natural Language
```bash
$ what files are in this directory?
$ how do I find large files?
$ fix the last error
$ what went wrong with that git command?
```

### Context-Aware Assistance
```bash
$ git push origin main
fatal: repository not found
$ what went wrong?
🤖 The git repository URL is incorrect or you don't have access...

$ fix it
🤖 Try: git remote set-url origin https://github.com/user/repo.git
```

## Built-in Commands

- `help` - Show help information
- `history` - Show recent command history with timestamps
- `exit` - Exit the AI Shell (or use Ctrl-D)

## Keyboard Shortcuts

- **Arrow Keys**: Navigate command history
- **Tab**: Auto-complete files and commands
- **Ctrl-R**: Reverse search through history
- **Ctrl-C**: Cancel current input (doesn't exit)
- **Ctrl-D**: Exit the shell

## Configuration

The AI Shell uses your existing AI Coder configuration:
- API keys from environment variables
- LLM settings from `config.yaml`
- Command execution through existing tool framework

## How It Works

1. **Three-Tier Classification**:
   - Obvious commands (70%): Instant execution
   - Obvious natural language (20%): Direct to AI
   - Ambiguous cases (10%): OpenAI classification

2. **Execution Methods**:
   - Regular commands: SSH-to-localhost for full environment
   - Stateful commands: Local execution with state sync
   - Natural language: Routes to existing AI agent

3. **State Management**:
   - Tracks current directory across contexts
   - Maintains command history with output
   - Syncs state between SSH and local sessions

## Troubleshooting

### SSH Not Available
The shell will automatically fall back to local execution mode if SSH isn't configured.

### To Enable SSH
```bash
# Install SSH server
sudo apt-get install openssh-server

# Start SSH service
sudo systemctl start ssh

# Run setup script
./setup_ai_shell.sh
```

### Debug Mode
Run with `--debug` flag to see classification decisions and detailed error messages:
```bash
aida-shell --debug
```

## Architecture

The AI Shell integrates with the existing AI Coder infrastructure:
- Uses `ChatSession` for AI interactions
- Leverages `LLMClient` for OpenAI API calls
- Routes commands through existing tool system
- Maintains consistent behavior with main agent
