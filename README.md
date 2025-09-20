# AI Coder V3

A coding assistant that uses AI to help with code tasks.

## Components

* **Agent**: Uses ReAct loop to complete tasks
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

3. Make the `aida` command executable:
   ```bash
   chmod +x aida
   ```

4. Index your code (optional for rag):
   ```bash
   python3 indexer.py
   ```

5. Run the agent:
   
   Using the `aida` command (recommended):
   ```bash
   # Interactive (with persistent chat history)
   ./aida
   
   # One task
   ./aida --prompt "task description"
   
   # With context mode
   ./aida --context-mode rag
   ```
   
   Or using Python directly:
   ```bash
   # Interactive (with persistent chat history)
   python3 main.py
   
   # One task
   python3 main.py --prompt "task description"
   
   # With context mode
   python3 main.py --context-mode rag
   ```
   
   Interactive mode features:
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

Uses proxy pattern to log LLM and tool calls. Has different strategies for building context. Everything gets traced so you can see what happened.