from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import re
import glob
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from web_app.models import LLMMetrics, MetricsFile, WorkflowContext, Usage, FullResponse, Choice, Message

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import ChromaDB-related classes
try:
    from src.rag.vector_store import VectorStore
    from src.rag.chunker import CodeChunk
    from src.rag.embedding_factory import get_embedding_function
    from src.config.settings import AppSettings
    import chromadb.utils.embedding_functions as embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# --- Constants ---
# The web_app is one level down, so we go up one level to find the root
# and then into the 'tmp' directory for metrics.
METRICS_DIR = Path(__file__).resolve().parent.parent / "tmp"
DB_DIR = Path(__file__).resolve().parent.parent / "db"

# Simple in-memory cache for file metadata
_metadata_cache = {}
_cache_timestamps = {}

# Custom Jinja2 filters
def strftime_filter(value, format_str):
    """Custom Jinja2 filter for formatting timestamps"""
    if isinstance(value, str):
        try:
            # Parse ISO format timestamp
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime(format_str)
        except ValueError:
            return value
    elif isinstance(value, datetime):
        return value.strftime(format_str)
    return value

app = FastAPI(title="LLM Metrics Dashboard", description="Agentic Evaluation System Metrics Viewer")

# Get the directory where this app.py file is located
APP_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
templates.env.filters["strftime"] = strftime_filter

# Add urlencode filter for URL encoding in templates
def urlencode_filter(value):
    """URL encode filter for Jinja2"""
    import urllib.parse
    if isinstance(value, str):
        return urllib.parse.quote(value)
    return value

templates.env.filters["urlencode"] = urlencode_filter

def extract_basic_metadata(file_path: str) -> Dict[str, Any]:
    """Extract basic metadata from trace file without full parsing - FAST"""
    # Check cache first
    file_stat = Path(file_path).stat()
    cache_key = file_path
    
    if (cache_key in _metadata_cache and 
        cache_key in _cache_timestamps and 
        _cache_timestamps[cache_key] >= file_stat.st_mtime):
        return _metadata_cache[cache_key]
    
    try:
        user_request = 'Unknown request'
        context_mode = 'none'
        start_time = None
        end_time = None
        total_duration = 0
        total_calls = 0
        total_tokens = 0
        
        # Only read first few lines and last few lines for basic info
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Count total lines for approximate call count
        total_calls = len([line for line in lines if line.strip()])
        
        # Parse first few lines for task start info
        for line in lines[:10]:  # Only check first 10 lines
            if not line.strip():
                continue
            try:
                event = json.loads(line.strip())
                if event.get('event_type') == 'task_started':
                    user_request = event.get('data', {}).get('user_request', 'Unknown request')
                    context_mode = event.get('data', {}).get('context_mode', 'none')
                    start_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    break
            except:
                continue
        
        # Parse last few lines for completion info
        for line in reversed(lines[-10:]):  # Only check last 10 lines
            if not line.strip():
                continue
            try:
                event = json.loads(line.strip())
                if event.get('event_type') == 'task_completed':
                    end_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    total_duration = event.get('data', {}).get('duration_seconds', 0)
                    break
            except:
                continue
        
        # Quick token estimation from a sample of LLM responses (not all)
        llm_response_count = 0
        token_sample = 0
        for line in lines[::max(1, len(lines)//20)]:  # Sample every 20th line
            if not line.strip():
                continue
            try:
                event = json.loads(line.strip())
                if event.get('event_type') == 'llm_response':
                    llm_response_count += 1
                    usage = event.get('data', {}).get('response', {}).get('usage', {})
                    token_sample += usage.get('total_tokens', 0)
                    if llm_response_count >= 3:  # Only sample first 3 LLM responses
                        break
            except:
                continue
        
        # Estimate total tokens based on sample
        if llm_response_count > 0:
            avg_tokens_per_response = token_sample / llm_response_count
            estimated_llm_responses = len([l for l in lines if 'llm_response' in l])
            total_tokens = int(avg_tokens_per_response * estimated_llm_responses)
        
        result = {
            'user_request': user_request,
            'context_mode': context_mode,
            'start_time': start_time,
            'end_time': end_time,
            'total_duration': total_duration,
            'total_calls': total_calls,
            'total_tokens': total_tokens,
            'models_used': ['estimated'],  # We'll get actual model on full parse
            'avg_duration_per_call': total_duration / max(1, total_calls)
        }
        
        # Cache the result
        _metadata_cache[cache_key] = result
        _cache_timestamps[cache_key] = file_stat.st_mtime
        
        return result
    except Exception as e:
        return {
            'user_request': 'Parse error',
            'context_mode': 'unknown',
            'start_time': None,
            'end_time': None,
            'total_duration': 0,
            'total_calls': 0,
            'total_tokens': 0,
            'models_used': ['unknown'],
            'avg_duration_per_call': 0,
            'error': str(e)
        }

def discover_metrics_files() -> List[Dict[str, Any]]:
    """Discover all trace files in the tmp directory - OPTIMIZED FOR SPEED"""
    metrics_files = []

    # Look for trace files in the tmp directory
    pattern = str(METRICS_DIR / "trace_*.jsonl")

    for file_path in glob.glob(pattern):
        path_obj = Path(file_path)
        try:
            # Use fast metadata extraction instead of full parsing
            basic_metadata = extract_basic_metadata(file_path)

            metrics_files.append({
                'filename': path_obj.name,
                'full_path': file_path,
                'total_calls': basic_metadata['total_calls'],
                'total_duration': basic_metadata['total_duration'],
                'total_tokens': basic_metadata['total_tokens'],
                'avg_duration': basic_metadata['avg_duration_per_call'],
                'models_used': basic_metadata['models_used'],
                'start_time': basic_metadata['start_time'],
                'end_time': basic_metadata['end_time'],
                'date_created': path_obj.stat().st_mtime,
                'context_mode': basic_metadata['context_mode'],
                'user_request': basic_metadata['user_request']
            })
        except Exception as e:
            # If parsing fails, still include the file with basic info
            metrics_files.append({
                'filename': path_obj.name,
                'full_path': file_path,
                'total_calls': 0,
                'total_duration': 0,
                'total_tokens': 0,
                'avg_duration': 0,
                'models_used': ['unknown'],
                'start_time': None,
                'end_time': None,
                'date_created': path_obj.stat().st_mtime,
                'context_mode': 'unknown',
                'user_request': 'unknown',
                'error': str(e)
            })

    # Sort by creation date (newest first)
    metrics_files.sort(key=lambda x: x['date_created'], reverse=True)

    return metrics_files

def parse_trace_file(file_path: str) -> 'TraceMetricsFile':
    """Parse a trace JSONL file and extract metrics"""
    try:
        events = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        
        # Extract key information from events
        user_request = None
        context_mode = None
        start_time = None
        end_time = None
        llm_responses = []
        tool_requests = []
        tool_responses = {}
        total_duration = 0
        
        # First pass: collect all events
        for event in events:
            event_type = event.get('event_type')
            
            if event_type == 'task_started':
                user_request = event['data'].get('user_request', '')
                context_mode = event['data'].get('context_mode', 'none')
                start_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            
            elif event_type == 'task_completed':
                end_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                total_duration = event['data'].get('duration_seconds', 0)
            
            elif event_type == 'llm_response':
                response_data = event['data'].get('response')
                if response_data:
                    # Parse the LLM's response to extract action details
                    content = response_data['choices'][0]['message']['content']
                    thought = ''
                    action = None
                    final_answer = None
                    
                    # Try parsing as JSON first (old format)
                    try:
                        llm_content = json.loads(content)
                        thought = llm_content.get('thought', '')
                        action = llm_content.get('action')
                        final_answer = llm_content.get('final_answer')
                    except:
                        # New format: content might be plain text reasoning
                        if content and content.strip():
                            thought = content
                    
                    # If thought is empty and we have tool calls, create a description
                    if not thought and 'tool_calls' in response_data['choices'][0]['message']:
                        tool_calls = response_data['choices'][0]['message']['tool_calls']
                        if tool_calls:
                            tool_names = [tc['function']['name'] for tc in tool_calls]
                            thought = f"Executing tool{'s' if len(tool_names) > 1 else ''}: {', '.join(tool_names)}"
                    
                    llm_responses.append({
                        'timestamp': event['timestamp'],
                        'duration_seconds': event['data'].get('duration_seconds', 0),
                        'model': response_data.get('model', 'unknown'),
                        'usage': response_data.get('usage', {}),
                        'thought': thought,
                        'action': action,
                        'final_answer': final_answer
                    })
            
            elif event_type == 'tool_request':
                tool_requests.append({
                    'timestamp': event['timestamp'],
                    'tool_name': event['data'].get('tool_name', ''),
                    'params': event['data'].get('params', {})
                })
            
            elif event_type == 'tool_response':
                # Store tool responses by timestamp for matching
                tool_responses[event['timestamp']] = {
                    'tool_name': event['data'].get('tool_name', ''),
                    'output': event['data'].get('output', ''),
                    'duration_seconds': event['data'].get('duration_seconds', 0)
                }
        
        # Group events into logical cycles
        grouped_events = []
        task_step = 0  # Step counter within current task
        
        # Track current cycle events
        current_cycle = []
        llm_request_data = None
        context_data = None
        in_task = False  # Track if we're currently in a task
        
        for event in events:
            event_type = event.get('event_type')
            timestamp = event.get('timestamp', '')
            data = event.get('data', {})
            
            if event_type == 'task_started':
                task_step = 0  # Reset step counter for new task
                in_task = True
                grouped_events.append({
                    'type': 'task_start',
                    'step': task_step,
                    'timestamp': timestamp,
                    'user_request': data.get('user_request', ''),
                    'events': [event]
                })
                
            elif event_type == 'context_build_completed':
                context_data = {
                    'strategy': data.get('strategy', ''),
                    'context_length': data.get('context_length', 0),
                    'duration': data.get('duration_seconds', 0),
                    'context': data.get('context', '')  # Store the actual context
                }
                # Add to the last task_start if exists
                if grouped_events and grouped_events[-1]['type'] == 'task_start':
                    grouped_events[-1]['context'] = context_data
                    grouped_events[-1]['events'].append(event)
                
            elif event_type == 'llm_request':
                # Start a new cycle
                if current_cycle:
                    # Finish previous cycle if exists
                    task_step += 1
                    grouped_events.append({
                        'type': 'react_cycle',
                        'step': task_step,
                        'events': current_cycle
                    })
                current_cycle = [event]
                llm_request_data = data
                
            elif event_type == 'llm_response' and current_cycle:
                current_cycle.append(event)
                
            elif event_type == 'tool_request' and current_cycle:
                current_cycle.append(event)
                
            elif event_type == 'tool_response' and current_cycle:
                current_cycle.append(event)
                # Complete the cycle
                task_step += 1
                grouped_events.append({
                    'type': 'react_cycle',
                    'step': task_step,
                    'events': current_cycle,
                    'timestamp': current_cycle[0].get('timestamp', '')
                })
                current_cycle = []
                
            elif event_type == 'task_completed':
                # Finish any pending cycle
                if current_cycle:
                    task_step += 1
                    grouped_events.append({
                        'type': 'react_cycle',
                        'step': task_step,
                        'events': current_cycle
                    })
                    current_cycle = []
                
                grouped_events.append({
                    'type': 'task_complete',
                    'step': 'Final',
                    'timestamp': timestamp,
                    'duration': data.get('duration_seconds', 0),
                    'result': data.get('result', ''),
                    'events': [event]
                })
                in_task = False
        
        # Process grouped events into display format
        tool_calls = []
        
        for group in grouped_events:
            if group['type'] == 'task_start':
                tool_calls.append({
                    'type': 'task_start',
                    'step': group['step'],
                    'timestamp': group['timestamp'],
                    'user_request': group['user_request'],
                    'context': group.get('context', None)
                })
                
            elif group['type'] == 'react_cycle':
                cycle_data = {
                    'type': 'react_cycle',
                    'step': group['step'],
                    'timestamp': group.get('timestamp', ''),
                    'llm_request': None,
                    'llm_response': None,
                    'tool_request': None,
                    'tool_response': None
                }
                
                for event in group['events']:
                    event_type = event.get('event_type')
                    data = event.get('data', {})
                    
                    if event_type == 'llm_request':
                        messages = data.get('messages', [])
                        cycle_data['llm_request'] = {
                            'messages': messages,
                            'message_count': len(messages)
                        }
                        
                    elif event_type == 'llm_response':
                        response_data = data.get('response', {})
                        if response_data:
                            model = response_data.get('model', 'unknown')
                            usage = response_data.get('usage', {})
                            duration = data.get('duration_seconds', 0)
                            
                            # Parse the LLM's response content
                            content = response_data['choices'][0]['message']['content']
                            thought = ''
                            action = None
                            final_answer = None
                            
                            # First check if content is JSON (old format)
                            try:
                                llm_content = json.loads(content)
                                thought = llm_content.get('thought', '')
                                action = llm_content.get('action')
                                final_answer = llm_content.get('final_answer')
                            except:
                                # New format: content might be plain text reasoning or empty
                                # If content is not empty and not JSON, it's the reasoning
                                if content and content.strip():
                                    thought = content
                                llm_content = {}
                            
                            # If thought is empty and we have tool calls in the response, create a description
                            if not thought and 'tool_calls' in response_data['choices'][0]['message']:
                                tool_calls = response_data['choices'][0]['message']['tool_calls']
                                if tool_calls:
                                    tool_names = [tc['function']['name'] for tc in tool_calls]
                                    thought = f"Executing tool{'s' if len(tool_names) > 1 else ''}: {', '.join(tool_names)}"
                            
                            cycle_data['llm_response'] = {
                                'model': model,
                                'usage': usage,
                                'duration': duration,
                                'thought': thought,
                                'action': action,
                                'final_answer': final_answer,
                                'raw_response': response_data
                            }
                            
                    elif event_type == 'tool_request':
                        tool_params = data.get('params', {})
                        cycle_data['tool_request'] = {
                            'tool_name': data.get('tool_name', ''),
                            'params': tool_params
                        }
                        # Extract reasoning from tool parameters if available
                        if 'reasoning' in tool_params:
                            # Store the reasoning - we'll use it if the LLM response didn't have content
                            cycle_data['tool_reasoning'] = tool_params['reasoning']
                        
                    elif event_type == 'tool_response':
                        cycle_data['tool_response'] = {
                            'tool_name': data.get('tool_name', ''),
                            'output': data.get('output', ''),
                            'duration': data.get('duration_seconds', 0)
                        }
                
                # If we have tool_reasoning but no thought in llm_response, use the tool_reasoning
                if cycle_data.get('tool_reasoning') and cycle_data.get('llm_response'):
                    if not cycle_data['llm_response'].get('thought'):
                        cycle_data['llm_response']['thought'] = cycle_data['tool_reasoning']
                
                tool_calls.append(cycle_data)
                
            elif group['type'] == 'task_complete':
                tool_calls.append({
                    'type': 'task_complete',
                    'step': group['step'],
                    'timestamp': group['timestamp'],
                    'duration': group['duration'],
                    'result': group['result']
                })
        
        # Calculate metrics
        total_llm_calls = len(llm_responses)
        total_tokens = sum(resp['usage'].get('total_tokens', 0) for resp in llm_responses)
        total_llm_duration = sum(resp['duration_seconds'] for resp in llm_responses)
        avg_duration = total_llm_duration / total_llm_calls if total_llm_calls > 0 else 0
        models_used = list(set(resp['model'] for resp in llm_responses))
        
        # Create metrics compatible with existing structure
        metrics = []
        for i, resp in enumerate(llm_responses):
            choice_content = json.dumps({
                'thought': resp.get('thought', ''),
                'action': resp.get('action'),
                'final_answer': resp.get('final_answer')
            })
            
            metrics.append(LLMMetrics(
                api_call_id=i + 1,
                timestamp=resp['timestamp'],
                duration_seconds=resp['duration_seconds'],
                model=resp['model'],
                reasoning_effort='unknown',
                verbosity='unknown',
                workflow_context=WorkflowContext(
                    user_request=user_request or '',
                    current_step=i + 1,
                    total_steps_completed=len(llm_responses)
                ),
                usage=Usage(**resp['usage']) if resp['usage'] else Usage(
                    completion_tokens=0,
                    prompt_tokens=0,
                    total_tokens=0
                ),
                full_response=FullResponse(
                    id='trace',
                    object='chat.completion',
                    created=0,
                    model=resp['model'],
                    choices=[Choice(
                        index=0,
                        message=Message(role='assistant', content=choice_content),
                        finish_reason='stop'
                    )],
                    usage=Usage(**resp['usage']) if resp['usage'] else Usage(
                        completion_tokens=0,
                        prompt_tokens=0,
                        total_tokens=0
                    )
                )
            ))
        
        # Create a TraceMetricsFile object with additional fields and tool_calls
        class TraceMetricsFile(MetricsFile):
            context_mode: str = 'none'
            user_request: str = ''
            tool_calls: List[Dict[str, Any]] = []
        
        return TraceMetricsFile(
            metrics=metrics,
            total_calls=len(events),
            total_duration=total_duration,
            total_tokens=total_tokens,
            avg_duration_per_call=avg_duration,
            models_used=models_used or ['unknown'],
            start_time=start_time,
            end_time=end_time,
            context_mode=context_mode or 'none',
            user_request=user_request or '',
            tool_calls=tool_calls
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing trace file: {str(e)}")

def parse_metrics_file(file_path: str) -> MetricsFile:
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        metrics = []
        
        # First try to parse as a JSON array (new format)
        try:
            data = json.loads(content)
            if isinstance(data, list):
                # New format - array of metrics
                for item in data:
                    if 'api_call_id' in item:
                        metrics.append(LLMMetrics(**item))
            elif isinstance(data, dict) and 'api_call_id' in data:
                # Single metric object
                metrics.append(LLMMetrics(**data))
        except json.JSONDecodeError:
            # Fall back to old format parsing
            # Split content by the separator lines to get individual JSON blocks
            separator_pattern = r'-{80,}'
            json_blocks = re.split(separator_pattern, content)

            for block in json_blocks:
                block = block.strip()
                if not block:
                    continue

                # Look for JSON objects within the block
                json_start = block.find('{')
                if json_start == -1:
                    continue

                # Extract the JSON part
                json_content = block[json_start:]

                try:
                    # Clean up any trailing content after the JSON
                    json_end = json_content.rfind('}')
                    if json_end != -1:
                        json_content = json_content[:json_end + 1]

                    data = json.loads(json_content)
                    if 'api_call_id' in data:  # Only process metrics entries
                        metrics.append(LLMMetrics(**data))
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Warning: Could not parse JSON block: {e}")
                    # Try to fix common JSON issues
                    try:
                        # Remove any trailing commas before closing braces
                        json_content = re.sub(r',(\s*[}\]])', r'\1', json_content)
                        data = json.loads(json_content)
                        if 'api_call_id' in data:
                            metrics.append(LLMMetrics(**data))
                    except:
                        continue

        if not metrics:
            raise ValueError("No valid metrics found in file")

        # Calculate summary statistics
        total_calls = len(metrics)
        total_duration = sum(m.duration_seconds for m in metrics)
        total_tokens = sum(m.usage.total_tokens for m in metrics)
        avg_duration = total_duration / total_calls if total_calls > 0 else 0

        # Get unique models used
        models_used = list(set(m.model for m in metrics))

        # Parse timestamps
        timestamps = []
        for m in metrics:
            try:
                # Handle different timestamp formats
                timestamp_str = m.timestamp.replace('Z', '+00:00')
                if '.' in timestamp_str:
                    # Parse with microseconds
                    timestamps.append(datetime.fromisoformat(timestamp_str))
                else:
                    # Parse without microseconds
                    timestamps.append(datetime.fromisoformat(timestamp_str))
            except ValueError:
                continue

        start_time = min(timestamps) if timestamps else None
        end_time = max(timestamps) if timestamps else None

        return MetricsFile(
            metrics=metrics,
            total_calls=total_calls,
            total_duration=total_duration,
            total_tokens=total_tokens,
            avg_duration_per_call=avg_duration,
            models_used=models_used,
            start_time=start_time,
            end_time=end_time
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Metrics file not found: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing metrics file: {str(e)}")

def extract_tool_calls(metrics: List[LLMMetrics]) -> List[Dict[str, Any]]:
    tool_calls = []
    for metric in metrics:
        if metric.full_response.choices:
            content = metric.full_response.choices[0].message.content.strip()

            # Try to extract tool information from the content
            tool_call = {
                'step': metric.workflow_context.current_step,
                'timestamp': metric.timestamp,
                'duration': metric.duration_seconds,
                'tokens': metric.usage.total_tokens,
                'model': metric.model,
                'reasoning_effort': metric.reasoning_effort,
                'verbosity': metric.verbosity,
                'raw_content': content  # Keep original content for debugging
            }

            try:
                # Parse the content as JSON - it should always be valid JSON now
                tool_data = json.loads(content)
                
                if isinstance(tool_data, dict):
                    if 'tool_name' in tool_data:
                        # Standard tool call
                        tool_call.update({
                            'tool_name': tool_data['tool_name'],
                            'params': tool_data.get('params', {}),
                            'description': tool_data.get('description', ''),
                            'reasoning': tool_data.get('reasoning', '')
                        })
                    elif 'stop' in tool_data:
                        # Stop command
                        tool_call.update({
                            'tool_name': 'stop',
                            'params': {},
                            'description': tool_data.get('reason', ''),
                            'reasoning': ''
                        })
                    else:
                        # Unknown format but valid JSON
                        tool_call.update({
                            'tool_name': 'unknown',
                            'params': tool_data,
                            'description': 'Unknown tool format',
                            'parse_error': True
                        })
                else:
                    # Not a dict
                    tool_call.update({
                        'tool_name': 'unknown',
                        'params': {},
                        'description': f'Unexpected data type: {type(tool_data).__name__}',
                        'parse_error': True
                    })

            except (json.JSONDecodeError, ValueError) as e:
                # JSON parsing failed - this shouldn't happen with the new format
                # but let's handle it gracefully
                tool_call.update({
                    'tool_name': 'error',
                    'params': {},
                    'description': f'JSON parse error: {str(e)}',
                    'parse_error': True
                })

            tool_calls.append(tool_call)

    return tool_calls

@app.get("/")
async def dashboard(request: Request, file: str = None):
    # Get list of available metrics files
    available_files = discover_metrics_files()

    # If no file specified, use the most recent one
    if not file and available_files:
        file = available_files[0]['full_path']

    # If still no file, show empty dashboard
    if not file:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "metrics": None,
            "tool_calls": [],
            "file_path": None,
            "available_files": available_files,
            "selected_file": None
        })

    try:
        # Try parsing as trace file first, then fall back to old format
        metrics_data = None
        tool_calls = []
        
        try:
            metrics_data = parse_trace_file(file)
            # Use tool_calls directly from the parsed trace file
            tool_calls = getattr(metrics_data, 'tool_calls', [])
            if not tool_calls:
                # Fall back to extracting from metrics
                tool_calls = extract_tool_calls(metrics_data.metrics)
        except:
            # Try old format
            metrics_data = parse_metrics_file(file)
            tool_calls = extract_tool_calls(metrics_data.metrics)

        # Find the selected file info
        selected_file = next((f for f in available_files if f['full_path'] == file), None)

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "metrics": metrics_data,
            "tool_calls": tool_calls,
            "file_path": file,
            "available_files": available_files,
            "selected_file": selected_file
        })
    except Exception as e:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "metrics": None,
            "tool_calls": [],
            "file_path": file,
            "available_files": available_files,
            "selected_file": None,
            "error": str(e)
        })

@app.get("/api/files")
async def get_available_files():
    """Get list of available metrics files"""
    return discover_metrics_files()

@app.get("/api/metrics")
async def get_metrics(file: str = None):
    if not file:
        available_files = discover_metrics_files()
        if available_files:
            file = available_files[0]['full_path']
        else:
            raise HTTPException(status_code=404, detail="No metrics files found")

    return parse_metrics_file(file)

@app.get("/api/tool-calls")
async def get_tool_calls(file: str = None):
    if not file:
        available_files = discover_metrics_files()
        if available_files:
            file = available_files[0]['full_path']
        else:
            raise HTTPException(status_code=404, detail="No metrics files found")

    metrics_data = parse_metrics_file(file)
    return extract_tool_calls(metrics_data.metrics)

@app.get("/api/compare")
async def compare_files(files: str = None):
    """Compare multiple metrics files"""
    if not files:
        return {"error": "No files specified for comparison"}

    file_list = files.split(",")
    comparison_data = []

    for file_path in file_list:
        file_path = file_path.strip()
        if not Path(file_path).is_absolute():
            file_path = str(METRICS_DIR / file_path)

        try:
            metrics_data = parse_metrics_file(file_path)
            comparison_data.append({
                "filename": Path(file_path).name,
                "total_calls": metrics_data.total_calls,
                "total_duration": metrics_data.total_duration,
                "total_tokens": metrics_data.total_tokens,
                "avg_duration": metrics_data.avg_duration_per_call,
                "models_used": metrics_data.models_used
            })
        except Exception as e:
            comparison_data.append({
                "filename": Path(file_path).name,
                "error": str(e)
            })

    return {"comparison": comparison_data}


# ChromaDB Routes
@app.get("/chromadb")
async def chromadb_explorer(request: Request, query: Optional[str] = None, limit: int = 20):
    """Explore the ChromaDB code index"""
    if not CHROMADB_AVAILABLE:
        return templates.TemplateResponse("chromadb.html", {
            "request": request,
            "error": "ChromaDB is not available. Please install chromadb package.",
            "chunks": [],
            "query": query,
            "total_chunks": 0
        })
    
    try:
        # Initialize vector store
        embedding_function = get_embedding_function()
        vector_store = VectorStore(
            db_path=str(DB_DIR),
            collection_name="codebase",
            embedding_function=embedding_function
        )
        
        # Get collection info
        collection = vector_store.collection
        total_chunks = collection.count()
        
        chunks = []
        query_metadata = {}
        if query:
            # Perform search with detailed results
            detailed_results = vector_store.query_with_scores(query, top_k=limit)
            
            # Extract query metadata for evaluation
            if detailed_results:
                query_metadata = {
                    'query_text': query,
                    'total_results': len(detailed_results),
                    'avg_similarity': sum(r['similarity_score'] for r in detailed_results if r['similarity_score']) / len([r for r in detailed_results if r['similarity_score']]) if detailed_results else 0,
                    'min_similarity': min(r['similarity_score'] for r in detailed_results if r['similarity_score']) if detailed_results else 0,
                    'max_similarity': max(r['similarity_score'] for r in detailed_results if r['similarity_score']) if detailed_results else 0,
                    'embedding_model': AppSettings.EMBEDDING_MODEL
                }
            
            chunks = [{
                "id": result['chunk'].id,
                "file_path": result['chunk'].file_path,
                "symbol_name": result['chunk'].symbol_name,
                "symbol_type": result['chunk'].symbol_type,
                "content": result['chunk'].content,
                "content_preview": result['chunk'].content[:200] + "..." if len(result['chunk'].content) > 200 else result['chunk'].content,
                "summary": result['summary'],
                "similarity_score": result['similarity_score'],
                "distance": result['distance'],
                "rank": result['rank'],
                "content_hash": result['chunk'].content_hash
            } for result in detailed_results]
        else:
            # Get all chunks (limited)
            results = collection.get(limit=limit)
            if results['ids']:
                for i, chunk_id in enumerate(results['ids']):
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    document = results['documents'][i] if results['documents'] else ""
                    
                    # Extract content from document (remove summary)
                    summary = metadata.get('summary', '')
                    content = document.replace(summary, '').strip()
                    if content.startswith('\n\n'):
                        content = content[2:]
                    
                    chunks.append({
                        "id": chunk_id,
                        "file_path": metadata.get('file_path', 'unknown'),
                        "symbol_name": metadata.get('symbol_name', 'unknown'),
                        "symbol_type": metadata.get('symbol_type', 'unknown'),
                        "content": content,
                        "content_preview": content[:200] + "..." if len(content) > 200 else content,
                        "summary": summary
                    })
        
        return templates.TemplateResponse("chromadb.html", {
            "request": request,
            "chunks": chunks,
            "query": query,
            "total_chunks": total_chunks,
            "limit": limit,
            "db_path": str(DB_DIR),
            "query_metadata": query_metadata
        })
        
    except Exception as e:
        return templates.TemplateResponse("chromadb.html", {
            "request": request,
            "error": f"Error accessing ChromaDB: {str(e)}",
            "chunks": [],
            "query": query,
            "total_chunks": 0
        })


@app.get("/api/chromadb/search")
async def chromadb_search(query: str, limit: int = Query(default=10, le=100)):
    """API endpoint for ChromaDB search"""
    if not CHROMADB_AVAILABLE:
        raise HTTPException(status_code=503, detail="ChromaDB is not available")
    
    try:
        embedding_function = get_embedding_function()
        vector_store = VectorStore(
            db_path=str(DB_DIR),
            collection_name="codebase",
            embedding_function=embedding_function
        )
        
        code_chunks = vector_store.query_chunks_only(query, top_k=limit)
        
        return {
            "query": query,
            "results": [{
                "id": chunk.id,
                "file_path": chunk.file_path,
                "symbol_name": chunk.symbol_name,
                "symbol_type": chunk.symbol_type,
                "content": chunk.content
            } for chunk in code_chunks]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.get("/api/chromadb/stats")
async def chromadb_stats():
    """Get ChromaDB statistics"""
    if not CHROMADB_AVAILABLE:
        raise HTTPException(status_code=503, detail="ChromaDB is not available")
    
    try:
        embedding_function = get_embedding_function()
        vector_store = VectorStore(
            db_path=str(DB_DIR),
            collection_name="codebase",
            embedding_function=embedding_function
        )
        
        collection = vector_store.collection
        total_chunks = collection.count()
        
        # Get sample of chunks to analyze
        sample = collection.get(limit=1000)
        
        file_count = len(set(m.get('file_path', '') for m in sample['metadatas'])) if sample['metadatas'] else 0
        
        symbol_types = {}
        if sample['metadatas']:
            for metadata in sample['metadatas']:
                sym_type = metadata.get('symbol_type', 'unknown')
                symbol_types[sym_type] = symbol_types.get(sym_type, 0) + 1
        
        return {
            "total_chunks": total_chunks,
            "approximate_file_count": file_count,
            "symbol_types": symbol_types,
            "db_path": str(DB_DIR)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")
