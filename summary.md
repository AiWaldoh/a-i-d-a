# A.I.D.A System Technical Summary

## Application Type

A.I.D.A (AI Intelligent Development Assistant) is an autonomous AI agent system with three operational modes:

1. **Interactive Chat Mode**: ReAct (Reasoning-Action) agent with tool-calling capabilities
2. **AI Shell Mode**: AI-enhanced shell that classifies input as Linux commands or natural language
3. **Brain-Worker Mode**: Autonomous penetration testing with dual-agent architecture

**Primary Domain**: Penetration testing and security research automation

---

## Component Architecture

### Agent System (`src/agent/`)

**agent.py** - ReAct Agent Implementation
- Implements Reason-Act loop with tool-calling
- Token counting with tiktoken, fallback to len()
- Retry logic: 10 attempts, 2-second exponential backoff
- Personality enhancement layer (separate LLM call)
- Rolling conversation summary for memory management
- Configurable step limit (default: 50)

**session.py** - Session Management
- Wraps Agent with persistent conversation context
- UUID-based session identification
- Tracks cumulative token usage

**tool_executor.py** - Plugin System
- Dynamic command loading from `src/commands/`
- Each tool = one Python file with `Command` class
- Runtime loading via `importlib`
- Dispatching pattern: `execute_tool(tool_name, params)`

**memory.py** - Conversation Persistence
- Port/Adapter pattern (MemoryPort protocol)
- InMemoryMemory implementation with thread isolation
- Stores messages with metadata (tool_calls, scratch notes)
- Summary storage for context compression

**prompt_builder.py** - Message Construction
- OpenAI-compatible message array builder
- Tool call formatting
- Context mode switching (none/ast/rag)
- YAML-based prompt template loading

**repo_map.py** - AST Repository Indexing
- Python AST parser for code structure extraction
- Hierarchical function/class mapping
- Ignores: .git, __pycache__, venv, node_modules

---

### LLM Integration (`src/llm/`)

**client.py** - LLM Communication
- AsyncOpenAI client wrapper
- Multi-model support via configuration
- Custom response parsers (qwen_thinking format)
- Configurable: temperature, top_p, max_tokens
- OpenRouter-specific parameters (reasoning_effort, verbosity)

**types.py** - Type Definitions
- LLMConfig dataclass

---

### RAG System (`src/rag/`)

**chunker.py** - Code Chunking
- AST-based Python parsing
- Extracts functions (sync/async) and classes
- Hierarchical symbol naming (e.g., "ClassName.method_name")
- SHA256 content hashing for change detection
- Nested definition support

**embedding.py** - Semantic Processing
- Wraps code chunks with LLM-generated summaries
- Summary + code = searchable document
- Template-based summarization prompts

**embedding_factory.py** - Factory Pattern
- Multiple embedding model support
- DefaultEmbeddingFunction (all-MiniLM-L6-v2)
- OpenAI embeddings
- Custom SentenceTransformer models

**vector_store.py** - ChromaDB Integration
- Persistent vector storage
- HNSW index: M=16, construction_ef=200, search_ef=10
- Similarity score calculation (cosine/l2/inner product)
- Query with metadata (distance, rank, similarity)

**strategy.py** - Context Strategy Pattern
- **NullContextStrategy**: No context injection
- **ASTContextStrategy**: Repository structure map
- **RAGContextStrategy**: Semantic search with filtering
  - Similarity threshold: 0.3
  - Max chunks: 10
  - Fallback: top 10 when insufficient results

**prompt_templates.py** - Template Manager
- YAML-based prompt storage
- String interpolation
- Template validation

---

### Trace System (`src/trace/`)

**events.py** - Event Logging
- TaskEvent dataclass for structured logging
- FileEventSink: writes JSONL to `tmp/trace_*.jsonl`
- Event types: task_started, task_completed, task_failed, llm_request, llm_response, tool_request, tool_response

**orchestrator.py** - Task Orchestrator
- Single-task execution mode (non-interactive)
- Context strategy integration
- Event emission for observability
- Agent lifecycle management

**proxies.py** - Proxy Pattern for Tracing
- **LLMProxy**: Wraps LLMClient, logs requests/responses with timing
- **ToolProxy**: Wraps ToolExecutor, logs tool calls with timing
- Transparent proxying without interface changes

---

### AI Shell (`src/ai_shell/`)

**shell.py** - Interactive Shell
- Readline integration (history, tab completion, Ctrl-R)
- Command history persistence
- SSH-based remote execution with local fallback
- Stateful command tracking (cd, export, alias)
- Built-in commands: exit, history, help, enhance-self, brain-session
- Dangerous command confirmation
- Colored prompt: `user@host:path` format

**classifier.py** - Command Classification
- Chain of Responsibility pattern
- Three-level classification:
  1. Heuristic: 60+ obvious command patterns (ls, cd, git, python, etc.)
  2. Heuristic: Natural language starters (what, how, why, help, explain)
  3. LLM-based classification (fallback)
- Classification caching
- Context-aware: uses recent command history
- Confidence scoring

**executor.py** - Command Execution
- Paramiko SSH client for persistent state
- Local subprocess fallback
- Stateful handling (cd changes process state)
- Command history with timestamps
- Environment variable tracking
- Tempfile-based state extraction

**ai_tool_executor.py** - Adapter Pattern
- Extends ToolExecutor
- Auto-injects current working directory
- Shell-aware context propagation

**config.py** - Configuration
- History file location
- Max history size
- Classification thresholds
- Dangerous command patterns

---

### Brain System (`src/brain/`)

**orchestrator.py** - Autonomous Pentesting
- Dual-agent architecture:
  - **Brain Agent**: Strategic planning, no tool execution
  - **Worker Agent**: Tool execution
- Target state tracking:
  - Phase progression: RECONNAISSANCE → ENUMERATION → EXPLOITATION
  - Open ports, services, vulnerabilities
  - Findings accumulation
- Iteration control (max: 50)
- Pattern-based state updates (regex parsing of nmap output)
- Stop condition detection (keywords: complete, finished, done, success)
- Final report generation

---

### Browser System (`src/browser/`)

**stealth_browser.py** - Web Automation
- Playwright-based (Firefox)
- Template Method pattern (StealthBrowser base class)
- Stealth techniques:
  - WebDriver detection removal
  - Custom user agent
  - Timezone/locale spoofing
  - Preference manipulation

**GoogleSearch** - Google Scraping
- Scrapes Google results
- Retry logic with exponential backoff

**WebpageFetcher** - Content Extraction
- Structured content extraction
- Link mapping with placeholder replacement
- Cookie banner auto-dismissal
- Semantic tag filtering (h1-h6, p, li, td, th, blockquote, pre, code)
- Word count filtering (>3 words)

---

### Commands (`src/commands/`)

Plugin-based tool implementations:

- **run_command.py**: Shell command execution with timeout
- **read_file.py**: File reading with pagination
- **write_to_file.py**: File creation/overwrite
- **ripgrep.py**: Text search with pattern matching
- **file_search.py**: Glob-based file finding
- **semantic_search.py**: RAG-based code search
- **google_search.py**: Google search via stealth browser
- **read_website.py**: Webpage fetching and parsing
- **install_app.py**: Package installation (sudo apt)
- **vpn_connection.py**: OpenVPN connection management
- **restart_shell.py**: Shell process restart
- **autorecon_scan.py**: AutoRecon integration
- **brain_session.py**: Brain orchestrator launcher

---

### Configuration (`src/config/`)

**settings.py** - Centralized Configuration
- Environment variable loading (.env)
- YAML configuration parsing (config.yaml)
- Multiple LLM provider support
- Separate LLM configs: agent_llm, classifier_llm, personality_llm
- ChromaDB tuning parameters
- RAG thresholds
- Brain configuration

---

### Utilities (`src/utils/`)

**paths.py** - Path Resolution
- Project root detection
- Absolute path resolution

**logger.py** - Logging infrastructure

---

## Design Patterns

### 1. Strategy Pattern
**Location**: `src/rag/strategy.py`
- Interface: ContextStrategy (abstract)
- Implementations: NullContextStrategy, ASTContextStrategy, RAGContextStrategy
- Runtime selection based on `--context-mode` argument
- Purpose: Different context building approaches

### 2. Proxy Pattern
**Location**: `src/trace/proxies.py`
- LLMProxy wraps LLMClient
- ToolProxy wraps ToolExecutor
- Cross-cutting concern: event tracing
- Maintains same interface as wrapped objects
- Purpose: Non-invasive observability

### 3. Factory Pattern
**Location**: `src/rag/embedding_factory.py`
- `get_embedding_function()` returns embedding implementations
- Decision based on configuration
- Returns: DefaultEmbeddingFunction, OpenAIEmbeddingFunction, SentenceTransformerEmbeddingFunction

### 4. Adapter Pattern
**Location**: `src/ai_shell/ai_tool_executor.py`
- AIShellToolExecutor extends ToolExecutor
- Adapts tool executor to shell context
- Injects current working directory automatically

### 5. Template Method Pattern
**Location**: `src/browser/stealth_browser.py`
- StealthBrowser abstract base class with `_create_stealth_page()`
- Concrete classes: GoogleSearch, WebpageFetcher
- Shared stealth setup, different execution

### 6. Plugin/Registry Pattern
**Location**: `src/agent/tool_executor.py`
- Dynamic tool discovery from `src/commands/`
- Each tool = one Python file with `Command` class
- Runtime loading with `importlib`
- Dispatching via `execute_tool(tool_name, params)`

### 7. Facade Pattern
**Location**: `src/agent/session.py`
- ChatSession provides simplified interface
- Hides: Agent, Memory, PromptBuilder, LLMClient, ToolExecutor complexity
- Exposes: Simple `ask()` method

### 8. Port/Adapter Pattern (Hexagonal Architecture)
**Location**: `src/agent/memory.py`
- MemoryPort protocol defines interface
- InMemoryMemory concrete implementation
- Allows swapping storage backends

### 9. Chain of Responsibility Pattern
**Location**: `src/ai_shell/classifier.py`
- Classification pipeline:
  1. Obvious command heuristics
  2. Obvious natural language heuristics
  3. LLM-based classification (fallback)
- Each level handles or passes to next
- Purpose: Performance optimization (avoid LLM calls)

---

## Architecture Patterns

### 1. ReAct (Reasoning-Action) Agent Architecture
**Implementation**: `src/agent/agent.py`
- LLM reasons → decides tools → observes results → repeats
- Tool calls via OpenAI function calling
- Scratch memory for action tracking
- Maximum step limit prevents infinite loops

### 2. RAG (Retrieval-Augmented Generation)
**Implementation**: `src/rag/` module
- Pipeline: Code chunking → embedding → vector storage → similarity search → context injection
- Semantic search over codebase
- Smart filtering with similarity thresholds
- Fallback strategy when insufficient high-quality matches

### 3. Dual-Agent System
**Implementation**: `src/brain/orchestrator.py`
- Brain Agent: Strategy, planning, decision-making (no tool access)
- Worker Agent: Execution, tool calling, task completion
- Asynchronous communication via prompt passing
- State tracking for coordination

### 4. Event-Driven Architecture
**Implementation**: `src/trace/` module
- EventSink interface for flexible backends
- Structured event emission throughout system
- JSONL file sink for trace storage
- Events tagged with trace_id for correlation

### 5. Command Pattern
**Implementation**: Tool system
- Each tool encapsulates an action
- Uniform interface: `execute(params) -> str`
- Parameters as dictionary (JSON-compatible)
- Result as formatted string

---

## Technology Stack

### Core Technologies
- Python 3.x
- AsyncIO (asynchronous execution)
- OpenAI API (via OpenRouter)
- Pydantic/Dataclasses (type safety)

### LLM & Embeddings
- OpenRouter (LLM gateway: gpt-4.1-mini, qwen3-next)
- ChromaDB (vector database)
- Sentence Transformers (all-MiniLM-L6-v2)
- tiktoken (token counting)

### Code Analysis
- AST (Abstract Syntax Tree) for Python parsing
- hashlib (SHA256 content hashing)

### Web & Browser
- Playwright (browser automation, Firefox)
- Paramiko (SSH client)

### Storage & Serialization
- PyYAML (configuration, prompts)
- JSON/JSONL (event logging)

### Testing
- pytest
- pytest-mock
- pytest-playwright
- pyfakefs

### System Integration
- subprocess (command execution)
- readline (shell history/completion)
- dotenv (environment variables)

---

## Key Workflows

### Workflow 1: Interactive Agent Task Execution

```
User Input
    ↓
main.py
    ↓
TaskOrchestrator.execute_task()
    ↓
Context Strategy builds context (none/ast/rag)
    ↓
Agent.step() - ReAct loop:
    ├─ PromptBuilder constructs messages
    ├─ LLMProxy logs and calls LLM
    ├─ LLM returns tool calls
    ├─ Agent parses tool calls
    ├─ ToolProxy logs and executes tools
    ├─ Results added to conversation
    └─ Repeat until final answer
    ↓
Personality LLM enhances response (optional)
    ↓
Result returned
    ↓
Events logged to trace file
```

### Workflow 2: RAG Context Building

```
User starts with --context-mode rag
    ↓
RAGContextStrategy.build() called
    ↓
VectorStore.query() performs semantic search
    ↓
ChromaDB returns top 20 results with scores
    ↓
Smart filtering:
    ├─ Filter by threshold (0.3)
    ├─ If <10 results: use fallback (top 10 regardless)
    └─ If >=10 results: top 10 above threshold
    ↓
Format chunks as markdown with file paths
    ↓
Context injected into system prompt
```

### Workflow 3: AI Shell Command Processing

```
User enters input in AIShell
    ↓
CommandClassifier.classify():
    ├─ Check heuristics (obvious command/NL)
    ├─ If ambiguous: call LLM classifier
    └─ Return classification + confidence
    ↓
If command:
    ├─ CommandExecutor.execute_command()
    ├─ Handle stateful commands (cd)
    ├─ Execute via SSH or local subprocess
    └─ Add to history
    ↓
If natural language:
    ├─ Build context from recent commands
    ├─ Create Agent instance
    ├─ Execute with tracing
    └─ Return AI response
    ↓
Display output with token usage
```

### Workflow 4: Brain-Worker Autonomous Pentesting

```
brain_session tool called with target IP
    ↓
BrainOrchestrator creates two ChatSessions:
    ├─ Brain: strategic planning (no tools)
    └─ Worker: execution (all tools)
    ↓
Iteration loop (max 50):
    ├─ Brain analyzes target_state
    ├─ Brain decides next action
    ├─ Check for completion keywords
    ├─ Worker executes task with tools
    ├─ Update target_state from results
    ├─ Pattern matching extracts ports/services
    └─ Phase progression: RECON → ENUM → EXPLOIT
    ↓
Generate final report with Brain LLM
    ↓
Return complete session history
```

### Workflow 5: Tool Plugin Loading

```
ToolExecutor.__init__() scans src/commands/
    ↓
For each .py file (except __init__.py):
    ├─ importlib dynamically imports
    ├─ Check for Command class
    ├─ Instantiate Command()
    └─ Store in commands dictionary
    ↓
Agent receives tools.yaml definitions
    ↓
Agent calls ToolExecutor.execute_tool(name, params)
    ↓
ToolExecutor dispatches to Command instance
    ↓
Command.execute() runs and returns result
```

---

## Data Flow

```
User Input
    ↓
[main.py / AIShell]
    ↓
[TaskOrchestrator / ChatSession]
    ↓
[Context Strategy] → RAG/AST context building
    ↓
[Agent] → ReAct loop management
    ↓
[PromptBuilder] → message construction
    ↓
[LLMProxy] → [LLMClient] → OpenRouter API
    ↓
[Agent] → receives tool calls
    ↓
[ToolProxy] → [ToolExecutor] → [Command plugin]
    ↓
[Command] → executes (subprocess/browser/vectorstore)
    ↓
Result → [Agent] → repeats or finalizes
    ↓
[Personality LLM] → response enhancement (optional)
    ↓
[Memory] → conversation storage
    ↓
Output → User

Parallel: All steps emit events to [EventSink] → trace file
```

---

## Technical Characteristics

1. **Multi-mode operation**: Three entry points (main.py, AI Shell, Brain sessions) sharing core components

2. **Comprehensive tracing**: Proxy pattern enables full observability without polluting business logic

3. **Smart classification**: Heuristic pre-filtering in AI Shell saves >90% of LLM calls

4. **Extensible tools**: Plugin architecture allows new tools by adding Python files

5. **Context strategies**: Clean separation allows easy addition of new context modes

6. **Async-first**: AsyncIO used throughout for concurrent operations

7. **Configuration-driven**: Multiple LLM configs (agent, classifier, personality)

8. **Stateful shell**: SSH persistence maintains environment across commands

9. **RAG filtering**: Smart threshold-based selection with fallback prevents empty contexts

10. **Dual-agent coordination**: Brain-Worker separation enables autonomous operation with strategic oversight