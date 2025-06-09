
## Description

**Emus Crypto Dashboard** is a cross-platform (Windows & Android via Pydroid3) Streamlit app built for real-time crypto analytics:

* **Live market data** from CoinGecko with CoinCap fallback
* **Fiat currency selector** (all major 3-letter codes)
* **Quick watchlists** (Top 10 by market cap, Trending, Gainers/Losers, DeFi, Privacy) + fully **customizable** coin lists
* **Historical price trends** (line & candlestick) over 24 h, 7 d, 1 m, 3 m, 1 y, and max
* **Price Change Distribution** scatter or candlestick view 📊
* **Network/Exchange fees** table with fiat conversion
* **Permalinks** via URL query params for instant share-ability
* **Dark & light themes**, retro “Press Start 2P” font, synthwave rainbow header animations
* **CSV & PNG export** on every table/chart
* **Robust error handling** & fallback caching so you never lose access if an API goes down

Perfect for traders or data scientists who need a fast, shareable, and visually striking crypto dashboard.


---

# Setup Guide for Emus Crypto Dashboard

Below are the steps to get **Emus Crypto Dashboard** up and running in a Windows environment, using a virtual environment named `venv5`. If you prefer another environment name, substitute `venv5` with your preferred name in both the instructions and the batch file.

---

## 1. Clone or Download the Repository

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
    ├─ cryptchecker.py       (original CLI version)
    ├─ streamlit_app.py      (the new Streamlit dashboard)
    ├─ requirements.txt
    ├─ run_dashboard.bat     (batch launcher)
    └─ … (other files)
```

---

## 2. Create & Activate a Virtual Environment (`venv5`)

1. Ensure you’re in the project folder (`EmusPythonCryptoChecker`).
2. Create a new virtual environment called `venv5`:

   ```bat
   python -m venv venv5
   ```

   This will create a `venv5\` subfolder containing a standalone Python environment.
3. Activate the new environment:

   ```bat
   call venv5\Scripts\activate.bat
   ```

   Your prompt should now be prefixed with `(venv5)` indicating you are inside that environment.
4. (Optional) Run `python --version` and `where python` to confirm you’re pointing to the `venv5` interpreter.

---

## 3. Install Dependencies

With the `(venv5)` environment active, install all required packages:

1. Upgrade pip and install from `requirements.txt`:

   ```bat
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   * This will install `streamlit`, `pandas`, `requests`, and `plotly` (if specified).
   * If `plotly` is not yet in `requirements.txt`, or if you need an update, run:

     ```bat
     pip install plotly
     ```
2. Wait for installation to complete. You should see a summary of installed packages at the end.

---

## 4. Verify & Run the Streamlit App Manually

1. Confirm you’re in the project folder and that `(venv5)` is active.
2. Launch the Streamlit app:

   ```bat
   streamlit run streamlit_app.py
   ```
3. A browser window (or tab) should open at `http://localhost:8501`. If it doesn’t open automatically, copy the “Local URL” from the terminal and paste it into your browser.
4. Interact with the dashboard to verify:

   * **Selected Coins Overview** table with ▲/▼ arrows.
   * **Historical Price Trends** using Plotly line charts for chosen timeframes.
   * **Price Change Distribution (24h)** toggled between Bar, Line, or Candlestick charts.
   * **Network / Exchange Fees** table showing ▲/▼ indicators for USD fees.

---

## 5. Create the Batch Launcher `run_dashboard.bat`

To avoid repeating commands each time, use a batch file:

1. In the `EmusPythonCryptoChecker` folder, create a file named `run_dashboard.bat`.
2. Open it in Notepad (or your editor) and paste:

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

### If You Use a Different Virtual Environment Name

* Replace `venv5\Scripts\activate.bat` with your own path, for example:

  ```bat
  call myenv\Scripts\activate.bat
  ```
* If your project folder sits elsewhere, update the `cd` line accordingly:

  ```bat
  cd C:\Users\YourName\Documents\CryptoDashboard
  ```

---

## 6. Launch with the Batch File

1. Double‐click **`run_dashboard.bat`** (or right‐click and choose “Run as administrator” if needed).
2. A console window will open, activate `venv5`, install any missing packages, and run Streamlit.
3. Leave this window open to view real‐time logs or errors.

---

## 7. Updating Dependencies & Requirements

* When you add or upgrade packages, update `requirements.txt`:

  1. With the `(venv5)` environment active, install new packages:

     ```bat
     pip install some_new_package
     ```
  2. Regenerate `requirements.txt`:

     ```bat
     pip freeze > requirements.txt
     ```
* Next time you run `run_dashboard.bat`, it will automatically install the updated dependencies.

---

## 8. Android / Pydroid3 Compatibility (Optional)

* Streamlit cannot run in Pydroid3 on Android. Instead, to test on mobile, keep the original `cryptchecker.py` file and run that script in Pydroid3’s Python console.
* The **“Mobile Mode (Lite Defaults)”** checkbox only affects which coins are preselected (does not make the Streamlit UI itself mobile‐native).
* For a truly responsive mobile view, consider deploying the Streamlit app to a cloud service (e.g. Streamlit Cloud, Heroku, AWS) and accessing via mobile browser.

---

### Congratulations!

You now have **Emus Crypto Dashboard** set up in `venv5` 
