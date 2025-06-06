Below is a step-by-step guide to get **Emus Crypto Dashboard** up and running on Windows, using a virtual environment named `venv5`. If you prefer another virtual‐environment name, simply adjust the `.bat` file accordingly.

---

## Setup Guide for Emus Crypto Dashboard

### 1. Clone or Download the Repository

1. Open a Command Prompt (cmd) or PowerShell window.
2. Navigate to the folder where you want to store the project. For example:

   ```bat
   D:
   cd D:\!EmuPythonProjects
   ```
3. Clone the GitHub repository (or download the ZIP and extract it):

   ```bat
   git clone https://github.com/mremuu/EmusPythonCryptoChecker.git
   ```
4. Change into the project folder:

   ```bat
   cd EmusPythonCryptoChecker
   ```

Your folder structure should now look like:

```
D:\!EmuPythonProjects\EmusPythonCryptoChecker\
    ├─ cryptchecker.py   (original CLI version)
    ├─ streamlit_app.py  (the new Streamlit dashboard)
    ├─ requirements.txt
    └─ … (other files/batch script)
```

---

### 2. Create & Activate a Virtual Environment (`venv5`)

We recommend isolating dependencies in a dedicated virtual environment. In this guide, we create one named `venv5`. If you already have a different name in mind, substitute that name everywhere you see `venv5`.

1. Ensure you’re still in the project folder (`EmusPythonCryptoChecker`).

2. Create a new virtual environment called `venv5`:

   ```bat
   python -m venv venv5
   ```

   * This creates a `venv5\` subfolder containing a standalone Python environment.

3. Activate the new environment:

   ```bat
   call venv5\Scripts\activate.bat
   ```

   * Your prompt should now be prefixed with `(venv5)` indicating you are inside that environment.

4. (Optional) Double-check that your prompt shows `(venv5)` and that `python --version` points to a Python interpreter within `venv5`.

---

### 3. Install Dependencies

With the `venv5` environment active, install all required packages using `requirements.txt`.

1. In the same terminal (where `(venv5)` is shown), run:

   ```bat
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   * This will install packages such as `streamlit`, `pandas`, `requests`, and (if needed) `plotly`.
   * If Plotly is missing (and you want Candlestick charts), ensure the line `plotly` is present in `requirements.txt` or install it manually:

     ```bat
     pip install plotly
     ```

2. Once installation completes, you should see a list of installed packages.

---

### 4. Verify & Run the Streamlit App Manually

At this point, everything is set up. Let’s test by launching the app directly:

1. Confirm you’re in the project folder and that the `(venv5)` environment is active.

2. Start Streamlit:

   ```bat
   streamlit run streamlit_app.py
   ```

3. A browser window (or tab) should open automatically at `http://localhost:8501`, displaying **Emus Crypto Dashboard**.

   * If it does not open automatically, copy‐paste the “Local URL” shown in the terminal into your browser.

4. Interact with sidebar controls (select fiat, coins, timeframes, etc.) to confirm that data appears correctly:

   * **Selected Coins Overview** table with up/down arrows.
   * **Historical Price Trends** with Plotly line charts.
   * **Price Change Distribution (24h)** toggleable between Bar, Line, or Candlestick.
   * **Network / Exchange Fees** table showing arrows when USD fees change.

---

### 5. Create (or Update) the Batch Launcher `run_dashboard.bat`

Rather than typing commands every time, we can automate activation, dependency installation, and running Streamlit with a batch file.

1. In your project root (`EmusPythonCryptoChecker`), create a file named `run_dashboard.bat`.
2. Open it in Notepad (or any text editor) and paste the following contents:

   ```bat
   @echo off
   REM --------------------------------------------------------
   REM Emus Crypto Dashboard Launcher
   REM --------------------------------------------------------

   REM 1) Switch to D: drive (modify if your project is elsewhere)
   D:

   REM 2) Change to the project folder
   cd D:\!EmuPythonProjects\EmusPythonCryptoChecker

   REM 3) Activate the virtual environment named venv5
   call venv5\Scripts\activate.bat

   REM 4) Install any missing requirements (runs pip install -r)
   pip install -r requirements.txt

   REM 5) Launch Streamlit
   streamlit run streamlit_app.py

   REM Keep the window open to view logs or errors
   pause
   ```
3. Save and close `run_dashboard.bat`.

#### If You Use a Different Virtual Environment Name

* Replace `venv5\Scripts\activate.bat` with your alternative path, e.g.:

  ```bat
  call my_env_name\Scripts\activate.bat
  ```
* If your project folder is in a different location, update the `cd` line accordingly:

  ```bat
  cd C:\Users\YourName\Documents\CryptoDashboard
  ```

---

### 6. Launch with the Batch File

From now on, to start the dashboard:

1. Double‐click **`run_dashboard.bat`**.
2. A console window will open, activate the venv, install any missing packages, and run Streamlit.
3. Leave this window open to see real-time Streamlit logs (warnings, errors, “Local URL,” etc.).

---

### 7. Modifying or Updating Dependencies

* If you add new Python packages to the project (e.g., a new library), update **`requirements.txt`**:

  1. With the `venv5` environment active, install the new package:

     ```bat
     pip install some_new_package
     ```
  2. Then update `requirements.txt` via:

     ```bat
     pip freeze > requirements.txt
     ```
* Next time `run_dashboard.bat` runs, it will automatically install the newly listed package.

---

### 8. Pydroid3 / Android Compatibility (Optional)

* **Streamlit does not run on Pydroid3**. Instead, maintain a separate “Lite” Python script for Android (the original console version).
* When on Android, open Pydroid3 and run the CLI script (`cryptchecker.py`) instead of the Streamlit app.
* The “Mobile Mode (Lite Defaults)” checkbox in the Streamlit sidebar only changes which coins are preselected. You still need a desktop/Windows environment for Streamlit itself.

---

## Summary of Commands

1. **Clone & navigate:**

   ```bat
   git clone https://github.com/mremuu/EmusPythonCryptoChecker.git
   cd EmusPythonCryptoChecker
   ```
2. **Create and activate venv:**

   ```bat
   python -m venv venv5
   call venv5\Scripts\activate.bat
   ```
3. **Install dependencies:**

   ```bat
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. **Run (manually):**

   ```bat
   streamlit run streamlit_app.py
   ```
5. **Run (via batch):**

   * Double‐click `run_dashboard.bat` (or execute it from the prompt).

---

With these steps, you should have a fully operational **Emus Crypto Dashboard** running in its own `venv5` virtual environment. Adjust the batch file if you prefer a different venv name or project path, and enjoy the interactive, synthwave‐themed crypto analytics UI!
