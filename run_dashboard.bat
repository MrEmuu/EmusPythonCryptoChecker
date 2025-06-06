@echo off
REM Switch to D: drive
D:

REM Change to the project folder
cd D:\!EmuPythonProjects\emu_crypto_dashboard

REM Activate the virtual environment
call .venv5\Scripts\activate.bat

REM Install requirements if not already installed
pip install -r requirements.txt

REM Launch the Streamlit app
streamlit run streamlit_app.py

REM Keep this window open so you can see any logs or errors
pause
