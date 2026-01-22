from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import datetime
from jose import JWTError, jwt

# Import existing logic
import auth
import database
import services
import utils
from constants import MAIN_CATEGORIES, SUBCATS_FOOD_CAFE

app = FastAPI(title="Owners API")

# CORS Setup (Allow Next.js frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For Replit, we might need to be specific later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# --- Models ---
class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class DashboardData(BaseModel):
    progress: int
    done: int
    total: int
    items: List[dict]
    store_name: str
    category: str

# --- Helpers ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user_name(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Owners API is running"}

@app.post("/api/auth/login", response_model=Token)
def login(req: LoginRequest):
    # 1. Verify credentials
    if not auth.verify_user(req.username, req.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    # 2. Generate Token
    access_token = create_access_token(data={"sub": req.username})
    return {"access_token": access_token, "token_type": "bearer", "username": req.username}

@app.post("/api/auth/signup", response_model=Token)
def signup(req: LoginRequest):
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
    if len(req.password) < 4:
         raise HTTPException(status_code=400, detail="Password too short")
    
    if auth.username_exists(username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    auth.create_user(username, req.password)
    
    access_token = create_access_token(data={"sub": username})
    return {"access_token": access_token, "token_type": "bearer", "username": username}

@app.get("/api/dashboard")
def get_dashboard(token: str):
    # 1. Auth check
    username = get_current_user_name(token)
    
    # 2. Get User's First Store (Simplification for MVP)
    stores = database.get_user_stores(username)
    if not stores:
        return {"has_store": False}
    
    store_id = stores[0]["store_id"]
    
    # 3. Get Store Logic (Reusing services.py)
    data = database.get_store_info(username, store_id)
    if not data:
        return {"has_store": False} # Should not happen if get_user_stores returned true
        
    database.refresh_checklist_from_store(username, store_id)
    ck = database.get_checklist(store_id)
    
    az_res = services.calc_az_progress(data, ck)
    
    # 4. Filter items for frontend
    items_out = []
    for label, is_done, _ in az_res['items']:
         if not is_done:
             items_out.append({"label": label, "done": False})
    
    return {
        "has_store": True,
        "store_name": data["store_name"],
        "category": data["category"],
        "progress": az_res['progress'],
        "done": az_res['done'],
        "total": az_res['total'],
        "items": items_out
    }

# Initialization on start
database.init_db()
app.state.db_initialized = True
