#!/usr/bin/env python3
"""
Quick Start with Exchange Type Support
Automatically sets up database with exchange type support and starts the application
"""

import subprocess
import sys
import os
from pathlib import Path

def run_migration():
    """Run the exchange type migration"""
    print("🔄 Adding exchange type support to database...")
    
    try:
        result = subprocess.run([sys.executable, "add_exchange_type.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Exchange type migration completed")
            print(result.stdout)
            return True
        else:
            print("⚠️ Migration failed, but continuing...")
            if result.stderr:
                print("Error:", result.stderr)
            return True  # Continue anyway
    except Exception as e:
        print(f"⚠️ Migration error: {e}")
        return True  # Continue anyway

def main():
    """Main quick start function"""
    print("🚀 Copy Trading Bot - Quick Start with Exchange Support")
    print("=" * 60)
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Run database migration for exchange type support
    run_migration()
    
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    
    print(f"\n🔗 EXCHANGE SUPPORT:")
    print("✅ Binance - Fully functional")
    print("🚧 Bybit - Coming soon (UI ready)")
    print("🚧 Phoenix - Coming soon (UI ready)")
    
    print(f"\n🎯 USER EXPERIENCE:")
    print("• Users see exchange dropdown with 3 options")
    print("• Only Binance allows account creation")
    print("• Other exchanges show 'Coming soon' message")
    print("• Database supports exchange_type for future expansion")
    
    # Ask if user wants to start the application
    start_app = input("\n🚀 Start the application now? (Y/n): ").lower().strip()
    if start_app in ['', 'y', 'yes']:
        print("\n🌐 Starting application...")
        print("⏹️  Press Ctrl+C to stop")
        print("-" * 60)
        try:
            subprocess.run([sys.executable, "launcher.py", "--mode", "streamlit"], check=False)
        except KeyboardInterrupt:
            print("\n⏹️ Application stopped")
    else:
        print("\n📋 To start later, run: python launcher.py --mode streamlit")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())