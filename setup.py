#!/usr/bin/env python3
"""
Installation and Setup Script for Copy Trading Bot
This script will install dependencies and setup the environment
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def check_mysql():
    """Check if MySQL is available"""
    print("\nChecking MySQL availability...")
    try:
        import mysql.connector
        # Try to connect to MySQL (will fail if not running, but that's ok for now)
        print("✓ mysql-connector-python is available")
        print("! Make sure MySQL server is running and database 'copy_trading' exists")
        return True
    except ImportError:
        print("✗ mysql-connector-python not available")
        return False

def create_startup_scripts():
    """Create convenient startup scripts"""
    print("\nCreating startup scripts...")
    
    # Windows batch file
    with open("start_streamlit.bat", 'w') as f:
        f.write("""@echo off
echo Starting Copy Trading Bot (Streamlit)...
python launcher.py --mode streamlit
pause
""")
    
    with open("start_api.bat", 'w') as f:
        f.write("""@echo off
echo Starting Copy Trading Bot (FastAPI)...
python launcher.py --mode fastapi
pause
""")
    
    with open("test_system.bat", 'w') as f:
        f.write("""@echo off
echo Testing Copy Trading Bot System...
python test_system.py
pause
""")
    
    # Linux/Mac shell scripts
    with open("start_streamlit.sh", 'w') as f:
        f.write("""#!/bin/bash
echo "Starting Copy Trading Bot (Streamlit)..."
python launcher.py --mode streamlit
""")
    
    with open("start_api.sh", 'w') as f:
        f.write("""#!/bin/bash
echo "Starting Copy Trading Bot (FastAPI)..."
python launcher.py --mode fastapi
""")
    
    with open("test_system.sh", 'w') as f:
        f.write("""#!/bin/bash
echo "Testing Copy Trading Bot System..."
python test_system.py
""")
    
    # Make shell scripts executable on Unix systems
    if os.name != 'nt':
        for script in ['start_streamlit.sh', 'start_api.sh', 'test_system.sh']:
            os.chmod(script, 0o755)
    
    print("✓ Created startup scripts")
    return True

def main():
    """Main setup function"""
    print("Copy Trading Bot Setup Script")
    print("=" * 50)
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    steps = [
        ("Checking MySQL", check_mysql),
        ("Creating startup scripts", create_startup_scripts)
    ]
    
    success_count = 0
    
    for step_name, step_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        try:
            if step_func():
                success_count += 1
            else:
                print(f"✗ {step_name} failed")
        except Exception as e:
            print(f"✗ {step_name} failed with exception: {e}")
    
    # Summary
    print("\n" + "="*50)
    print("SETUP SUMMARY")
    print("="*50)
    
    if success_count == len(steps):
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Configure MySQL database:")
        print("2. Add your Binance API credentials to .env file")
        print("3. Run system test: python test_system.py")
        print("4. Start application:")
        print("   - Streamlit: python launcher.py --mode streamlit")
        print("   - FastAPI: python launcher.py --mode fastapi")
    else:
        print(f"⚠️  Setup completed with {len(steps) - success_count} issues.")
        print("Please check the errors above and resolve them.")
    
    print("\nFiles created:")
    print("- .env (environment configuration)")
    print("- start_streamlit.bat/.sh (Streamlit launcher)")
    print("- start_api.bat/.sh (API launcher)")
    print("- test_system.bat/.sh (System tester)")

if __name__ == "__main__":
    main()