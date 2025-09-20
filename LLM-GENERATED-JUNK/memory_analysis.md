# AI Coder V3: Memory System (Simplified)

## The Simple Truth

**Memory exists to build the message array that gets sent to OpenAI.**

Everything else is just implementation details for:
1. **Storing** previous conversations
2. **Building context** for the next API call
3. **Tracking** what tools were executed

---

## What Actually Happens

### Every OpenAI API Call Gets This:
```python
messages = [
    {"role": "system", "content": "You are AIDA..."},
    {"role": "user", "content": "hello"},                    # From memory
    {"role": "assistant", "content": "Hi there!"},           # From memory
    {"role": "user", "content": "create a folder"},          # From memory
    {"role": "assistant", "content": "I'll create that"},    # From memory
    {"role": "tool", "content": "✅ COMMAND SUCCEEDED"},     # From memory
    {"role": "assistant", "content": "Done!"},               # From memory
    {"role": "user", "content": "current question"}         # Current input
]
```

**That's it.** Everything else is just building this array.

---

## Memory Components (Simple)

### 1. **InMemoryMemory** - The Message Store

**What it does**: Stores an array of messages per conversation thread.

```python
# Just a dictionary of message lists
_events = {
    "thread-123": [
        Message(role="user", content="hello"),
        Message(role="assistant", content="hi there"),
        Message(role="user", content="create folder"),
        # ... more messages
    ]
}
```

**That's it.** It's just a list of messages that gets longer over time.

### 2. **Scratch Memory** - Tool Execution Tracking

**What it does**: Tracks what tools were used during the current turn.

```python
# During one turn, if agent uses tools:
_scratch = [
    {"action": "run_command", "observation": "file1.txt", "duration": 0.5},
    {"action": "read_file", "observation": "# README...", "duration": 0.2}
]

# Gets attached to final assistant message
Message(role="assistant", content="I found your files", meta={"scratch": _scratch})
```

**Why**: For debugging what the agent actually did during complex turns.

### 3. **Recent Window** - Context Limit

**What it does**: Only sends the last 20 messages to OpenAI (not the entire conversation).

```python
# Instead of sending 1000 messages:
all_messages = memory.get_all_messages()  # Could be huge

# Send only recent messages:
recent = memory.last_events(thread_id, 20)  # Just last 20
```

**Why**: Prevents hitting OpenAI's context limits and saves tokens.

---

## The AI Shell Memory Problem

### Current Approach (Wasteful)

Every time you ask a natural language question, the AI Shell does this:

```python
# Build context from last 10 commands (EVERY TIME)
context = """
Recent commands:
$ ls -la
file1.txt file2.txt
$ git status  
clean working tree
"""

# Inject into prompt (EVERY TIME)
full_prompt = f"{question}\n\nContext:\n{context}"
await chat_session.ask(full_prompt)  # Sends same context repeatedly
```

### Token Waste Example

```bash
$ ls -la                    # Command executed, stored in command history
$ git status               # Command executed, stored in command history
$ what files are here?     # Sends: question + 2 commands (200 tokens)
$ how many files?          # Sends: question + SAME 2 commands (200 tokens)  
$ are there Python files? # Sends: question + SAME 2 commands (200 tokens)
```

**Result**: Same command context sent 3 times = 600 tokens instead of 200.

### Better Approach (Memory Integration)

Store commands as proper conversation messages:

```python
# When commands execute, add to conversation memory:
$ ls -la  → Message(role="assistant", content="Command result: file1.txt file2.txt")
$ git status → Message(role="assistant", content="Command result: clean working tree")

# Natural language questions use normal memory (no re-injection):
$ what files are here?     # Agent already has command context in conversation
$ how many files?          # Agent still has context, no duplication
$ are there Python files? # Agent still has context, no duplication
```

**Result**: Command context sent once, reused for all questions = 66% token savings.

---

## How Memory Actually Works

### Simple Flow

```
1. User asks question
   ↓
2. Load last 20 messages from memory
   ↓  
3. Build message array for OpenAI
   [system_prompt, old_messages..., new_user_message]
   ↓
4. Send to OpenAI → Get response
   ↓
5. Save response to memory
   memory.append(new_assistant_message)
```

**That's the entire flow.** Everything else is just details.

### The Key Insight: AI Shell Token Waste

**Current AI Shell behavior**:
- Every natural language question rebuilds and re-sends command context
- Same command outputs sent multiple times
- Massive token waste for repeated questions

**Your insight**: If commands were stored in conversation memory, they'd only be sent once and reused automatically.

**Bottom line**: The current AI Shell approach is inefficient. Commands should be integrated into the conversation memory, not injected as context strings.

## Summary

**Memory is just a message list builder.**

1. **Store** user questions and AI responses
2. **Load** recent messages for context
3. **Send** to OpenAI as message array
4. **Save** new response back to memory

**The AI Shell wastes tokens** by re-injecting the same command context instead of storing commands in the conversation memory once.

**The fix**: Store command executions as conversation messages, not separate command history.

---

## Message Roles (4 Types)

OpenAI expects these message roles:

1. **`"user"`** - What the user typed
2. **`"assistant"`** - AI responses  
3. **`"system"`** - System prompts
4. **`"tool"`** - Tool execution results

## Tool Call Flow

```python
# 1. Assistant wants to use a tool
{"role": "assistant", "content": "I'll list files", "tool_calls": [...]}

# 2. Tool executes, result gets saved
{"role": "tool", "content": "file1.txt\nfile2.txt", "tool_call_id": "abc123"}

# 3. Assistant sees tool result and responds
{"role": "assistant", "content": "Here are your files: file1.txt, file2.txt"}
```

**Important**: The `tool_call_id` must be at the top level of the message, not in metadata. Your `PromptBuilder` correctly handles this conversion from internal format to OpenAI format.

