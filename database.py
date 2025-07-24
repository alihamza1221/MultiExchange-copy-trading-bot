import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

load_dotenv()

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.database = os.getenv('DB_NAME', 'copy_trading')
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '')
        self.connection = None
        
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
            if self.connection.is_connected():
                logging.info("Successfully connected to MySQL database")
                return True
        except Error as e:
            logging.error(f"Error while connecting to MySQL: {e}")
            return False
    
    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logging.info("MySQL connection is closed")
    
    def create_tables(self):
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        
        # Users table with role support
        users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role ENUM('admin', 'user') DEFAULT 'user',
            status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_by INT NULL,
            approved_at TIMESTAMP NULL,
            FOREIGN KEY (approved_by) REFERENCES users(id)
        )
        """
        
        # Binance accounts table
        binance_accounts_table = """
        CREATE TABLE IF NOT EXISTS binance_accounts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            api_key VARCHAR(255) NOT NULL,
            secret_key VARCHAR(255) NOT NULL,
            account_name VARCHAR(100),
            total_trades INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
        """
        
        # Trades table
        trades_table = """
        CREATE TABLE IF NOT EXISTS trades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            account_id INT NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL,
            order_type VARCHAR(50) NOT NULL,
            quantity DECIMAL(20, 8) NOT NULL,
            price DECIMAL(20, 8),
            stop_price DECIMAL(20, 8),
            order_id BIGINT,
            status VARCHAR(50),
            trade_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES binance_accounts(id)
        )
        """
        
        try:
            cursor.execute(users_table)
            cursor.execute(binance_accounts_table)
            cursor.execute(trades_table)
            self.connection.commit()
            
            # Insert admin user from environment variables
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@test.com').strip('"')
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123').strip('"')
            
            admin_user_query = """
            INSERT IGNORE INTO users (email, password, role, status, approved_at) 
            VALUES (%s, %s, 'admin', 'approved', NOW())
            """
            cursor.execute(admin_user_query, (admin_email, admin_password))
            self.connection.commit()
            
            logging.info("Database tables created successfully")
            return True
        except Error as e:
            logging.error(f"Error creating tables: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def authenticate_user(self, email, password):
        """Authenticate user and return user details"""
        if not self.connect():
            return None
            
        cursor = self.connection.cursor(dictionary=True)
        query = """
        SELECT id, email, role, status FROM users 
        WHERE email = %s AND password = %s
        """
        
        try:
            cursor.execute(query, (email, password))
            result = cursor.fetchone()
            return result
        except Error as e:
            logging.error(f"Error authenticating user: {e}")
            return None
        finally:
            cursor.close()
            self.disconnect()
    
    def register_user(self, email, password):
        """Register a new user with pending status"""
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        query = """
        INSERT INTO users (email, password, role, status)
        VALUES (%s, %s, 'user', 'pending')
        """
        
        try:
            cursor.execute(query, (email, password))
            self.connection.commit()
            logging.info(f"User registered with pending status: {email}")
            return cursor.lastrowid
        except Error as e:
            logging.error(f"Error registering user: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def get_pending_users(self):
        """Get all users with pending status"""
        if not self.connect():
            return []
            
        cursor = self.connection.cursor(dictionary=True)
        query = """
        SELECT id, email, created_at FROM users 
        WHERE status = 'pending' 
        ORDER BY created_at ASC
        """
        
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as e:
            logging.error(f"Error getting pending users: {e}")
            return []
        finally:
            cursor.close()
            self.disconnect()
    
    def approve_user(self, user_id, admin_id):
        """Approve a pending user"""
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        query = """
        UPDATE users 
        SET status = 'approved', approved_by = %s, approved_at = NOW()
        WHERE id = %s AND status = 'pending'
        """
        
        try:
            cursor.execute(query, (admin_id, user_id))
            self.connection.commit()
            return cursor.rowcount > 0
        except Error as e:
            logging.error(f"Error approving user: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def reject_user(self, user_id, admin_id):
        """Reject a pending user"""
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        query = """
        UPDATE users 
        SET status = 'rejected', approved_by = %s, approved_at = NOW()
        WHERE id = %s AND status = 'pending'
        """
        
        try:
            cursor.execute(query, (admin_id, user_id))
            self.connection.commit()
            return cursor.rowcount > 0
        except Error as e:
            logging.error(f"Error rejecting user: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def get_all_users(self):
        """Get all users (admin only)"""
        if not self.connect():
            return []
            
        cursor = self.connection.cursor(dictionary=True)
        query = """
        SELECT u.id, u.email, u.role, u.status, u.created_at,
               a.email as approved_by_email, u.approved_at
        FROM users u
        LEFT JOIN users a ON u.approved_by = a.id
        ORDER BY u.created_at DESC
        """
        
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as e:
            logging.error(f"Error getting all users: {e}")
            return []
        finally:
            cursor.close()
            self.disconnect()
    
    def add_binance_account_with_exchange_type(self, user_email, api_key, secret_key, account_name=None, exchange_type='binance'):
        """Add a new trading account with exchange type support"""
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        
        # Check if exchange_type column exists, if not use old method
        try:
            # First check if the column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'binance_accounts' AND COLUMN_NAME = 'exchange_type'
            """, (os.getenv('DB_NAME', 'copy_trading'),))
            
            column_exists = cursor.fetchone()[0] > 0
            
            if column_exists:
                # Use new schema with exchange_type
                query = """
                INSERT INTO binance_accounts (user_email, exchange_type, api_key, secret_key, account_name)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (user_email, exchange_type, api_key, secret_key, account_name))
            else:
                # Use old schema without exchange_type
                query = """
                INSERT INTO binance_accounts (user_email, api_key, secret_key, account_name)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(query, (user_email, api_key, secret_key, account_name))
            
            self.connection.commit()
            logging.info(f"Account added for {user_email} on {exchange_type}")
            return cursor.lastrowid
            
        except Error as e:
            logging.error(f"Error adding {exchange_type} account: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    # Override the original method to maintain compatibility
    def add_binance_account(self, user_email, api_key, secret_key, account_name=None, exchange_type='binance'):
        """Add a new trading account with optional exchange type support"""
        return self.add_binance_account_with_exchange_type(user_email, api_key, secret_key, account_name, exchange_type)
    
    def get_user_accounts(self, user_email):
        if not self.connect():
            return []
            
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM binance_accounts WHERE user_email = %s"
        
        try:
            cursor.execute(query, (user_email,))
            result = cursor.fetchall()
            return result
        except Error as e:
            logging.error(f"Error getting user accounts: {e}")
            return []
        finally:
            cursor.close()
            self.disconnect()
    
    def delete_account(self, account_id, user_email):
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        query = "DELETE FROM binance_accounts WHERE id = %s AND user_email = %s"
        
        try:
            cursor.execute(query, (account_id, user_email))
            self.connection.commit()
            return cursor.rowcount > 0
        except Error as e:
            logging.error(f"Error deleting account: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def get_all_binance_accounts(self):
        """Get all Binance accounts (admin view)"""
        if not self.connect():
            return []
            
        cursor = self.connection.cursor(dictionary=True)
        query = """
        SELECT ba.*, u.email as user_email 
        FROM binance_accounts ba
        JOIN users u ON ba.user_email = u.email
        ORDER BY ba.created_at DESC
        """
        
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as e:
            logging.error(f"Error getting all Binance accounts: {e}")
            return []
        finally:
            cursor.close()
            self.disconnect()
    
    def update_binance_account(self, account_id, api_key, secret_key, account_name):
        """Update Binance account credentials"""
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        query = """
        UPDATE binance_accounts 
        SET api_key = %s, secret_key = %s, account_name = %s
        WHERE id = %s
        """
        
        try:
            cursor.execute(query, (api_key, secret_key, account_name, account_id))
            self.connection.commit()
            return cursor.rowcount > 0
        except Error as e:
            logging.error(f"Error updating Binance account: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def delete_account_admin(self, account_id):
        """Delete account (admin privilege)"""
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        query = "DELETE FROM binance_accounts WHERE id = %s"
        
        try:
            cursor.execute(query, (account_id,))
            self.connection.commit()
            return cursor.rowcount > 0
        except Error as e:
            logging.error(f"Error deleting account (admin): {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def get_account_by_id(self, account_id, user_email):
        """Get specific account information by ID for a user"""
        if not self.connect():
            return None
            
        cursor = self.connection.cursor(dictionary=True)
        query = """
        SELECT * FROM binance_accounts 
        WHERE id = %s AND user_email = %s
        """
        
        try:
            cursor.execute(query, (account_id, user_email))
            result = cursor.fetchone()
            return result
        except Error as e:
            logging.error(f"Error getting account by ID: {e}")
            return None
        finally:
            cursor.close()
            self.disconnect()
    
    def get_account_trades(self, account_id):
        """Get trading history for a specific account"""
        if not self.connect():
            return []
            
        cursor = self.connection.cursor(dictionary=True)
        query = """
        SELECT t.*, ba.account_name, ba.user_email
        FROM trades t
        JOIN binance_accounts ba ON t.account_id = ba.id
        WHERE t.account_id = %s
        ORDER BY t.trade_time DESC
        LIMIT 100
        """
        
        try:
            cursor.execute(query, (account_id,))
            results = cursor.fetchall()
            return results or []
        except Error as e:
            logging.error(f"Error getting account trades: {e}")
            return []
        finally:
            cursor.close()
            self.disconnect()
    
    def add_trade(self, account_id, symbol, side, order_type, quantity, 
                  price=None, stop_price=None, order_id=None, status='PENDING', source_order_id=None):
        """Add a trade record to the database"""
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        query = """
        INSERT INTO trades (account_id, symbol, side, order_type, quantity, 
                           price, stop_price, order_id, status, source_order_id, trade_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        try:
            cursor.execute(query, (
                account_id, symbol, side, order_type, quantity,
                price, stop_price, order_id, status, source_order_id
            ))
            self.connection.commit()
            
            # Update account trade count
            cursor.execute("""
                UPDATE binance_accounts 
                SET total_trades = total_trades + 1 
                WHERE id = %s
            """, (account_id,))
            self.connection.commit()
            
            logging.info(f"Trade recorded for account {account_id}: {symbol} {side} {quantity}")
            return cursor.lastrowid
        except Error as e:
            logging.error(f"Error adding trade: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()