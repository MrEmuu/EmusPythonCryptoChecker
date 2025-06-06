import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from typing import Union

# ─────────────────────────────────────────────────────────────────────────────
# Important: set_page_config must be the very first Streamlit call in this file
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Crypto Analytics Dashboard", layout="wide")


# ─────────────────────────────────────────────────────────────────────────────
# Constants / Config
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
    # …add more pairs if desired…
}

# Historical timeframes to mirror CoinGecko
TIMEFRAMES = {
    "24h": "1",
    "7d": "7",
    "1m": "30",
    "3m": "90",
    "1y": "365",
    "max": "max"
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_coins_list(fiat: str) -> pd.DataFrame:
    """
    Fetch top-100 coins from CoinGecko (fallback to CoinCap).
    Returns a DataFrame with columns: id, symbol, name, price, change_24h.
    """
    fiat_lower = fiat.lower()
    # Try CoinGecko first
    try:
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
        # Fallback to CoinCap
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
    """
    Fetch historical price data from CoinGecko.
    Returns DataFrame with columns: datetime, price.
    If CoinGecko fails, returns an empty DataFrame.
    """
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

        # OPTIONAL: down-sample if too many points
        # if len(df) > 1000:
        #     df = df.iloc[::5]

        return df[['datetime', 'price']]
    except Exception:
        return pd.DataFrame()


def get_fiat_conversion_rate(fiat: str) -> float:
    """
    Fetch USD → <fiat> conversion rate via CoinGecko.
    If request fails, return 1.0 (i.e., treat as USD).
    """
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
    """Convert a crypto amount into its fiat equivalent."""
    return amount * price


# ─────────────────────────────────────────────────────────────────────────────
# Build the Page
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Title
    st.title("📊 Crypto Analytics Dashboard")

    # Sidebar: Settings
    st.sidebar.header("Settings")
    fiat_currency = st.sidebar.selectbox(
        "Select Fiat Currency",
        SUPPORTED_CURRENCIES,
        index=SUPPORTED_CURRENCIES.index('USD')
    )
    auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=True)
    refresh_interval = st.sidebar.slider(
        "Refresh Interval (seconds)",
        min_value=30, max_value=300, value=60, step=30
    )

    # If auto-refresh is checked, immediately rerun
    if auto_refresh:
        st.experimental_rerun()

    # Fetch coin list
    coins_df = get_coins_list(fiat_currency)

    # “Mobile Mode” toggle (light default) for phones
    is_mobile = st.sidebar.checkbox("Mobile Mode (Lite Defaults)", value=False)
    default_selection = ["BTC"] if is_mobile else ["BTC", "ETH"]

    selected_coins = st.sidebar.multiselect(
        "Select Coins to Analyze",
        options=coins_df["symbol"].tolist(),
        default=default_selection
    )

    # ─ Selected Coins Overview ───────────────────────────────
    st.subheader("Selected Coins Overview")
    if not coins_df.empty and selected_coins:
        overview_df = coins_df[coins_df["symbol"].isin(selected_coins)].set_index("symbol")
        overview_display = overview_df[["name", "price", "change_24h"]].copy()
        overview_display["price"] = overview_display["price"].map(lambda x: f"{x:,.2f}")
        overview_display["change_24h"] = overview_display["change_24h"].map(lambda x: f"{x:.2f}%")
        st.dataframe(overview_display)
    else:
        st.write("No coins selected or no data available.")

    # ─ Historical Price Trends ───────────────────────────────
    st.subheader("Historical Price Trends")
    timeframe_options = list(TIMEFRAMES.keys())
    selected_timeframes = st.multiselect(
        "Select Timeframes",
        options=timeframe_options,
        default=[]
    )

    if selected_coins and selected_timeframes:
        for timeframe in selected_timeframes:
            st.markdown(f"**{timeframe} Trend**")
            chart_data = pd.DataFrame()
            with st.spinner(f"⏳ Fetching {timeframe} data for {len(selected_coins)} coin(s)…"):
                for symbol in selected_coins:
                    try:
                        coin_id = coins_df.loc[coins_df["symbol"] == symbol, "id"].values[0]
                    except Exception:
                        continue
                    days_param = TIMEFRAMES[timeframe]
                    hist_df = get_historical_data(coin_id, fiat_currency, days_param)
                    if not hist_df.empty:
                        chart_data[symbol] = hist_df.set_index("datetime")["price"]
            if not chart_data.empty:
                st.line_chart(chart_data)
            else:
                st.write(f"No historical data available for {timeframe}.")
    elif not selected_timeframes:
        st.info("ℹ️ Select one or more timeframes above to load historical charts.")
    else:
        st.write("No coins selected for historical data.")

    # ─ Network / Exchange Fees ───────────────────────────────
    st.subheader("Network / Exchange Fees")
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
                f"Fixed Fee ({fiat_currency})": f"{fee_fixed_fiat:,.2f}",
                "Min Amount (Crypto)": min_amount_crypto,
                f"Min Amount ({fiat_currency})": f"{min_amount_fiat:,.2f}"
            })

    if fee_records:
        fee_df = pd.DataFrame(fee_records).set_index("Pair")
        st.dataframe(fee_df)
    else:
        st.write("No exchange pairs available for the selected coins.")

    # ─ 24h Price Change Distribution ─────────────────────────
    st.subheader("Price Change Distribution (24h)")
    if not coins_df.empty:
        change_chart = coins_df[["symbol", "change_24h"]].copy().set_index("symbol")
        st.bar_chart(change_chart)
    else:
        st.write("No data available for price change distribution.")

    # ─ Footer / Meta Info ───────────────────────────────────
    st.markdown("---")
    st.write(f"Data Source: CoinGecko (with CoinCap fallback) | Refresh Interval: {refresh_interval} seconds")


# ─────────────────────────────────────────────────────────────────────────────
# Run the dashboard immediately when Streamlit imports this script
# ─────────────────────────────────────────────────────────────────────────────
main()
