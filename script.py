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
        tab1, tab2, tab3, tab4 = st.tabs([
            "Bot Control", 
            "User Management", 
            "Account Management", 
            "Trading Stats"
        ])
        
        with tab1:
            AdminDashboard._show_bot_control()
        
        with tab2:
            AdminDashboard._show_user_management()
        
        with tab3:
            AdminDashboard._show_account_management()
        
        with tab4:
            AdminDashboard._show_trading_stats()
        

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
        """Enhanced account management for admin with Binance and Phemex tabs"""
        st.subheader("Trading Account Management")
        
        try:
            db = Database()
            # Two tabs: Binance and Phemex
            binance_tab, phemex_tab = st.tabs(["Binance Accounts", "Phemex Accounts"])

            with binance_tab:
                try:
                    accounts = db.get_all_binance_accounts()
                    
                    if accounts:
                        st.info(f"📊 **Binance Accounts**: {len(accounts)}")
                        for account in accounts:
                            with st.expander(f"💳 {account['account_name'] or 'Unnamed Account'} - {account['user_email']}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**Account Details:**")
                                    st.write(f"• **Owner**: {account['user_email']}")
                                    st.write(f"• **Created**: {account.get('created_at', 'N/A')}")
                                    st.write(f"• **Total Trades**: {account.get('total_trades', 0)}")
                                with col2:
                                    st.write("**API Configuration:**")
                                    api_key = account.get('api_key', '')
                                    secret_key = account.get('secret_key', '')
                                    if api_key:
                                        st.code(f"API Key: {api_key[:8]}...{api_key[-8:]}")
                                    if secret_key:
                                        st.code(f"Secret: {secret_key[:8]}...{secret_key[-8:]}")
                                # Account actions
                                col1a, col2a, col3a = st.columns(3)
                                with col1a:
                                    if st.button("Edit", key=f"edit_{account['id']}"):
                                        st.session_state[f"editing_{account['id']}"] = True
                                        st.rerun()
                                with col2a:
                                    if st.button("Delete", key=f"delete_{account['id']}", type="secondary"):
                                        if st.button("Confirm Delete", key=f"confirm_delete_{account['id']}", type="primary"):
                                            if db.delete_account_admin(account['id']):
                                                st.success("Account deleted!")
                                                time.sleep(1)
                                                st.rerun()
                                # Edit form
                                if st.session_state.get(f"editing_{account['id']}", False):
                                    with st.form(f"edit_form_{account['id']}"):
                                        st.write("**Edit Account:**")
                                        new_name = st.text_input("Account Name", value=account['account_name'] or "")
                                        new_api_key = st.text_input("API Key", value=account.get('api_key', ''))
                                        new_secret = st.text_input("Secret Key", value=account.get('secret_key', ''), type="password")
                                        colL, colR = st.columns(2)
                                        with colL:
                                            if st.form_submit_button("Save", type="primary"):
                                                if db.update_binance_account(account['id'], new_api_key, new_secret, new_name):
                                                    st.success("Account updated!")
                                                    st.session_state[f"editing_{account['id']}"] = False
                                                    time.sleep(1)
                                                    st.rerun()
                                        with colR:
                                            if st.form_submit_button("Cancel"):
                                                st.session_state[f"editing_{account['id']}"] = False
                                                st.rerun()
                                st.divider()
                    else:
                        st.info("📝 No trading accounts configured yet")
                except Exception as e:
                    st.error(f"Error loading Binance account management: {e}")

            with phemex_tab:
                try:
                    # Try to fetch all Phemex accounts (admin view)
                    try:
                        p_accounts = db.get_all_phemex_accounts()
                    except Exception as fetch_err:
                        logging.warning(f"get_all_phemex_accounts unavailable or failed: {fetch_err}")
                        p_accounts = []
                    
                    if p_accounts:
                        st.info(f"📊 **Phemex Accounts**: {len(p_accounts)}")
                        for account in p_accounts:
                            with st.expander(f"💳 {account.get('account_name') or 'Unnamed Account'} - {account.get('user_email', '')}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**Account Details:**")
                                    st.write(f"• **Owner**: {account.get('user_email', 'N/A')}")
                                    st.write(f"• **Created**: {account.get('created_at', 'N/A')}")
                                    # Total trades (from precomputed field or fallback to query)
                                    total_trades = account.get('total_trades')
                                    if total_trades is None:
                                        try:
                                            trades = db.get_phemex_trades(account_id=account['id'])
                                            total_trades = len(trades)
                                        except Exception:
                                            total_trades = 'N/A'
                                    st.write(f"• **Total Trades**: {total_trades}")
                                with col2:
                                    st.write("**API Configuration:**")
                                    api_key = account.get('api_key', '')
                                    secret_key = account.get('secret_key', '')
                                    if api_key:
                                        st.code(f"API Key: {api_key[:8]}...{api_key[-8:]}")
                                    if secret_key:
                                        st.code(f"Secret: {secret_key[:8]}...{secret_key[-8:]}")
                                # Actions (Edit if available, Delete with admin or fallback)
                                col1a, col2a = st.columns(2)
                                with col1a:
                                    if hasattr(db, 'update_phemex_account'):
                                        if st.button("Edit", key=f"phemex_edit_{account['id']}"):
                                            st.session_state[f"phemex_editing_{account['id']}"] = True
                                            st.rerun()
                                with col2a:
                                    if st.button("Delete", key=f"phemex_delete_{account['id']}", type="secondary"):
                                        deleted = False
                                        try:
                                            if hasattr(db, 'delete_phemex_account_admin'):
                                                deleted = db.delete_phemex_account_admin(account['id'])
                                            else:
                                                deleted = db.delete_phemex_account(account['id'], account.get('user_email'))
                                        except Exception as de:
                                            logging.error(f"Delete Phemex account failed: {de}")
                                        if deleted:
                                            st.success("Phemex account deleted!")
                                            time.sleep(1)
                                            st.rerun()
                                # Edit form (only if method exists)
                                if st.session_state.get(f"phemex_editing_{account['id']}", False) and hasattr(db, 'update_phemex_account'):
                                    with st.form(f"phemex_edit_form_{account['id']}"):
                                        new_name = st.text_input("Account Name", value=account.get('account_name', '') or '')
                                        new_api_key = st.text_input("API Key", value=account.get('api_key', '') or '')
                                        new_secret = st.text_input("Secret Key", value=account.get('secret_key', '') or '', type="password")
                                        c1, c2 = st.columns(2)
                                        with c1:
                                            if st.form_submit_button("Save", type="primary"):
                                                try:
                                                    if db.update_phemex_account(account['id'], new_api_key, new_secret, new_name):
                                                        st.success("Account updated!")
                                                        st.session_state[f"phemex_editing_{account['id']}"] = False
                                                        time.sleep(1)
                                                        st.rerun()
                                                    else:
                                                        st.error("Failed to update account")
                                                except Exception as ue:
                                                    st.error(f"Update error: {ue}")
                                        with c2:
                                            if st.form_submit_button("Cancel"):
                                                st.session_state[f"phemex_editing_{account['id']}"] = False
                                                st.rerun()
                                st.divider()
                    else:
                        st.info("📝 No Phemex accounts configured yet")
                except Exception as e:
                    st.error(f"Error loading Phemex account management: {e}")
        except Exception as e:
            st.error(f"Error loading account management: {e}")
    @staticmethod
    def _show_trading_stats() -> None:
        """Show trading statistics split by exchange (Binance / Phemex)"""
        st.subheader("📊 Trading Statistics")
        
        try:
            db = Database()
            binance_tab, phemex_tab = st.tabs(["🔶 Binance", "🔴 Phemex"])

            # BINANCE TAB
            with binance_tab:
                try:
                    accounts = db.get_all_binance_accounts() or []
                except Exception as e:
                    logging.error(f"Failed to load Binance accounts: {e}")
                    accounts = []
                
                all_trades = []
                name_by_id = {}
                for acc in accounts:
                    acc_id = acc.get('id')
                    name_by_id[acc_id] = acc.get('account_name') or 'Unnamed Account'
                    try:
                        trades = db.get_account_trades(acc_id) or []
                    except Exception as te:
                        logging.error(f"Failed to load trades for Binance account {acc_id}: {te}")
                        trades = []
                    for t in trades:
                        t['account_id'] = acc_id
                        t['account_name'] = name_by_id[acc_id]
                    all_trades.extend(trades)
                
                if not all_trades:
                    st.info("📝 No Binance trades found.")
                else:
                    UserDashboard._display_trades_table(all_trades, "Binance", show_account_column=True)

            # PHEMEX TAB
            with phemex_tab:
                try:
                    phemex_trades = db.get_phemex_trades() or []
                except Exception as pe:
                    logging.error(f"Failed to load Phemex trades: {pe}")
                    phemex_trades = []
                
                # Map account_id to account_name if available
                name_by_id = {}
                try:
                    phemex_accounts = db.get_all_phemex_accounts() or []
                    name_by_id = {a.get('id'): (a.get('account_name') or 'Unnamed Account') for a in phemex_accounts}
                except Exception as ae:
                    logging.warning(f"get_all_phemex_accounts unavailable or failed: {ae}")
                    name_by_id = {}
                
                for t in phemex_trades:
                    t['account_name'] = name_by_id.get(t.get('account_id'), 'Unknown Account')
                
                if not phemex_trades:
                    st.info("📝 No Phemex trades found.")
                else:
                    UserDashboard._display_trades_table(phemex_trades, "Phemex", show_account_column=True)
        except Exception as e:
            st.error(f"Error loading trading statistics: {e}")
            logging.error(f"Trading statistics error: {e}")
class UserDashboard:
    """User dashboard with limited access"""
    
    @staticmethod
    def show_user_dashboard() -> None:
        """Main user dashboard with account details navigation"""
        # Check if we should show account details page
        if st.session_state.get('show_account_details', False) and st.session_state.get('selected_account'):
            UserDashboard._show_account_details()
            return        
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
                    # Binance setup help
                    st.markdown("---")
                    st.markdown("### 💡 Binance Setup Help")
                    
                    col1, = st.columns(1)
                    with col1:
                        st.info("""
                        **📚 API Setup Guide:**
                        1. Visit [Binance](https://www.binance.com)
                        2. Go to API Management
                        3. Create new API key
                        4. Enable trading permissions
                        """)
                    
                    # Detailed PDF guide button
                    st.markdown("---")
                    col1, = st.columns(1)
                    pdf_path = os.path.join(os.path.dirname(__file__), "binance.pdf")

                    if os.path.exists(pdf_path):
                        try:
                            # Read PDF file as bytes for download
                            with open(pdf_path, 'rb') as pdf_file:
                                pdf_bytes = pdf_file.read()

                            st.success("📄 PDF Guide Available - Download to view complete instructions with images")
                            with col1:
                                # File info
                                file_size_mb = len(pdf_bytes) / (1024 * 1024)
                                st.markdown(f"**📋 File Size:** {file_size_mb:.2f} MB")
                                st.markdown("**📄 Format:** PDF with images and screenshots")

                                # Primary download button with unique key
                                st.download_button(
                                    label="📥 Download Complete Guide",
                                    data=pdf_bytes,
                                    file_name="binance.pdf",
                                    mime="application/pdf",
                                    use_container_width=True,
                                    type="primary",
                                    help="Downloads the complete PDF guide with step-by-step instructions",
                                    key="download_pdf_primary"
                                )

                                st.caption("💡 **Tip:** Open with your default PDF reader for best viewing experience")
                        except Exception as e:
                            st.info(f"Error loading PDF guide: {e}")
                    st.markdown("---")
                    st.markdown("### Add Binance Account")

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
                                if exchange_type == 'binance':
                                    with col3:
                                        if st.button("📊 Details",  key=f"details_{exchange_type}_{account   ['id']}"):
                                            st.session_state.selected_account =     account['id']
                                            st.session_state.   selected_exchange_type =   exchange_type
                                            st.session_state.   show_account_details = True
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
        """Show user's trading history with separate tabs for different exchanges"""
        st.subheader("📊 My Trading History")
        
        try:
            db = Database()
            user_email = st.session_state.user_data.email
            
            # Get user's accounts to filter trades
            binance_accounts = db.get_user_accounts(user_email) or []
            phemex_accounts = db.get_user_phemex_accounts(user_email) or []
            
            # Create tabs for different exchanges
            tab1, tab2, tab3 = st.tabs(["🔶 Binance Trades", "🔴 Phemex Trades", "📊 Overall Summary"])
            
            with tab1:
                UserDashboard._show_binance_trades(db, binance_accounts)
            
            with tab2:
                UserDashboard._show_phemex_trades(db, phemex_accounts, user_email)
            
            with tab3:
                UserDashboard._show_trading_summary(db, binance_accounts, phemex_accounts, user_email)
                
        except Exception as e:
            st.error(f"Error loading trading history: {e}")
            logging.error(f"Trading history error: {e}")

    @staticmethod
    def _show_binance_trades(db, binance_accounts):
        """Show Binance trading history"""
        st.subheader("🔶 Binance Trading History")
        
        if not binance_accounts:
            st.info("📝 No Binance accounts found. Add a Binance account in the 'My Accounts' tab to see trades here.")
            return
        
        # Account selector for multiple accounts
        if len(binance_accounts) > 1:
            account_options = {account['id']: f"{account['account_name'] or 'Unnamed Account'} ({account['api_key'][:8]}...)" 
                             for account in binance_accounts}
            account_options['all'] = "All Accounts"
            
            selected_account = st.selectbox(
                "Select Account:",
                options=list(account_options.keys()),
                format_func=lambda x: account_options[x],
                index=len(account_options) - 1  # Default to "All Accounts"
            )
        else:
            selected_account = binance_accounts[0]['id']
        
        # Get trades based on selection
        all_binance_trades = []
        
        if selected_account == 'all':
            # Get trades from all accounts
            for account in binance_accounts:
                account_trades = db.get_account_trades(account['id']) or []
                for trade in account_trades:
                    trade['account_name'] = account['account_name'] or 'Unnamed Account'
                    trade['account_id'] = account['id']
                all_binance_trades.extend(account_trades)
        else:
            # Get trades from selected account
            account_trades = db.get_account_trades(selected_account) or []
            account_name = next((acc['account_name'] for acc in binance_accounts if acc['id'] == selected_account), 'Unnamed Account')
            for trade in account_trades:
                trade['account_name'] = account_name
                trade['account_id'] = selected_account
            all_binance_trades = account_trades
        
        UserDashboard._display_trades_table(all_binance_trades, "Binance", show_account_column=(selected_account == 'all'))

    @staticmethod
    def _show_phemex_trades(db, phemex_accounts, user_email):
        """Show Phemex trading history"""
        st.subheader("🔴 Phemex Trading History")
        
        if not phemex_accounts:
            st.info("📝 No Phemex accounts found. Add a Phemex account in the 'My Accounts' tab to see trades here.")
            return
        
        # Account selector for multiple accounts
        if len(phemex_accounts) > 1:
            account_options = {account['id']: f"{account['account_name'] or 'Unnamed Account'} ({account['api_key'][:8]}...)" 
                             for account in phemex_accounts}
            account_options['all'] = "All Accounts"
            
            selected_account = st.selectbox(
                "Select Phemex Account:",
                options=list(account_options.keys()),
                format_func=lambda x: account_options[x],
                index=len(account_options) - 1  # Default to "All Accounts"
            )
        else:
            selected_account = phemex_accounts[0]['id']
        
        # Get Phemex trades
        try:
            if selected_account == 'all':
                # Get all Phemex trades for user
                all_phemex_trades = db.get_phemex_trades() or []
                # Filter by user's account IDs
                user_account_ids = [acc['id'] for acc in phemex_accounts]
                all_phemex_trades = [trade for trade in all_phemex_trades if trade.get('account_id') in user_account_ids]
                
                # Add account names
                for trade in all_phemex_trades:
                    account = next((acc for acc in phemex_accounts if acc['id'] == trade.get('account_id')), None)
                    trade['account_name'] = account['account_name'] if account else 'Unknown Account'
            else:
                # Get trades for specific account
                all_phemex_trades = db.get_phemex_trades(account_id=selected_account) or []
                account_name = next((acc['account_name'] for acc in phemex_accounts if acc['id'] == selected_account), 'Unnamed Account')
                for trade in all_phemex_trades:
                    trade['account_name'] = account_name
            
            UserDashboard._display_trades_table(all_phemex_trades, "Phemex", show_account_column=(selected_account == 'all'))
            
        except Exception as e:
            st.error(f"Error loading Phemex trades: {e}")
            logging.error(f"Phemex trades error: {e}")

    @staticmethod
    def _show_trading_summary(db, binance_accounts, phemex_accounts, user_email):
        """Show overall trading summary across all exchanges"""
        st.subheader("📊 Overall Trading Summary")
        
        try:
            # Get all trades from both exchanges
            all_binance_trades = []
            all_phemex_trades = []
            
            # Collect Binance trades
            for account in binance_accounts:
                account_trades = db.get_account_trades(account['id']) or []
                for trade in account_trades:
                    trade['exchange'] = 'Binance'
                    trade['account_name'] = account['account_name'] or 'Unnamed Account'
                all_binance_trades.extend(account_trades)
            
            # Collect Phemex trades
            try:
                user_account_ids = [acc['id'] for acc in phemex_accounts]
                phemex_trades = db.get_phemex_trades() or []
                all_phemex_trades = [trade for trade in phemex_trades if trade.get('account_id') in user_account_ids]
                
                for trade in all_phemex_trades:
                    trade['exchange'] = 'Phemex'
                    account = next((acc for acc in phemex_accounts if acc['id'] == trade.get('account_id')), None)
                    trade['account_name'] = account['account_name'] if account else 'Unknown Account'
                    
            except Exception as e:
                logging.error(f"Error loading Phemex trades for summary: {e}")
                all_phemex_trades = []
            
            # Summary metrics
            total_trades = len(all_binance_trades) + len(all_phemex_trades)
            
            if total_trades > 0:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📊 Total Trades", total_trades)
                
                with col2:
                    st.metric("🔶 Binance Trades", len(all_binance_trades))
                
                with col3:
                    st.metric("🔴 Phemex Trades", len(all_phemex_trades))
                
                with col4:
                    success_count = len([t for t in (all_binance_trades + all_phemex_trades) 
                                       if t.get('status') in ['FILLED', 'MIRRORED']])
                    success_rate = (success_count / total_trades * 100) if total_trades > 0 else 0
                    st.metric("✅ Success Rate", f"{success_rate:.1f}%")
                
                # Exchange distribution chart
                st.markdown("---")
                st.subheader("📈 Trading Distribution")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Exchange distribution
                    exchange_data = {
                        'Exchange': ['Binance', 'Phemex'],
                        'Trades': [len(all_binance_trades), len(all_phemex_trades)]
                    }
                    if exchange_data['Trades'][0] > 0 or exchange_data['Trades'][1] > 0:
                        st.bar_chart(data=exchange_data, x='Exchange', y='Trades')
                
                with col2:
                    # Side distribution
                    all_trades = all_binance_trades + all_phemex_trades
                    buy_count = len([t for t in all_trades if t.get('side') == 'BUY'])
                    sell_count = len([t for t in all_trades if t.get('side') == 'SELL'])
                    
                    side_data = {
                        'Side': ['BUY', 'SELL'],
                        'Count': [buy_count, sell_count]
                    }
                    if side_data['Count'][0] > 0 or side_data['Count'][1] > 0:
                        st.bar_chart(data=side_data, x='Side', y='Count')
                
                # Recent activity across all exchanges
                st.markdown("---")
                st.subheader("🕐 Recent Activity (All Exchanges)")
                
                # Combine and sort all trades
                combined_trades = []
                for trade in all_binance_trades:
                    trade['exchange'] = 'Binance'
                    combined_trades.append(trade)
                for trade in all_phemex_trades:
                    trade['exchange'] = 'Phemex'
                    combined_trades.append(trade)
                
                # Sort by trade time (most recent first)
                combined_trades.sort(key=lambda x: x.get('trade_time', ''), reverse=True)
                
                # Show recent trades (limit to 20)
                recent_trades = combined_trades[:20]
                UserDashboard._display_trades_table(recent_trades, "Combined", show_account_column=True, show_exchange_column=True)
                
            else:
                st.info("📝 No trading activity found across any accounts.")
                st.markdown("""
                **Getting Started:**
                - 🔗 Add trading accounts in the 'My Accounts' tab
                - 🤖 Ensure the copy trading bot is running
                - 📡 Bot will automatically copy trades when signals are received
                - 📊 Your trading history will appear here
                """)
                
        except Exception as e:
            st.error(f"Error generating trading summary: {e}")
            logging.error(f"Trading summary error: {e}")

    @staticmethod
    def _display_trades_table(trades, exchange_name, show_account_column=False, show_exchange_column=False):
        """Display trades in a formatted table with filtering options"""
        
        if not trades:
            st.info(f"📝 No {exchange_name} trades found.")
            return
        
        # Filter options
        st.markdown("### 🔍 Filter Options")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            symbols = list(set([trade.get('symbol', 'N/A') for trade in trades]))
            selected_symbol = st.selectbox("Symbol", ["All"] + sorted(symbols), key=f"symbol_{exchange_name}")
        
        with col2:
            sides = ['All', 'BUY', 'SELL']
            selected_side = st.selectbox("Side", sides, key=f"side_{exchange_name}")
        
        with col3:
            statuses = list(set([trade.get('status', 'N/A') for trade in trades]))
            selected_status = st.selectbox("Status", ["All"] + sorted(statuses), key=f"status_{exchange_name}")
        
        with col4:
            limit_options = [10, 25, 50, 100, "All"]
            selected_limit = st.selectbox("Show", limit_options, index=1, key=f"limit_{exchange_name}")
        
        # Apply filters
        filtered_trades = trades
        if selected_symbol != "All":
            filtered_trades = [t for t in filtered_trades if t.get('symbol') == selected_symbol]
        if selected_side != "All":
            filtered_trades = [t for t in filtered_trades if t.get('side') == selected_side]
        if selected_status != "All":
            filtered_trades = [t for t in filtered_trades if t.get('status') == selected_status]
        
        # Apply limit
        if selected_limit != "All":
            filtered_trades = filtered_trades[:selected_limit]
        
        # Sort by most recent
        filtered_trades.sort(key=lambda x: x.get('trade_time', ''), reverse=True)
        
        # Display summary
        st.markdown(f"### 📋 {exchange_name} Trades ({len(filtered_trades)} shown)")
        
        if filtered_trades:
            # Quick stats
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                buy_orders = len([t for t in filtered_trades if t.get('side') == 'BUY'])
                st.metric("📈 Buy Orders", buy_orders)
            
            with col2:
                sell_orders = len([t for t in filtered_trades if t.get('side') == 'SELL'])
                st.metric("📉 Sell Orders", sell_orders)
            
            with col3:
                successful = len([t for t in filtered_trades if t.get('status') in ['FILLED', 'MIRRORED']])
                st.metric("✅ Successful", successful)
            
            with col4:
                total_volume = sum([float(t.get('quantity', 0)) for t in filtered_trades])
                st.metric("📊 Total Volume", f"{total_volume:.4f}")
            
            st.markdown("---")
            
            # Display trades
            for i, trade in enumerate(filtered_trades):
                with st.container():
                    # Determine number of columns based on what we need to show
                    num_cols = 7
                    if show_account_column:
                        num_cols += 1
                    if show_exchange_column:
                        num_cols += 1
                    
                    cols = st.columns(num_cols)
                    col_idx = 0
                    
                    # Symbol
                    with cols[col_idx]:
                        symbol = trade.get('symbol', 'N/A')
                        st.write(f"**{symbol}**")
                        order_id = trade.get('order_id', 'N/A')
                        if len(str(order_id)) > 15:
                            st.caption(f"ID: {str(order_id)[:12]}...")
                        else:
                            st.caption(f"ID: {order_id}")
                    col_idx += 1
                    
                    # Side
                    with cols[col_idx]:
                        side = trade.get('side', 'N/A')
                        side_color = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "⚪"
                        st.write(f"{side_color} {side}")
                    col_idx += 1
                    
                    # Type
                    with cols[col_idx]:
                        order_type = trade.get('order_type', 'N/A')
                        st.write(f"📋 {order_type}")
                    col_idx += 1
                    
                    # Quantity
                    with cols[col_idx]:
                        quantity = trade.get('quantity', 0)
                        st.write(f"📊 {quantity}")
                    col_idx += 1
                    
                    # Price
                    with cols[col_idx]:
                        price = trade.get('price')
                        if price and float(price) > 0:
                            st.write(f"💰 ${float(price):,.4f}")
                        else:
                            st.write("💰 Market")
                    col_idx += 1
                    
                    # Status
                    with cols[col_idx]:
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
                    col_idx += 1
                    
                    # Time
                    with cols[col_idx]:
                        trade_time = trade.get('trade_time', 'N/A')
                        formatted_time = safe_datetime_to_string(trade_time)
                        if formatted_time != 'N/A' and len(formatted_time) >= 10:
                            try:
                                date_part = formatted_time[5:10].replace('-', '/')
                                time_part = formatted_time[11:16] if len(formatted_time) > 11 else ""
                                short_display = f"{date_part} {time_part}".strip()
                                st.write(f"⏰ {short_display}")
                            except:
                                st.write(f"⏰ {formatted_time}")
                        else:
                            st.write("⏰ N/A")
                    col_idx += 1
                    
                    # Account (if showing)
                    if show_account_column:
                        with cols[col_idx]:
                            account_name = trade.get('account_name', 'Unknown')
                            if len(account_name) > 15:
                                st.caption(f"👤 {account_name[:12]}...")
                            else:
                                st.caption(f"👤 {account_name}")
                        col_idx += 1
                    
                    # Exchange (if showing)
                    if show_exchange_column:
                        with cols[col_idx]:
                            exchange = trade.get('exchange', 'Unknown')
                            exchange_icons = {'Binance': '🔶', 'Phemex': '🔴'}
                            icon = exchange_icons.get(exchange, '🔗')
                            st.caption(f"{icon} {exchange}")
                    
                    if i < len(filtered_trades) - 1:  # Don't add divider after last item
                        st.divider()
        else:
            st.info("📝 No trades match the selected filters.")

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