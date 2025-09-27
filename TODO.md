# TODO

## 🧠 AI Learning & Memory

### Directory Embedding Tool
- **File**: `src/commands/embed_directory.py`
- **Purpose**: Enable AI to autonomously learn entire code folders
- **Features**:
  - Embed directories with metadata from folder structure
  - Tag embeddings with folder paths for context
  - Allow AI to build its own knowledge base

## 🌐 Web Browsing Capabilities

### Playwright-based Web Tools
- **Implementation**: Playwright wrapper for web interaction
- **Tools**:
  1. **Search Web** (`src/commands/search_web.py`)
     - Execute web searches
     - Return relevant results
  2. **Load URL** (`src/commands/load_url.py`)
     - Load and parse specific URLs
     - Extract content for AI processing

## ⚠️ Security Considerations

### Dangerous Command Handling
- **Note**: We don't need to prevent dangerous commands
- **Current State**:
  - `src/commands/run_command.py` - No protection (by design)
  - `src/ai_shell/shell.py` - Has dangerous command detection (for comparison)

## 🧬 Meta-Agent Architecture

### "Brain" Agent Design
- **Concept**: Higher-level agent that observes and adjusts the basic agent
- **Capabilities**:
  - Monitor task performance in real-time
  - Dynamically adjust strategy based on progress
  - Modify prompts and context as needed
  - Act as a meta-cognitive layer above the ReAct loop

## 🔍 Security Research Tools

### Exploit Database Search Tool
- **File**: `src/commands/exploitdb_search.py`
- **Purpose**: Search exploit-db.com for vulnerabilities and exploits
- **Features**:
  - Search by software name, version, CVE
  - Return exploit details and references
  - Parse exploit metadata

### Google Dork Search Tool
- **File**: `src/commands/google_dork.py`
- **Purpose**: Execute Google dork queries for security research
- **Features**:
  - Support advanced Google operators (site:, filetype:, intitle:, etc.)
  - Handle authentication/cookies like google_search tool
  - Return targeted results for security research