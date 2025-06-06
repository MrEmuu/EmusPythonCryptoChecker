@echo off
REM --------------------------------------------------------
REM Emus Crypto Dashboard Launcher (portable for any user)
REM --------------------------------------------------------

REM 1) Change directory to where this batch file lives (%~dp0),
REM    using /d so it can switch drives if needed.
cd /d "%~dp0"

REM 2) Activate the virtual environment named venv5 (assumes venv5 is next to this .bat)
call "%~dp0venv5\Scripts\activate.bat"

REM 3) Install any missing requirements (from requirements.txt in the same folder)
pip install -r "%~dp0requirements.txt"

REM 4) Launch Streamlit (streamlit_app.py must also be in the same folder)
streamlit run "%~dp0streamlit_app.py"

REM 5) Keep the console window open so you can see logs or errors
pause
