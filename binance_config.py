import os
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from binance.enums import *
from binance import ThreadedWebsocketManager
import json
from threading import Thread
import time
from database import Database
import logging

load_dotenv()

class BinanceClient:
    def __init__(self, api_key=None, secret_key=None, is_source=False):
        self.api_key = api_key or os.getenv('SOURCE_BINANCE_API_KEY' if is_source else 'BINANCE_API_KEY')
        self.secret_key = secret_key or os.getenv('SOURCE_BINANCE_SECRET' if is_source else 'BINANCE_SECRET')
        
        if not self.api_key or not self.secret_key:
            raise ValueError(f"Missing API credentials for {'source' if is_source else 'target'} account")
        
        self.client = Client(
            api_key=self.api_key,
            api_secret=self.secret_key,
            testnet=False  # Set to True for testnet
        )
        self.is_source = is_source
        self.db = Database()
        
    def test_connection(self):
        """Test if the API credentials are valid"""
        try:
            account_info = self.client.futures_account()
            logging.info(f"Binance connection test successful for {'source' if self.is_source else 'target'} account")
            return True
        except BinanceAPIException as error:
            logging.error(
                f"Binance API Error - Code: {error.code}, Message: {error.message}"
            )
            return False
        except BinanceRequestException as error:
            logging.error(
                f"Binance Request Error - Message: {error.message}"
            )
            return False
        except Exception as error:
            logging.error(f"Unexpected error during connection test: {str(error)}")
            return False
    
    def get_account_info(self):
        """Get account information"""
        try:
            return self.client.futures_account()
        except BinanceAPIException as error:
            logging.error(
                f"Error getting account info - Code: {error.code}, Message: {error.message}"
            )
            return None
        except Exception as error:
            logging.error(f"Unexpected error getting account info: {str(error)}")
            return None
    
    def place_order(self, symbol, side, order_type, quantity, price=None, stop_price=None, time_in_force='GTC'):
        """Place a new futures order"""
        try:
            order_params = {}
            if order_type == 'MARKET': 
                order_params = {
                    'symbol': symbol,
                    'side': side,
                    'type': order_type,
                    'quantity': quantity,
                }
            elif order_type in ['LIMIT', 'STOP_MARKET', 'TAKE_PROFIT_MARKET']:
                order_params = {
                    'symbol': symbol,
                    'side': side,
                    'type': order_type,
                    'quantity': quantity,
                    'timeInForce': time_in_force
                }

            if price:
                order_params['price'] = str(price)
            if stop_price:
                order_params['stopPrice'] = str(stop_price)
                
            response = self.client.futures_create_order(**order_params)
            logging.info(f"Order placed successfully: {response}")
            return response
            
        except BinanceAPIException as error:
            logging.error(
                f"Error placing order - Code: {error.code}, Message: {error.message}"
            )
            return None
        except Exception as error:
            logging.error(f"Unexpected error placing order: {str(error)}")
            return None
    
    def cancel_order(self, symbol, order_id):
        """Cancel an existing order"""
        try:
            response = self.client.futures_cancel_order(symbol=symbol, orderId=order_id)
            logging.info(f"Order cancelled successfully: {response}")
            return response
        except BinanceAPIException as error:
            logging.error(
                f"Error cancelling order - Code: {error.code}, Message: {error.message}"
            )
            return None
        except Exception as error:
            logging.error(f"Unexpected error cancelling order: {str(error)}")
            return None
    
    def start_user_stream(self):
        """Start user data stream"""
        try:
            listen_key_response = self.client.futures_stream_get_listen_key()
            logging.info(f"Listen key created: {listen_key_response}")
            return listen_key_response
        except BinanceAPIException as error:
            logging.error(
                f"Error creating listen key - Code: {error.code}, Message: {error.message}"
            )
            return None
        except Exception as error:
            logging.error(f"Unexpected error creating listen key: {str(error)}")
            return None
        
    def get_leverage(self, symbol):
        """Fetch leverage for a symbol, with fallback and error handling."""
        return 40

    def set_leverage(self, symbol, leverage):
        try:
            # Set leverage
            response = self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logging.info(f"Leverage set for {symbol} to {leverage}x")
            
            return response
        
        except BinanceAPIException as e:
            logging.error(f"Error setting leverage for {symbol}: {e}") 
    
    def keep_alive_user_stream(self, listen_key):
        """Keep user data stream alive"""
        try:
            self.client.futures_stream_keepalive(listenKey=listen_key)
            return True
        except BinanceAPIException as error:
            logging.error(
                f"Error renewing listen key - Code: {error.code}, Message: {error.message}"
            )
            return False
        except Exception as error:
            logging.error(f"Unexpected error renewing listen key: {str(error)}")
            return False

class SourceAccountListener:
    def __init__(self):
        self.source_client = BinanceClient(is_source=True)
        self.db = Database()
        self.listen_key = None
        self.twm = None
        
    def handle_socket_message(self, msg):
        """Handle WebSocket messages from futures user data stream"""
        try:
            if msg.get('e') == 'ORDER_TRADE_UPDATE':
                order_data = msg.get('o', {})
                self.handle_order_update(order_data)
        except Exception as e:
            logging.error(f"Error handling socket message: {e}")
    
    def handle_order_update(self, order_data):
        """Handle order update from source account"""
        leverage= 5
        try:
            # Extract order information
            symbol = order_data.get('s')
            side = order_data.get('S')
            order_type = order_data.get('o')
            quantity = order_data.get('q')
            price = order_data.get('p')
            stop_price = order_data.get('sp')
            status = order_data.get('X')
            order_id = order_data.get('i')
            time_in_force = order_data.get('f')
            leverage = 40
            print("order: ", order_data, "levg:", leverage)
            logging.info(f"Received order update: {symbol} {side} {status} ps {order_data.get('ps')}")
            
            # Process only NEW orders or CANCELED orders
            if status in ['NEW', 'CANCELED']:
                self.process_order_update(
                    symbol, side, order_type, quantity, 
                    price, stop_price, status, order_id, leverage, time_in_force
                )
                
        except Exception as e:
            logging.error(f"Error handling order update: {e}")
    
    def process_order_update(self, symbol, side, order_type, quantity, price, stop_price, status, source_order_id, leverage = 5, time_in_force='GTC'):
        """Process order update and mirror to target accounts"""
        try:
            # Get all target accounts
            target_accounts = self.db.get_all_binance_accounts()
            
            for account in target_accounts:
                try:
                    # Create client for target account
                    target_client = BinanceClient(
                        api_key=account['api_key'],
                        secret_key=account['secret_key']
                    )
                    
                    if status == 'NEW':
                        # Mirror the trade
                        response = None
                        target_client.set_leverage(symbol, leverage)

                        if order_type == 'MARKET':
                            response = target_client.place_order(
                                symbol=symbol,
                                side=side,
                                order_type=order_type,
                                quantity=quantity,
                            )
                        elif order_type == 'LIMIT':
                            response = target_client.place_order(
                                symbol=symbol,
                                side=side,
                                order_type=order_type,
                                quantity=quantity,
                                price=price,
                                time_in_force=time_in_force
                            )
                        elif order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET']:
                            response = target_client.place_order(
                                symbol=symbol,
                                side=side,
                                order_type=order_type,
                                quantity=quantity,
                                stop_price=stop_price,
                                time_in_force=time_in_force
                            )
                        else:
                            continue
                        
                        if response:
                            # Log the trade in database
                            self.db.add_trade(
                                account_id=account['id'],
                                symbol=symbol,
                                side=side,
                                order_type=order_type,
                                quantity=float(quantity),
                                price=float(price) if price and price != '0' else None,
                                stop_price=float(stop_price) if stop_price and stop_price != '0' else None,
                                order_id=response.get('orderId'),
                                status='MIRRORED'
                            )
                            
                            logging.info(f"Trade mirrored to account {account['id']}: {symbol} {side}")
                    
                    elif status == 'CANCELED':
                        # Handle order cancellation if needed
                        logging.info(f"Order cancelled in source account: {symbol} {source_order_id}")
                        
                except Exception as e:
                    logging.error(f"Error processing order for account {account['id']}: {e}")
                    
        except Exception as e:
            logging.error(f"Error processing order update: {e}")
    
    def start_listening(self):
        """Start listening to source account order updates"""
        try:
            # Get listen key for futures user data stream
            self.twm = ThreadedWebsocketManager(
                api_key=self.source_client.api_key,
                api_secret=self.source_client.secret_key
            )
            self.twm.start()

            # Start futures user data stream (no listen_key arg needed!)
            self.twm.start_futures_user_socket(
                callback=self.handle_socket_message
            )

            logging.info("Started listening to source account order updates")
            
            # Keep alive loop in a separate thread
            def keep_alive():
                while True:
                    time.sleep(900)  # 15 minutes
                    if not self.source_client.keep_alive_user_stream(self.listen_key):
                        logging.error("Failed to keep stream alive")
                        break
            
            alive_thread = Thread(target=keep_alive, daemon=True, name="KeepAliveThread")
            alive_thread.start()
            
        except Exception as e:
            logging.error(f"Error starting listener: {e}")
        
    def stop(self):
        """Stop the WebSocket manager"""
        try:
            if self.twm:
                self.twm.stop()
                logging.info("WebSocket manager stopped")
        except Exception as e:
            logging.error(f"Error stopping WebSocket manager: {e}")
            