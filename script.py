"""
Copy Trading Bot - Streamlit Web Interface
Main application entry point for the web-based copy trading dashboard
"""

import streamlit as st
import os
import time
import logging
from typing import Optional, Dict, Any

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="Copy Trading Bot",
    page_icon="$",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import application modules
from database import Database
from binance_config import BinanceClient
from bot_config import bot
import hashlib
import time

# Initialize database
db = Database()

# Session state initialization
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = None

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_page():
    """Login page UI"""
    st.title("Copy Trading Bot - Login")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if db.authenticate_user(email, password):
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    # Show default credentials
    st.info("Default credentials:\nEmail: admin@test.com\nPassword: admin123")

def dashboard_page():
    """Main dashboard page"""
    st.title(f"Copy Trading Dashboard - Welcome {st.session_state.user_email}")
    
    # Server IP display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Server IP", bot.get_server_ip())
    with col2:
        st.metric("Bot Status", "Running" if bot.is_running else "Stopped")
    with col3:
        if st.button("Start Bot" if not bot.is_running else "Stop Bot"):
            if not bot.is_running:
                if bot.start_bot():
                    st.success("Bot started successfully!")
                else:
                    st.error("Failed to start bot")
            else:
                bot.stop_bot()
                st.success("Bot stopped!")
            st.rerun()
    
    st.divider()
    
    # Exchange sections
    exchanges = ["Binance", "MEXC", "Phemex", "Blofin", "Bybit"]
    
    for exchange in exchanges:
        if exchange == "Binance":
            show_binance_section()
        else:
            st.subheader(f"{exchange} Accounts")
            st.info(f"{exchange} integration coming soon...")
            st.divider()

def show_binance_section():
    """Show Binance accounts section"""
    st.subheader("Binance Accounts")
    
    # Get user's Binance accounts
    accounts = db.get_user_accounts(st.session_state.user_email)
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("+ Add New Account", key="add_binance"):
            st.session_state.show_add_form = True
    
    # Add account form
    if st.session_state.get('show_add_form', False):
        with st.form("add_binance_account"):
            st.subheader("Add Binance Account")
            account_name = st.text_input("Account Name")
            api_key = st.text_input("API Key")
            secret_key = st.text_input("Secret Key", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Add Account")
            with col2:
                cancel = st.form_submit_button("Cancel")
            
            if submit and api_key and secret_key:
                # Validate credentials
                if bot.validate_api_credentials(api_key, secret_key):
                    if db.add_binance_account(st.session_state.user_email, api_key, secret_key, account_name):
                        st.success("Account added successfully!")
                        st.session_state.show_add_form = False
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to add account")
                else:
                    st.error("Invalid API credentials")
            elif submit:
                st.error("Please fill all fields")
            
            if cancel:
                st.session_state.show_add_form = False
                st.rerun()
    
    # Display accounts
    if accounts:
        for account in accounts:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.write(f"**{account['account_name'] or 'Unnamed Account'}**")
                    st.caption(f"Added: {account['created_at']}")
                
                with col2:
                    st.metric("Total Trades", account['total_trades'])
                
                with col3:
                    if st.button("View Details", key=f"view_{account['id']}"):
                        st.session_state.selected_account = account['id']
                        st.session_state.show_account_details = True
                        st.rerun()
                
                with col4:
                    if st.button("Delete", key=f"del_{account['id']}", type="secondary"):
                        if db.delete_account(account['id'], st.session_state.user_email):
                            st.success("Account deleted!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to delete account")
                
                st.divider()
    else:
        st.info("No Binance accounts added yet. Click 'Add New Account' to get started.")

def account_details_page():
    """Account details page"""
    account_id = st.session_state.selected_account
    
    if st.button("< Back to Dashboard"):
        st.session_state.show_account_details = False
        st.rerun()
    
    st.title("Account Details")
    
    # Get account stats
    stats = bot.get_account_stats(account_id)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Trades", stats['total_trades'])
    
    # Show recent trades
    st.subheader("Recent Trades")
    if stats['recent_trades']:
        for trade in stats['recent_trades']:
            with st.container():
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**{trade['symbol']}**")
                with col2:
                    st.write(f"{trade['side']}")
                with col3:
                    st.write(f"{trade['quantity']}")
                with col4:
                    st.write(f"{trade['trade_time']}")
                st.divider()
    else:
        st.info("No trades found for this account.")

def main():
    """Main application"""
    if not st.session_state.authenticated:
        login_page()
    else:
        # Add logout button in sidebar
        with st.sidebar:
            st.write(f"Logged in as: {st.session_state.user_email}")
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.user_email = None
                st.rerun()
        
        # Show appropriate page
        if st.session_state.get('show_account_details', False):
            account_details_page()
        else:
            dashboard_page()

if __name__ == "__main__":
    main()