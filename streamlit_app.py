import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Tuple, Union, List, Dict
import os
import re
import json
import hashlib
import time
import firebase_admin
from firebase_admin import credentials, firestore
import math
import random

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
# Firebase Initialization
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def initialize_firebase():
    """Initializes Firebase Admin SDK using Streamlit secrets."""
    try:
        cred_dict = dict(st.secrets.firebase_service_account)
        cred_dict['private_key'] = cred_dict['private_key'].replace('\\n', '\n')
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(cred_dict))
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}. Ensure secrets are set.")
        st.stop()

initialize_firebase()
db = firestore.client()

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
SUPPORTED_CURRENCIES = ['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'INR', 'BRL', 'RUB', 'KRW', 'SGD', 'MXN', 'NZD', 'HKD', 'NOK', 'SEK', 'ZAR', 'TRY']
TIMEFRAMES = {"24h": "1", "7d": "7", "1m": "30", "3m": "90", "1y": "365", "max": "max"}

# ─────────────────────────────────────────────────────────────────────────────
# Helper & Utility Functions
# ─────────────────────────────────────────────────────────────────────────────
def to_float(value) -> float:
    if value is None: return 0.0
    try: return float(value)
    except (ValueError, TypeError): return 0.0

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ─────────────────────────────────────────────────────────────────────────────
# Gamification System
# ─────────────────────────────────────────────────────────────────────────────
def get_xp_for_level(level: int) -> int:
    return math.floor(100 * (level ** 1.5))

def grant_xp(username: str, amount: int):
    user_ref = db.collection('users').document(username)
    user_data = user_ref.get().to_dict()
    if not user_data: return
    
    current_xp = user_data.get('xp', 0)
    current_level = user_data.get('level', 1)
    new_xp = current_xp + amount
    xp_for_next_level = get_xp_for_level(current_level)
    
    leveled_up = False
    while new_xp >= xp_for_next_level:
        new_xp -= xp_for_next_level
        current_level += 1
        xp_for_next_level = get_xp_for_level(current_level)
        leveled_up = True
    
    save_user_data(username, {'xp': new_xp, 'level': current_level})
    if leveled_up:
        st.session_state.leveled_up_message = f"Congratulations! You've reached Level {current_level}!"

# ─────────────────────────────────────────────────────────────────────────────
# Data Fetching & User/Portfolio Management (Firestore)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
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
    except requests.RequestException: return 1.0

def load_user_data(username: str) -> dict:
    doc_ref = db.collection('users').document(username)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else {}

def save_user_data(username: str, data: dict):
    db.collection('users').document(username).set(data, merge=True)

def load_portfolio_transactions(username: str) -> List[Dict]:
    user_data = load_user_data(username)
    return user_data.get('portfolio', [])

def save_portfolio_transactions(transactions: List[Dict], username: str):
    save_user_data(username, {'portfolio': transactions})

def check_password(username, password) -> bool:
    try:
        if username in st.secrets.get("passwords", {}) and password == st.secrets["passwords"][username]: return True
    except (AttributeError, KeyError): pass
    user_data = load_user_data(username)
    hashed_password = hash_password(password)
    if user_data and user_data.get('hashed_password') == hashed_password: return True
    return False

@st.cache_data(ttl=3600)
def get_custom_emotes() -> dict:
    emotes_ref = db.collection('emotes').stream()
    return {f":{doc.id}:": doc.to_dict()['url'] for doc in emotes_ref}

def parse_emotes(message: str) -> str:
    custom_emotes = get_custom_emotes()
    for emote_name, url in custom_emotes.items():
        message = message.replace(emote_name, f'<img src="{url}" width="24" style="vertical-align:middle; margin: 0 2px;">')
    return message
    
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
            .pfp-sidebar {{ border-radius: 50%; object-fit: cover; width: 35px; height: 35px; vertical-align: middle; margin-left: 10px; }}
            .online-indicator {{ height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; vertical-align: middle; }}
            .online {{ background-color: #2de040; }} .offline {{ background-color: #888; }}
            .chat-bubble {{ padding: 10px 15px; border-radius: 20px; margin-bottom: 5px; display: inline-block; max-width: 100%; word-wrap: break-word; }}
            .chat-bubble.user {{ background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%); color: white; border-bottom-right-radius: 5px; }}
            .chat-bubble.other {{ background: #333; color: white; border-bottom-left-radius: 5px; }}
            .chat-row {{ display: flex; margin-bottom: 10px; align-items: flex-end; }}
            .chat-row.user {{ justify-content: flex-end; }}
            .chat-pfp {{ width: 40px; height: 40px; border-radius: 50%; object-fit: cover; align-self: flex-start; }}
            .chat-row.user .chat-pfp {{ margin-left: 10px; }}
            .chat-row.other .chat-pfp {{ margin-right: 10px; }}
            .chat-content {{ max-width: 80%; }}
    """
    
    gradient_animation = "background-size: 200% 200%; -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: rainbow-flow 12s ease infinite;"
    keyframes = "@keyframes rainbow-flow { 0%{{background-position:0% 50%}} 50%{{background-position:100% 50%} 100%{{background-position:0% 50%} }"
    
    if dark:
        css += f".rainbow-text, .rainbow-text-sm {{ background: linear-gradient(90deg, #ff0080, #ff4500, #ff8c00, #ffff00); {gradient_animation} }} {keyframes}"
    else:
        css += f".rainbow-text, .rainbow-text-sm {{ background: linear-gradient(90deg, cyan, magenta, cyan); {gradient_animation} }} {keyframes}"

    st.markdown(f"{css}</style>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# UI Rendering Functions
# ─────────────────────────────────────────────────────────────────────────────
def calculate_holdings(transactions: List[Dict]) -> dict:
    holdings = {}
    for row in transactions:
        qty = to_float(row.get('Quantity')) if row.get('Type') == 'Buy' else -to_float(row.get('Quantity'))
        cost = qty * to_float(row.get('Price per Coin'))
        coin_id = row.get('Coin ID')
        if coin_id not in holdings: holdings[coin_id] = {'quantity': 0, 'total_cost': 0}
        holdings[coin_id]['quantity'] += qty
        holdings[coin_id]['total_cost'] += cost
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
    st.markdown('<h2 class="rainbow-text-sm">Real Portfolio Tracker</h2>', unsafe_allow_html=True)
    if 'holdings' not in st.session_state:
        st.session_state.holdings = calculate_holdings(load_portfolio_transactions(username))

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
                    transactions = load_portfolio_transactions(username)
                    transactions.append({"Coin ID": coin_id, "Type": trans_type, "Quantity": quantity, "Price per Coin": price_per_coin, "Date": datetime.now(timezone.utc).isoformat()})
                    save_portfolio_transactions(transactions, username)
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
                    save_portfolio_transactions([], username)
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

def render_community_tab(current_user, coins_df, fiat):
    st.markdown('<h2 class="rainbow-text-sm">Community Hub</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3,1])
    with col1:
        auto_refresh_chat = st.toggle("Auto-refresh chat", value=True, help="Automatically fetch new messages every 15 seconds.")
    with col2:
        if st.button("Refresh Now"):
            st.rerun()
    
    if auto_refresh_chat and st.session_state.get('active_tab') == '🌐 Community':
        st.components.v1.html("<meta http-equiv='refresh' content='15'>", height=0)

    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat Room", "👥 Users", "🤝 Friends", "🎨 Custom Emotes"])

    with tab1:
        st.subheader("Live Chat")
        chat_container = st.container()
        with chat_container:
            chat_ref = db.collection('chat').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(50)
            chat_docs = list(chat_ref.stream())
            for msg_doc in reversed(chat_docs):
                msg = msg_doc.to_dict()
                user_data = load_user_data(msg.get('username','?'))
                pfp = user_data.get('pfp_url', 'https://placehold.co/40x40/222/fff?text=??')
                
                with st.chat_message(name=" ", avatar=pfp):
                    st.markdown(f"**{msg.get('username','?')}**")
                    st.markdown(f"<div style='margin-top: -10px;'>{parse_emotes(msg['message'])}</div>", unsafe_allow_html=True)
                    st.caption(f"_{msg['timestamp'].strftime('%H:%M')}_")
        
        if prompt := st.chat_input("Say something..."):
            db.collection('chat').add({'username': current_user, 'message': prompt, 'timestamp': datetime.now(timezone.utc)})
            grant_xp(current_user, 2)
            st.rerun()

    with tab2:
        st.subheader("Registered Users")
        users_docs = db.collection('users').stream()
        all_users = {doc.id: doc.to_dict() for doc in users_docs}
        
        for username, data in all_users.items():
            last_seen = data.get('last_seen')
            if isinstance(last_seen, datetime):
                 is_online = (datetime.now(timezone.utc) - last_seen).total_seconds() < 300
            else: is_online = False
            status_class = "online" if is_online else "offline"
            st.markdown(f'<div><span class="online-indicator {status_class}"></span> {username}</div>', unsafe_allow_html=True)

        selected_user = st.selectbox("View a user's profile:", list(all_users.keys()))

        if selected_user:
            st.markdown("---")
            render_portfolio_component(selected_user, coins_df, fiat, is_comparison=True)
            if selected_user != current_user:
                if st.button(f"➕ Add {selected_user} as a Friend"):
                    db.collection('users').document(selected_user).collection('friend_requests').document(current_user).set({'from': current_user, 'timestamp': datetime.now(timezone.utc)})
                    grant_xp(current_user, 10)
                    st.success(f"Friend request sent to {selected_user}!")
                if st.button(f"Compare Portfolios with {selected_user}"):
                    st.session_state.compare_user = selected_user
        
        if st.session_state.get('compare_user'):
            compare_with = st.session_state.compare_user
            st.markdown(f'<h3 class="rainbow-text-sm">Comparison: {current_user} vs. {compare_with}</h3>', unsafe_allow_html=True)
            my_portfolio_df = render_portfolio_component(current_user, coins_df, fiat, is_comparison=True)
            their_portfolio_df = render_portfolio_component(compare_with, coins_df, fiat, is_comparison=True)
            if not my_portfolio_df.empty and not their_portfolio_df.empty:
                merged = pd.merge(my_portfolio_df, their_portfolio_df, on="Symbol", how="inner", suffixes=(f'_{current_user}', f'_{compare_with}'))
                if not merged.empty:
                    st.markdown("---"); st.subheader("Side-by-Side Value")
                    st.dataframe(merged[['Symbol', f'Value ({fiat})_{current_user}', f'Value ({fiat})_{compare_with}']].set_index('Symbol'))
                else: st.info("You and this user do not hold any of the same assets to compare.")

    with tab3:
        st.subheader("Your Friends")
        my_data = load_user_data(current_user)
        friends = my_data.get('friends', [])
        if not friends:
            st.info("You haven't added any friends yet.")
        else:
            for friend in friends:
                st.write(friend)

        st.markdown("---")
        st.subheader("Friend Requests")
        requests_ref = db.collection('users').document(current_user).collection('friend_requests').stream()
        incoming_requests = {req.id: req.to_dict() for req in requests_ref}
        
        if not incoming_requests:
            st.info("No new friend requests.")
        else:
            for req_user, req_data in incoming_requests.items():
                col1, col2, col3 = st.columns([2,1,1])
                with col1: st.write(f"**{req_user}** wants to be your friend.")
                with col2: 
                    if st.button("Accept", key=f"accept_{req_user}"):
                        batch = db.batch()
                        user_ref = db.collection('users').document(current_user)
                        batch.update(user_ref, {'friends': firestore.ArrayUnion([req_user])})
                        friend_ref = db.collection('users').document(req_user)
                        batch.update(friend_ref, {'friends': firestore.ArrayUnion([current_user])})
                        req_ref = user_ref.collection('friend_requests').document(req_user)
                        batch.delete(req_ref)
                        batch.commit()
                        grant_xp(current_user, 10)
                        st.success(f"You are now friends with {req_user}!")
                        st.rerun()
                with col3:
                    if st.button("Decline", key=f"decline_{req_user}"):
                        db.collection('users').document(current_user).collection('friend_requests').document(req_user).delete()
                        st.rerun()
                        
    with tab4:
        st.subheader("Add Custom Emotes")
        with st.form("add_emote"):
            emote_name = st.text_input("Emote Name (e.g., pog)")
            emote_url = st.text_input("Image URL")
            if st.form_submit_button("Add Emote"):
                if emote_name and emote_url:
                    db.collection('emotes').document(emote_name).set({'url': emote_url})
                    st.success("Emote added!")
                    st.cache_data.clear()
                else:
                    st.error("Please provide a name and URL.")

def render_simulator_tab(current_user, coins_df, fiat):
    st.markdown('<h2 class="rainbow-text-sm">Simulator & Games</h2>', unsafe_allow_html=True)
    user_data = load_user_data(current_user)
    wallet = user_data.get('virtual_wallet', {'USD': 10000.0})
    st.metric("Your Simulator Wallet", f"${wallet.get('USD', 0):,.2f} USD")

    tab1, tab2 = st.tabs(["📈 Simulated Trading", "🎲 Coin Flip"])

    with tab1:
        st.subheader("Simulated Trading")
        all_coins = coins_df.sort_values('name').copy()
        all_coins['display'] = all_coins['name'] + " (" + all_coins['symbol'] + ")"
        
        trade_type = st.radio("Action", ["Buy", "Sell"], horizontal=True)
        selected_coin_display = st.selectbox("Select Coin", all_coins['display'].tolist())
        selected_symbol = selected_coin_display.split('(')[-1][:-1]
        
        current_price = coins_df.loc[coins_df['symbol'] == selected_symbol, 'price'].iloc[0]
        st.info(f"Current Market Price for {selected_symbol}: ${current_price:,.2f}")

        if trade_type == "Buy":
            spend_amount = st.number_input("Amount of USD to spend", min_value=0.0, max_value=wallet.get('USD', 0.0), step=100.0)
            if st.button("Buy Simulated Crypto"):
                if spend_amount > 0:
                    crypto_bought = spend_amount / current_price
                    wallet['USD'] -= spend_amount
                    wallet[selected_symbol] = wallet.get(selected_symbol, 0.0) + crypto_bought
                    save_user_data(current_user, {'virtual_wallet': wallet})
                    grant_xp(current_user, 5)
                    st.success(f"Successfully bought {crypto_bought:,.6f} {selected_symbol}!")
                    st.rerun()
        else: # Sell
            current_balance = wallet.get(selected_symbol, 0.0)
            sell_amount = st.number_input(f"Amount of {selected_symbol} to sell", min_value=0.0, max_value=current_balance, format="%.8f")
            if st.button("Sell Simulated Crypto"):
                if sell_amount > 0:
                    usd_gained = sell_amount * current_price
                    wallet['USD'] += usd_gained
                    wallet[selected_symbol] -= sell_amount
                    save_user_data(current_user, {'virtual_wallet': wallet})
                    grant_xp(current_user, 5)
                    st.success(f"Successfully sold {sell_amount:,.6f} {selected_symbol} for ${usd_gained:,.2f} USD!")
                    st.rerun()

        st.subheader("Your Simulated Holdings")
        virtual_holdings = {k: v for k, v in wallet.items() if k != 'USD' and v > 0}
        if not virtual_holdings:
            st.info("You don't own any simulated crypto yet.")
        else:
            for symbol, qty in virtual_holdings.items():
                st.metric(symbol, f"{qty:,.6f}")

    with tab2:
        st.subheader("Coin Flip")
        usd_balance = wallet.get('USD', 0.0)
        if usd_balance < 1.0:
            st.warning("You don't have enough USD to play Coin Flip. Go trade something to earn more!")
        else:
            wager = st.number_input("Wager Amount (USD)", min_value=1.0, max_value=usd_balance, step=50.0)
            choice = st.radio("Choose your side", ["Heads", "Tails"], horizontal=True)
            if st.button("Flip Coin!"):
                with st.spinner("Flipping..."):
                    time.sleep(2)
                    result = random.choice(["Heads", "Tails"])
                    st.header(f"It's... {result}!")
                    if choice == result:
                        winnings = wager * 0.9 # House edge
                        wallet['USD'] += winnings
                        st.success(f"You win! You get ${winnings:,.2f} USD.")
                        grant_xp(current_user, int(winnings / 100))
                    else:
                        wallet['USD'] -= wager
                        st.error(f"You lose! You lost ${wager:,.2f} USD.")
                    save_user_data(current_user, {'virtual_wallet': wallet})
                    time.sleep(2)
                    st.rerun()

def render_portfolio_component(username, coins_df, fiat, is_comparison=False):
    if not is_comparison: st.markdown(f'<h3 class="rainbow-text-sm">Portfolio for {username}</h3>', unsafe_allow_html=True)
    transactions = load_portfolio_transactions(username)
    if not transactions:
        st.info(f"{username} has not added any transactions yet.")
        return pd.DataFrame()
    holdings = calculate_holdings(transactions)
    portfolio_data = []
    for coin_id, data in holdings.items():
        if data['quantity'] > 0:
            coin_info = coins_df[coins_df['id'] == coin_id]
            if not coin_info.empty:
                current_price = coin_info['price'].iloc[0]
                portfolio_data.append({'Coin': coin_info['name'].iloc[0], 'Symbol': coin_info['symbol'].iloc[0], 'Quantity': data['quantity'], f'Value ({fiat})': data['quantity'] * current_price})
    summary_df = pd.DataFrame(portfolio_data)
    if not summary_df.empty: st.dataframe(summary_df.set_index('Coin'))
    return summary_df

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if 'dark_theme' not in st.session_state: st.session_state.dark_theme = True
    st.sidebar.checkbox("Dark Theme", key='dark_theme')
    apply_theme()
    
    st.markdown('<div class="rainbow-text">Emus Crypto Dashboard</div>', unsafe_allow_html=True)
    if not st.session_state.dark_theme:
        st.markdown('<p style="text-align: center; font-style: italic;">(why would you even use light mode?!)</p>', unsafe_allow_html=True)

    with st.sidebar.expander("User Account", expanded=True):
        if 'username' in st.session_state:
            user_data = load_user_data(st.session_state.username)
            pfp = user_data.get('pfp_url', '')
            pfp_html = f'<img src="{pfp}" class="pfp-sidebar" onerror="this.src=\'https://placehold.co/40x40/222/fff?text=??\';">' if pfp else ""
            st.markdown(f'<div style="display: flex; align-items: center; margin-bottom: 10px;"><span style="flex-grow: 1;">Logged in as <b>{st.session_state.username}</b></span>{pfp_html}</div>', unsafe_allow_html=True)
            
            level = user_data.get('level', 1)
            xp = user_data.get('xp', 0)
            xp_needed = get_xp_for_level(level)
            st.progress(xp / xp_needed if xp_needed > 0 else 0, text=f"Level {level} ({xp}/{xp_needed} XP)")

            if st.button("Logout"):
                save_user_data(st.session_state.username, {'last_seen': datetime.now(timezone.utc) - timedelta(minutes=10)})
                for key in list(st.session_state.keys()):
                    if key != 'dark_theme': del st.session_state[key]
                st.rerun()
        else:
            auth_tab1, auth_tab2 = st.tabs(["Login", "Create Account"])
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
                        user_doc = db.collection('users').document(new_user).get()
                        if not new_user or not new_pass: st.error("Fields cannot be empty.")
                        elif user_doc.exists or new_user in st.secrets.get("passwords", {}): st.error("Username already exists.")
                        else:
                            user_data = {'hashed_password': hash_password(new_pass), 'friends': [], 'pfp_url': '', 'level': 1, 'xp': 0, 'virtual_wallet': {'USD': 10000.0}}
                            save_user_data(new_user, user_data)
                            st.success("Account created! Please log in.")
            st.info("👋 Welcome! Please log in or create an account to begin.")
            st.stop()
    
    username = st.session_state.username
    with st.sidebar.expander("Profile Settings"):
        user_data = load_user_data(username)
        pfp_url = st.text_input("Profile Picture URL", value=user_data.get('pfp_url', ''))
        if st.button("Update Profile"):
            save_user_data(username, {'pfp_url': pfp_url})
            st.success("Profile updated!")
        if pfp_url: st.image(pfp_url, width=100)

    with st.sidebar.expander("Market Controls", expanded=True):
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
    
    # This logic is a bit of a hack to track the active tab for the auto-refresh
    active_tab = st.session_state.get('active_tab', "📈 Overview")
    tabs = st.tabs(["📈 Overview", "📉 Historical", "💼 Portfolio Tracker", "🌐 Community", "🏆 Simulator & Games"])
    
    # We can't directly know which tab is clicked, but we can infer it.
    # This is not perfect but works for this use case.
    # A better solution requires custom components.

    with tabs[0]: render_overview_tab(coins_df, fiat)
    with tabs[1]: render_historical_tab(coins_df, selected_coins, fiat, timeframe, chart_h)
    with tabs[2]: render_portfolio_tab(coins_df, fiat, username)
    with tabs[3]: render_community_tab(username, coins_df, fiat)
    with tabs[4]: render_simulator_tab(username, coins_df, fiat)

    if 'last_seen_update' not in st.session_state or (datetime.now(timezone.utc) - st.session_state.last_seen_update).total_seconds() > 60:
        save_user_data(username, {'last_seen': datetime.now(timezone.utc)})
        st.session_state.last_seen_update = datetime.now(timezone.utc)
        
    if st.session_state.get('leveled_up_message'):
        st.toast(st.session_state.leveled_up_message)
        del st.session_state.leveled_up_message

if __name__ == "__main__":
    main()
