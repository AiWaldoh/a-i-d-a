# A.I.D.A

A coding assistant that uses AI to help with code tasks.

## Components

* **Agent**: Uses ReAct loop to complete tasks
* **AI Shell**: Intelligent command line that understands both shell commands and natural language
* **RAG System**: ChromaDB for code search and context
* **Web Interface**: FastAPI app to view traces and search code

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Add API key to `.env` file:
   - `OPENROUTER_API_KEY` or
   - `OPENAI_API_KEY`

3. Make the commands executable:
   ```bash
   chmod +x aida aida-shell
   ```

4. Index your code (optional for rag):
   ```bash
   python3 indexer.py
   ```

5. Run the AI Shell or traditional agent:

   **AI Shell** (intelligent command line):
   ```bash
   # Setup AI Shell (one-time)
   ./setup_ai_shell.sh
   
   # Run AI Shell from anywhere
   aida-shell
   
   # Or with debug mode
   aida-shell --debug
   ```
   
   **Traditional Agent**:
   ```bash
   # Interactive (with persistent chat history)
   ./aida
   
   # One task
   ./aida --prompt "task description"
   
   # With context mode
   ./aida --context-mode rag
   ```
   
   AI Shell features:
   - Seamless switching between shell commands and natural language
   - Context-aware assistance based on recent commands
   - Full shell experience (tab completion, history, arrow keys)
   
   Traditional agent features:
   - Persistent chat history within session
   - Token usage tracking per turn and total
   - Full event tracing for all interactions

6. Run web interface:
   ```bash
   python3 -m web_app.main
   ```
   - Dashboard: `http://localhost:8000`
   - Code search: `http://localhost:8000/chromadb`

## Config Files

* `config.yaml`: Model and API settings
* `prompts.yaml`: System prompts
* `tools.yaml`: Agent tools

## How It Works

**AI Shell**: Uses intelligent classification to route input between direct command execution and AI processing. Commands like `ls` execute normally, while natural language like "show me files" routes to the AI agent with command history context.

**Traditional Agent**: Uses proxy pattern to log LLM and tool calls. Has different strategies for building context. Everything gets traced so you can see what happened.

## AI Shell Examples

```bash
$ ls -la                           # Executes directly
$ what files are in this directory? # Routes to AI
$ git push origin main             # Executes directly  
(error occurs)
$ what went wrong?                 # AI analyzes with error context
$ fix it                          # AI runs commands and fixes it
```