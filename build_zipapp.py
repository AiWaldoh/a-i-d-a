#!/usr/bin/env python3
"""
Build script for creating AIDA zipapp bundle
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

def create_main_py():
    """Create the __main__.py entry point"""
    main_content = '''#!/usr/bin/env python3
import sys
import os
import subprocess
from pathlib import Path

def install_missing_deps():
    """Install any missing dependencies that couldn't be bundled"""
    missing_deps = []
    
    try:
        import playwright
    except ImportError:
        missing_deps.append('playwright')
    
    if missing_deps:
        print(f"Installing missing dependencies: {', '.join(missing_deps)}")
        for dep in missing_deps:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep, '--user'])
        
        if 'playwright' in missing_deps:
            print("Installing Playwright browsers...")
            subprocess.check_call([sys.executable, '-m', 'playwright', 'install'])

def setup_environment():
    """Set up the environment for AIDA"""
    # Detect if we're running from a zipapp
    # In a zipapp, __file__ will be something like '/path/to/app.pyz/__main__.py'
    is_zipapp = '.pyz' in __file__
    
    if is_zipapp:
        # Running from zipapp - extract the .pyz path
        zipapp_path = __file__.split('/__main__.py')[0]
        bundle_dir = os.path.dirname(zipapp_path)
        
        # Add the zipapp itself to Python path
        if zipapp_path not in sys.path:
            sys.path.insert(0, zipapp_path)
        
        # Check for .env file in the same directory as the zipapp
        env_file = os.path.join(bundle_dir, '.env')
        if not os.path.exists(env_file):
            print("WARNING: No .env file found!")
            print("Please create a .env file in the same directory as aida.pyz with your API keys:")
            print("  OPENROUTER_API_KEY=your_key_here")
            print("  # or")
            print("  OPENAI_API_KEY=your_key_here")
            print()
    else:
        # Running from directory (development mode)
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
        if bundle_dir not in sys.path:
            sys.path.insert(0, bundle_dir)
        
        # Change to bundle directory for relative imports in dev mode
        os.chdir(bundle_dir)
        
        # Check for .env file
        env_file = os.path.join(bundle_dir, '.env')
        if not os.path.exists(env_file):
            print("WARNING: No .env file found!")
            print("Please create a .env file with your API keys:")
            print("  OPENROUTER_API_KEY=your_key_here")
            print("  # or")
            print("  OPENAI_API_KEY=your_key_here")
            print()

def main():
    """Main entry point for AIDA zipapp"""
    setup_environment()
    install_missing_deps()
    
    # Parse command line arguments to determine which component to run
    if len(sys.argv) > 1:
        if sys.argv[1] == 'shell':
            # Run AI Shell
            from ai_shell import main as shell_main
            import asyncio
            asyncio.run(shell_main())
        elif sys.argv[1] == 'web':
            # Run web interface
            import subprocess
            subprocess.run([sys.executable, '-m', 'web_app.main'])
        elif sys.argv[1] == 'index':
            # Run indexer
            from indexer import main as indexer_main
            indexer_main()
        else:
            # Run traditional agent with the argument as prompt
            from main import main as agent_main
            sys.argv = ['main.py', '--prompt'] + sys.argv[1:]
            agent_main()
    else:
        # Interactive mode - show menu
        print("🤖 A.I.D.A - AI Development Assistant")
        print("====================================")
        print("1. Interactive Agent (default)")
        print("2. AI Shell")
        print("3. Web Interface")
        print("4. Index Codebase")
        print()
        
        choice = input("Select mode (1-4) or press Enter for interactive agent: ").strip()
        
        if choice == '2':
            from ai_shell import main as shell_main
            import asyncio
            asyncio.run(shell_main())
        elif choice == '3':
            import subprocess
            subprocess.run([sys.executable, '-m', 'web_app.main'])
        elif choice == '4':
            from indexer import main as indexer_main
            indexer_main()
        else:
            # Default to interactive agent
            from main import main as agent_main
            agent_main()

if __name__ == '__main__':
    main()
'''
    
    with open('aida_bundle/__main__.py', 'w') as f:
        f.write(main_content)
    print("✅ Created __main__.py entry point")

def clean_bundle_dir():
    """Remove existing bundle directory"""
    if os.path.exists('aida_bundle'):
        shutil.rmtree('aida_bundle')
    if os.path.exists('aida.pyz'):
        os.remove('aida.pyz')

def create_bundle_structure():
    """Create the bundle directory structure"""
    print("📁 Creating bundle structure...")
    os.makedirs('aida_bundle', exist_ok=True)
    
    # Copy source files
    shutil.copytree('src/', 'aida_bundle/src/')
    
    # Copy main files
    files_to_copy = [
        'main.py', 'ai_shell.py', 'indexer.py',
        'requirements.txt', 'config.yaml', 'prompts.yaml', 'tools.yaml'
    ]
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, 'aida_bundle/')
        else:
            print(f"⚠️  Warning: {file} not found")
    
    # Copy __main__.py from previous bundle if it exists
    if os.path.exists('aida_bundle/__main__.py'):
        print("✅ Using existing __main__.py")
    else:
        # Create the __main__.py file
        create_main_py()
    
    # Copy .env if it exists
    if os.path.exists('.env'):
        shutil.copy2('.env', 'aida_bundle/')
    else:
        print("⚠️  No .env file found - users will need to create one")

def install_dependencies():
    """Install dependencies into bundle"""
    print("📦 Installing dependencies...")
    os.chdir('aida_bundle')
    
    try:
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', 
            '-r', 'requirements.txt', 
            '--target', '.', 
            '--no-deps', 
            '--quiet'
        ], check=True)
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False
    
    os.chdir('..')
    return True

def create_zipapp():
    """Create the zipapp executable"""
    print("🗜️  Creating zipapp...")
    
    try:
        subprocess.run([
            sys.executable, '-m', 'zipapp', 
            'aida_bundle', 
            '-o', 'aida.pyz', 
            '-p', '/usr/bin/env python3',
            '-c'  # Compress
        ], check=True)
        
        # Make executable
        os.chmod('aida.pyz', 0o755)
        
        size_mb = os.path.getsize('aida.pyz') / 1024 / 1024
        print(f"✅ Created aida.pyz ({size_mb:.1f} MB)")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating zipapp: {e}")
        return False

def cleanup():
    """Clean up temporary files"""
    print("🧹 Cleaning up...")
    if os.path.exists('aida_bundle'):
        shutil.rmtree('aida_bundle')

def main():
    """Main build process"""
    print("🚀 Building AIDA zipapp bundle...")
    print("=" * 40)
    
    # Clean previous builds
    clean_bundle_dir()
    
    # Create bundle
    create_bundle_structure()
    
    # Install dependencies
    if not install_dependencies():
        cleanup()
        sys.exit(1)
    
    # Create zipapp
    if not create_zipapp():
        cleanup()
        sys.exit(1)
    
    # Cleanup
    cleanup()
    
    print("=" * 40)
    print("🎉 AIDA zipapp bundle created successfully!")
    print("\nUsage:")
    print("  ./aida.pyz                    # Interactive menu")
    print("  ./aida.pyz shell              # AI Shell mode")
    print("  ./aida.pyz web                # Web interface")
    print("  ./aida.pyz index              # Index codebase")
    print("  ./aida.pyz 'your prompt'      # Direct agent mode")
    print("\nDon't forget to create a .env file with your API keys!")

if __name__ == '__main__':
    main()
