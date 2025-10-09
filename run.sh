#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: ./run.sh <YOUR_BOT_TOKEN>"
    exit 1
fi

source venv/bin/activate

python bot.py "$1"
