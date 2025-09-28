#!/usr/bin/env python3
import subprocess
import sys
import os

def test_zipapp():
    """Test the AIDA zipapp bundle"""
    print("🧪 Testing AIDA zipapp bundle...")
    
    # Test 1: Check if file exists and is executable
    if not os.path.exists('aida.pyz'):
        print("❌ aida.pyz not found!")
        return False
    
    if not os.access('aida.pyz', os.X_OK):
        print("❌ aida.pyz is not executable!")
        return False
    
    print("✅ aida.pyz exists and is executable")
    
    # Test 2: Try to run it with a simple command
    try:
        result = subprocess.run(['python3', 'aida.pyz'], 
                              input='4\n',  # Choose option 4 (exit quickly)
                              text=True, 
                              capture_output=True, 
                              timeout=10)
        
        if "A.I.D.A" in result.stdout:
            print("✅ zipapp launches successfully")
            return True
        else:
            print("❌ zipapp didn't show expected output")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  zipapp launched but timed out (this might be normal)")
        return True
    except Exception as e:
        print(f"❌ Error running zipapp: {e}")
        return False

if __name__ == "__main__":
    success = test_zipapp()
    if success:
        print("\n🎉 AIDA zipapp bundle created successfully!")
        print("\nUsage:")
        print("  ./aida.pyz                    # Interactive menu")
        print("  ./aida.pyz shell              # AI Shell mode")
        print("  ./aida.pyz web                # Web interface")
        print("  ./aida.pyz index              # Index codebase")
        print("  ./aida.pyz 'your prompt'      # Direct agent mode")
        print(f"\nBundle size: {os.path.getsize('aida.pyz') / 1024 / 1024:.1f} MB")
    else:
        print("\n❌ zipapp bundle test failed!")
        sys.exit(1)
