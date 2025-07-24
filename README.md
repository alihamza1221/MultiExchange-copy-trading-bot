# Copy Trading Bot

A sophisticated copy trading bot for Binance UM Futures that automatically mirrors trades from a source account to multiple target accounts.

## Features

- **Web Dashboard**: User-friendly Streamlit interface
- **REST API**: FastAPI backend for programmatic access
- **Real-time Trading**: WebSocket-based order monitoring and copying
- **Multi-Account Support**: Support for multiple target accounts per user
- **User Management**: Login system with MySQL database
- **Trade Tracking**: Complete trade history and statistics
- **Exchange Support**: Currently supports Binance (extensible to MEXC, Phemex, Blofin, Bybit)

## Architecture

### Backend Components

- `database.py`: MySQL database models and operations
- `binance_config.py`: Binance API client and WebSocket listener
- `bot_config.py`: Main bot logic and configuration
- `api.py`: FastAPI REST API endpoints

### Frontend

- `script.py`: Streamlit web application
- `launcher.py`: Application launcher script

## Installation

1. Install required packages:

```bash
pip install -r requirements.txt
```

2. Setup MySQL database and create the required database:

```sql
CREATE DATABASE copy_trading;
```

3. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your actual configuration
```

4. Run the application:

```bash
python launcher.py --mode streamlit
```

## Configuration

### Environment Variables (.env)

- `DB_HOST`: MySQL host (default: localhost)
- `DB_NAME`: Database name (default: copy_trading)
- `DB_USER`: MySQL username
- `DB_PASSWORD`: MySQL password
- `SOURCE_BINANCE_API_KEY`: Source account API key
- `SOURCE_BINANCE_SECRET`: Source account secret key

### Default Login Credentials

- Email: admin@test.com
- Password: admin123

## Usage

### Web Dashboard

1. Open browser to http://localhost:8501
2. Login with credentials
3. Add target Binance accounts
4. Start the bot to begin copying trades
5. Monitor trades and account statistics

### API Endpoints

- `POST /api/login`: User authentication
- `GET /api/accounts`: Get user accounts
- `POST /api/accounts`: Add new account
- `DELETE /api/accounts/{id}`: Delete account
- `GET /api/accounts/{id}/stats`: Get account statistics
- `GET /api/bot/status`: Get bot status
- `POST /api/bot/start`: Start bot
- `POST /api/bot/stop`: Stop bot

## Trading Logic

1. **Source Account Monitoring**: Listens to Binance WebSocket for ORDER_TRADE_UPDATE events
2. **Order Processing**: Processes NEW and CANCELED orders from source account
3. **Trade Mirroring**: Replicates trades to all configured target accounts
4. **Database Logging**: Records all trades with complete details
5. **Error Handling**: Comprehensive error handling and logging

### Supported Order Types

- Market Orders
- Limit Orders
- Stop Market Orders
- Take Profit Market Orders

## Database Schema

### Tables

- `users`: User authentication
- `binance_accounts`: Target account credentials
- `trades`: Complete trade history

## Security Features

- Password-based authentication
- JWT token support for API
- Encrypted API key storage
- Input validation and sanitization

## Monitoring & Logging

- Comprehensive logging to file and console
- Real-time bot status monitoring
- Trade statistics and analytics
- Error tracking and reporting

## Extensibility

The architecture supports easy addition of new exchanges:

- Implement exchange-specific client classes
- Add WebSocket listeners for each exchange
- Extend database models for exchange-specific data
- Update frontend to support new exchanges

## Development

### Running in Development Mode

```bash
# Streamlit only
python launcher.py --mode streamlit

# FastAPI only
python launcher.py --mode fastapi

# Both interfaces
python launcher.py --mode both
```

### Testing

```bash
# Check requirements and setup
python launcher.py --check
```

## Production Deployment

1. Set up secure MySQL database
2. Configure proper environment variables
3. Use production WSGI server (e.g., Gunicorn for FastAPI)
4. Set up reverse proxy (nginx)
5. Enable SSL/TLS
6. Configure logging and monitoring

## Disclaimer

This software is for educational and personal use only. Trading cryptocurrencies involves substantial risk of loss. Use at your own risk and ensure compliance with applicable regulations.
