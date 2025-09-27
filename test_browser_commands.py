#!/usr/bin/env python3
import sys
import os

# Get the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Add it to Python path
sys.path.insert(0, script_dir)

# Now we can import from src
from src.commands.google_search import Command as GoogleSearchCommand
from src.commands.fetch_webpage import Command as FetchWebpageCommand

def test_google_search():
    print("Testing Google Search Command...")
    print("="*50)
    cmd = GoogleSearchCommand()
    result = cmd.execute({
        "query": "playwright stealth test",
        "num_results": 15
    })
    print(result)
    print("\n" + "="*50 + "\n")

def test_webpage_fetcher():
    print("Testing Webpage Fetcher Command...")
    print("="*50)
    cmd = FetchWebpageCommand()
    result = cmd.execute({
        "url": "https://www.politico.com/news/2025/09/27/donald-trump-portland-military-protest-00583423",
        "headless": False
    })
    print(result)
    print("\n" + "="*50 + "\n")

def test_webpage_fetcher_no_file():
    print("Testing Webpage Fetcher (auto-save to /tmp/html-results/)...")
    print("="*50)
    cmd = FetchWebpageCommand()
    result = cmd.execute({
        "url": "https://httpbin.org/html",
        "headless": True
    })
    print(result)
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test browser automation commands")
    parser.add_argument("--google", action="store_true", help="Test Google search")
    parser.add_argument("--fetch", action="store_true", help="Test webpage fetcher with file output")
    parser.add_argument("--fetch-preview", action="store_true", help="Test webpage fetcher with preview")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    args = parser.parse_args()
    
    if args.all:
        test_google_search()
        test_webpage_fetcher()
        test_webpage_fetcher_no_file()
    elif args.google:
        test_google_search()
    elif args.fetch:
        test_webpage_fetcher()
    elif args.fetch_preview:
        test_webpage_fetcher_no_file()
    else:
        print("Usage: python test_browser_commands.py [--google|--fetch|--fetch-preview|--all]")
        print("\nExamples:")
        print("  python test_browser_commands.py --google     # Test Google search")
        print("  python test_browser_commands.py --fetch      # Test webpage fetch with file save")
        print("  python test_browser_commands.py --all        # Run all tests")
