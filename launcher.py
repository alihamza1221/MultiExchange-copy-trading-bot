#!/usr/bin/env python3
"""
Copy Trading Bot Launcher
Run this script to start the copy trading bot with either Streamlit or FastAPI
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path




def start_streamlit():
    """Start the Streamlit application"""
    print("Starting Streamlit application...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "script.py"])

def start_fastapi():
    """Start the FastAPI application"""
    print("Starting FastAPI application...")
    try:
        import uvicorn
        uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
    except ImportError:
        print("uvicorn not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "uvicorn"])
        import uvicorn
        uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

def main():
    """Main launcher function"""
    parser = argparse.ArgumentParser(description="Copy Trading Bot Launcher")
    parser.add_argument(
        "--mode", 
        choices=["streamlit", "fastapi", "both"], 
        default="streamlit",
        help="Choose which interface to launch (default: streamlit)"
    )
    parser.add_argument(
        "--check", 
        action="store_true",
        help="Check requirements and setup"
    )
    
    args = parser.parse_args()
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    print("Copy Trading Bot Launcher")
    print("=" * 40)
    
    if args.check:
        print("All requirements satisfied!")
        return
    
    # Start the application
    if args.mode == "streamlit":
        start_streamlit()
    elif args.mode == "fastapi":
        start_fastapi()
    elif args.mode == "both":
        print("Starting both Streamlit and FastAPI...")
        print("FastAPI will run on http://localhost:8000")
        print("Streamlit will run on http://localhost:8501")
        
        # Start FastAPI in background
        import threading
        api_thread = threading.Thread(target=start_fastapi, daemon=True)
        api_thread.start()
        
        # Start Streamlit in foreground
        start_streamlit()

if __name__ == "__main__":
    main()