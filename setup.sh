#!/bin/bash

echo "==================================="
echo "HARVEX - Quick Start Guide"
echo "==================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    exit 1
fi

echo "Prerequisites check passed!"
echo ""

# Backend setup
echo "Setting up backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -q

# Train crop model
echo "Training crop recommendation model..."
python3 app/ml/train_crop_model.py

# Initialize database
echo "Initializing database..."
python3 -c "from app.core.database import engine, Base; Base.metadata.create_all(bind=engine)" 2>/dev/null || echo "Note: Database initialization requires PostgreSQL"

cd ..

# Frontend setup
echo ""
echo "Setting up frontend..."
cd frontend
npm install
cd ..

echo ""
echo "==================================="
echo "Setup complete!"
echo ""
echo "To start the application:"
echo ""
echo "1. Start PostgreSQL database"
echo "2. Configure .env file with your settings"
echo "3. Start backend: cd backend && uvicorn main:app --reload"
echo "4. Start frontend: cd frontend && npm run dev"
echo ""
echo "Access the app at: http://localhost:5173"
echo "==================================="
