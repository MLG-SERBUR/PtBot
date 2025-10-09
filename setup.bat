@echo off

echo Setting up Python virtual environment...

rem Create virtual environment if it doesn't exist
if not exist venv (
    py -3.13 -m venv venv
)

rem Activate virtual environment
call venv\Scripts\activate.bat

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo Setup complete!
echo Remember to install FFmpeg on your system if you haven't already.
echo   - Download from https://ffmpeg.org/download.html and add to PATH.
echo.
echo To activate the environment manually: call venv\Scripts\activate.bat
echo To run the bot: run.bat <YOUR_BOT_TOKEN>
