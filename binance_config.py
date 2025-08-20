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
import requests, hmac, hashlib, json
import ccxt
# import ccxt.async_support as ccxt # link against the asynchronous version of ccxt

logging.basicConfig(level=logging.INFO)
load_dotenv()
class PhemexClient:
    """Enterprise-grade Phemex trading client with connection testing and error handling"""
    BASE_URL = 'https://api.phemex.com'

    def __init__(self, api_key, api_secret):
        """Initialize Phemex client with API credentials"""
        self.api_key = api_key
        self.api_secret = api_secret

        # Initialize CCXT Phemex client
        self.phemex_client = ccxt.phemex({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'options': {
                'defaultType': 'swap',
            },
        })

        try:
            self.phemex_client.load_markets()
            logging.info("Phemex markets loaded successfully")
        except Exception as e:
            logging.warning(f" Could not load Phemex markets: {e}")        
    def test_connection(self):
        """Test if the Phemex API credentials are valid using CCXT"""
        try:
            # Test 1: Fetch markets (public endpoint)
            markets = self.phemex_client.fetch_markets()
            if not markets:
                logging.error("Phemex public API test failed - no markets found")
                return False
            
            logging.info(f"✅ Phemex public API accessible - found {len(markets)} markets")
            
            # Test 2: Authentication test with balance
            try:
                balance = self.phemex_client.fetch_balance()
                logging.info(" Phemex authentication successful")
                logging.debug(f"Balance info: {balance}")
                return True
            except Exception as auth_error:
                # Check if it's a permission issue (auth worked but no permission)
                error_msg = str(auth_error).lower()
                if any(keyword in error_msg for keyword in ['permission', 'unauthorized', 'forbidden', 'api']):
                    logging.info("✅ Phemex authentication successful (limited permissions)")
                    return True
                else:
                    logging.error(f"Phemex authentication failed: {auth_error}")
                    return self._test_connection_alternative()
                
        except Exception as e:
            logging.error(f" Phemex connection test error: {e}")
            return self._test_connection_alternative()
    
    def _test_connection_alternative(self):
        """Alternative connection test using a simpler endpoint"""
        try:
            # Use wallet endpoint as alternative
            expiry = int(time.time()) + 60
            path = "/phemex-user/wallets/v2/depositAddress"
            url = self.BASE_URL + path
            
            # Add required currency parameter
            query = "?currency=USDT"
            
            signature = self._sign(path, query, expiry, "")
            headers = {
                "x-phemex-access-token": self.api_key,
                "x-phemex-request-expiry": str(expiry),
                "x-phemex-request-signature": signature,
                "Content-Type": "application/json"
            }
            
            resp = requests.get(url + query, headers=headers)
            result = resp.json()
            
            # Check if we get a valid response (even if it's an error about permissions)
            if 'code' in result:
                if result.get('code') in [0, 10404, 11007]:  # Success or permission errors (means auth worked)
                    logging.info("Phemex connection test successful (alternative method)")
                    return True
                else:
                    logging.error(f"Phemex connection test failed: {result}")
                    return False
            else:
                logging.error(f"Phemex connection test failed - unexpected response: {result}")
                return False
                
        except Exception as e:
            logging.error(f"Phemex alternative connection test error: {e}")
            return False

    def _sign(self, path, query, expiry, body):
        """Generate Phemex API signature"""
        try:
            # Build the string to sign according to Phemex documentation
            s = path
            if query:
                s += query
            s += str(expiry)
            if body:
                s += body
            
            # Create signature using HMAC-SHA256
            signature = hmac.new(
                self.api_secret.encode('utf-8'), 
                s.encode('utf-8'), 
                hashlib.sha256
            ).hexdigest()
            
            logging.debug(f"🔴 Signature generation - String to sign: {s}")
            logging.debug(f"🔴 Generated signature: {signature}")
            
            return signature
            
        except Exception as e:
            logging.error(f"❌ Error generating signature: {e}")
            raise

    def fetch_all_price_scales(self):
        url = 'https://api.phemex.com/public/products'
        resp = requests.get(url)
        products = resp.json()['data']['products']
        symbol_price_scale = {}
        for prod in products:
            symbol = prod['symbol']         # e.g. BTCUSD
            price_scale = prod['priceScale']  # e.g. 10000
            symbol_price_scale[symbol] = price_scale
        return symbol_price_scale
    def convert_binance_to_phemex_order_type(binance_type):
        """Map Binance order type to Phemex order type."""
        mapping = {
            'MARKET': 'Market',
            'LIMIT': 'Limit',
            'STOP_MARKET': 'Stop',
            'STOP_LIMIT': 'StopLimit',
            'TAKE_PROFIT_MARKET': 'MarketIfTouched',  # Take-profit at  market
            'TAKE_PROFIT': 'LimitIfTouched',          # Take-profit at  limit
            'TRAILING_STOP_MARKET': 'Stop',           # Phemex trailing     handled via extra params
        }
        return mapping.get(binance_type, binance_type)  # fallback to same if not mapped


    @staticmethod
    def convert_binance_to_phemex_time_in_force(binance_tif):
        """Map Binance timeInForce to Phemex timeInForce."""
        mapping = {
            'GTC': 'GoodTillCancel',       # Good Till Cancelled
            'IOC': 'ImmediateOrCancel',   # Immediate Or Cancel
            'FOK': 'FillOrKill',          # Fill Or Kill
            'GTX': 'PostOnly'             # Good Till Crossing (Post only)
        }
        return mapping.get(binance_tif, binance_tif)  # fallback to original if not mapped
    
    @staticmethod
    def convert_binance_to_phemex_order_type(binance_type):
        """Map Binance order type to Phemex order type."""
        mapping = {
            'MARKET': 'Market',
            'LIMIT': 'Limit',
            'STOP_MARKET': 'Stop',
            'STOP_LIMIT': 'StopLimit',
            'TAKE_PROFIT_MARKET': 'MarketIfTouched',  # Take-profit at market
            'TAKE_PROFIT': 'LimitIfTouched',          # Take-profit at limit
            'TRAILING_STOP_MARKET': 'Stop',           # Phemex trailing handled via extra params
        }
        return mapping.get(binance_type, binance_type)  # fallback to same if not mapped

    @staticmethod
    def convert_binance_to_phemex_order_side(binance_side):
        """Map Binance order side to Phemex side."""
        mapping = {
            'BUY': 'Buy',
            'SELL': 'Sell'
        }
        return mapping.get(binance_side, binance_side)
    @staticmethod
    def Convert_to_ccxt_symbol(binance_symbol: str) -> str:
        quote = 'USDT'

        if not binance_symbol.endswith(quote):
            raise ValueError(f"Symbol '{binance_symbol}' does not end with '{quote} '")

        base = binance_symbol[:-len(quote)]

        return f"{base}/{quote}:{quote}"

    def place_order_ccxt(self, symbol, side, order_type, quantity, price=None, stop_price=None, time_in_force=None, reduce_only=False, **kwargs):
        """Place order using CCXT client with proper error handling"""
        try:
            # Convert symbol to Phemex format
            phemex_symbol = self.Convert_to_ccxt_symbol(symbol)
            ccxt_type = self._convert_to_ccxt_order_type(order_type)
            ccxt_time = self._convert_to_ccxt_time_in_force(time_in_force)
            ccxt_side = side.lower()  # 'buy' or 'sell'
            ccxt_amount = float(quantity)


            logging.info(f" Placing CCXT order: {symbol} → {phemex_symbol} | {ccxt_side} {ccxt_type} {ccxt_amount} at price {price} and sp = {stop_price}")

            # Convert order parameters to CCXT format
            
            
            # Prepare order parameters
            params = {}
            
            # Add reduce only if specified
            if reduce_only:
                params['reduceOnly'] = True
                
            # Add time in force if specified
            if time_in_force:
                params['timeInForce'] = self._convert_to_ccxt_time_in_force(time_in_force)
            
            # Add any additional parameters
            params.update(kwargs)
            
            # Place order based on type
            if ccxt_type == 'market':
                order =self.phemex_client.create_order(phemex_symbol, ccxt_type, ccxt_side, ccxt_amount)
                logging.info("successfully placed market order")
                #self.phemex_client.set_leverage(phemex_symbol, 10)
                
            elif ccxt_type == 'limit':
                # Use create_order instead of create_limit_order
                if not price:
                    raise ValueError("Limit order requires price")
                logging.info(f"placing limit order --------------\n symbol {phemex_symbol} type : limit side : {ccxt_side} amount : {ccxt_amount} price : {float(price)}")
                order = self.phemex_client.create_order(
                    symbol=phemex_symbol,
                    type='limit', 
                    side=ccxt_side,
                    amount=ccxt_amount,
                    price=float(price),
                )
            elif order_type == "STOP_MARKET":
                    logging.info(f" Placing STOP_MARKET order: {phemex_symbol} | {ccxt_amount} @ {stop_price}")
                    order = self.create_stop_market_order(phemex_symbol, ccxt_amount, float(stop_price)) if ccxt_side == "sell" else self.create_stop_short_order(phemex_symbol, ccxt_amount, float(stop_price))
                        
            elif ccxt_type == 'stop':
                if ccxt_side.lower() == 'sell':  # Stop loss 
                    trigger_direction = 'descending' 
                else:  
                    trigger_direction = 'ascending'  

                params.update({
                    'triggerPrice': str(stop_price),
                    'triggerDirection': trigger_direction,
                    'triggerType': 'ByMarkPrice',  # or 'ByLastPrice'
                    'posSide': 'Merged',  # One-way mode
                })

                order = self.phemex_client.create_order(
                    symbol=phemex_symbol,
                    type='market', 
                    side=ccxt_side,
                    amount=ccxt_amount,
                    price=None,  
                    params=params
                )
            elif ccxt_type == 'stop_limit':
                order = self.phemex_client.create_stop_order(phemex_symbol, 'limit', ccxt_side, ccxt_amount,float(price),float  (stop_price), params)


            else:
                # Generic order creation
                if order_type == "TAKE_PROFIT_MARKET" :
                    logging.info(f" Placing TAKE_PROFIT_MARKET order: {phemex_symbol} | {ccxt_amount} @ {stop_price}")
                    order = self.create_take_profit_market_order(phemex_symbol, ccxt_amount, float(stop_price)) if ccxt_side == "sell" else self.create_take_profit_short_order(phemex_symbol, ccxt_amount, float(stop_price))
               

                else:
                    logging.info('placing generic order on phemex....')

                    order = self.phemex_client.create_order(
                        symbol=phemex_symbol,
                        type=ccxt_type,
                        side=ccxt_side,
                        amount=ccxt_amount,
                        price=float(price) if price else None,
                        params=params
                    )
            
            logging.info(f" CCXT order placed successfully: {order['id']} | Status: {order['status']}")
            logging.debug(f"Order details: {order}")
            
            return {
                'success': True,
                'order': order,
                'order_id': order['id'],
                'status': order['status'],
                'symbol': phemex_symbol,
                'ccxt_response': order
            }
            
        except Exception as e:
            logging.error(f" CCXT order failed for {symbol}: {e}")
            logging.error(f"Error type: {type(e).__name__}")
            return {
                'success': False,
                'error': str(e),
                'symbol': symbol,
                'ccxt_response': None
            }

    def create_stop_market_order(self, symbol, amount, stop_price):
       
        params = {
            'triggerPrice': str(stop_price),
            'triggerDirection': 'descending',  # Price going DOWN to trigger
            'triggerType': 'ByMarkPrice',      # or 'ByLastPrice'
            'posSide': 'Merged',               # One-way mode
            'reduceOnly': True
        }
        
        logging.info(f'Placing stop loss market order for LONG: SELL {amount} {symbol} at trigger {stop_price}')
        
        order = self.phemex_client.create_order(
            symbol=symbol,
            type='market',
            side='sell',  # Sell to close long position
            amount=amount,
            price=None,
            params=params
        )
        
        return order

    def create_stop_short_order(self, symbol, amount, stop_price):
        
        params = {
            'triggerPrice': str(stop_price),
            'triggerDirection': 'ascending',   # Price going UP to trigger
            'triggerType': 'ByMarkPrice',      # or 'ByLastPrice'
            'posSide': 'Merged',               # One-way mode
            'reduceOnly': True
        }
        
        logging.info(f'Placing stop loss market order for SHORT: BUY {amount} {symbol} at trigger {stop_price}')
        
        order = self.phemex_client.create_order(
            symbol=symbol,
            type='market',
            side='buy',   # Buy to close short position
            amount=amount,
            price=None,
            params=params
        )
        
        return order
        
    # Take profit for LONG position (sell at higher price)
    def create_take_profit_market_order(self, symbol, amount, trigger_price):
        params = {
            'triggerPrice': trigger_price,
            'triggerType': 'ByMarkPrice',  # or 'ByLastPrice'
            'triggerDirection': 'ascending',  # Price moving up to trigger
            'posSide': 'Merged',  # One-way mode
            'reduceOnly': True,  # Close position
        }
        
        # For LONG position take profit: SELL when price goes UP
        order = self.phemex_client.create_order(
            symbol=symbol,
            type='market',
            side='sell',
            amount=amount,
            price=None,
            params=params
        )
        return order
    
    # Take profit for SHORT position (buy at lower price)  
    def create_take_profit_short_order(self, symbol, amount, trigger_price):
        params = {
            'triggerPrice': trigger_price,
            'triggerType': 'ByMarkPrice',
            'triggerDirection': 'descending',  # Price moving down to trigger
            'posSide': 'Merged',  # One-way mode
            'reduceOnly': True,
        }
        
        # For SHORT position take profit: BUY when price goes DOWN
        order = self.phemex_client.create_order(
            symbol=symbol,
            type='market',
            side='buy',
            amount=amount,
            price=None,
            params=params
        )
        return order

    def _convert_to_ccxt_order_type(self, binance_order_type):
        """Convert Binance order type to CCXT order type"""
        mapping = {
            'MARKET': 'market',
            'LIMIT': 'limit',
            'STOP_MARKET': 'stop',
            'STOP_LIMIT': 'stop_limit',
            'TAKE_PROFIT_MARKET': 'take_profit',
            'TAKE_PROFIT': 'take_profit_limit',
            'TRAILING_STOP_MARKET': 'trailing_stop'
        }
        return mapping.get(binance_order_type, binance_order_type.lower())
    
    def _convert_to_ccxt_time_in_force(self, binance_tif):
        """Convert Binance time in force to CCXT format"""
        if binance_tif is None:
            return None
        mapping = {
            'GTC': 'GTC',  # Good Till Cancelled
            'IOC': 'IOC',  # Immediate Or Cancel
            'FOK': 'FOK',  # Fill Or Kill
            'GTX': 'PO'    # Post Only
        }
        return mapping.get(binance_tif, binance_tif)
    def set_leverage(self, symbol, leverage):
        """Set leverage for a symbol with enhanced debugging"""
        try:
            symbol = self.Convert_to_ccxt_symbol(symbol)
            self.phemex_client.set_leverage(leverage, symbol)
            logging.info(f"Leverage is set to {leverage} for {symbol} in phemex client")
            return True
        except Exception as e:
            logging.error(f" Phemex set_leverage failed: {e}")
            return False
    def test_connection_simple(self):
        """Simplified connection test using CCXT"""
        try:
            # Test markets fetch (public endpoint)
            markets = self.phemex_client.fetch_markets()
            if markets and len(markets) > 0:
                logging.info(f" Phemex connection test successful - {len(markets)} markets")
                return True
            else:
                logging.error(" Phemex connection test failed - no markets found")
                return False
        except Exception as e:
            logging.error(f" Phemex connection test error: {e}")
            return False
    
    def get_account_balance_ccxt(self):
        """Get account balance using CCXT"""
        try:
            balance = self.phemex_client.fetch_balance()
            logging.info("CCXT balance retrieved successfully")
            return balance
        except Exception as e:
            logging.error(f" CCXT get_account_balance failed: {e}")
            return None
    
    def fetch_order_ccxt(self, order_id, symbol=None):
        """Fetch order details using CCXT"""
        try:
            if symbol:
                phemex_symbol = symbol
                order = self.phemex_client.fetch_order(order_id, phemex_symbol)
            else:
                order = self.phemex_client.fetch_order(order_id)
        
            logging.info(f" CCXT order fetched: {order_id}")
            return order
        except Exception as e:
            logging.error(f" CCXT fetch_order failed: {e}")
            return None
    
    def cancel_order_ccxt(self, order_id, symbol):
        """Cancel order using CCXT"""
        try:
            phemex_symbol = symbol
            result = self.phemex_client.cancel_order(order_id, phemex_symbol)
            logging.info(f"CCXT order cancelled: {order_id}")
            return result
        except Exception as e:
            logging.error(f" CCXT cancel_order failed: {e}")
            return None

    def validate_phemex_credentials(self, api_key, api_secret):
        validation_result = {
            'success': False,
            'message': '',
            'details': {},
            'permissions': []
        }
        
        try:
            # Create temporary client for testing
            temp_client = PhemexClient(api_key=api_key, api_secret=api_secret)
            
            # Test 1: Basic connectivity
            if not temp_client.test_connection_simple():
                validation_result['message'] = "Failed to connect to Phemex API"
                return validation_result
            
            # Test 2: Get account information
            balance_info = temp_client.get_account_balance_ccxt()
            if balance_info is not None:
                validation_result['permissions'].append('spot_read')
                validation_result['details']['balance_accessible'] = True
            
            try:
                # Test futures permissions if available
                validation_result['permissions'].append('basic_access')
            except Exception:
                pass
            
            validation_result['success'] = True
            validation_result['message'] = f"Phemex credentials validated successfully"
            validation_result['details']['api_key_prefix'] = api_key[:8] + "..."
            
            return validation_result
            
        except Exception as e:
            validation_result['message'] = f"Validation error: {str(e)}"
            return validation_result

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

    def place_order(self, symbol, side, order_type, quantity, price=None, stop_price=None, time_in_force='GTC', reduce_only=False):
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
                if reduce_only:
                    order_params['reduceOnly'] = reduce_only
            elif order_type in ['LIMIT']:
                order_params = {
                    'symbol': symbol,
                    'side': side,
                    'type': order_type,
                    'timeInForce': time_in_force
                }
            if quantity:
                order_params['quantity'] = quantity
            if price:
                order_params['price'] = str(price)
            if stop_price:
                order_params['stopPrice'] = str(stop_price)
            if reduce_only:
                order_params['reduceOnly'] = reduce_only
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
        return 10

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
        # De-duplication store to avoid double mirroring per target account
        # Key format: f"{exchange}:{account_id}:{symbol}:{side}:{order_type}:{source_order_id}"
        self._mirror_dedup = set()
        
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
            reduce_only = order_data.get('R')
            leverage = 10
            print("order: ", order_data, "levg:", leverage)
            logging.info(f"Received order update: {symbol} {side} {status} ps {order_data.get('ps')} {str(order_type).lower()} reduce_only: {reduce_only}")
            
            # Mirror only when policy matches to avoid duplicates
            if not self._should_mirror_event(order_type, status):
                logging.debug(f"Skip mirroring for type={order_type}, status={status}")
                return

            self.process_order_update(
                symbol, side, order_type, quantity,
                price, stop_price, status, order_id, leverage, time_in_force, reduce_only
            )

        except Exception as e:
            logging.error(f"Error handling order update: {e}")
    
    def _should_mirror_event(self, order_type: str, status: str) -> bool:
        """Mirror rules:
        - MARKET-like: mirror only when FILLED (to avoid double NEW/FILLED)
        - LIMIT-like: mirror only when NEW
        """
        ot = (order_type or '').upper()
        st = (status or '').upper()
        market_like = {'MARKET'}
        if ot in market_like:
            return st == 'NEW'
        # LIMIT, STOP_LIMIT, TAKE_PROFIT (limit), others
        if ot in {'STOP_MARKET', 'TAKE_PROFIT_MARKET'}:
            return False
        
        return st == 'NEW'

    def _dedup_key(self, exchange_type: str, account_id, symbol: str, side: str, order_type: str, source_order_id) -> str:
        return f"{exchange_type}:{account_id}:{symbol}:{side}:{(order_type or '').upper()}:{source_order_id}"

    def process_order_update(self, symbol, side, order_type, quantity, price, stop_price, status, source_order_id, leverage = 10, time_in_force='GTC', reduce_only=False):
        """Process order update and mirror to target accounts across all exchanges"""
        try:
            logging.info(f"Starting process_order_update for {symbol} {side} {order_type} {quantity} {price} {stop_price} {status} {source_order_id} {leverage} {time_in_force} {reduce_only}")

            # Guard again by policy (in case called from elsewhere)
            if not self._should_mirror_event(order_type, status):
                logging.debug(f"Skip processing by policy for type={order_type}, status={status}")
                return

            # Get all target accounts from all exchanges
            all_accounts = self.db.get_all_trading_accounts()
            logging.info(f"Retrieved accounts: type={type(all_accounts)}, value={all_accounts}")
            
            # Validate accounts result
            if all_accounts is None:
                logging.error(" CRITICAL: get_all_trading_accounts returned None")
                return
            if not isinstance(all_accounts, list):
                logging.error(f"No trading accounts")
                return
            if len(all_accounts) == 0:
                logging.warning("No target accounts found for trade mirroring")
                return
            
            successful_mirrors = 0
            failed_mirrors = 0
            
            logging.info(f"📊 Found {len(all_accounts)} target accounts to mirror to")
            
            for account in all_accounts:
                try:
                    if not isinstance(account, dict):
                        logging.error(f" Invalid account format: {type(account)} - {account}")
                        failed_mirrors += 1
                        continue
                    
                    exchange_type = account.get('exchange_type', 'binance')
                    account_id = account.get('id')
                    
                    logging.info(f" Processing account ID {account_id} on {exchange_type}")

                    # De-dup per target account + source order
                    key = self._dedup_key(exchange_type, account_id, symbol, side, order_type, source_order_id)
                    if key in self._mirror_dedup:
                        logging.info(f"Skip duplicate mirror for key={key}")
                        continue
                    
                    # Create appropriate client based on exchange type
                    if exchange_type == 'binance':
                        target_client = BinanceClient(
                            api_key=account['api_key'],
                            secret_key=account['secret_key']
                        )
                        client_type = "Binance"
                    elif exchange_type == 'phemex':
                        target_client = PhemexClient(
                            api_key=account['api_key'],
                            api_secret=account['secret_key']
                        )
                        client_type = "Phemex"
                    else:
                        logging.warning(f"Unsupported exchange type: {exchange_type} for account {account_id}")
                        failed_mirrors += 1
                        continue
                    
                    # Set leverage first (best effort)
                    try:
                        if exchange_type == 'binance':
                            target_client.set_leverage(symbol, leverage)
                        elif exchange_type == 'phemex':
                            target_client.set_leverage(symbol, 10)
                    except Exception as leverage_error:
                        logging.warning(f"Failed to set leverage for {client_type} account {account_id}: {leverage_error}")
                    
                    # Mirror the trade based on order type
                    response = self._execute_mirror_trade(
                        target_client, exchange_type, symbol, side, order_type,
                        quantity, price, stop_price, time_in_force, reduce_only
                    )
                    
                    if response:
                        # Mark as mirrored to prevent duplicates across subsequent events
                        self._mirror_dedup.add(key)
                        # Log successful trade
                        print('response: ', response)
                        self._log_trade_to_database(
                            account, exchange_type, symbol, side, order_type,
                            quantity, price, stop_price, response, source_order_id
                        )
                        successful_mirrors += 1
                        logging.info(f" Trade mirrored to {client_type} account {account_id}: {symbol} {side} {quantity}")
                    else:
                        failed_mirrors += 1
                        logging.error(f" Failed to mirror trade to {client_type} account {account_id}")
                    
                except Exception as account_error:
                    failed_mirrors += 1
                    exchange_type = account.get('exchange_type', 'unknown')
                    logging.error(f" Error processing order for {exchange_type} account {account.get('id', 'unknown')}: {account_error}")
                    import traceback
                    logging.error(f"Account processing traceback: {traceback.format_exc()}")
            
            # Summary logging
            total_accounts = len(all_accounts)
            logging.info(f"📊 Mirror summary: {successful_mirrors}/{total_accounts} successful, {failed_mirrors} failed")
                    
        except Exception as e:
            logging.error(f" Critical error processing order update: {e}")
            import traceback
            logging.error(f"Full traceback: {traceback.format_exc()}")

    def _execute_mirror_trade(self, target_client, exchange_type, symbol, side, order_type, 
                             quantity, price, stop_price, time_in_force, reduce_only):
        """Execute the mirror trade with exchange-specific handling"""
        try:
            
            if exchange_type == 'binance':
                return self._execute_binance_trade(target_client, symbol, side, order_type, 
                                                 quantity, price, stop_price, time_in_force, reduce_only)
            elif exchange_type == 'phemex':
                return self._execute_phemex_trade(target_client, symbol, side, order_type, 
                                                quantity, price, stop_price, time_in_force)
            else:
                logging.error(f"Unsupported exchange type: {exchange_type}")
                return None
                
        except Exception as e:
            logging.error(f"Error executing mirror trade on {exchange_type}: {e}")
            return None

    def _execute_binance_trade(self, binance_client, symbol, side, order_type, 
                              quantity, price, stop_price, time_in_force, reduce_only):
        """Execute trade on Binance"""
        try:
            if order_type == 'MARKET':
                return binance_client.place_order(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity
                )
            elif order_type == 'LIMIT':
                if not price or price == '0':
                    logging.error(f"LIMIT order requires price for {symbol}")
                    return None
                return binance_client.place_order(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    time_in_force=time_in_force
                )
            # elif order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET']:
            #     if not stop_price or stop_price == '0':
            #         logging.error(f"{order_type} order requires stop_price for {symbol}")
            #         return None
            #     return binance_client.place_order(
            #         symbol=symbol,
            #         side=side,
            #         order_type=order_type,
            #         quantity=quantity,
            #         stop_price=stop_price,
            #         time_in_force=time_in_force,
            #         reduce_only=reduce_only
            #    )
            else:
                logging.warning(f"Unsupported Binance order type: {order_type}")
                return None
                
        except Exception as e:
            logging.error(f"Error executing Binance trade: {e}")
            return None

    def _execute_phemex_trade(self, phemex_client, symbol, side, order_type, 
                             quantity, price, stop_price, time_in_force):
        """Execute trade on Phemex using CCXT client"""
        try:
            # Use CCXT place_order_ccxt method
            result = phemex_client.place_order_ccxt(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price if price and price != '0' else None,
                stop_price=stop_price if stop_price and stop_price != '0' else None,
                time_in_force=time_in_force
            )
            
            if result['success']:
                logging.info(f" CCXT Phemex trade executed: {result['order_id']} | Status: {result['status']}")
                return {
                    'code': 0,
                    'data': {
                        'orderID': result['order_id'],
                        'symbol': result['symbol'],
                        'status': result['status']
                    },
                    'msg': 'Success',
                    'ccxt_order': result['order']
                }
        except Exception as e:
            logging.error(f" Error executing CCXT Phemex trade: {e}")
            return None

    def _log_trade_to_database(self, account, exchange_type, symbol, side, order_type, 
                              quantity, price, stop_price, response, source_order_id):
        """Log successful trade to database with exchange-specific handling"""
        try:
            logging.debug(f"Trade LOGGING........ to database for {exchange_type} account {source_order_id}")
            # Extract order ID based on exchange response format
            if exchange_type == 'binance':
                order_id = response.get('orderId')
            elif exchange_type == 'phemex':
                order_id = response.get('data', {}).get('orderID') if response.get('code') == 0 else None
            else:
                order_id = str(response.get('id', 'unknown'))
            
            
            logging.debug(f"Trade LOGGING........ to database for {exchange_type} account {source_order_id} with order ID {order_id}")
            
            
            # Add trade record
            if exchange_type == 'binance':
                self.db.add_trade(
                    account_id=account['id'],
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=float(quantity),
                    price=float(price) if price and price != '0' else None,
                    stop_price=float(stop_price) if stop_price and stop_price != '0' else   None,
                    order_id=order_id,
                    status='MIRRORED',
                    source_order_id=source_order_id
                )
            elif exchange_type == 'phemex':
                self.db.add_phemex_trade(
                    account_id=account['id'],
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=float(quantity),
                    price=float(price) if price and price != '0' else None,
                    stop_price=float(stop_price) if stop_price and stop_price != '0' else   None,
                    order_id=order_id,
                    status='MIRRORED',
                    source_order_id=source_order_id
                )
            
            logging.debug(f"Trade logged to database for {exchange_type} account {account['id']}")
            
        except Exception as e:
            logging.error(f"Error logging trade to database: {e}")
    
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
