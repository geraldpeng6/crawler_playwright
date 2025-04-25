@echo off
REM Setup script for the web interaction element crawler

REM Check if uv is installed
where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Installing uv...
    pip install uv
)

REM Create virtual environment
echo Creating virtual environment...
uv venv

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
uv pip install -r requirements.txt

REM Install Playwright browsers
echo Installing Playwright browsers...
python -m playwright install chromium

echo Setup completed successfully!
echo To activate the virtual environment, run:
echo   .venv\Scripts\activate.bat
