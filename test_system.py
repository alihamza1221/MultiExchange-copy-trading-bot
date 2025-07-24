#!/usr/bin/env python3
"""
System Test Script for Copy Trading Bot
This script verifies that all components are working correctly
"""

import sys
import os
import traceback
from pathlib import Path

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    
    try:
        from database import Database
        print("✓ Database module imported successfully")
        
        from binance_config import BinanceClient, SourceAccountListener
        print("✓ Binance config module imported successfully")
        
        from bot_config import bot, CopyTradingBot
        print("✓ Bot config module imported successfully")
        
        import streamlit as st
        print("✓ Streamlit imported successfully")
        
        from api import app
        print("✓ FastAPI app imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error during imports: {e}")
        traceback.print_exc()
        return False

def test_database():
    """Test database connection and table creation"""
    print("\nTesting database...")
    
    try:
        # First, try to setup the database completely
        print("🔄 Running database setup...")
        from setup_database import DatabaseSetup
        setup = DatabaseSetup()
        
        if setup.run_complete_setup():
            print("✓ Database setup completed successfully")
        else:
            print("⚠️ Database setup had issues, trying basic connection...")
        
        # Now test with our Database class
        from database import Database
        db = Database()
        
        # Test table creation
        if db.create_tables():
            print("✓ Database tables created/verified successfully")
        else:
            print("✗ Failed to create database tables")
            return False
        
        # Test admin authentication
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@test.com').strip('"')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123').strip('"')
        
        # Hash password for authentication test
        import hashlib
        hashed_password = hashlib.sha256(admin_password.encode()).hexdigest()
        
        user_data = db.authenticate_user(admin_email, hashed_password)
        if user_data:
            print(f"✓ Admin user authentication works: {user_data['email']} ({user_data.get('role', 'unknown')})")
        else:
            print("⚠️ Admin user authentication failed, but database is set up")
            
        return True
        
    except Exception as e:
        print(f"✗ Database test error: {e}")
        traceback.print_exc()
        return False

def test_bot_initialization():
    """Test bot initialization"""
    print("\nTesting bot initialization...")
    
    try:
        from bot_config import bot
        
        # Test server IP
        ip = bot.get_server_ip()
        print(f"✓ Server IP: {ip}")
        
        # Test database initialization
        if bot.initialize_database():
            print("✓ Bot database initialization successful")
        else:
            print("✗ Bot database initialization failed")
            return False
            
        print("✓ Bot initialized successfully")
        return True
        
    except Exception as e:
        print(f"✗ Bot initialization error: {e}")
        traceback.print_exc()
        return False

def test_api_creation():
    """Test API application creation"""
    print("\nTesting API creation...")
    
    try:
        from api import app
        
        # Check if FastAPI app is created
        if app:
            print("✓ FastAPI app created successfully")
            
            # List available routes
            routes = []
            for route in app.routes:
                if hasattr(route, 'methods') and hasattr(route, 'path'):
                    methods = ', '.join(route.methods)
                    routes.append(f"{methods} {route.path}")
            
            print(f"✓ Available API routes ({len(routes)}):")
            for route in routes:
                print(f"  - {route}")
                
            return True
        else:
            print("✗ Failed to create FastAPI app")
            return False
            
    except Exception as e:
        print(f"✗ API creation error: {e}")
        traceback.print_exc()
        return False

def test_environment():
    """Test environment setup"""
    print("\nTesting environment...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check critical environment variables
        required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER']
        optional_vars = ['SOURCE_BINANCE_API_KEY', 'SOURCE_BINANCE_SECRET']
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"✓ {var}: {value}")
            else:
                print(f"! {var}: Not set (using default)")
        
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                print(f"✓ {var}: ***configured***")
            else:
                print(f"! {var}: Not configured (required for trading)")
        
        return True
        
    except Exception as e:
        print(f"✗ Environment test error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("Copy Trading Bot System Test")
    print("=" * 50)
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    tests = [
        ("Import Tests", test_imports),
        ("Database Tests", test_database),
        ("Bot Initialization", test_bot_initialization),
        ("API Creation", test_api_creation),
        ("Environment Setup", test_environment)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! The system is ready to use.")
        print("\nNext steps:")
        print("1. Configure your .env file with actual API keys")
        print("2. Start the application: python launcher.py")
        print("3. Open browser to http://localhost:8501")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())