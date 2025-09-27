#!/usr/bin/env python3
import sys
import os

# Get the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Add it to Python path
sys.path.insert(0, script_dir)

# Now we can import from src
from src.commands.google_search import Command as GoogleSearchCommand
from src.commands.read_website import Command as ReadWebsiteCommand

def test_google_search():
    print("Testing Google Search Command...")
    print("="*50)
    cmd = GoogleSearchCommand()
    result = cmd.execute({
        "query": "playwright stealth test"
    })
    print(result)
    print("\n" + "="*50 + "\n")

def test_read_website():
    print("Testing Read Website Command...")
    print("="*50)
    cmd = ReadWebsiteCommand()
    result = cmd.execute({
        "url": "https://www.pgatour.com/player/39335/kevin-roy"
    })
    print(result)
    print("\n" + "="*50 + "\n")

def test_read_website_no_file():
    print("Testing Read Website (auto-save to /tmp/html-results/)...")
    print("="*50)
    cmd = ReadWebsiteCommand()
    result = cmd.execute({
        "url": "https://httpbin.org/html"
    })
    print(result)
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test browser automation commands")
    parser.add_argument("--google", action="store_true", help="Test Google search")
    parser.add_argument("--read", action="store_true", help="Test read website with file output")
    parser.add_argument("--read-preview", action="store_true", help="Test read website with preview")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    args = parser.parse_args()
    
    if args.all:
        test_google_search()
        test_read_website()
        test_read_website_no_file()
    elif args.google:
        test_google_search()
    elif args.read:
        test_read_website()
    elif args.read_preview:
        test_read_website_no_file()
    else:
        print("Usage: python test_browser_commands.py [--google|--read|--read-preview|--all]")
        print("\nExamples:")
        print("  python test_browser_commands.py --google        # Test Google search")
        print("  python test_browser_commands.py --read          # Test read website with file save")
        print("  python test_browser_commands.py --all           # Run all tests")
