# AIDA Deployment Guide

## Zipapp Bundle (Recommended for HTB/CTF)

The AIDA application has been packaged as a single executable Python zipapp (`aida.pyz`) for easy deployment.

### What's Included

- ✅ All Python dependencies bundled
- ✅ Complete AIDA source code
- ✅ Configuration files (prompts.yaml, tools.yaml, config.yaml)
- ✅ Self-contained executable (25.3 MB)

### Requirements on Target System

- Python 3.7+ (most Linux systems have this)
- Internet connection (for missing dependencies like Playwright)

### Deployment Steps

1. **Transfer the bundle**:
   ```bash
   # From your HTTP server
   wget http://your-server/aida.pyz
   chmod +x aida.pyz
   ```

2. **Create .env file** (in same directory as aida.pyz):
   ```bash
   cat > .env << 'EOF'
   OPENROUTER_API_KEY=your_key_here
   # or
   OPENAI_API_KEY=your_key_here
   EOF
   ```

3. **Run AIDA**:
   ```bash
   # Interactive menu
   ./aida.pyz
   
   # Direct modes
   ./aida.pyz shell              # AI Shell
   ./aida.pyz web                # Web interface  
   ./aida.pyz index              # Index codebase
   ./aida.pyz "your prompt"      # Direct agent
   ```

### First Run

On first execution, AIDA will automatically:
- Install any missing dependencies (like Playwright)
- Download Playwright browser binaries if needed
- Set up the environment

### Usage Examples

```bash
# Quick AI assistance
./aida.pyz "find all python files in this directory"

# Start AI Shell for interactive use
./aida.pyz shell

# Launch web interface (runs on http://localhost:8000)
./aida.pyz web

# Index current directory for semantic search
./aida.pyz index
```

### Troubleshooting

**Permission denied**: 
```bash
chmod +x aida.pyz
```

**Missing dependencies**: The app will auto-install them, but you can manually install:
```bash
pip3 install playwright --user
python3 -m playwright install
```

**No .env file warning**: Create a `.env` file with your API keys in the same directory as `aida.pyz`.

### File Structure After Deployment

```
your-directory/
├── aida.pyz          # The executable bundle
├── .env              # Your API keys (create this)
└── db/               # Created automatically for ChromaDB
```

## Building Your Own Bundle

To rebuild the zipapp bundle:

```bash
# From the AIDA source directory
python3 build_zipapp.py
```

This will create a fresh `aida.pyz` with all current code and dependencies.
