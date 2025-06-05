A Python-based terminal crypto converter with Android (Pydroid3) and Windows support. It fetches real-time prices and historical trends (24h, 7d, 1m, 3m, 1y, all-time) from CoinGecko and CoinCap (with automatic failover), supports user-selected fiat currency, and displays network/exchange fees (with fiat equivalents). Fully navigable via keyboard, paginated top-100 list, search by symbol/ID/name, and customizable API prioritization. Designed primarily for Pydroid3 on Android—Windows support is included but may have quirks.

**Features:**

* **Multi-API Support**

  * Primary: CoinGecko; Fallback: CoinCap
  * Automatic failover if one API is unavailable
* **Real-Time Prices & Historical Trends**

  * Live top-100 list in user’s chosen fiat (USD, EUR, etc.)
  * Historical data for 24h, 7d, 1m, 3m, 1y, and all-time
* **User-Selectable Fiat Currency**

  * One-time prompt on first run; defaults to USD if Enter is pressed
* **Network & Exchange Fees**

  * Displays variable fee %, fixed fee + fiat equivalent, and minimum amount + fiat equivalent
  * Only shows direct “base → quote” pairs for the selected coin
* **Clean, Two-Decimal Formatting**

  * Prices formatted with commas and exactly two decimals (e.g., `103,159.00`)
  * Ensures percentage signs (e.g., `2.00%`) never wrap or get cut off
* **Keyboard-Driven Navigation**

  * Paginated top-100 list (N/P to navigate, S to search, Q to quit)
  * Search by symbol, ID, or name, returning up to 10 matches
  * Numbered menus for coin details and fee views, with consistent “3: Go Back”
* **API Switching & Status Display**

  * “A: Switch API” in the main menu to reorder primary/fallback
  * Shows “API SELECTED = \<CoinGecko/CoinCap>” under the header
* **Cross-Platform**

  * Built for Android (Pydroid3) but also runnable on Windows
  * Windows version may have minor display quirks compared to Pydroid3

Feel free to adjust or expand as needed!
