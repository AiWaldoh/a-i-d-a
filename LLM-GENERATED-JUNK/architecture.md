# AI Coder V3: System Architecture

## Core Architectural Pattern: Proxy-Based Observability

AI Coder V3 is built around a **proxy pattern** that provides comprehensive observability and tracing without coupling the core agent logic to logging concerns. This is a critical architectural decision that enables complete system introspection.

---

## The Proxy Pattern Implementation

### Philosophy
**Separation of Concerns**: The agent focuses on reasoning and task execution, while proxies handle cross-cutting concerns like logging, tracing, and observability.

### Key Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   Traditional   │  │         AI Shell                │   │
│  │     Agent       │  │      (BYPASSES PROXY!)         │   │
│  │    main.py      │  │       ai_shell.py               │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                ↓                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Proxy Layer                               │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │    LLMProxy     │  │        ToolProxy                │   │
│  │  (Wraps LLM)    │  │   (Wraps ToolExecutor)          │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                ↓                           ↓
┌─────────────────────────────────────────────────────────────┐
│                 Implementation Layer                        │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   LLMClient     │  │     ToolExecutor                │   │
│  │ (OpenAI API)    │  │  (Command Execution)            │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                ↓                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  External Services                          │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   OpenRouter    │  │    System Commands              │   │
│  │      API        │  │   (SSH/Subprocess)              │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Proxy Components Deep Dive

### 1. LLMProxy (`src/trace/proxies.py`)

**Purpose**: Wraps `LLMClient` to provide transparent logging and tracing of all LLM interactions.

**Responsibilities**:
- **Request Logging**: Captures messages, tools, model parameters
- **Response Logging**: Captures choices, usage stats, timing
- **Error Handling**: Logs failures and exceptions
- **Performance Metrics**: Tracks duration and token usage
- **Trace Correlation**: Links requests to specific user tasks

**Key Methods**:
```python
async def get_response(self, messages: list, tools: list = None) -> Optional[ChatCompletion]:
    # 1. Log the request
    self.event_sink.emit(TaskEvent(
        event_type="llm_request",
        data={"messages": messages, "tools": tools}
    ))
    
    # 2. Execute the actual request
    response = await self.real_client.get_response(messages, tools)
    
    # 3. Log the response
    self.event_sink.emit(TaskEvent(
        event_type="llm_response", 
        data={"response": response_data, "duration": duration}
    ))
```

**What Gets Logged**:
- **Input**: Complete message history, tool schemas, model config
- **Output**: Response content, token usage, finish reasons, timing
- **Metadata**: Model name, trace ID, timestamps
- **Errors**: Exception details, failure modes

### 2. ToolProxy (`src/trace/proxies.py`)

**Purpose**: Wraps `ToolExecutor` to provide transparent logging of all tool executions.

**Responsibilities**:
- **Tool Request Logging**: Captures tool name and parameters
- **Tool Response Logging**: Captures output and execution time
- **Performance Tracking**: Times tool execution duration
- **Error Logging**: Captures tool execution failures

**What Gets Logged**:
- **Input**: Tool name, parameters, reasoning
- **Output**: Tool results, execution time
- **Context**: Working directory, environment state
- **Errors**: Command failures, timeout issues

### 3. Event System (`src/trace/events.py`)

**Purpose**: Structured event emission and storage system.

**Components**:
- **TraceContext**: Groups related events by trace ID
- **TaskEvent**: Individual logged events with timestamps
- **EventSink**: Abstract interface for event storage
- **FileEventSink**: JSONL file storage implementation

**Event Types**:
```python
# LLM Events
"llm_request"     # Before API call
"llm_response"    # After API call

# Tool Events  
"tool_request"    # Before tool execution
"tool_response"   # After tool execution

# Task Events
"task_started"    # User request begins
"task_completed"  # User request completes
"task_failed"     # User request fails

# Session Events
"session_started" # Interactive session begins
"context_build_completed" # RAG context built
```

---

## Proxy Pattern Guidelines for Developers

### Mandatory Proxy Usage Rule

**CRITICAL**: All LLM and tool interactions MUST go through the proxy layer. This is not optional.

**Correct Pattern**:
```python
# ✅ ALWAYS DO THIS
real_llm_client = LLMClient()
real_tool_executor = ToolExecutor()

llm_proxy = LLMProxy(real_llm_client, trace_context, event_sink)
tool_proxy = ToolProxy(real_tool_executor, trace_context, event_sink)

session = ChatSession(
    llm_client=llm_proxy,      # ✅ PROXIED
    tool_executor=tool_proxy   # ✅ PROXIED
)
```

**Incorrect Pattern**:
```python
# ❌ NEVER DO THIS
session = ChatSession()  # Uses default LLMClient() - NO PROXY!
llm_client = LLMClient()  # Direct usage - NO PROXY!
```

### When Creating New Components

**Rule**: Any component that makes LLM calls or executes tools must accept proxied clients.

**Example**:
```python
class NewAIComponent:
    def __init__(self, llm_client: LLMClient, tool_executor: ToolExecutor):
        # Accept injected clients (which should be proxied)
        self.llm_client = llm_client
        self.tool_executor = tool_executor
    
    # DON'T create clients internally:
    # self.llm_client = LLMClient()  # ❌ BYPASSES PROXY
```

---

## Why The Proxy Pattern Exists

### 1. **Separation of Concerns**
The agent doesn't need to know about logging - it focuses purely on reasoning and execution.

### 2. **Non-Intrusive Observability**
Complete system visibility without modifying core business logic.

### 3. **Centralized Logging**
All interactions flow through the same logging pipeline for consistency.

### 4. **Trace Correlation**
Links all events (LLM calls, tool executions, user requests) with trace IDs.

### 5. **Performance Monitoring**
Automatic timing and usage tracking for optimization.

### 6. **Debugging Support**
Complete request/response logging for troubleshooting.

---

## Proxy Pattern Benefits

### For Development
- **Complete Visibility**: See exactly what the AI is doing
- **Performance Analysis**: Identify slow operations and bottlenecks
- **Cost Tracking**: Monitor API usage and token consumption
- **Error Debugging**: Full context for troubleshooting failures

### For Operations  
- **Usage Analytics**: Understand user interaction patterns
- **Resource Planning**: Track API usage trends and costs
- **Quality Monitoring**: Analyze response quality and success rates
- **Audit Trail**: Complete log of all system interactions

### For Optimization
- **Token Analysis**: Identify expensive prompts and optimize
- **Caching Opportunities**: Find repeated requests for caching
- **Model Selection**: Compare performance across different models
- **Workflow Analysis**: Understand user task patterns

---

## Event Storage & Analysis

### Current Implementation
**Storage**: JSONL files in `/tmp/trace_TIMESTAMP.jsonl`
**Format**: Structured events with timestamps and trace correlation
**Access**: Direct file reading or web interface dashboard

### Event Structure
```json
{
  "event_type": "llm_request",
  "trace_id": "uuid-1234",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "messages": [...],
    "tools": [...],
    "model": "openai/gpt-5-mini"
  }
}
```

### Analysis Capabilities
- **Token Usage**: Sum usage across all events
- **Performance**: Analyze duration distributions  
- **Error Rates**: Track failure patterns
- **User Workflows**: Follow trace IDs across events
- **Cost Analysis**: Calculate API costs by model and time

---

## Integration Points

### Traditional Agent Flow
```
User Input → TaskOrchestrator → ChatSession(proxied) → Agent → LLMProxy → LLMClient → API
                                                              ↓
                                                         EventSink → JSONL File
```

### AI Shell Flow (Current - BROKEN)
```
User Input → AIShell → ChatSession(direct) → Agent → LLMClient → API
                                                         ↓
                                                   NO LOGGING!

User Input → AIShell → CommandClassifier → LLMClient → API  
                                              ↓
                                        NO LOGGING!
```

### AI Shell Flow (Should Be)
```
User Input → AIShell → ChatSession(proxied) → Agent → LLMProxy → LLMClient → API
                                                          ↓
                                                     EventSink → JSONL File

User Input → AIShell → CommandClassifier(proxied) → LLMProxy → LLMClient → API
                                                        ↓
                                                   EventSink → JSONL File
```

---

## Critical Architectural Insight

**The proxy pattern is not optional decoration - it's a fundamental system component that provides:**

1. **Complete System Observability** - Without it, the AI Shell is a black box
2. **Consistent Logging Architecture** - All components should use the same tracing
3. **Debugging and Optimization** - Essential for understanding system behavior  
4. **Cost and Performance Monitoring** - Required for production operations

**The AI Shell's bypass of the proxy pattern represents a significant architectural inconsistency that breaks system observability and violates the design principles of the application.**

---

## Developer Guidelines

### 1. Always Use Dependency Injection

**Rule**: Never instantiate `LLMClient` or `ToolExecutor` directly in component constructors.

**Rationale**: Direct instantiation bypasses the proxy layer and breaks observability.

### 2. Trace Context Propagation

**Rule**: All components should accept and propagate `TraceContext` for event correlation.

**Implementation**:
```python
class MyComponent:
    def __init__(self, llm_client: LLMClient, trace_context: TraceContext, event_sink: EventSink):
        self.llm_client = llm_client  # Should be proxied
        self.trace_context = trace_context
        self.event_sink = event_sink
```

### 3. Event Emission Standards

**Rule**: Emit structured events for all significant operations.

**Event Naming**: Use consistent event types:
- `{component}_request` - Before operation
- `{component}_response` - After operation  
- `{component}_error` - On failure

### 4. Error Handling in Proxies

**Rule**: Proxies should never suppress errors - they should log and re-raise.

**Pattern**:
```python
try:
    result = await self.real_client.operation()
    self._log_success(result)
    return result
except Exception as e:
    self._log_error(e)
    raise  # Always re-raise
```

### 5. Testing with Proxies

**Rule**: Integration tests should use proxied components to verify logging behavior.

**Anti-Pattern**: Testing with direct clients and missing logging bugs.

---

## Architecture Principles

### 1. **Observability First**
Every system interaction should be observable and traceable.

### 2. **Separation of Concerns**  
Business logic should be independent of cross-cutting concerns like logging.

### 3. **Consistent Patterns**
All components should follow the same architectural patterns.

### 4. **Dependency Injection**
Components should accept dependencies rather than creating them.

### 5. **Event-Driven Design**
System behavior should be observable through structured events.

This proxy-based architecture enables complete system introspection while maintaining clean separation between business logic and observability concerns.
