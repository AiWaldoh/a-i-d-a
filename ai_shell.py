#!/usr/bin/env python3

import sys
import os
import asyncio
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai_shell import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Shell - Intelligent command line interface")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    if args.debug:
        os.environ['AI_SHELL_DEBUG'] = 'true'
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
