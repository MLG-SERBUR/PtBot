#!/bin/bash

echo "Setting up Python virtual environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo "Remember to install FFmpeg on your system if you haven't already."
echo "  - On Debian/Ubuntu: sudo apt update && sudo apt install ffmpeg"
echo "  - On macOS (with Homebrew): brew install ffmpeg"
echo ""
echo "To activate the environment manually: source venv/bin/activate"
echo "To run the bot: ./run.sh <YOUR_BOT_TOKEN>"
