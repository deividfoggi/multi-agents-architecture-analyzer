#!/bin/bash
# Setup script for the Multi-Agent Architecture Analyzer

set -e  # Exit on error

echo "🚀 Setting up Multi-Agent Architecture Analyzer..."

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "✓ Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Install package in editable mode
echo "📦 Installing package in editable mode..."
pip install -e .

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        echo "⚠️  No .env file found. Copying from .env.template..."
        cp .env.template .env
        echo "⚠️  Please update .env with your actual configuration values"
    else
        echo "⚠️  No .env or .env.template file found. Please create .env with required variables."
    fi
else
    echo "✓ .env file exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the application, use:"
echo "  python main.py"
echo ""
echo "Or with environment variables:"
echo "  PYTHONPATH=\$PWD/src python main.py"
