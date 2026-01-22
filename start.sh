#!/bin/bash

# 1. Install Backend Deps
echo "📦 Installing Python Dependencies..."
pip install -r requirements.txt

# 2. Install Frontend Deps (if module missing)
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing Frontend Dependencies..."
    cd frontend && npm install && cd ..
fi

# 3. Start Servers
echo "🚀 Starting Servers..."
# Start FastAPI in background
uvicorn api:app --host 0.0.0.0 --port 8000 & 

# Start Streamlit in background
streamlit run streamlit_app.py --server.port 8501 &

# Start Next.js (Foreground)
cd frontend && npm run dev
