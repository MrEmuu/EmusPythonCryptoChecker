import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from typing import Union

# Attempt to import Plotly; if missing, disable candlestick option
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# ─────────────────────────────────────────────────────────────────────────────
# Important: set_page_config must be the very first Streamlit call in this file
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Emus Crypto Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# Inject custom CSS for synthwave/cyberpunk styling,
# animated background & warm‐rainbow‐flow text (background‐clip technique)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* 1) Full‐page animated gradient background (synthwave grid + gradient) */
    body, .reportview-container, .main {
      background: radial-gradient(circle at bottom, #0f0f3a, #0a0a20) no‐repeat fixed;
      color: #ffffff;
    }
    /* Subtle grid overlay */
    .reportview-container {
      background-image:
        repeating-linear-gradient(0deg, rgba(255,255,255,0.03), rgba(255,255,255,0.03) 49px, transparent 50px, transparent 99px),
        repeating-linear-gradient(90deg, rgba(255,255,255,0.03), rgba(255,255,255,0.03) 49px, transparent 50px, transparent 99px);
    }

    /* 2) Sidebar styling */
    .css-1d391kg { background-color: #111129 !important; }
    .css-1d391kg .css-hxt7ib { background-color: #111129 !important; }
    .css-1d391kg .css-1avcm0n { color: #00ffff !important; font-weight: bold; font-size: 1.1rem; }

    /* 3) Warm‐rainbow‐flow background animation */
    @keyframes warm-rainbow-flow {
      0%   { background-position: 0% 50%; }
      50%  { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    .rainbow-text, .rainbow-text-sm {
      background: linear-gradient(90deg,
        #ff0080 0%,   /* hot pink/red */
        #ff4500 33%,  /* orange‐red */
        #ff8c00 66%,  /* orange */
        #ffff00 100%  /* yellow */
      );
      background-size: 200% 200%;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: warm-rainbow-flow 12s ease-in-out infinite;
    }
    .rainbow-text {
      font-family: "Source Code Pro", monospace;
      font-size: 2.5rem;
      font-weight: bold;
      text-align: center;
      margin-bottom: 1rem;
    }
    .rainbow-text-sm {
      font-family: "Source Code Pro", monospace;
      font-size: 1.75rem;
      font-weight: bold;
      margin-bottom: 0.5rem;
    }

    /* 4) Neon‐style buttons */
    .stButton>button {
      background: linear-gradient(45deg, #ff0080 0%, #00ffff 100%) !important;
      color: #000000 !important;
      font-weight: bold !important;
      border: none !important;
      box-shadow:
        0px 0px 8px rgba(255, 0, 128, 0.7),
        0px 0px 12px rgba(0, 255, 255, 0.7) !important;
      transition: transform 0.1s ease-in-out !important;
    }
    .stButton>button:hover {
      transform: scale(1.03) !important;
    }

    /* 5) DataFrame styling: dark background & neon headers */
    .stDataFrame table {
      background-color: #12122e !important;
      color: #ffffff;
    }
    .stDataFrame thead tr th {
      background-color: #1f1f4d !important;
      color: #00ffff !important;
    }
    .stDataFrame tbody tr:nth-child(odd) {
      background-color: #15153b !important;
    }
    .stDataFrame tbody tr:nth-child(even) {
      background-color: #12122e !important;
    }

    /* 6) Chart container background */
    .stChart {
      background-color: #12122e !important;
      padding: 1rem !important;
      border-radius: 8px !important;
    }

    /* 7) Static h2 subheaders are neon magenta—exclude elements using rainbow-text-sm */
    .stMarkdown h2:not(.rainbow-text-sm) {
      color: #ff00ff !important;
      font-family: "Source Code Pro", monospace;
    }

    /* 8) Sidebar label colors */
    .css-1kyxreq.edgvbvh3, .css-1i15e8 {
      color: #00ffff !important;
    }

    /* 9) Hide default Streamlit menu & footer */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────────────────────
# Rainbow‐animated title
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="rainbow-text">Emus Crypto Dashboard</div>', unsafe_allow_html=True)

# Warn if Plotly is missing (disable candlestick)
if not HAS_PLOTLY:
    st.warning(
        "Plotly not installed → Candlestick charts are disabled.\n"
        "Run `pip install plotly` in your venv to enable."
    )

# ─────────────────────────────────────────────────────────────────────────────
# Constants for data fetching
# ─────────────────────────────────────────────────────────────────────────────
SUPPORTED_CURRENCIES = [
    'AED','ARS','AUD','BDT','BHD','BNB','BRL','BTC','CAD','CHF','CLP','CNY','CZK',
    'DKK','EUR','GBP','HKD','HUF','IDR','ILS','INR','JPY','KRW','KWD','LKR','MMK',
    'MXN','MYR','NGN','NOK','NZD','PHP','PKR','PLN','RUB','SAR','SEK','SGD','THB',
    'TWD','TRY','UAH','USD','VEF','VND','ZAR'
]

EXCHANGE_PAIRS = {
    "xmr_btc": {"fee_percent": 0.5, "fee_fixed": 0.0005, "min_amount": 0.01},
    "btc_eth": {"fee_percent": 0.3, "fee_fixed": 0.0003, "min_amount": 0.001},
    "eth_usdt": {"fee_percent": 0.2, "fee_fixed": 1.0,   "min_amount": 0.1},
    # … you can add more pairs here …
}

TIMEFRAMES = {
    "24h": "1",
    "7d": "7",
    "1m": "30",
    "3m": "90",
    "1y": "365",
    "max": "max"
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions (data retrieval + processing)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_coins_list(fiat: str) -> pd.DataFrame:
    fiat_lower = fiat.lower()
    try:
        # Primary: CoinGecko
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': fiat_lower,
            'order': 'market_cap_desc',
            'per_page': 100,
            'page': 1,
            'sparkline': 'false'
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame([{
            'id': coin['id'],
            'symbol': coin['symbol'].upper(),
            'name': coin['name'],
            'price': coin['current_price'],
            'change_24h': coin.get('price_change_percentage_24h', 0)
        } for coin in data])
        return df

    except Exception:
        # Fallback: CoinCap
        try:
            cc_url = "https://api.coincap.io/v2/assets"
            cc_params = {'limit': 100}
            cc_resp = requests.get(cc_url, params=cc_params, timeout=10)
            cc_resp.raise_for_status()
            cc_data = cc_resp.json().get('data', [])
            rate = get_fiat_conversion_rate(fiat)
            df_cc = pd.DataFrame([{
                'id': asset['id'],
                'symbol': asset['symbol'].upper(),
                'name': asset['name'],
                'price': float(asset['priceUsd']) if fiat_lower == 'usd'
                         else float(asset['priceUsd']) * rate,
                'change_24h': float(asset.get('changePercent24Hr', 0))
            } for asset in cc_data])
            return df_cc

        except Exception:
            st.error("⛔ Both CoinGecko and CoinCap APIs failed. Please try again later.")
            return pd.DataFrame()

@st.cache_data(ttl=60)
def get_historical_data(coin_id: str, fiat: str, days: Union[int, str]) -> pd.DataFrame:
    fiat_lower = fiat.lower()
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {'vs_currency': fiat_lower, 'days': days}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get('prices', [])
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data, columns=['timestamp', 'price'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        # Optional downsampling if too many points
        # if len(df) > 1000:
        #     df = df.iloc[::5]
        return df[['datetime', 'price']]
    except Exception:
        return pd.DataFrame()

def get_fiat_conversion_rate(fiat: str) -> float:
    fiat_lower = fiat.lower()
    try:
        url = "https://api.coingecko.com/api/v3/exchange_rates"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        rates = resp.json().get('rates', {})
        if fiat_lower in rates:
            return float(rates[fiat_lower]['value'])
    except Exception:
        pass
    return 1.0

def compute_fiat_value(amount: float, price: float) -> float:
    return amount * price

# ─────────────────────────────────────────────────────────────────────────────
# Main Dashboard Layout
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Sidebar: Settings
    st.sidebar.header("Settings")
    fiat_currency = st.sidebar.selectbox(
        "Select Fiat Currency",
        SUPPORTED_CURRENCIES,
        index=SUPPORTED_CURRENCIES.index('USD')
    )
    auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=False)
    refresh_interval = st.sidebar.slider(
        "Refresh Interval (seconds)",
        min_value=30, max_value=300, value=60, step=30
    )
    st.sidebar.markdown(
        "<span style='color:#ff00ff; font-size:0.9rem;'>"
        "To refresh data, reload your browser</span>",
        unsafe_allow_html=True
    )

    # Fetch coin list
    coins_df = get_coins_list(fiat_currency)

    # If the fetch returned an empty DataFrame (no 'symbol' column), show an error and exit
    if coins_df.empty or "symbol" not in coins_df.columns:
        st.error("⚠️ Unable to load coin data. Please check your network or try again later.")
        return

    # Mobile Mode (light default)
    is_mobile = st.sidebar.checkbox("Mobile Mode (Lite Defaults)", value=False)
    default_selection = ["BTC", "XMR"] if not is_mobile else ["BTC", "XMR"]

    selected_coins = st.sidebar.multiselect(
        "Select Coins to Analyze",
        options=coins_df["symbol"].tolist(),
        default=default_selection
    )

    # ─ Selected Coins Overview ───────────────────────────────
    st.markdown('<h2 class="rainbow-text-sm">Selected Coins Overview</h2>', unsafe_allow_html=True)
    if not coins_df.empty and selected_coins:
        overview_df = coins_df[coins_df["symbol"].isin(selected_coins)].set_index("symbol")
        # Build a display DataFrame that includes up/down arrows
        display_df = overview_df[["name", "price", "change_24h"]].copy()

        def format_change(val):
            try:
                num = float(val)
            except:
                return f"{val}"
            arrow = "▲" if num >= 0 else "▼"
            return f"{arrow} {abs(num):.2f}%"

        display_df["price"] = display_df["price"].map(lambda x: f"{x:,.2f}")
        display_df["change_24h"] = display_df["change_24h"].map(format_change)
        display_df = display_df.rename(columns={"name": "Name", "price": "Price", "change_24h": "24 h Change"})
        st.dataframe(display_df)
    else:
        st.write("No coins selected or no data available.")

    # ─ Historical Price Trends ───────────────────────────────
    st.markdown('<h2 class="rainbow-text-sm">Historical Price Trends</h2>', unsafe_allow_html=True)
    timeframe_options = list(TIMEFRAMES.keys())
    selected_timeframes = st.multiselect(
        "Select Timeframes",
        options=timeframe_options,
        default=[]
    )

    if selected_coins and selected_timeframes:
        for timeframe in selected_timeframes:
            st.markdown(f'<h3 class="rainbow-text-sm">{timeframe} Trend</h3>', unsafe_allow_html=True)
            merged_df = None

            with st.spinner(f"⏳ Fetching {timeframe} data for {len(selected_coins)} coin(s)…"):
                for symbol in selected_coins:
                    # 1) Look up the coin’s “id”
                    try:
                        coin_id = coins_df.loc[coins_df["symbol"] == symbol, "id"].values[0]
                    except Exception:
                        continue

                    # 2) Fetch that coin’s historical data
                    days_param = TIMEFRAMES[timeframe]
                    hist_df = get_historical_data(coin_id, fiat_currency, days_param)

                    if not hist_df.empty:
                        # 3) Build a Series indexed by datetime, named after the symbol
                        ser = hist_df.set_index("datetime")["price"].rename(symbol)

                        # 4) Merge (outer-join) onto merged_df
                        if merged_df is None:
                            merged_df = ser.to_frame()
                        else:
                            merged_df = merged_df.join(ser, how="outer")

            # 5) After the loop, plot using Plotly if we have data
            if merged_df is not None and not merged_df.empty:
                fig = go.Figure()
                for col in merged_df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=merged_df.index,
                            y=merged_df[col],
                            mode="lines",
                            name=col,
                            line=dict(width=2)
                        )
                    )
                fig.update_layout(
                    plot_bgcolor="#12122e",
                    paper_bgcolor="#12122e",
                    font_color="#ffffff",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis=dict(
                        title="Date",
                        showgrid=True,
                        gridcolor="#2e2e3e",
                        tickfont=dict(color="#ffffff")
                    ),
                    yaxis=dict(
                        title=f"Price ({fiat_currency})",
                        showgrid=True,
                        gridcolor="#2e2e3e",
                        tickfont=dict(color="#ffffff")
                    ),
                    title_text=f"{timeframe} Price Trend",
                    title_x=0.5,
                    title_font=dict(color="#ff00ff", size=18)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write(f"No historical data available for {timeframe}.")

    elif not selected_timeframes:
        st.info("ℹ️ Select one or more timeframes above to load historical charts.")
    else:
        st.write("No coins selected for historical data.")

    # ─ Price Change Distribution (24h) ───────────────────────
    st.markdown('<h2 class="rainbow-text-sm">Price Change Distribution (24h)</h2>', unsafe_allow_html=True)
    # Offer three chart types: Bar, Line, Candlestick (if Plotly installed)
    if HAS_PLOTLY:
        chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Candlestick"], key="distribution_chart")
    else:
        chart_type = st.selectbox("Chart Type", ["Bar", "Line"], key="distribution_chart")

    if not coins_df.empty and chart_type == "Bar":
        change_df = coins_df[["symbol", "change_24h"]].copy().set_index("symbol")
        # Reformat for plotting so negative/positive are left as numbers
        change_df["change_24h"] = change_df["change_24h"].astype(float)
        st.bar_chart(change_df)
    elif not coins_df.empty and chart_type == "Line":
        line_df = coins_df[["symbol", "change_24h"]].copy().set_index("symbol")
        line_df["change_24h"] = line_df["change_24h"].astype(float)
        st.line_chart(line_df)
    elif HAS_PLOTLY and not coins_df.empty and chart_type == "Candlestick":
        if selected_coins:
            symbol = selected_coins[0]
            coin_id = coins_df.loc[coins_df["symbol"] == symbol, "id"].values[0]
            hist_df = get_historical_data(coin_id, fiat_currency, "1")
            if not hist_df.empty:
                # Changed resample from "1H" to "1h" to silence FutureWarning
                df_ohlc = hist_df.set_index("datetime").resample("1h").agg({
                    "price": ["first", "max", "min", "last"]
                })
                df_ohlc.columns = ["open", "high", "low", "close"]
                df_ohlc = df_ohlc.dropna()
                fig = go.Figure(data=[
                    go.Candlestick(
                        x=df_ohlc.index,
                        open=df_ohlc["open"],
                        high=df_ohlc["high"],
                        low=df_ohlc["low"],
                        close=df_ohlc["close"],
                        increasing_line_color="#00ff00",
                        decreasing_line_color="#ff0000"
                    )
                ])
                fig.update_layout(
                    plot_bgcolor="#12122e",
                    paper_bgcolor="#12122e",
                    font_color="#ffffff",
                    xaxis_title="Time",
                    yaxis_title=f"Price ({fiat_currency})",
                    margin=dict(l=20, r=20, t=20, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("No historical data available for candlestick.")
        else:
            st.write("Select at least one coin to view candlestick.")
    else:
        st.write("No data available for price change distribution.")

    # ─ Network / Exchange Fees ───────────────────────────────
    st.markdown('<h2 class="rainbow-text-sm">Network / Exchange Fees</h2>', unsafe_allow_html=True)

    # Build current fees as a DataFrame
    fee_records = []
    for pair, info in EXCHANGE_PAIRS.items():
        base, quote = pair.split("_")
        base_upper = base.upper()
        quote_upper = quote.upper()

        if base_upper in selected_coins or quote_upper in selected_coins:
            try:
                price_base = float(coins_df.loc[coins_df["symbol"] == base_upper, "price"].values[0])
            except Exception:
                continue

            fee_fixed_crypto = info["fee_fixed"]
            min_amount_crypto = info["min_amount"]
            fee_fixed_fiat = compute_fiat_value(fee_fixed_crypto, price_base)
            min_amount_fiat = compute_fiat_value(min_amount_crypto, price_base)

            fee_records.append({
                "Pair": f"{base_upper} → {quote_upper}",
                "Fee (%)": info["fee_percent"],
                "Fixed Fee (Crypto)": fee_fixed_crypto,
                "Fixed Fee (USD)": fee_fixed_fiat,
                "Min Amount (Crypto)": min_amount_crypto,
                "Min Amount (USD)": min_amount_fiat
            })

    # Convert to DataFrame
    current_fee_df = pd.DataFrame(fee_records).set_index("Pair")

    # --- Compare with previous run (stored in session_state) to add up/down indicators ---
    prev_fee_df = st.session_state.get("prev_fee_df", None)

    # We will build a display DataFrame where USD columns get arrows
    display_fee_df = current_fee_df.copy()

    # Only add arrows if we have a previous run to compare to
    if prev_fee_df is not None and not prev_fee_df.empty:
        for col in ["Fixed Fee (USD)", "Min Amount (USD)"]:
            arrows = []
            for pair in display_fee_df.index:
                curr_val = display_fee_df.at[pair, col]
                # If the previous DataFrame is missing this pair or column, treat as unchanged
                if pair in prev_fee_df.index:
                    prev_val = prev_fee_df.at[pair, col] if col in prev_fee_df.columns else None
                else:
                    prev_val = None

                if prev_val is None:
                    arrow = ""  # No comparison possible
                else:
                    # Compare current vs previous
                    if curr_val > prev_val:
                        arrow = "▲ "  # went up
                    elif curr_val < prev_val:
                        arrow = "▼ "  # went down
                    else:
                        arrow = ""   # unchanged

                # Prefix the arrow string to the formatted number (two decimals)
                arrows.append(f"{arrow}{curr_val:,.2f}")

            # Replace the raw numeric column with the arrow‐annotated string column
            display_fee_df[col] = arrows
    else:
        # First run: just format to two decimals (no arrow)
        display_fee_df["Fixed Fee (USD)"] = display_fee_df["Fixed Fee (USD)"].map(lambda x: f"{x:,.2f}")
        display_fee_df["Min Amount (USD)"] = display_fee_df["Min Amount (USD)"].map(lambda x: f"{x:,.2f}")

    # Also format the Crypto columns (no arrow, just format)
    display_fee_df["Fixed Fee (Crypto)"] = display_fee_df["Fixed Fee (Crypto)"].map(lambda x: f"{x}")
    display_fee_df["Min Amount (Crypto)"] = display_fee_df["Min Amount (Crypto)"].map(lambda x: f"{x}")
    display_fee_df["Fee (%)"] = display_fee_df["Fee (%)"].map(lambda x: f"{x}")

    # Show the DataFrame
    st.dataframe(display_fee_df)

    # Store current fees for next run
    # But store raw numeric values (not arrow‐annotated) so next comparison is accurate:
    numeric_prev = current_fee_df.copy()
    st.session_state["prev_fee_df"] = numeric_prev

    # ─ Footer / Meta Info ───────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<span style='color:#00ffff;'>"
        "Data Source: CoinGecko (with CoinCap fallback)  |  "
        f"Refresh Interval: {refresh_interval} sec</span>",
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────────────────────────────────────
# Run the dashboard immediately when Streamlit loads this script
# ─────────────────────────────────────────────────────────────────────────────
main()
