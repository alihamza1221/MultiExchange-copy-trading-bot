import os
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from binance.enums import *
import logging
from binance_config import BinanceClient, SourceAccountListener
from database import Database
import threading

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
        

    def test_source_connection(self):
        """Test source account connection"""
        source_client = BinanceClient(is_source=True)
        return source_client.test_connection()
    
    def start_bot(self):
        """Start the copy trading bot"""
       
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

