
## Description

**Emus Crypto Dashboard** is a feature-rich, synthwave‐themed web application built with Streamlit, designed to provide real‐time and historical analytics for the top cryptocurrencies. Originally based on a terminal‐driven Python script, this modern dashboard consolidates price data, historical trends, exchange/network fee comparisons, and interactive visualizations—all within a dark, cyberpunk‐inspired interface. Users can select multiple coins, view automated up/down indicators for price changes and fees, and toggle between bar, line, and candlestick charts. The app also supports a fallback mechanism (CoinCap) if CoinGecko is unreachable, and it caches data to minimize redundant API calls.

Whether you’re an active trader, a data scientist, or simply a crypto enthusiast, Emus Crypto Dashboard offers an at‐a‐glance view of market movements, plus plenty of tools to drill deeper into specific coins’ performance over various timeframes.

---

## Planned / Optional Features to Add

Below is a non‐exhaustive list of potential enhancements you might consider adding in future iterations:

1. **User Authentication & Personal Watchlists**

   * Allow users to log in (e.g. via OAuth) and save personalized coin watchlists so that selections persist across sessions.
   * Enable push notifications or email alerts when a coin’s price crosses a certain threshold.

2. **Advanced Charting & Drawing Tools**

   * Integrate more advanced Plotly features: zoom/pan presets, RSI/MACD overlays, Bollinger Bands, volume bars.
   * Offer on‐chart drawing tools (trendlines, Fibonacci retracements) for technical analysis.

3. **Portfolio Tracking & Profit/Loss Calculator**

   * Let users input their holdings (amount of each coin and purchase price) to see real‐time portfolio value and P\&L.
   * Provide a “Tax Summary” section that calculates realized/unrealized gains in fiat.

4. **Deeper Fund Flow / On‐Chain Metrics**

   * Pull in on‐chain metrics (e.g. network transaction volume, active addresses, hash rate).
   * Display fund flow heatmaps for major exchanges (inflows vs. outflows) to gauge market sentiment.

5. **Multiple Fiat/Stablecoin Support**

   * Expand beyond static fiat conversion: allow quoting in stablecoins (USDT, USDC, BUSD) or other fiat pairs (e.g., EUR‐BTC, JPY‐ETH).
   * Show a small sparkline of FX rate changes alongside coin prices (e.g., EUR→USD, JPY→USD).

6. **News & Sentiment Integration**

   * Embed a news RSS/JSON feed widget for each selected coin (e.g., CoinTelegraph, CryptoPanic).
   * Overlay sentiment analysis (positive/negative) from Twitter or Reddit posts alongside price charts.

7. **Comparison Mode & Correlation Matrix**

   * Allow side‐by‐side comparisons of two or more coins on the same axes (axis scaling options, normalization).
   * Compute and display a coin‐correlation matrix (heatmap) over the chosen timeframe (7d, 30d, 90d).

8. **Order Book Snapshot & Live Ticker**

   * Fetch and display a top‐10 order book snapshot for a selected coin/pair (via exchange REST WebSocket).
   * Show a live ticker of trades (in the sidebar or a marquee at the top) for real‐time feel.

9. **Dark‐Light Mode Toggle**

   * Offer a “Light Mode” CSS theme switch for users who prefer higher‐contrast or paper‐white backgrounds.
   * Store preference in `st.session_state` or user settings so that UI text and chart backgrounds switch accordingly.

10. **Export & Download Options**

    * Let users export historical data (CSV/Excel) for selected coins/timeframes.
    * Provide a “Download Chart as PNG” button on each Plotly figure.

11. **Mobile‐Friendly Layout Tweaks**

    * Create a responsive layout using `st.beta_columns` or container widths so components stack gracefully on narrow screens.
    * Offer a simplified “Lite Mode” that hides heavier charts for slower mobile connections (Android).

12. **Multi‐Exchange Price Aggregation**

    * Query additional APIs (e.g., Binance, Kraken, Coinbase) and display an aggregated “best bid/ask” or volume‐weighted average price (VWAP).
    * Show the price spread across different exchanges in a small table.

13. **Historical Volatility & Metrics Dashboard**

    * Compute and visualize realized/perceived volatility (e.g., 30d rolling volatility).
    * Add metrics like Sharpe ratio, Sortino ratio, and drawdown curves for each coin over chosen timeframes.

14. **Custom Alerts & Triggers**

    * Allow users to set alerts for when a coin’s price moves by a certain % in an hour/day.
    * Use a back‐end scheduler (e.g., PingStreamlit or a lightweight Celery worker) to check and trigger notifications.

15. **Localization & Internationalization**

    * Translate UI text into multiple languages (Spanish, Chinese, Russian, etc.).
    * Detect the browser’s locale and auto‐select the appropriate fiat (EUR, GBP, CNY).

16. **Plugin System for Community‐Contributed Widgets**

    * Architect a simple plugin API so advanced users can drop in additional charts or data sources (e.g., DeFi TVL, NFT floor prices).
    * Provide a “Plugins” folder where each `.py` plugin can register itself with the main dashboard.

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
