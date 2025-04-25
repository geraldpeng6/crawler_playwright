#!/bin/bash
# Setup script for the web interaction element crawler

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    pip install uv
fi

# Create virtual environment
echo "Creating virtual environment..."
uv venv

# Activate virtual environment
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "Activating virtual environment..."
    source .venv/Scripts/activate
else
    echo "Unknown OS type. Please activate the virtual environment manually."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
python -m playwright install chromium

echo "Setup completed successfully!"
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate  # Linux/macOS"
echo "  .venv\\Scripts\\activate    # Windows"
