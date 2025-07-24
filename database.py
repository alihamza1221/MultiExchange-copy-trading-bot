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
        
        # Users table
        users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            # Insert default user
            default_user_query = """
            INSERT IGNORE INTO users (email, password) 
            VALUES (%s, %s)
            """
            cursor.execute(default_user_query, ('admin@test.com', 'admin123'))
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
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        query = "SELECT email FROM users WHERE email = %s AND password = %s"
        
        try:
            cursor.execute(query, (email, password))
            result = cursor.fetchone()
            return result is not None
        except Error as e:
            logging.error(f"Error authenticating user: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def add_binance_account(self, user_email, api_key, secret_key, account_name):
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        query = """
        INSERT INTO binance_accounts (user_email, api_key, secret_key, account_name)
        VALUES (%s, %s, %s, %s)
        """
        
        try:
            cursor.execute(query, (user_email, api_key, secret_key, account_name))
            self.connection.commit()
            logging.info(f"Binance account added for user: {user_email}")
            return cursor.lastrowid
        except Error as e:
            logging.error(f"Error adding Binance account: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
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
        if not self.connect():
            return []
            
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM binance_accounts"
        
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
    
    def add_trade(self, account_id, symbol, side, order_type, quantity, price, stop_price, order_id, status):
        if not self.connect():
            return False
            
        cursor = self.connection.cursor()
        query = """
        INSERT INTO trades (account_id, symbol, side, order_type, quantity, price, stop_price, order_id, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            cursor.execute(query, (account_id, symbol, side, order_type, quantity, price, stop_price, order_id, status))
            self.connection.commit()
            
            # Update total trades count
            update_query = "UPDATE binance_accounts SET total_trades = total_trades + 1 WHERE id = %s"
            cursor.execute(update_query, (account_id,))
            self.connection.commit()
            
            return True
        except Error as e:
            logging.error(f"Error adding trade: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def get_account_trades(self, account_id):
        if not self.connect():
            return []
            
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM trades WHERE account_id = %s ORDER BY trade_time DESC"
        
        try:
            cursor.execute(query, (account_id,))
            result = cursor.fetchall()
            return result
        except Error as e:
            logging.error(f"Error getting account trades: {e}")
            return []
        finally:
            cursor.close()
            self.disconnect()