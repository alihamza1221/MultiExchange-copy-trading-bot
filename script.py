"""
Copy Trading Bot - Streamlit Web Interface
Main application entry point for the web-based copy trading dashboard
"""

import streamlit as st
import hashlib
import time
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)

# Page configuration
st.set_page_config(
    page_title="Copy Trading Bot",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import application modules
try:
    from database import Database
    from binance_config import BinanceClient, PhemexClient
    from bot_config import bot
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.stop()

# Utility function to safely convert datetime to string
def safe_datetime_to_string(dt_value):
    """Convert any datetime value to a safe string for Streamlit display"""
    if dt_value is None:
        return 'N/A'
    
    try:
        # If it's a datetime object, format it
        if hasattr(dt_value, 'strftime'):
            return dt_value.strftime('%Y-%m-%d')
        # If it's already a string, return as-is (but clean it)
        elif isinstance(dt_value, str):
            return str(dt_value).split('.')[0][:19]  # Remove microseconds and limit length
        # For anything else, convert to string
        else:
            return str(dt_value)
    except Exception:
        return str(dt_value) if dt_value else 'N/A'

# Enums for better type safety
class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"

class UserStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class User:
    """User data class for type safety"""
    id: int
    email: str
    role: str
    status: str

class SessionManager:
    """Enhanced session management with role-based access"""
    
    @staticmethod
    def initialize_session() -> None:
        """Initialize session state variables"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_data' not in st.session_state:
            st.session_state.user_data = None
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'login'
        if 'show_register' not in st.session_state:
            st.session_state.show_register = False
        if 'selected_account' not in st.session_state:
            st.session_state.selected_account = None
        if 'show_account_details' not in st.session_state:
            st.session_state.show_account_details = False
        if 'accounts_refresh_trigger' not in st.session_state:
            st.session_state.accounts_refresh_trigger = 0

    @staticmethod
    def trigger_accounts_refresh():
        """Trigger a refresh of the accounts display"""
        st.session_state.accounts_refresh_trigger = st.session_state.get('accounts_refresh_trigger', 0) + 1

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[User]:
        """Authenticate user and return user data"""
        try:
            db = Database()
            hashed_password = SessionManager.hash_password(password)
            user_data = db.authenticate_user(email, hashed_password)
            
            if user_data:
                return User(
                    id=user_data['id'],
                    email=user_data['email'],
                    role=user_data['role'],
                    status=user_data['status']
                )
            return None
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            return None

    @staticmethod
    def register_user(email: str, password: str) -> bool:
        """Register new user with pending status"""
        try:
            db = Database()
            hashed_password = SessionManager.hash_password(password)
            return db.register_user(email, hashed_password)
        except Exception as e:
            logging.error(f"Registration error: {e}")
            return False

    @staticmethod
    def is_admin() -> bool:
        """Check if current user is admin"""
        return (st.session_state.authenticated and 
                st.session_state.user_data and 
                st.session_state.user_data.role == UserRole.ADMIN.value)

    @staticmethod
    def is_approved_user() -> bool:
        """Check if current user is approved"""
        return (st.session_state.authenticated and 
                st.session_state.user_data and 
                st.session_state.user_data.status == UserStatus.APPROVED.value)

    @staticmethod
    def logout() -> None:
        """Clear session and logout user"""
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.session_state.current_page = 'login'
        st.session_state.show_register = False
        st.rerun()

class AuthenticationUI:
    """Enhanced authentication UI with registration"""
    
    @staticmethod
    def login_page() -> None:
        """Enhanced login page with registration option"""
        st.title("🚀 Copy Trading Bot")
        st.markdown("---")
        
        # Toggle between login and register
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔑 Login", use_container_width=True, 
                        type="primary" if not st.session_state.show_register else "secondary"):
                st.session_state.show_register = False
                st.rerun()
        
        with col2:
            if st.button("📝 Register", use_container_width=True,
                        type="primary" if st.session_state.show_register else "secondary"):
                st.session_state.show_register = True
                st.rerun()
        
        st.markdown("---")
        
        if st.session_state.show_register:
            AuthenticationUI._show_register_form()
        else:
            AuthenticationUI._show_login_form()

    @staticmethod
    def _show_login_form() -> None:
        """Show login form"""
        st.subheader("🔑 Login to Your Account")
        
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("📧 Email", placeholder="Enter your email")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns([3, 1])
            with col2:
                submit = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submit and email and password:
                user = SessionManager.authenticate_user(email, password)
                
                if user:
                    if user.status == UserStatus.APPROVED.value:
                        st.session_state.authenticated = True
                        st.session_state.user_data = user
                        st.session_state.current_page = 'dashboard'
                        st.success(f"Welcome back, {user.email}!")
                        time.sleep(1)
                        st.rerun()
                    elif user.status == UserStatus.PENDING.value:
                        st.warning("⏳ Your account is pending approval. Please wait for admin approval.")
                    else:
                        st.error("❌ Your account has been rejected. Please contact administrator.")
                else:
                    st.error("❌ Invalid credentials. Please try again.")
            elif submit:
                st.error("❌ Please fill in all fields.")
        
        # Admin credentials hint
        st.info("💡 **Demo Access**: Use the credentials from your .env file")

    @staticmethod
    def _show_register_form() -> None:
        """Show registration form"""
        st.subheader("📝 Create New Account")
        
        with st.form("register_form", clear_on_submit=True):
            email = st.text_input("📧 Email", placeholder="Enter your email")
            password = st.text_input("🔒 Password", type="password", placeholder="Create a password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
            
            col1, col2 = st.columns([3, 1])
            with col2:
                submit = st.form_submit_button("Register", use_container_width=True, type="primary")
            
            if submit and email and password and confirm_password:
                if password != confirm_password:
                    st.error("❌ Passwords do not match.")
                elif len(password) < 6:
                    st.error("❌ Password must be at least 6 characters long.")
                else:
                    if SessionManager.register_user(email, password):
                        st.success("✅ Registration successful! Your account is pending admin approval.")
                        st.info("📧 You will be notified once your account is approved.")
                        time.sleep(2)
                        st.session_state.show_register = False
                        st.rerun()
                    else:
                        st.error("❌ Registration failed. Email might already exist.")
            elif submit:
                st.error("❌ Please fill in all fields.")

class AdminDashboard:
    """Comprehensive admin dashboard"""
    
    @staticmethod
    def show_admin_dashboard() -> None:
        """Main admin dashboard"""
        st.title(f"👑 Admin Dashboard - {st.session_state.user_data.email}")
        
        # Admin metrics
        AdminDashboard._show_admin_metrics()
        
        # Navigation tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🤖 Bot Control", 
            "👥 User Management", 
            "💳 Account Management", 
            "📊 Trading Stats",
            "⚙️ Settings"
        ])
        
        with tab1:
            AdminDashboard._show_bot_control()
        
        with tab2:
            AdminDashboard._show_user_management()
        
        with tab3:
            AdminDashboard._show_account_management()
        
        with tab4:
            AdminDashboard._show_trading_stats()
        
        with tab5:
            AdminDashboard._show_settings()

    @staticmethod
    def _show_admin_metrics() -> None:
        """Show admin dashboard metrics"""
        try:
            db = Database()
            
            # Get metrics
            all_users = db.get_all_users()
            pending_users = db.get_pending_users()
            all_accounts = db.get_all_binance_accounts()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("🤖 Bot Status", "Running" if bot.is_running else "Stopped",
                         delta="Active" if bot.is_running else "Inactive")
            
            with col2:
                st.metric("👥 Total Users", len(all_users))
            
            with col3:
                st.metric("⏳ Pending Approvals", len(pending_users),
                         delta=f"+{len(pending_users)}" if pending_users else None)
            
            with col4:
                st.metric("💳 Trading Accounts", len(all_accounts))
                
        except Exception as e:
            st.error(f"Error loading metrics: {e}")

    @staticmethod
    def _show_bot_control() -> None:
        """Bot control panel for admin"""
        st.subheader("🤖 Copy Trading Bot Control")
        
        # Server info
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"🌐 **Server IP**: 208.77.246.15")
        
        with col2:
            status = "🟢 Running" if bot.is_running else "🔴 Stopped"
            st.info(f"📊 **Bot Status**: {status}")
        
        st.markdown("---")
        
        # Bot controls
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🚀 Start Bot", disabled=bot.is_running, use_container_width=True, type="primary"):
                with st.spinner("Starting bot..."):
                    if bot.start_bot():
                        st.success("✅ Copy trading bot started successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to start bot. Check configuration.")
        
        with col2:
            if st.button("⏹️ Stop Bot", disabled=not bot.is_running, use_container_width=True):
                with st.spinner("Stopping bot..."):
                    bot.stop_bot()
                    st.success("✅ Copy trading bot stopped!")
                    time.sleep(1)
                    st.rerun()
        
        with col3:
            if bot.is_running:
                st.success("🟢 **Bot is actively monitoring and copying trades**")
            else:
                st.warning("🔴 **Bot is stopped - No trade monitoring active**")

    @staticmethod
    def _show_user_management() -> None:
        """User management panel"""
        st.subheader("👥 User Management")
        
        try:
            db = Database()
            
            # Pending approvals section
            pending_users = db.get_pending_users()
            if pending_users:
                st.warning(f"⏳ **{len(pending_users)} users awaiting approval**")
                
                for user in pending_users:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                        
                        with col1:
                            st.write(f"📧 **{user['email']}**")
                        
                        with col2:
                            st.caption(f"Registered: {user['created_at']}")
                        
                        with col3:
                            if st.button("✅ Approve", key=f"approve_{user['id']}", type="primary"):
                                if db.approve_user(user['id'], st.session_state.user_data.id):
                                    st.success(f"✅ Approved {user['email']}")
                                    time.sleep(1)
                                    st.rerun()
                        
                        with col4:
                            if st.button("❌ Reject", key=f"reject_{user['id']}"):
                                if db.reject_user(user['id'], st.session_state.user_data.id):
                                    st.error(f"❌ Rejected {user['email']}")
                                    time.sleep(1)
                                    st.rerun()
                        
                        st.divider()
            else:
                st.info("✅ No pending user approvals")
            
            st.markdown("---")
            
            # All users section
            st.subheader("📋 All Users")
            all_users = db.get_all_users()
            
            if all_users:
                for user in all_users:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 1, 2, 2])
                        
                        with col1:
                            role_icon = "👑" if user['role'] == 'admin' else "👤"
                            st.write(f"{role_icon} **{user['email']}**")
                        
                        with col2:
                            status_color = {
                                'approved': '🟢',
                                'pending': '🟡', 
                                'rejected': '🔴'
                            }
                            st.write(f"{status_color.get(user['status'], '⚪')} {user['status'].title()}")
                        
                        with col3:
                            st.caption(f"Joined: {user['created_at']}")
                        
                        with col4:
                            if user['approved_by_email']:
                                st.caption(f"By: {user['approved_by_email']}")
                        
                        st.divider()
                        
        except Exception as e:
            st.error(f"Error loading user management: {e}")

    @staticmethod
    def _show_account_management() -> None:
        """Enhanced account management for admin"""
        st.subheader("💳 Trading Account Management")
        
        try:
            db = Database()
            accounts = db.get_all_binance_accounts()
            
            if accounts:
                st.info(f"📊 **Total Accounts**: {len(accounts)}")
                
                for account in accounts:
                    with st.expander(f"💳 {account['account_name'] or 'Unnamed Account'} - {account['user_email']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Account Details:**")
                            st.write(f"• **Owner**: {account['user_email']}")
                            st.write(f"• **Created**: {account['created_at']}")
                            st.write(f"• **Total Trades**: {account['total_trades']}")
                        
                        with col2:
                            st.write("**API Configuration:**")
                            st.code(f"API Key: {account['api_key'][:8]}...{account['api_key'][-8:]}")
                            st.code(f"Secret: {account['secret_key'][:8]}...{account['secret_key'][-8:]}")
                        
                        # Account actions
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("✏️ Edit", key=f"edit_{account['id']}"):
                                st.session_state[f"editing_{account['id']}"] = True
                                st.rerun()
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_{account['id']}", type="secondary"):
                                if st.button("⚠️ Confirm Delete", key=f"confirm_delete_{account['id']}", type="primary"):
                                    if db.delete_account_admin(account['id']):
                                        st.success("✅ Account deleted!")
                                        time.sleep(1)
                                        st.rerun()
                        
                        # Edit form
                        if st.session_state.get(f"editing_{account['id']}", False):
                            with st.form(f"edit_form_{account['id']}"):
                                st.write("**Edit Account:**")
                                new_name = st.text_input("Account Name", value=account['account_name'] or "")
                                new_api_key = st.text_input("API Key", value=account['api_key'])
                                new_secret = st.text_input("Secret Key", value=account['secret_key'], type="password")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("💾 Save", type="primary"):
                                        if db.update_binance_account(account['id'], new_api_key, new_secret, new_name):
                                            st.success("✅ Account updated!")
                                            st.session_state[f"editing_{account['id']}"] = False
                                            time.sleep(1)
                                            st.rerun()
                                
                                with col2:
                                    if st.form_submit_button("Cancel"):
                                        st.session_state[f"editing_{account['id']}"] = False
                                        st.rerun()
                        
                        st.divider()
            else:
                st.info("📝 No trading accounts configured yet")
                
        except Exception as e:
            st.error(f"Error loading account management: {e}")

    @staticmethod
    def _show_trading_stats() -> None:
        """Show trading statistics"""
        st.subheader("📊 Trading Statistics")
        st.info("📈 Trading statistics and analytics will be displayed here")
        # TODO: Implement trading statistics

    @staticmethod
    def _show_settings() -> None:
        """Show admin settings"""
        st.subheader("⚙️ System Settings")
        st.info("🔧 System configuration options will be displayed here")
        # TODO: Implement system settings

class UserDashboard:
    """User dashboard with limited access"""
    
    @staticmethod
    def show_user_dashboard() -> None:
        """Main user dashboard with account details navigation"""
        # Check if we should show account details page
        if st.session_state.get('show_account_details', False) and st.session_state.get('selected_account'):
            UserDashboard._show_account_details()
            return
        
        st.title(f"👤 User Dashboard - {st.session_state.user_data.email}")
        
        # Show server info for users
        col1, = st.columns(1)
        with col1:
            st.info(f"🌐 **Server IP**: 208.77.246.15")
        
        st.markdown("---")
        
        # User status check
        if st.session_state.user_data.status != UserStatus.APPROVED.value:
            UserDashboard._show_approval_pending()
            return
        
        # Approved user interface
        tab1, tab2 = st.tabs(["💳 My Accounts", "📊 My Trades"])
        
        with tab1:
            UserDashboard._show_user_accounts()
        
        with tab2:
            UserDashboard._show_user_trades()

    @staticmethod
    def _show_approval_pending() -> None:
        """Show approval pending message"""
        st.warning("⏳ **Account Pending Approval**")
        st.info("""
        📧 Your account registration is currently under review by our administrators.
        
        **What's next?**
        - ✅ Your registration has been received
        - ⏳ Admin review is in progress  
        - 📧 You'll be notified once approved
        - 🚀 Full access will be granted after approval
        
        **Need help?** Contact support if you have any questions.
        """)
            
    @staticmethod
    def _show_user_accounts() -> None:
        """Show user's trading accounts with exchange selection"""
        st.subheader("💳 My Trading Accounts")
        
        try:
            db = Database()
            # accounts = db.get_user_accounts(st.session_state.user_data.email)
            
            # Add new account form with exchange selection
            with st.expander("➕ Add New Trading Account"):
                st.markdown("### 🔗 Select Exchange")
                
                # Exchange selection dropdown
                exchange_options = {
                    "binance": "Binance",
                    "bybit": "Bybit", 
                    "phemex": "Phemex"
                }
                
                selected_exchange = st.selectbox(
                    "Choose Exchange:",
                    options=list(exchange_options.keys()),
                    format_func=lambda x: exchange_options[x],
                    index=0  # Default to Binance
                )
                
                # Show warning for non-supported exchanges
                if selected_exchange not in ["binance", "phemex"]:
                    st.warning(f" {exchange_options[selected_exchange]} integration is coming soon!")
                    st.info("For now, please use Binance or Phemex exchanges which are fully supported.")
                elif selected_exchange == "binance":
                    # Binance account creation form
                    st.markdown("---")
                    st.markdown("### S Add Binance Account")
                    
                    with st.form("add_binance_account_form"):
                        account_name = st.text_input(
                            "Account Name", 
                            placeholder="e.g., My Binance Trading Account"
                        )
                        
                        api_key = st.text_input(
                            "Binance API Key", 
                            placeholder="Your Binance API Key"
                        )
                        
                        secret_key = st.text_input(
                            "Binance Secret Key", 
                            type="password", 
                            placeholder="Your Binance Secret Key"
                        )
                        
                        if st.form_submit_button("➕ Add Account", type="primary"):
                            if api_key and secret_key:
                                # Validate credentials
                                try:
                                    test_client = BinanceClient(api_key=api_key, secret_key=secret_key)
                                    if test_client.test_connection():
                                        # Try to add with exchange type, fallback to old method
                                        try:
                                            if db.add_binance_account(
                                                st.session_state.user_data.email, 
                                                api_key, 
                                                secret_key, 
                                                account_name,
                                                selected_exchange
                                            ):
                                                st.success("✅ Binance account added successfully!")
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("Failed to add account to database")
                                        except Exception:
                                            # Fallback to old method without exchange type
                                            if db.add_binance_account(
                                                st.session_state.user_data.email, 
                                                api_key, 
                                                secret_key, 
                                                account_name
                                            ):
                                                st.success(" Binance account added successfully!")
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("Failed to add account to database")
                                    else:
                                        st.error(" Invalid Binance API credentials")
                                except Exception as e:
                                    st.error(f"Error validating credentials: {e}")
                            else:
                                st.error("Please fill in all fields")
                    
                    # Binance setup help
                    st.markdown("---")
                    st.markdown("### 💡 Binance Setup Help")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info("""
                        **📚 API Setup Guide:**
                        1. Visit [Binance](https://www.binance.com)
                        2. Go to API Management
                        3. Create new API key
                        4. Enable trading permissions
                        """)
                    
                    with col2:
                        st.info("""
                        **🔒 Security Tips:**
                        • Use dedicated trading account
                        • Enable IP whitelist
                        • Never share your keys
                        • Regular key rotation
                        """)
                    
                    # Detailed PDF guide button
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button("📖 View Detailed Step-by-Step Guide", use_container_width=True, type="secondary", key="binance_pdf_guide_button"):
                            st.session_state.show_binance_guide = True
                            st.rerun()
                    
                    # Show detailed guide from PDF
                    if st.session_state.get('show_binance_guide', False):
                        UserDashboard._show_binance_pdf_guide()
                elif selected_exchange == "phemex":
                    # Phemex account creation form
                    st.markdown("---")
                    st.markdown("### 🔴 Add Phemex Account")
                    
                    with st.form("add_phemex_account_form", clear_on_submit=True):
                        account_name = st.text_input(
                            "Account Name", 
                            placeholder="e.g., My Phemex Trading Account",
                            key="phemex_account_name"
                        )
                        
                        api_key = st.text_input(
                            "Phemex Id", 
                            placeholder="Your Phemex Id",
                            key="phemex_api_key"
                        )
                        
                        secret_key = st.text_input(
                            "Phemex Secret Key", 
                            type="password", 
                            placeholder="Your Phemex Secret Key",
                            key="phemex_secret_key"
                        )
                        
                        if st.form_submit_button("➕ Add Account", type="primary"):
                            if api_key and secret_key:
                                # Validate Phemex credentials
                                try:
                                    test_client = PhemexClient(api_key=api_key, api_secret=secret_key)
                                    # Try the simplified connection test first
                                    connection_success = test_client.test_connection_simple()
                                    
                                    if not connection_success:
                                        # Fallback to original test method
                                        connection_success = test_client.test_connection()
                                    
                                    if connection_success:
                                        if db.add_phemex_account(
                                            st.session_state.user_data.email, 
                                            api_key, 
                                            secret_key, 
                                            account_name
                                        ):
                                            st.success("✅ Phemex account added successfully!")
                                            st.info("🔄 Refreshing page to show new account...")
                                            # Trigger refresh
                                            SessionManager.trigger_accounts_refresh()
                                            time.sleep(2)
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to add account to database")
                                    else:
                                        st.error("❌ Invalid Phemex API credentials")
                                except Exception as e:
                                    st.error(f"❌ Error validating credentials: {e}")
                                    logging.error(f"Phemex credential validation error: {e}")
                            else:
                                st.error("❌ Please fill in all fields")
                    
                    # Phemex setup help
                    st.markdown("---")
                    st.markdown("### � Phemex Setup Help")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info("""
                        **📚 API Setup Guide:**
                        1. Visit [Phemex](https://phemex.com)
                        2. Go to API Management
                        3. Create new API key
                        4. Enable trading permissions
                        """)
                    
                    with col2:
                        st.info("""
                        **🔒 Security Tips:**
                        • Use dedicated trading account
                        • Enable IP whitelist
                        • Never share your keys
                        • Regular key rotation
                        """)
            
            # Display user accounts (from all exchanges)
            try:
                binance_accounts = []
                phemex_accounts = []
                
                try:
                    binance_accounts = db.get_user_accounts(st.session_state.user_data.email) or []
                    logging.info(f"Successfully loaded {len(binance_accounts)} Binance accounts")
                except Exception as e:
                    logging.error(f"Error fetching Binance accounts: {e}")
                    st.warning("No Binance Accounts Found")
                    binance_accounts = []
                
                try:
                    phemex_accounts = db.get_user_phemex_accounts(st.session_state.user_data.email)
                    logging.info(f"Phemex accounts result type: {type(phemex_accounts)}")
                    logging.info(f"Phemex accounts result: {phemex_accounts}")
                    
                    if phemex_accounts is None:
                        phemex_accounts = []
                        st.warning("⚠️ Phemex accounts query returned None")
                    elif not isinstance(phemex_accounts, list):
                        logging.error(f"UI: Expected list, got {type(phemex_accounts)}: {phemex_accounts}")
                        phemex_accounts = []
                        st.error(f"❌ Invalid data type for Phemex accounts: {type(phemex_accounts)}")
                    else:
                        logging.info(f"UI: Successfully loaded {len(phemex_accounts)} Phemex accounts")
                        
                except Exception as e:
                    logging.error(f"Error fetching Phemex accounts: {e}")
                    import traceback
                    logging.error(f"Full traceback: {traceback.format_exc()}")
                    st.error(f"❌ Error loading Phemex accounts: {e}")
                    phemex_accounts = []
                
                all_user_accounts = []
                
                # Combine all accounts with proper error handling
                for account in binance_accounts:
                    try:
                        account['exchange_type'] = account.get('exchange_type', 'binance')
                        all_user_accounts.append(account)
                    except Exception as e:
                        logging.error(f"Error processing Binance account {account.get('id', 'unknown')}: {e}")
                
                for account in phemex_accounts:
                    try:
                        account['exchange_type'] = 'phemex'
                        all_user_accounts.append(account)
                    except Exception as e:
                        logging.error(f"Error processing Phemex account {account.get('id', 'unknown')}: {e}")
                
                if all_user_accounts:
                    st.markdown("---")
                    st.markdown("### 📊 My Trading Accounts")
                    
                    for account in all_user_accounts:
                        try:
                            # Get exchange type and display name
                            exchange_type = account.get('exchange_type', 'binance')
                            exchange_name = exchange_options.get(exchange_type, f"🔗 {exchange_type.title()}")
                            
                            with st.container():
                                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                                
                                with col1:
                                    account_display_name = account.get('account_name') or 'Unnamed Account'
                                    st.write(f"**{account_display_name}**")
                                    created_at_safe = safe_datetime_to_string(account.get('created_at'))
                                    st.caption(f"Exchange: {exchange_name} • Added: {created_at_safe}")
                                
                                with col2:
                                    total_trades = account.get('total_trades', 0)
                                    st.metric("Total Trades", total_trades)
                                
                                with col3:
                                    if st.button("📊 Details", key=f"details_{exchange_type}_{account['id']}"):
                                        st.session_state.selected_account = account['id']
                                        st.session_state.selected_exchange_type = exchange_type
                                        st.session_state.show_account_details = True
                                        st.rerun()
                                
                                with col4:
                                    if st.button("🗑️ Delete", key=f"del_{exchange_type}_{account['id']}", type="secondary"):
                                        # Handle deletion based on exchange type
                                        if exchange_type == 'binance':
                                            if db.delete_account(account['id'], st.session_state.user_data.email):
                                                st.success("✅ Binance account deleted!")
                                                time.sleep(1)
                                                st.rerun()
                                        elif exchange_type == 'phemex':
                                            if db.delete_phemex_account(account['id'], st.session_state.user_data.email):
                                                st.success("✅ Phemex account deleted!")
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("❌ Failed to delete Phemex account")
                                
                                st.divider()
                        except Exception as e:
                            logging.error(f"Error displaying account {account.get('id', 'unknown')}: {e}")
                            st.error(f"Error displaying account: {e}")
                else:
                    st.info("📝 No trading accounts configured. Add your first account above!")
                    
            except Exception as e:
                logging.error(f"Critical error in account display: {e}")
                st.error(f"Error loading accounts: {e}")
                st.info("Please try refreshing the page or contact support if the issue persists.")
                
        except Exception as e:
            st.error(f"Error loading accounts: {e}")
            logging.error(f"Account management error: {e}")


    @staticmethod
    def _show_account_details() -> None:
        """Show detailed account information and trading history"""
        account_id = st.session_state.selected_account
        
        # Back button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back to Dashboard", type="secondary"):
                st.session_state.show_account_details = False
                st.session_state.selected_account = None
                st.rerun()
        
        try:
            db = Database()
            
            # Get account information
            account_info = db.get_account_by_id(account_id, st.session_state.user_data.email)
            
            if not account_info:
                st.error("❌ Account not found or access denied")
                st.session_state.show_account_details = False
                st.rerun()
                return
            
            # Page title
            st.title(f"📊 Account Details: {account_info.get('account_name', 'Unnamed Account')}")
            
            # Account overview
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📈 Total Trades", account_info.get('total_trades', 0))
            
            with col2:
                exchange_type = account_info.get('exchange_type', 'binance')
                exchange_icons = {'binance': '🔶', 'bybit': '🟡', 'phemex': '🔴'}
                st.metric("🔗 Exchange", f"{exchange_icons.get(exchange_type, '🔗')} {exchange_type.title()}")
            
            with col3:
                st.metric("📅 Created", safe_datetime_to_string(account_info.get('created_at', 'N/A')))
            
            with col4:
                # Account status (could be enhanced with real-time balance check)
                try:
                    test_client = BinanceClient(
                        api_key=account_info['api_key'],
                        secret_key=account_info['secret_key']
                    )
                    connection_status = "🟢 Connected" if test_client.test_connection() else "🔴 Disconnected"
                    st.metric("🔌 Status", connection_status)
                except Exception:
                    st.metric("🔌 Status", "⚠️ Unknown")
            
            st.markdown("---")
            
            # Trading history section
            st.subheader("📈 Trading History")
            
            # Get trades for this account
            trades = db.get_account_trades(account_id)
            
            if trades:
                # Summary metrics
                st.markdown("### 📊 Trading Summary")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("🔢 Total Orders", len(trades))
                
                with col2:
                    buy_orders = len([t for t in trades if t.get('side') == 'BUY'])
                    st.metric("📈 Buy Orders", buy_orders)
                
                with col3:
                    sell_orders = len([t for t in trades if t.get('side') == 'SELL'])
                    st.metric("📉 Sell Orders", sell_orders)
                
                with col4:
                    successful_trades = len([t for t in trades if t.get('status') in ['FILLED', 'MIRRORED']])
                    st.metric("✅ Successful", successful_trades)
                
                st.markdown("---")
                
                # Recent trades table
                st.markdown("### 🕐 Recent Trades")
                
                # Filter options
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    symbols = list(set([trade.get('symbol', 'N/A') for trade in trades]))
                    selected_symbol = st.selectbox("Filter by Symbol", ["All"] + symbols)
                
                with col2:
                    sides = ['All', 'BUY', 'SELL']
                    selected_side = st.selectbox("Filter by Side", sides)
                
                with col3:
                    statuses = list(set([trade.get('status', 'N/A') for trade in trades]))
                    selected_status = st.selectbox("Filter by Status", ["All"] + statuses)
                
                # Apply filters
                filtered_trades = trades
                if selected_symbol != "All":
                    filtered_trades = [t for t in filtered_trades if t.get('symbol') == selected_symbol]
                if selected_side != "All":
                    filtered_trades = [t for t in filtered_trades if t.get('side') == selected_side]
                if selected_status != "All":
                    filtered_trades = [t for t in filtered_trades if t.get('status') == selected_status]
                
                # Display filtered trades
                if filtered_trades:
                    # Sort by most recent first
                    filtered_trades.sort(key=lambda x: x.get('trade_time', ''), reverse=True)
                    
                    # Pagination
                    trades_per_page = 10
                    total_pages = (len(filtered_trades) - 1) // trades_per_page + 1
                    
                    if total_pages > 1:
                        page = st.selectbox(f"Page (Total: {total_pages})", range(1, total_pages + 1))
                        start_idx = (page - 1) * trades_per_page
                        end_idx = start_idx + trades_per_page
                        display_trades = filtered_trades[start_idx:end_idx]
                    else:
                        display_trades = filtered_trades
                    
                    # Display trades
                    for trade in display_trades:
                        with st.container():
                            col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 2])
                            
                            with col1:
                                symbol = trade.get('symbol', 'N/A')
                                st.write(f"**{symbol}**")
                                st.caption(f"Order ID: {trade.get('order_id', 'N/A')}")
                            
                            with col2:
                                side = trade.get('side', 'N/A')
                                side_color = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "⚪"
                                st.write(f"{side_color} {side}")
                            
                            with col3:
                                order_type = trade.get('order_type', 'N/A')
                                st.write(f"📋 {order_type}")
                            
                            with col4:
                                quantity = trade.get('quantity', 0)
                                st.write(f"📊 {quantity}")
                            
                            with col5:
                                price = trade.get('price')
                                if price:
                                    st.write(f"💰 ${price}")
                                else:
                                    st.write("💰 Market")
                            
                            with col6:
                                status = trade.get('status', 'N/A')
                                status_colors = {
                                    'FILLED': '✅',
                                    'MIRRORED': '🔄',
                                    'PENDING': '⏳',
                                    'CANCELED': '❌',
                                    'REJECTED': '🚫'
                                }
                                status_icon = status_colors.get(status, '⚪')
                                st.write(f"{status_icon} {status}")
                                
                                trade_time = trade.get('trade_time', 'N/A')
                                formatted_time = safe_datetime_to_string(trade_time)
                                if formatted_time != 'N/A' and len(formatted_time) >= 10:
                                    # Convert to short format for display (MM/DD HH:MM)
                                    try:
                                        # Extract month/day and time from YYYY-MM-DD HH:MM:SS format
                                        date_part = formatted_time[5:10].replace('-', '/')  # MM/DD
                                        time_part = formatted_time[11:16] if len(formatted_time) > 11 else ""  # HH:MM
                                        short_display = f"{date_part} {time_part}".strip()
                                        st.caption(f"⏰ {short_display}")
                                    except:
                                        st.caption(f"⏰ {formatted_time}")
                                else:
                                    st.caption("⏰ N/A")
                            
                            st.divider()
                    
                    # Show pagination info
                    if total_pages > 1:
                        st.caption(f"Showing {len(display_trades)} of {len(filtered_trades)} trades")
                        
                else:
                    st.info("📝 No trades match the selected filters")
                    
            else:
                st.info("📝 No trading activity found for this account")
                st.markdown("""
                **Why no trades?**
                - 🤖 Copy trading bot might not be running
                - 📡 No signals received from source account
                - ⚙️ Account might be newly added
                - 🔄 Trades will appear here once copy trading begins
                """)
            
            # Account management section
            st.markdown("---")
            st.subheader("⚙️ Account Management")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Test Connection", use_container_width=True):
                    try:
                        test_client = BinanceClient(
                            api_key=account_info['api_key'],
                            secret_key=account_info['secret_key']
                        )
                        if test_client.test_connection():
                            st.success("✅ Connection successful!")
                        else:
                            st.error("❌ Connection failed!")
                    except Exception as e:
                        st.error(f"❌ Connection error: {e}")
            
            with col2:
                if st.button("✏️ Edit Account", use_container_width=True):
                    st.session_state[f"editing_user_{account_id}"] = True
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Delete Account", use_container_width=True, type="secondary"):
                    st.session_state[f"confirming_delete_{account_id}"] = True
                    st.rerun()
            
            # Edit form
            if st.session_state.get(f"editing_user_{account_id}", False):
                with st.form(f"edit_user_account_{account_id}"):
                    st.markdown("### ✏️ Edit Account")
                    
                    new_name = st.text_input("Account Name", value=account_info.get('account_name', ''))
                    new_api_key = st.text_input("API Key", value=account_info.get('api_key', ''))
                    new_secret = st.text_input("Secret Key", value=account_info.get('secret_key', ''), type="password")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Save Changes", type="primary"):
                            if db.update_binance_account(account_id, new_api_key, new_secret, new_name):
                                st.success("✅ Account updated successfully!")
                                st.session_state[f"editing_user_{account_id}"] = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Failed to update account")
                    
                    with col2:
                        if st.form_submit_button("❌ Cancel"):
                            st.session_state[f"editing_user_{account_id}"] = False
                            st.rerun()
            
            # Delete confirmation
            if st.session_state.get(f"confirming_delete_{account_id}", False):
                st.warning("⚠️ **Confirm Account Deletion**")
                st.markdown(f"Are you sure you want to delete **{account_info.get('account_name', 'this account')}**?")
                st.markdown("This action cannot be undone and will remove all trading history.")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🗑️ Yes, Delete", type="primary"):
                        if db.delete_account(account_id, st.session_state.user_data.email):
                            st.success("✅ Account deleted successfully!")
                            st.session_state[f"confirming_delete_{account_id}"] = False
                            st.session_state.show_account_details = False
                            st.session_state.selected_account = None
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete account")
                
                with col2:
                    if st.button("❌ Cancel"):
                        st.session_state[f"confirming_delete_{account_id}"] = False
                        st.rerun()
                        
        except Exception as e:
            st.error(f"Error loading account details: {e}")
            logging.error(f"Account details error: {e}")

    @staticmethod
    def _show_user_trades() -> None:
        """Show user's trading history"""
        st.subheader("📊 My Trading History")
        st.info("📈 Your trading history and performance will be displayed here")
        # TODO: Implement user trading history

    @staticmethod
    def _show_binance_pdf_guide():
        """Display download option for Binance API setup guide PDF"""
        with st.container():
            st.markdown("---")
            st.markdown("## 📖 Complete Binance API Setup Guide")
            
            # Close button with unique key
            col1, col2, col3 = st.columns([1, 2, 1])
            with col3:
                if st.button("❌ Close Guide", type="secondary", use_container_width=True, key="close_pdf_guide"):
                    st.session_state.show_binance_guide = False
                    st.rerun()
            
            # Check if PDF file exists
            pdf_path = os.path.join(os.path.dirname(__file__), "binance.pdf")
            
            if os.path.exists(pdf_path):
                try:
                    # Read PDF file as bytes for download
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_bytes = pdf_file.read()
                    
                    st.success("📄 PDF Guide Available - Download to view complete instructions with images")
                    
                    # Guide description
                    st.markdown("### 📋 What's in the Guide?")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info("""
                        **📚 Complete Setup Instructions:**
                        • Step-by-step screenshots
                        • API key creation process
                        • Security configuration
                        • Permission settings
                        """)
                    
                    with col2:
                        st.info("""
                        **🎯 Visual Learning:**
                        • Detailed images for each step
                        • Highlighted important sections
                        • Real Binance interface screenshots
                        • Troubleshooting tips
                        """)
                    
                    # Download section
                    st.markdown("---")
                    st.markdown("### 📥 Download Guide")
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        # File info
                        file_size_mb = len(pdf_bytes) / (1024 * 1024)
                        st.markdown(f"**📋 File Size:** {file_size_mb:.2f} MB")
                        st.markdown("**📄 Format:** PDF with images and screenshots")
                        
                        # Primary download button with unique key
                        st.download_button(
                            label="📥 Download Complete Guide",
                            data=pdf_bytes,
                            file_name="binance_api_setup_guide.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary",
                            help="Downloads the complete PDF guide with all images and step-by-step instructions",
                            key="download_pdf_primary"
                        )
                        
                        st.caption("💡 **Tip:** Open with your default PDF reader for best viewing experience")
                        
                except Exception as e:
                    st.error(f"❌ Error loading PDF file: {e}")
                    UserDashboard._show_fallback_binance_guide()
            else:
                st.warning("⚠️ PDF guide not found at expected location")
                st.info("📍 **Expected location:** `binance.pdf` in the project directory")
                
                # Show expected path for debugging
                st.code(f"Looking for: {pdf_path}")
                
                # Check if file exists with different name
                possible_names = ["binance.pdf", "Binance.pdf", "BINANCE.pdf", "binance_guide.pdf"]
                pdf_dir = os.path.dirname(__file__)
                
                st.markdown("🔍 **Checking for alternative filenames:**")
                found_alternative = False
                
                for idx, name in enumerate(possible_names):
                    alt_path = os.path.join(pdf_dir, name)
                    exists = os.path.exists(alt_path)
                    status = "✅ Found" if exists else "❌ Not found"
                    st.write(f"• {name}: {status}")
                    
                    if exists and not found_alternative:
                        found_alternative = True
                        st.success(f"📄 Found alternative file: {name}")
                        
                        try:
                            with open(alt_path, 'rb') as pdf_file:
                                alt_pdf_bytes = pdf_file.read()
                            
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                st.download_button(
                                    label=f"📥 Download {name}",
                                    data=alt_pdf_bytes,
                                    file_name="binance_api_setup_guide.pdf",
                                    mime="application/pdf",
                                    use_container_width=True,
                                    type="primary",
                                    key=f"download_pdf_alt_{idx}"
                                )
                        except Exception as e:
                            st.error(f"Error reading {name}: {e}")
                
                if not found_alternative:
                    # Show fallback guide if no PDF found
                    UserDashboard._show_fallback_binance_guide()
        with st.container():
            st.markdown("---")
            st.markdown("## 📖 Complete Binance API Setup Guide")
            
            # Close button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col3:
                if st.button("❌ Close Guide", type="secondary", use_container_width=True):
                    st.session_state.show_binance_guide = False
                    st.rerun()
            
            # Check if PDF file exists
            pdf_path = os.path.join(os.path.dirname(__file__), "binance.pdf")
            
            if os.path.exists(pdf_path):
                try:
                    # Read PDF file as bytes for display
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_bytes = pdf_file.read()
                    
                    st.success(f"📄 PDF Guide Ready - Click to view or download")
                    
                    # Display PDF using Streamlit's built-in viewer (supports images)
                    st.markdown("### 📖 PDF Viewer")
                    
                    # Create tabs for viewing options
                    tab1, tab2 = st.tabs(["🖥️ View Online", "📥 Download"])
                    
                    with tab1:
                        try:
                            # Use Streamlit's PDF display (works with images)
                            import base64
                            
                            # Encode PDF to base64 for embedding
                            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                            
                            # Create HTML embed for PDF viewer
                            pdf_display = f"""
                            <iframe 
                                src="data:application/pdf;base64,{pdf_base64}" 
                                width="100%" 
                                height="800" 
                                type="application/pdf"
                                style="border: 1px solid #ccc; border-radius: 5px;">
                                <p>Your browser does not support PDF viewing. 
                                   <a href="data:application/pdf;base64,{pdf_base64}" download="binance_api_guide.pdf">
                                   Click here to download the PDF</a>
                                </p>
                            </iframe>
                            """
                            
                            # Display the PDF
                            st.markdown(pdf_display, unsafe_allow_html=True)
                            
                            # Alternative: Use Streamlit's native PDF display
                            st.markdown("---")
                            st.markdown("#### 📄 Alternative Viewer")
                            st.markdown("*If the PDF doesn't display above, try this viewer:*")
                            
                            # Display PDF using st.download_button with auto-open
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                st.download_button(
                                    label="📖 Open PDF in New Tab",
                                    data=pdf_bytes,
                                    file_name="binance_api_setup_guide.pdf",
                                    mime="application/pdf",
                                    use_container_width=True,
                                    help="Opens PDF in a new browser tab where you can view all images and content"
                                )
                            
                        except Exception as display_error:
                            st.warning(f"⚠️ PDF viewer error: {display_error}")
                            st.info("📥 Please use the download option below to view the complete guide with images.")
                            
                            # Fallback to download button
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                st.download_button(
                                    label="📥 Download PDF Guide",
                                    data=pdf_bytes,
                                    file_name="binance_api_setup_guide.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                    
                    with tab2:
                        st.markdown("### 📥 Download Options")
                        st.info("💡 **Recommended**: Download the PDF to view all images and detailed instructions on your device.")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Primary download button
                            st.download_button(
                                label="📥 Download Full Guide",
                                data=pdf_bytes,
                                file_name="binance_api_setup_guide.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                type="primary",
                                help="Downloads the complete PDF guide with all images and step-by-step screenshots"
                            )
                        
                        with col2:
                            # Quick view button
                            st.download_button(
                                label="� Quick Download",
                                data=pdf_bytes,
                                file_name="binance_setup.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                help="Same PDF with a shorter filename for quick access"
                            )
                        
                        # File info
                        st.markdown("---")
                        st.markdown("**📋 File Information:**")
                        file_size_mb = len(pdf_bytes) / (1024 * 1024)
                        st.write(f"• **Size**: {file_size_mb:.2f} MB")
                        st.write(f"• **Format**: PDF with images and screenshots")
                        st.write(f"• **Content**: Complete Binance API setup guide")
                        st.write(f"• **Best viewed**: In your default PDF reader")
                        
                except Exception as e:
                    st.error(f"❌ Error loading PDF file: {e}")
                    UserDashboard._show_fallback_binance_guide()
            else:
                st.warning("⚠️ PDF guide not found at expected location")
                st.info("📍 **Expected location**: `binance.pdf` in the project directory")
                
                # Show expected path for debugging
                st.code(f"Looking for: {pdf_path}")
                
                # Check if file exists with different name
                possible_names = ["binance.pdf", "Binance.pdf", "BINANCE.pdf", "binance_guide.pdf"]
                pdf_dir = os.path.dirname(__file__)
                
                st.markdown("🔍 **Checking for alternative filenames:**")
                for name in possible_names:
                    alt_path = os.path.join(pdf_dir, name)
                    exists = os.path.exists(alt_path)
                    status = "✅ Found" if exists else "❌ Not found"
                    st.write(f"• {name}: {status}")
                    
                    if exists:
                        st.success(f"📄 Found alternative file: {name}")
                        if st.button(f"📖 Use {name}", key=f"use_{name}"):
                            # Update the PDF path and reload
                            st.session_state.pdf_path_override = alt_path
                            st.rerun()
                
                # Show fallback guide
                UserDashboard._show_fallback_binance_guide()

    @staticmethod
    def _show_fallback_binance_guide():
        """Show fallback detailed guide when PDF is not available"""
        st.markdown("### 📚 Detailed Binance API Setup Instructions")
        
        with st.expander("🔧 Step 1: Account Preparation", expanded=True):
            st.markdown("""
            **Before You Start:**
            1. ✅ Ensure you have a verified Binance account
            2. ✅ Complete all KYC (Know Your Customer) requirements
            3. ✅ Enable two-factor authentication (2FA)
            4. ✅ Consider using a dedicated trading account
            """)
        
        with st.expander("🔑 Step 2: Creating API Keys"):
            st.markdown("""
            **Creating Your API Keys:**
            1. 🌐 Log into your Binance account at [binance.com](https://www.binance.com)
            2. 👤 Go to your profile (top right corner)
            3. ⚙️ Select "API Management"
            4. ➕ Click "Create API"
            5. 📝 Enter a label for your API (e.g., "Copy Trading Bot")
            6. ✅ Complete any security verification (SMS, Email, 2FA)
            7. 💾 **IMPORTANT**: Save both API Key and Secret Key immediately
            """)
        
        with st.expander("🔐 Step 3: Configuring Permissions"):
            st.markdown("""
            **Required Permissions:**
            - ✅ **Enable Reading** - Required for account information
            - ✅ **Enable Spot & Margin Trading** - For spot trading
            - ✅ **Enable Futures** - For futures/derivatives trading
            - ❌ **Withdraw** - NOT recommended for security
            
            **IP Restrictions (Recommended):**
            1. 🔒 Add your server IP: `208.77.246.15`
            2. 🏠 Add your home/office IP for manual access
            3. 💡 Leave blank only if you have dynamic IP
            """)
        
        with st.expander("⚡ Step 4: Testing Your API"):
            st.markdown("""
            **Verify Your Setup:**
            1. 📋 Copy your API Key and Secret
            2. 📝 Paste them in the form above
            3. 🧪 Click "Add Account" to test
            4. ✅ You should see "Binance account added successfully!"
            
            **If Connection Fails:**
            - 🔍 Double-check API key and secret
            - 🌐 Verify IP restrictions
            - ⏰ Wait a few minutes for API activation
            - 🔐 Ensure all required permissions are enabled
            """)
        
        with st.expander("🛡️ Step 5: Security Best Practices"):
            st.markdown("""
            **Keep Your Account Safe:**
            - 🔐 Never share your API keys
            - 🔄 Rotate keys regularly (monthly recommended)
            - 📊 Monitor API usage in Binance dashboard
            - 🚫 Disable withdraw permissions
            - 🔒 Use IP restrictions when possible
            - 📱 Keep 2FA enabled
            - 💰 Consider using smaller amounts initially
            """)

def main():
    """Main application entry point"""
    # Initialize session
    SessionManager.initialize_session()
    
    # Sidebar
    with st.sidebar:
        if st.session_state.authenticated:
            st.success(f"✅ Logged in as: {st.session_state.user_data.email}")
            st.caption(f"Role: {st.session_state.user_data.role.title()}")
            
            if st.button("🚪 Logout", use_container_width=True):
                SessionManager.logout()
        else:
            st.info("🔐 Please log in to continue")
    
    # Main content based on authentication and role
    if not st.session_state.authenticated:
        AuthenticationUI.login_page()
    elif SessionManager.is_admin():
        AdminDashboard.show_admin_dashboard()
    elif SessionManager.is_approved_user():
        UserDashboard.show_user_dashboard()
    else:
        UserDashboard.show_user_dashboard()  # This will show approval pending

if __name__ == "__main__":
    main()