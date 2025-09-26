# Token Optimization Improvements

## Problem Analysis

The current system stores all tool execution results in full detail, leading to significant token waste:

- `file_search` results: Long lists of file paths
- `read_file` results: Entire file contents (up to 200 lines)
- `run_command` results: Full command outputs  
- `semantic_search` results: Multiple code chunks

These verbose results are stored in memory and sent to the LLM in every subsequent conversation turn, causing exponential token growth.

## Token Savings Potential

**Example savings:**
- Current `read_file` result: ~1000-3000 tokens
- Summarized version: "Found file_search.py at /path/to/file with Command class that searches files using glob patterns" (~30 tokens)
- **Potential reduction: 97%**

## Implementation Strategy

### 1. Selective Summarization

```python
# In agent.py after tool execution
if should_summarize_tool_result(tool_name, tool_output):
    summary = await self._summarize_tool_result(tool_name, params, tool_output)
    tool_message = Message(
        role="tool", 
        content=summary,
        meta={"tool_call_id": tool_call.id, "original_length": len(tool_output)}
    )
```

### 2. Context-Aware Summarization

Different tools require different summarization approaches:

- **file_search**: "Found N files: [key files], located in [main directories]"
- **read_file**: "File contains [main purpose] with [key functions/classes]"
- **run_command**: "Command succeeded/failed, key output: [essential info]"
- **semantic_search**: "Found relevant code in [files] related to [topic]"

### 3. Critical Information Preservation

The summarization must preserve:
- **File paths** (critical for path memory!)
- **Error messages** (needed for debugging)
- **Key data** (function names, important values)
- **Success/failure status**

## Proposed Prompt Template

Add to `prompts.yaml`:

```yaml
tool_result_summarization: |
  Summarize this tool execution result, preserving essential information:
  
  Tool: {tool_name}
  Parameters: {params}
  Result: {tool_output}
  
  Extract and preserve:
  1. Success/failure status
  2. Key file paths or locations discovered
  3. Important data or findings (function names, classes, etc.)
  4. Any errors or issues
  5. Actionable information for future reference
  
  Provide a concise summary (max 100 words) that preserves all actionable information:
```

## Hybrid Approach (Recommended)

Implement a tiered memory system:

1. **Keep recent tool results** in full detail (last 5-10 executions)
2. **Summarize older tool results** when they age out of recent memory
3. **Never summarize critical information**:
   - File paths and locations
   - Error messages
   - Success/failure status
4. **Use fast/cheap model** for summarization (GPT-3.5-turbo)

## Implementation Details

### Memory Management

```python
class ToolResultManager:
    def __init__(self, recent_limit=10):
        self.recent_limit = recent_limit
        
    def should_summarize(self, tool_result_age, tool_name):
        # Keep recent results full, summarize older ones
        if tool_result_age < self.recent_limit:
            return False
        # Never summarize critical path information
        if self._contains_critical_info(tool_result):
            return False
        return True
        
    def _contains_critical_info(self, result):
        # Check for file paths, error messages, etc.
        return any([
            "/home/" in result,  # File paths
            "Error:" in result,  # Error messages
            "Failed:" in result, # Failure indicators
        ])
```

### Summarization Service

```python
async def _summarize_tool_result(self, tool_name, params, tool_output):
    prompt = self.prompts["tool_result_summarization"].format(
        tool_name=tool_name,
        params=params,
        tool_output=tool_output[:2000]  # Truncate very long outputs
    )
    
    # Use cheaper model for summarization
    summary_response = await self.summarization_llm.get_response(
        messages=[{"role": "user", "content": prompt}]
    )
    
    return summary_response.choices[0].message.content
```

## Expected Benefits

- **Token reduction**: 70-90% reduction in memory token usage
- **Cost savings**: Significant reduction in API costs
- **Performance**: Faster processing due to smaller context
- **Scalability**: Enables longer conversation histories

## Trade-offs

**Pros:**
- ✅ Massive token savings
- ✅ Faster processing
- ✅ Lower costs
- ✅ Preserves essential context

**Cons:**
- ❌ Slight delay for summarization LLM call
- ❌ Risk of losing nuanced details
- ❌ Additional system complexity
- ❌ Potential for summarization errors

## Implementation Priority

1. **Phase 1**: Implement basic summarization for `read_file` results (biggest token waste)
2. **Phase 2**: Add summarization for `run_command` outputs
3. **Phase 3**: Implement hybrid recent/summarized memory system
4. **Phase 4**: Add intelligent critical information detection

## Monitoring

Track metrics to validate improvements:
- Average tokens per conversation
- Token reduction percentage
- Information loss incidents
- User satisfaction with AI memory
