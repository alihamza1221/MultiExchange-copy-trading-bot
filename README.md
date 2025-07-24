# 🚀 Copy Trading Bot - Enterprise Edition

A comprehensive, role-based copy trading bot system that automatically mirrors trades from a source Binance account to multiple target accounts with advanced user management and approval workflows.

## 🌟 Key Features

### 👑 Admin Features

- **🤖 Bot Control**: Start/stop copy trading bot with real-time monitoring
- **👥 User Management**: Approve/reject user registrations with comprehensive user oversight
- **💳 Account Management**: View, edit, and delete all trading accounts across users
- **📊 System Dashboard**: Complete system metrics and trading statistics
- **⚙️ Configuration**: Advanced system settings and configuration management

### 👤 User Features

- **📝 Registration**: Self-service registration with admin approval workflow
- **💳 Account Management**: Add and manage personal Binance trading accounts
- **📊 Trading History**: View personal trading performance and history
- **🔐 Security**: Secure account management with credential validation

### 🔧 Technical Features

- **🏗️ Role-Based Access Control**: Complete RBAC implementation with admin and user roles
- **🔄 Real-Time Trading**: WebSocket-based order mirroring with position mode synchronization
- **🛡️ Enhanced Security**: Secure authentication, password hashing, and session management
- **📱 Dual Interface**: Both Streamlit web UI and FastAPI REST API
- **🗄️ Advanced Database**: MySQL with foreign key constraints and data integrity
- **⚡ High Performance**: Async operations and efficient resource management

## 📋 Prerequisites

- **Python 3.8+**
- **MySQL 8.0+**
- **Binance Futures Account** with API access
- **Valid API Credentials** for source and target accounts

## 🚀 Quick Start

### 1. **Clone and Setup**

```bash
cd c:\Users\aliha\Desktop\copy_trading
python setup_enhanced.py
```

### 2. **Configure Environment**

Your `.env` file is already configured with:

```env
# Admin Configuration
ADMIN_EMAIL="adminxmel2394@gmail.com"
ADMIN_PASSWORD="admin1234"

# Source Account (The account to copy trades from)
SOURCE_BINANCE_API_KEY="guOC851LwX9GoziDdfStNlvbRDLxsR7nQCacFfKYyMkytcFEFX8ZIMlb3WzSNjPLGg"
SOURCE_BINANCE_SECRET="LELD3xEhuqzldHdfYSS8nBSp4pPGLo9xgmFOHV9v8ddG915FTJxXp1dwFv2FFj7nmG"

# Database Configuration
DB_HOST=localhost
DB_NAME=copy_trading
DB_USER=root
DB_PASSWORD=.123
```

### 3. **Run Database Migration**

```bash
python migrate_database.py
```

### 4. **Start Application**

```bash
# Web Interface (Recommended)
python launcher.py --mode streamlit

# API Server
python launcher.py --mode fastapi

# Both Interfaces
python launcher.py --mode both
```

### 5. **Access the Application**

- **Web UI**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **Admin Login**: adminxmel2394@gmail.com / admin1234

## 🏗️ System Architecture

### **Role-Based Access Control**

#### 👑 Admin Role

- **Dashboard Access**: Complete system overview with metrics
- **Bot Control**: Start/stop trading bot with real-time status
- **User Management**:
  - View all users and their status
  - Approve/reject pending registrations
  - Monitor user activity and accounts
- **Account Management**:
  - View all trading accounts across all users
  - Edit API keys and account settings
  - Delete accounts with admin privileges
- **System Settings**: Configure system-wide parameters

#### 👤 User Role

- **Registration Flow**: Self-service registration with admin approval
- **Account Status**:
  - **Pending**: Awaiting admin approval
  - **Approved**: Full access to features
  - **Rejected**: Contact administrator
- **Personal Dashboard**:
  - Add/manage personal Binance accounts
  - View personal trading history
  - Account statistics and performance

## 📱 User Interface Guide

### **Admin Dashboard Navigation**

#### **🤖 Bot Control Tab**

- **Server Information**: IP address and current status
- **Bot Controls**: Start/stop buttons with real-time feedback
- **Status Monitoring**: Live bot status and trade monitoring

#### **👥 User Management Tab**

- **Pending Approvals**: Review and approve/reject new users
- **User Overview**: Complete list of all users with status
- **User Actions**: Approve, reject, or monitor user activity

#### **💳 Account Management Tab**

- **All Accounts View**: See all trading accounts across users
- **Account Details**: API keys, owner, creation date, trade count
- **Admin Actions**: Edit credentials, update settings, delete accounts
- **Security**: Masked API keys with edit capabilities

## ⚙️ Configuration Guide

### **Environment Variables**

| Variable                 | Description            | Current Value             |
| ------------------------ | ---------------------- | ------------------------- |
| `ADMIN_EMAIL`            | Admin account email    | `adminxmel2394@gmail.com` |
| `ADMIN_PASSWORD`         | Admin account password | `admin1234`               |
| `SOURCE_BINANCE_API_KEY` | Source account API key | Configured                |
| `SOURCE_BINANCE_SECRET`  | Source account secret  | Configured                |
| `DB_HOST`                | MySQL host             | `localhost`               |
| `DB_NAME`                | Database name          | `copy_trading`            |
| `DB_USER`                | Database user          | `root`                    |
| `DB_PASSWORD`            | Database password      | `player.123`              |

### **Binance API Setup**

#### **Security Best Practices**

- Use dedicated trading accounts
- Enable IP whitelist restrictions
- Regular key rotation
- Monitor API usage

#### **Position Mode Configuration**

- **Source Account**: Can use One-Way or Hedge mode
- **Target Accounts**: Will auto-sync to match source mode
- **Supported**: Both position modes fully supported

## 🛡️ Security Features

### **Authentication & Authorization**

- **Password Hashing**: SHA256 with secure storage
- **Session Management**: Secure session handling
- **Role-Based Access**: Granular permission system
- **Input Validation**: Comprehensive data validation

### **API Security**

- **Credential Validation**: Real-time API key testing
- **Secure Storage**: Encrypted credential storage
- **Access Control**: User-specific account access
- **Audit Logging**: Complete action logging

## 🔧 Troubleshooting

### **Common Issues**

#### **1. Database Connection Failed**

```bash
# Check MySQL service
net start mysql

# Verify credentials match your .env file
```

#### **2. Binance API Errors**

```python
# Error: "Order's position side does not match user's setting"
# Solution: Bot automatically syncs position modes

# Error: "Invalid API credentials"
# Solution: Verify API keys in .env file
```

#### **3. WebSocket Connection Issues**

```python
# Error: "Failed to create listen key"
# Solution: Check Binance API permissions

# Error: "WebSocket connection lost"
# Solution: Bot automatically reconnects
```

### **System Health Check**

```bash
# Run comprehensive system test
python test_system.py

# Test specific components
python test_binance_integration.py
```

## 🚀 Quick Start Commands

### **Essential Commands**

```bash
# Complete setup with migration
python setup_enhanced.py

# Start web interface
python launcher.py --mode streamlit

# Run database migration
python migrate_database.py

# System test
python test_system.py
```

### **Access Information**

- **Admin Email**: adminxmel2394@gmail.com
- **Admin Password**: admin1234
- **Web UI**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

## 📊 Workflow Overview

### **For Administrators**

1. **Login** with admin credentials
2. **Start Bot** from Bot Control tab
3. **Approve Users** from User Management tab
4. **Monitor Accounts** from Account Management tab
5. **Review Statistics** from Trading Stats tab

### **For Users**

1. **Register** new account
2. **Wait for Approval** from admin
3. **Add Trading Accounts** once approved
4. **Monitor Performance** in personal dashboard

### **Trading Process**

1. **Source Account** places orders
2. **Bot Detects** new orders via WebSocket
3. **Position Sync** ensures compatibility
4. **Mirror Orders** to all target accounts
5. **Log Results** to database

## 🎯 Key Benefits

### **✅ Enterprise Ready**

- Role-based access control
- Approval workflows
- Comprehensive audit trails
- Scalable architecture

### **✅ User Friendly**

- Intuitive web interface
- Self-service registration
- Real-time monitoring
- Detailed documentation

### **✅ Technically Advanced**

- WebSocket real-time trading
- Position mode synchronization
- Automatic reconnection
- Error handling and recovery

### **✅ Secure & Reliable**

- Encrypted credential storage
- Secure authentication
- Input validation
- Database integrity

---

**🎉 Your copy trading bot is ready for enterprise-level trading operations!**

Need help? Check the troubleshooting section or run the system tests to verify everything is working correctly.
