from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
from database import Database
from bot_config import bot
import hashlib
import logging

app = FastAPI(title="Copy Trading Bot API", version="1.0.0")
security = HTTPBearer()

# Configuration
SECRET_KEY = "your-secret-key-here"  # Change this in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database instance
db = Database()

# Request models
class LoginRequest(BaseModel):
    email: str
    password: str

class AddAccountRequest(BaseModel):
    account_name: str
    api_key: str
    secret_key: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# Authentication helpers
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return email
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# API Routes
@app.post("/api/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login endpoint"""
    if db.authenticate_user(request.email, request.password):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": request.email}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

@app.get("/api/accounts")
async def get_accounts(current_user: str = Depends(get_current_user)):
    """Get all accounts for the current user"""
    accounts = db.get_user_accounts(current_user)
    return {"accounts": accounts}

@app.post("/api/accounts")
async def add_account(request: AddAccountRequest, current_user: str = Depends(get_current_user)):
    """Add a new Binance account"""
    # Validate API credentials
    if not bot.validate_api_credentials(request.api_key, request.secret_key):
        raise HTTPException(status_code=400, detail="Invalid API credentials")
    
    account_id = db.add_binance_account(
        current_user, 
        request.api_key, 
        request.secret_key, 
        request.account_name
    )
    
    if account_id:
        return {"message": "Account added successfully", "account_id": account_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to add account")

@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: int, current_user: str = Depends(get_current_user)):
    """Delete a Binance account"""
    if db.delete_account(account_id, current_user):
        return {"message": "Account deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Account not found or access denied")

@app.get("/api/accounts/{account_id}/stats")
async def get_account_stats(account_id: int, current_user: str = Depends(get_current_user)):
    """Get account statistics"""
    # Verify account belongs to user
    accounts = db.get_user_accounts(current_user)
    if not any(acc['id'] == account_id for acc in accounts):
        raise HTTPException(status_code=404, detail="Account not found")
    
    stats = bot.get_account_stats(account_id)
    return stats

@app.get("/api/bot/status")
async def get_bot_status(current_user: str = Depends(get_current_user)):
    """Get bot status"""
    return {
        "is_running": bot.is_running,
        "server_ip": bot.get_server_ip()
    }

@app.post("/api/bot/start")
async def start_bot(current_user: str = Depends(get_current_user)):
    """Start the copy trading bot"""
    if bot.start_bot():
        return {"message": "Bot started successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start bot")

@app.post("/api/bot/stop")
async def stop_bot(current_user: str = Depends(get_current_user)):
    """Stop the copy trading bot"""
    bot.stop_bot()
    return {"message": "Bot stopped successfully"}

@app.get("/")
async def root():
    """API root endpoint"""
    return {"message": "Copy Trading Bot API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)