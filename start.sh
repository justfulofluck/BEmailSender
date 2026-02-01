#!/bin/bash

# BEmailSender Start Script

echo "🚀 Starting BEmailSender..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if requirements.txt has changed
echo "📚 Checking dependencies..."
pip install -r requirements.txt

# Create uploads directory if it doesn't exist
mkdir -p uploads

# Start the Flask application
echo "🌐 Starting Flask application..."
echo "Access the application at: http://127.0.0.1:5000"
echo "Press Ctrl+C to stop the server"
echo ""

python app.py