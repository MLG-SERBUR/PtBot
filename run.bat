@echo off

rem Check if token is provided
if "%1"=="" (
    echo Usage: run.bat ^<YOUR_BOT_TOKEN^>
    exit /b 1
)

rem Activate virtual environment
call venv\Scripts\activate.bat

rem Run the bot script
.\venv\Scripts\python.exe bot.py %1
