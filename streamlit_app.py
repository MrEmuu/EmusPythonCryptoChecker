import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from typing import Tuple, Union
import os
import re
import json
import hashlib

# Plotly support
try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Page config
st.set_page_config(page_title="Emus Crypto Dashboard", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
SUPPORTED_CURRENCIES = ['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'INR', 'BRL', 'RUB', 'KRW', 'SGD', 'MXN', 'NZD', 'HKD', 'NOK', 'SEK', 'ZAR', 'TRY']
TIMEFRAMES = {"24h": "1", "7d": "7", "1m": "30", "3m": "90", "1y": "365", "max": "max"}
USERS_FILE = "users.json"
EXCHANGE_PAIRS = {"xmr_btc": {"fee_percent": 0.5, "fee_fixed": 0.0005, "min_amount": 0.01}, "btc_eth": {"fee_percent": 0.3, "fee_fixed": 0.0003, "min_amount": 0.001}, "eth_usdt": {"fee_percent": 0.2, "fee_fixed": 1.0, "min_amount": 0.1}}


# ─────────────────────────────────────────────────────────────────────────────
# Helper & Utility Functions
# ─────────────────────────────────────────────────────────────────────────────
def to_float(value) -> float:
    if value is None: return 0.0
    try: return float(value)
    except (ValueError, TypeError): return 0.0

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_users() -> dict:
    if not os.path.exists(USERS_FILE): return {}
    with open(USERS_FILE, 'r') as f: return json.load(f)

def save_users(users_data: dict):
    with open(USERS_FILE, 'w') as f: json.dump(users_data, f, indent=4)

# ─────────────────────────────────────────────────────────────────────────────
# Data Fetching & User Management
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_coins_list(fiat: str) -> Tuple[pd.DataFrame, str]:
    fiat_lower = fiat.lower()
    try:
        url, params = "https://api.coingecko.com/api/v3/coins/markets", {'vs_currency': fiat_lower, 'order': 'market_cap_desc', 'per_page': 250, 'page': 1}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        df = pd.DataFrame([{"id": c["id"], "symbol": c["symbol"].upper(), "name": c["name"], "price": to_float(c.get("current_price")), "change_24h": to_float(c.get("price_change_percentage_24h")), "market_cap": to_float(c.get("market_cap"))} for c in r.json()])
        return df, "coingecko_ok"
    except requests.RequestException: pass
    try:
        cc_url, cc_params = "https://api.coincap.io/v2/assets", {'limit': 250}
        cc_resp = requests.get(cc_url, params=cc_params, timeout=10)
        cc_resp.raise_for_status()
        df_cc = pd.DataFrame([{"id": asset["id"], "symbol": asset["symbol"].upper(), "name": asset["name"], "price": to_float(asset.get("priceUsd")), "change_24h": to_float(asset.get("changePercent24Hr")), "market_cap": to_float(asset.get("marketCapUsd"))} for asset in cc_resp.json().get('data', [])])
        if fiat.upper() != 'USD':
            conversion_rate = get_fiat_conversion_rate(fiat)
            for col in ['price', 'market_cap']: df_cc[col] *= conversion_rate
        return df_cc, "coincap_ok"
    except requests.RequestException:
        return pd.DataFrame(), "api_fail"

@st.cache_data(ttl=300)
def fetch_trending_symbols() -> list[str]:
    try:
        r = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=5)
        r.raise_for_status()
        return [c["item"]["symbol"].upper() for c in r.json().get("coins", [])]
    except requests.RequestException: return []

@st.cache_data(ttl=60)
def get_historical_data(coin_id: str, fiat: str, days: Union[int,str]) -> pd.DataFrame:
    try:
        url, params = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart", {"vs_currency": fiat.lower(), "days": days}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        prices = r.json().get("prices", [])
        if not prices: return pd.DataFrame()
        df = pd.DataFrame(prices, columns=["ts", "price"])
        df["datetime"] = pd.to_datetime(df["ts"], unit="ms")
        return df[["datetime", "price"]]
    except requests.RequestException:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_fiat_conversion_rate(fiat: str) -> float:
    if fiat.upper() == 'USD': return 1.0
    try:
        resp = requests.get(f"https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
        resp.raise_for_status()
        return resp.json().get('rates', {}).get(fiat.upper(), 1.0)
    except requests.RequestException:
        return 1.0

def get_portfolio_path(username: str) -> str:
    safe_username = re.sub(r'[^a-zA-Z0-9_-]', '', username)
    return f"{safe_username}_portfolio.csv"

def load_portfolio(username: str) -> pd.DataFrame:
    path = get_portfolio_path(username)
    if os.path.exists(path): return pd.read_csv(path)
    return pd.DataFrame(columns=["Coin ID", "Type", "Quantity", "Price per Coin", "Date"])

def save_portfolio(df: pd.DataFrame, username: str):
    df.to_csv(get_portfolio_path(username), index=False)

def check_password(username, password) -> bool:
    try:
        if username in st.secrets["passwords"] and password == st.secrets["passwords"][username]: return True
    except (AttributeError, KeyError): pass
    users = load_users()
    hashed_password = hash_password(password)
    if username in users and users[username] == hashed_password: return True
    return False

# ─────────────────────────────────────────────────────────────────────────────
# THEME & Layout CSS
# ─────────────────────────────────────────────────────────────────────────────
def apply_theme():
    dark = st.session_state.get('dark_theme', True)
    FONT = "@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');"
    
    dark_theme = {"bg": "#0a0a20", "text": "#fff", "table_bg": "#12122e", "header_bg": "#1f1f4d", "header_text": "#0ff"}
    light_theme = {"bg": "#FFFFFF", "text": "#31333F", "table_bg": "#f0f2f6", "header_bg": "#e0e0e0", "header_text": "#31333F"}
    theme = dark_theme if dark else light_theme
    
    css = f"""
        <style>
            {FONT}
            body {{ background-color: {theme['bg']}; color: {theme['text']}; font-family: 'Press Start 2P', monospace; }}
            .stDataFrame table {{ background-color: {theme['table_bg']} !important; color: {theme['text']} !important; }}
            .stDataFrame thead th {{ background-color: {theme['header_bg']} !important; color: {theme['header_text']} !important; }}
            .rainbow-text, .rainbow-text-sm {{ font-size: 2.5rem; text-align: center; margin: 1rem 0; }}
            .rainbow-text-sm {{ font-size: 1.75rem; }}
            #MainMenu, footer {{ visibility: hidden; }}
    """
    
    gradient_animation = "background-size: 200% 200%; -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: rainbow-flow 12s ease infinite;"
    keyframes = "@keyframes rainbow-flow { 0%{{background-position:0% 50%}} 50%{{background-position:100% 50%}} 100%{{background-position:0% 50%} }"
    
    if dark:
        css += f".rainbow-text, .rainbow-text-sm {{ background: linear-gradient(90deg, #ff0080, #ff4500, #ff8c00, #ffff00); {gradient_animation} }} {keyframes}"
    else:
        css += f".rainbow-text, .rainbow-text-sm {{ background: linear-gradient(90deg, cyan, magenta, cyan); {gradient_animation} }} {keyframes}"

    st.markdown(f"{css}</style>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# UI Rendering Functions
# ─────────────────────────────────────────────────────────────────────────────
def calculate_holdings(transactions_df: pd.DataFrame) -> dict:
    holdings = {}
    for _, row in transactions_df.iterrows():
        qty = row['Quantity'] if row['Type'] == 'Buy' else -row['Quantity']
        cost = qty * row['Price per Coin']
        if row['Coin ID'] not in holdings: holdings[row['Coin ID']] = {'quantity': 0, 'total_cost': 0}
        holdings[row['Coin ID']]['quantity'] += qty
        holdings[row['Coin ID']]['total_cost'] += cost
    return holdings

def render_overview_tab(coins_df: pd.DataFrame, fiat: str):
    st.markdown('<h2 class="rainbow-text-sm">Quick Converter</h2>', unsafe_allow_html=True)
    all_coins = coins_df.sort_values('name').copy()
    all_coins['display'] = all_coins['name'] + " (" + all_coins['symbol'] + ")"
    coin_options = all_coins['display'].tolist()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Crypto to Fiat")
        selected_coin_display = st.selectbox("Select Coin", coin_options, key="crypto_to_fiat_coin")
        if selected_coin_display:
            selected_symbol = selected_coin_display.split('(')[-1][:-1]
            coin_price = coins_df.loc[coins_df['symbol'] == selected_symbol, 'price'].iloc[0]
            crypto_amount = st.number_input("Amount of Crypto", min_value=0.0, format="%.6f", key="crypto_amount")
            st.metric(label=f"Value in {fiat}", value=f"{crypto_amount * coin_price:,.2f}")
    with col2:
        st.markdown(f"#### {fiat} to Crypto")
        fiat_amount = st.number_input(f"Amount of {fiat}", min_value=0.0, format="%.2f", key="fiat_amount")
        target_coin_display = st.selectbox("Select Coin", coin_options, key="fiat_to_crypto_coin")
        if target_coin_display:
            target_symbol = target_coin_display.split('(')[-1][:-1]
            target_price = coins_df.loc[coins_df['symbol'] == target_symbol, 'price'].iloc[0]
            st.metric(label=f"Value in {target_symbol}", value=f"{fiat_amount / target_price:,.6f}" if target_price > 0 else "0.00")
    st.markdown("---")
    st.markdown('<h2 class="rainbow-text-sm">Market Overview</h2>', unsafe_allow_html=True)
    overview_df = coins_df[['name', 'symbol', 'price', 'change_24h', 'market_cap']].set_index('symbol')
    st.dataframe(overview_df)

def render_portfolio_tab(coins_df, fiat, username):
    st.markdown('<h2 class="rainbow-text-sm">Portfolio Tracker</h2>', unsafe_allow_html=True)
    if 'holdings' not in st.session_state:
        st.session_state.holdings = calculate_holdings(load_portfolio(username))

    def update_price_in_form():
        try:
            selected_symbol = st.session_state.portfolio_coin_select.split('(')[-1][:-1]
            st.session_state.current_price = coins_df.loc[coins_df['symbol'] == selected_symbol, 'price'].iloc[0]
        except (IndexError, KeyError): st.session_state.current_price = 0.0
    if 'current_price' not in st.session_state: st.session_state.current_price = 0.0

    with st.expander("Add New Transaction", expanded=True):
        all_coins = coins_df.sort_values('name').copy()
        all_coins['display'] = all_coins['name'] + " (" + all_coins['symbol'] + ")"
        st.selectbox("Select Coin", all_coins['display'].tolist(), key="portfolio_coin_select", on_change=update_price_in_form)
        with st.form("transaction_form"):
            price_per_coin = st.number_input(f"Price per Coin ({fiat})", value=st.session_state.current_price, format="%.2f")
            quantity = st.number_input("Quantity", min_value=0.0, format="%.8f")
            trans_type = st.radio("Type", ["Buy", "Sell"], horizontal=True)
            if st.form_submit_button("Add Transaction"):
                if quantity > 0:
                    coin_id = all_coins.loc[all_coins['display'] == st.session_state.portfolio_coin_select, 'id'].iloc[0]
                    transactions_df = load_portfolio(username)
                    new_tx = pd.DataFrame([{"Coin ID": coin_id, "Type": trans_type, "Quantity": quantity, "Price per Coin": price_per_coin, "Date": datetime.now().isoformat()}])
                    save_portfolio(pd.concat([transactions_df, new_tx], ignore_index=True), username)
                    st.success("Transaction added!")
                    del st.session_state.holdings
                    st.rerun()

    if not st.session_state.holdings:
        st.info("Your portfolio is empty. Add a transaction to begin.")
        return
    
    portfolio_data, total_value, total_investment = [], 0, 0
    for coin_id, data in st.session_state.holdings.items():
        if data['quantity'] > 0:
            coin_info = coins_df.loc[coins_df['id'] == coin_id]
            if not coin_info.empty:
                current_price, current_value = coin_info['price'].iloc[0], data['quantity'] * coin_info['price'].iloc[0]
                portfolio_data.append({'Coin': coin_info['name'].iloc[0], 'Symbol': coin_info['symbol'].iloc[0], 'Quantity': data['quantity'], 'Current Value': current_value, 'P/L': current_value - data['total_cost']})
                total_value, total_investment = total_value + current_value, total_investment + data['total_cost']
    
    if portfolio_data:
        portfolio_df = pd.DataFrame(portfolio_data)
        col1, col2 = st.columns(2)
        col1.metric("Total Portfolio Value", f"{fiat} {total_value:,.2f}")
        total_pl = total_value - total_investment
        col2.metric("Unrealized P/L", f"{fiat} {total_pl:,.2f}", f"{(total_pl / total_investment) * 100 if total_investment else 0:.2f}%")
        st.dataframe(portfolio_df.set_index('Coin'))

    with st.expander("⚠️ Manage History"):
        if st.button("Clear All Transactions"): st.session_state.confirm_delete = True
        if st.session_state.get('confirm_delete'):
            if st.checkbox("I understand this is permanent."):
                if st.button("CONFIRM DELETION"):
                    os.remove(get_portfolio_path(username))
                    del st.session_state.holdings
                    del st.session_state.confirm_delete
                    st.success("Transaction history deleted.")
                    st.rerun()

def render_historical_tab(coins_df, selected_symbols, fiat, timeframe, chart_type):
    st.markdown('<h2 class="rainbow-text-sm">Historical Price Trends</h2>', unsafe_allow_html=True)
    if not selected_symbols:
        st.info("Select coins in the sidebar to see historical data.")
        return

    chart_data = pd.DataFrame()
    with st.spinner("Fetching historical data…"):
        for sym in selected_symbols:
            try:
                coin_id = coins_df.loc[coins_df["symbol"] == sym, "id"].iloc[0]
                hist_df = get_historical_data(coin_id, fiat, TIMEFRAMES[timeframe])
                if not hist_df.empty:
                    s = hist_df.set_index("datetime")["price"].rename(sym)
                    chart_data = pd.concat([chart_data, s], axis=1)
            except IndexError: pass
    
    if not chart_data.empty and HAS_PLOTLY:
        fig = go.Figure()
        if chart_type == "Line":
            for c in chart_data.columns:
                fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data[c], mode="lines", name=c))
        else:
            if len(selected_symbols) == 1:
                o = chart_data.resample("1h").agg({selected_symbols[0]: ["first", "max", "min", "last"]})
                o.columns = ["open", "high", "low", "close"]
                fig.add_trace(go.Candlestick(x=o.index, open=o["open"], high=o["high"], low=o["low"], close=o["close"]))
            else:
                st.warning("Candlestick chart is only available for a single selected coin.")
        
        st.plotly_chart(fig, use_container_width=True)
    elif not HAS_PLOTLY:
        st.line_chart(chart_data)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if 'dark_theme' not in st.session_state: st.session_state.dark_theme = True
    
    st.sidebar.checkbox("Dark Theme", value=st.session_state.dark_theme, key='dark_theme')
    apply_theme()
    
    st.markdown('<div class="rainbow-text">Emus Crypto Dashboard</div>', unsafe_allow_html=True)
    if not st.session_state.dark_theme:
        st.markdown('<p style="text-align: center; font-style: italic;">(why would you even use light mode?!)</p>', unsafe_allow_html=True)

    st.sidebar.subheader("User Account")
    if 'username' in st.session_state:
        st.sidebar.success(f"Logged in as **{st.session_state.username}**")
        if st.sidebar.button("Logout"):
            for key in list(st.session_state.keys()):
                if key != 'dark_theme': del st.session_state[key]
            st.rerun()
    else:
        auth_tab1, auth_tab2 = st.sidebar.tabs(["Login", "Create Account"])
        with auth_tab1:
            with st.form("login_form"):
                username, password = st.text_input("Username"), st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    if check_password(username, password): 
                        st.session_state.username = username
                        st.rerun()
                    else: st.error("Invalid username or password.")
        with auth_tab2:
            with st.form("signup_form"):
                new_user, new_pass = st.text_input("New Username"), st.text_input("New Password", type="password")
                if st.form_submit_button("Sign Up"):
                    users = load_users()
                    if not new_user or not new_pass: st.error("Fields cannot be empty.")
                    elif new_user in users or new_user in st.secrets.get("passwords", {}): st.error("Username already exists.")
                    else:
                        users[new_user] = hash_password(new_pass)
                        save_users(users)
                        st.success("Account created! Please log in.")
        st.info("👋 Welcome! Please log in or create an account to begin.")
        st.stop()
    
    username = st.session_state.username
    with st.sidebar:
        st.markdown("---"); st.subheader("Controls")
        fiat = st.selectbox("Fiat Currency", SUPPORTED_CURRENCIES, index=SUPPORTED_CURRENCIES.index('USD'))
        with st.spinner("Loading coin list..."): coins_df, status = get_coins_list(fiat)
        if status != "coingecko_ok": st.warning("Using fallback API.")
        if coins_df.empty: st.error("Could not fetch coin data."); st.stop()
        st.session_state.coins_cache = coins_df

        symbols = coins_df["symbol"].tolist()
        PRESETS = {"Custom": [], "Top 10": symbols[:10], "Trending": fetch_trending_symbols(), "Gainers": coins_df.nlargest(5, "change_24h")["symbol"].tolist(), "Losers": coins_df.nsmallest(5, "change_24h")["symbol"].tolist()}
        def set_watchlist(): st.session_state.selected_coins = PRESETS.get(st.session_state.watchlist_radio, [])
        def set_custom(): st.session_state.watchlist_radio = "Custom"
        if 'watchlist_radio' not in st.session_state:
            st.session_state.watchlist_radio = "Top 10"
            set_watchlist()
        st.radio("Watchlist", list(PRESETS.keys()), key="watchlist_radio", on_change=set_watchlist)
        selected_coins = st.multiselect("Select Coins", options=symbols, key="selected_coins", on_change=set_custom)
        
        tf_list = list(TIMEFRAMES.keys())
        timeframe = st.selectbox("Timeframe", tf_list, index=0)
        chart_h = st.selectbox("Historical Chart Type", ["Line", "Candlestick"] if HAS_PLOTLY else ["Line"])

    if selected_coins:
        cols = st.columns(len(selected_coins))
        for col, sym in zip(cols, selected_coins):
            try: col.metric(label=sym, value=f"{coins_df.loc[coins_df['symbol']==sym, 'price'].iloc[0]:,.2f} {fiat}")
            except IndexError: pass

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "📉 Historical", "💼 Portfolio Tracker"])
    with tab1: render_overview_tab(coins_df, fiat)
    with tab2: render_historical_tab(coins_df, selected_coins, fiat, timeframe, chart_h)
    with tab3: render_portfolio_tab(coins_df, fiat, username)

if __name__ == "__main__":
    main()
