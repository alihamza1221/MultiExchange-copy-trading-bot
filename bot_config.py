import os
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from binance.enums import *
import logging
from binance_config import BinanceClient, SourceAccountListener
from database import Database
import threading
import socket

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('LogsBinanceQuantTradingEngine.log'),
        logging.StreamHandler()
    ]
)

class CopyTradingBot:
    def __init__(self):
        self.db = Database()
        self.source_listener = None
        self.is_running = False
        
    def initialize_database(self):
        """Initialize database tables"""
        if self.db.create_tables():
            logging.info("Database initialized successfully")
            return True
        else:
            logging.error("Failed to initialize database")
            return False
    
    def test_source_connection(self):
        """Test source account connection"""
        source_client = BinanceClient(is_source=True)
        return source_client.test_connection()
    
    def start_bot(self):
        """Start the copy trading bot"""
        if not self.initialize_database():
            return False
        
        if not self.test_source_connection():
            logging.error("Source account connection failed")
            return False
        
        # Start source account listener
        self.source_listener = SourceAccountListener()
        listener_thread = threading.Thread(
            target=self.source_listener.start_listening, 
            daemon=True
        )
        listener_thread.start()
        
        self.is_running = True
        logging.info("Copy trading bot started successfully")
        return True
    
    def stop_bot(self):
        """Stop the copy trading bot"""
        self.is_running = False
        if self.source_listener and self.source_listener.ws:
            self.source_listener.ws.stop()
        logging.info("Copy trading bot stopped")
    
    def get_server_ip(self):
        """Get server IP address"""
        try:
            # Connect to a remote server to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "192.168.8.2"  # Default IP as requested
    
    def validate_api_credentials(self, api_key, secret_key):
        """Validate Binance API credentials"""
        try:
            client = BinanceClient(api_key=api_key, secret_key=secret_key)
            return client.test_connection()
        except Exception as e:
            logging.error(f"Error validating credentials: {e}")
            return False
    
    def get_account_stats(self, account_id):
        """Get account statistics"""
        trades = self.db.get_account_trades(account_id)
        return {
            'total_trades': len(trades),
            'recent_trades': trades[:10] if trades else []
        }

# Global bot instance
bot = CopyTradingBot()

