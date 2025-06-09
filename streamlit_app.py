import streamlit as st
import requests
import pandas as pd
import smtplib
from email.message import EmailMessage
from datetime import datetime
from typing import Union

# Plotly support
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Page config
st.set_page_config(page_title="Emus Crypto Dashboard", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
SUPPORTED_CURRENCIES = [
    'AED','ARS','AUD','BDT','BHD','BNB','BRL','BTC','CAD','CHF','CLP','CNY','CZK',
    'DKK','EUR','GBP','HKD','HUF','IDR','ILS','INR','JPY','KRW','KWD','LKR','MMK',
    'MXN','MYR','NGN','NOK','NZD','PHP','PKR','PLN','RUB','SAR','SEK','SGD','THB',
    'TWD','TRY','UAH','USD','VEF','VND','ZAR'
]
EXCHANGE_PAIRS = {
    "xmr_btc": {"fee_percent":0.5,  "fee_fixed":0.0005, "min_amount":0.01},
    "btc_eth": {"fee_percent":0.3,  "fee_fixed":0.0003, "min_amount":0.001},
    "eth_usdt":{"fee_percent":0.2,  "fee_fixed":1.0,    "min_amount":0.1},
}
TIMEFRAMES = {"24h":"1","7d":"7","1m":"30","3m":"90","1y":"365","max":"max"}

# ─────────────────────────────────────────────────────────────────────────────
# Notification helpers
# ─────────────────────────────────────────────────────────────────────────────
def send_email(smtp_server, smtp_port, username, password, recipient, subject, body):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = username, recipient, subject
    msg.set_content(body)
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
        smtp.login(username, password)
        smtp.send_message(msg)

def send_discord(webhook_url, content):
    try:
        requests.post(webhook_url, json={"content": content}, timeout=5)
    except:
        pass

def notify_in_app(symbol, pct):
    try:
        st.toast(f"{symbol} moved {pct:+.2f}%")
    except:
        if pct >= 0:
            st.success(f"{symbol} ↑ {pct:.2f}%")
        else:
            st.error(f"{symbol} ↓ {abs(pct):.2f}%")

# ─────────────────────────────────────────────────────────────────────────────
# Trending coins helper
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_trending_symbols() -> list[str]:
    try:
        r = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=5)
        return [c["item"]["symbol"].upper() for c in r.json().get("coins", [])]
    except:
        return []

# ─────────────────────────────────────────────────────────────────────────────
# Data fetching (no cache on list)
# ─────────────────────────────────────────────────────────────────────────────
def get_coins_list(fiat: str) -> pd.DataFrame:
    f = fiat.lower()
    # 1) CoinGecko
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={"vs_currency": f, "order": "market_cap_desc", "per_page": 100, "page": 1, "sparkline": "false"},
            timeout=10
        ); r.raise_for_status()
        data = r.json()
        return pd.DataFrame([{
            "id":         c["id"],
            "symbol":     c["symbol"].upper(),
            "name":       c["name"],
            "price":      c["current_price"],
            "change_24h": c.get("price_change_percentage_24h", 0),
            "market_cap": c.get("market_cap", 0)
        } for c in data])
    except:
        pass

    # 2) CoinCap fallback
    try:
        cc = requests.get("https://api.coincap.io/v2/assets", params={"limit": 100}, timeout=10)
        cc.raise_for_status()
        rate = get_fiat_conversion_rate(fiat)
        arr  = cc.json().get("data", [])
        return pd.DataFrame([{
            "id":         a["id"],
            "symbol":     a["symbol"].upper(),
            "name":       a["name"],
            "price":      float(a["priceUsd"]) * rate,
            "change_24h": float(a.get("changePercent24Hr", 0)),
            "market_cap": float(a.get("marketCapUsd", 0)) * rate
        } for a in arr])
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_historical_data(coin_id: str, fiat: str, days: Union[int,str]) -> pd.DataFrame:
    f = fiat.lower()
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
            params={"vs_currency": f, "days": days}, timeout=10
        ); r.raise_for_status()
        df = pd.DataFrame(r.json().get("prices", []), columns=["ts","price"])
        df["datetime"] = pd.to_datetime(df["ts"], unit="ms")
        return df[["datetime","price"]]
    except:
        return pd.DataFrame()

def get_fiat_conversion_rate(fiat: str) -> float:
    try:
        rates = requests.get("https://api.coingecko.com/api/v3/exchange_rates", timeout=5)\
                     .json().get("rates", {})
        return float(rates.get(fiat.lower(), {}).get("value", 1.0))
    except:
        return 1.0

def compute_fiat_value(amount: float, price: float) -> float:
    return amount * price

# ─────────────────────────────────────────────────────────────────────────────
# THEME & Layout CSS
# ─────────────────────────────────────────────────────────────────────────────
FONT = "@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');"
dark = st.sidebar.checkbox("Dark Theme", True)
if dark:
    st.markdown(f"""
    <style>{FONT}
      body{{background:#0a0a20;color:#fff;font-family:'Press Start 2P',monospace;}}
      .rainbow-text, .rainbow-text-sm {{
        background:linear-gradient(90deg,#ff0080,#ff4500,#ff8c00,#ffff00);
        background-size:200% 200%;-webkit-background-clip:text;
        -webkit-text-fill-color:transparent;
        animation:rainbow-flow 12s infinite;
      }}
      @keyframes rainbow-flow{{0%{{background-position:0% 50%;}}50%{{background-position:100% 50%;}}100%{{background-position:0% 50%;}}}}
      .rainbow-text{{font-size:2.5rem;text-align:center;margin:1rem 0;}}
      .rainbow-text-sm{{font-size:1.75rem;margin:1rem 0;}}
      .stDataFrame table{{background:#12122e!important;color:#fff!important;}}
      .stDataFrame thead th{{background:#1f1f4d!important;color:#0ff!important;}}
      #MainMenu,footer{{visibility:hidden;}}
    </style>""", unsafe_allow_html=True)
else:
    st.markdown(f"""
    <style>{FONT}
      body{{background:#fff;color:#000;font-family:'Press Start 2P',monospace;}}
      .rainbow-text, .rainbow-text-sm{{color:#000;animation:none;}}
      .stDataFrame table{{background:#f0f0f0!important;color:#000!important;}}
      .stDataFrame thead th{{background:#d0d0d0!important;color:#000!important;}}
      #MainMenu,footer{{visibility:hidden;}}
    </style>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Last Updated & Auto-Refresh
# ─────────────────────────────────────────────────────────────────────────────
now = datetime.now()
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = now
last = st.session_state.last_refresh

auto = st.sidebar.checkbox("Auto-Refresh Data", False)
if auto:
    secs = st.sidebar.slider("Refresh Interval (s)", 30, 300, 60, step=30)
    if (now - last).total_seconds() >= secs:
        st.session_state.last_refresh = now
        st.rerun()

st.markdown(f"**Last Updated:** {st.session_state.last_refresh:%Y-%m-%d %H:%M:%S}")

# ─────────────────────────────────────────────────────────────────────────────
# Title & Permalink load
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="rainbow-text">Emus Crypto Dashboard</div>', unsafe_allow_html=True)
if not HAS_PLOTLY:
    st.warning("Plotly not installed → candlestick disabled.")

qp = st.query_params
param_fiat  = qp.get("fiat",   ["USD"])[0]
param_coins = qp.get("coins",  [""])[0]
param_tf    = qp.get("tf",     ["24h"])[0]
param_hc    = qp.get("hist_chart", ["Line"])[0]
param_dc    = qp.get("dist_chart", ["Scatter"])[0]

def main():
    # Sidebar: Fiat
    default_idx = SUPPORTED_CURRENCIES.index(param_fiat) if param_fiat in SUPPORTED_CURRENCIES else SUPPORTED_CURRENCIES.index("USD")
    fiat = st.sidebar.selectbox("Fiat Currency", SUPPORTED_CURRENCIES, index=default_idx)

    # Track fiat changes
    prev_fiat = st.session_state.get("last_fiat", None)
    fiat_changed = (prev_fiat != fiat)
    st.session_state["last_fiat"] = fiat

    # ─── Fetch coins with spinner & cache fallback ─────────────────────────
    with st.spinner(f"Loading coin list for {fiat}…"):
        df_coins = get_coins_list(fiat)
    if not df_coins.empty:
        st.session_state.coins_cache = df_coins.copy()
    elif "coins_cache" in st.session_state:
        if fiat_changed:
            st.warning(f"⚠️ Fetch failed for “{fiat}”, using last known data.")
        df_coins = st.session_state.coins_cache
    else:
        if fiat_changed:
            st.warning(f"⚠️ Fetch failed for “{fiat}”. No cache – lists will be empty.")
        df_coins = pd.DataFrame(columns=["id","symbol","name","price","change_24h","market_cap"])

    symbols = df_coins.sort_values("market_cap", ascending=False)["symbol"].tolist()

    # ─────────────────────────────────────────────────────────────────────────
    # Alerts setup
    # ─────────────────────────────────────────────────────────────────────────
    if "alerts" not in st.session_state:
        st.session_state.alerts = []

    with st.sidebar.expander("📣 Alerts"):
        st.markdown("**Create new alert**")
        coin = st.selectbox("Coin", symbols, key="al_coin")
        thresh = st.number_input("Threshold (%)", min_value=0.0, value=1.0, step=0.1, key="al_thresh")
        direction = st.selectbox("Direction", ["Both","Up","Down"], key="al_dir")
        methods = st.multiselect("Notify via", ["In-app","Email","Discord"], default=["In-app"], key="al_methods")

        # Email inputs
        if "Email" in methods:
            smtp_srv = st.text_input("SMTP Server", key="al_smtp_srv")
            smtp_prt = st.number_input("SMTP Port", min_value=0, value=465, key="al_smtp_prt")
            smtp_usr = st.text_input("SMTP User", key="al_smtp_usr")
            smtp_pwd = st.text_input("SMTP Password", type="password", key="al_smtp_pwd")
            email_to = st.text_input("Recipient Email", key="al_email_to")
        else:
            smtp_srv = smtp_prt = smtp_usr = smtp_pwd = email_to = None

        # Discord webhook
        webhook = st.text_input("Discord Webhook URL", key="al_webhook") if "Discord" in methods else None

        if st.button("➕ Add Alert", key="al_add"):
            baseline = float(df_coins.loc[df_coins["symbol"]==coin, "price"].iloc[0])
            st.session_state.alerts.append({
                "coin":      coin,
                "threshold": thresh,
                "direction": direction,
                "methods":   methods,
                "smtp":      (smtp_srv, smtp_prt, smtp_usr, smtp_pwd, email_to),
                "webhook":   webhook,
                "baseline":  baseline,
                "fired":     False
            })
            st.success(f"Alert for {coin} @ {thresh}% [{direction}] added")

        # List & remove
        for i, a in enumerate(st.session_state.alerts):
            st.write(f"• {a['coin']} {a['direction']} {a['threshold']}% → {', '.join(a['methods'])}")
            if st.button("Remove", key=f"al_rem_{i}"):
                st.session_state.alerts.pop(i)
                st.experimental_rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # Check & fire alerts
    # ─────────────────────────────────────────────────────────────────────────
    for a in st.session_state.alerts:
        if a["fired"]: continue
        cur_price = float(df_coins.loc[df_coins["symbol"]==a["coin"], "price"].iloc[0])
        change_pct = (cur_price - a["baseline"]) / a["baseline"] * 100
        triggered = (
            (a["direction"]=="Both" and abs(change_pct)>=a["threshold"]) or
            (a["direction"]=="Up"   and change_pct>=a["threshold"]) or
            (a["direction"]=="Down" and change_pct<=-a["threshold"])
        )
        if triggered:
            if "In-app" in a["methods"]:
                notify_in_app(a["coin"], change_pct)
            if "Email" in a["methods"]:
                srv,prt,usr,pwd,to = a["smtp"]
                subj = f"Crypto Alert: {a['coin']} moved {change_pct:+.2f}%"
                body = f"{a['coin']} was {a['baseline']:.4f}, now {cur_price:.4f} ({change_pct:+.2f}%)"
                send_email(srv,prt,usr,pwd,to,subj,body)
            if "Discord" in a["methods"] and a["webhook"]:
                msg = f"🚨 {a['coin']} moved {change_pct:+.2f}% (from {a['baseline']:.4f} to {cur_price:.4f})"
                send_discord(a["webhook"], msg)
            a["fired"] = True

    # ─────────────────────────────────────────────────────────────────────────
    # Quick watchlists & coin selector
    # ─────────────────────────────────────────────────────────────────────────
    def _clear_sel(): st.session_state.pop("selected_coins", None)
    PRESETS = {
        "Custom":   [], "Top 10": symbols[:10],
        "Trending": fetch_trending_symbols(),
        "Gainers":  df_coins.nlargest(5, "change_24h")["symbol"].tolist(),
        "Losers":   df_coins.nsmallest(5, "change_24h")["symbol"].tolist(),
        "DeFi":     ["UNI","AAVE","COMP","SUSHI","YFI"],
        "Privacy":  ["XMR","ZEC","DASH"],
    }
    st.sidebar.radio("Watchlist", list(PRESETS.keys()), key="watchlist", on_change=_clear_sel)
    watch = st.session_state.watchlist
    url_coins = param_coins.split(",") if param_coins else []
    defaults = ([c for c in PRESETS[watch] if c in symbols] if watch!="Custom" else url_coins)
    if st.sidebar.button("🔄 Reset Coins"):
        st.session_state.pop("selected_coins", None)
        defaults = []
        st.rerun()
    sel = st.sidebar.multiselect("Select Coins", options=symbols, default=defaults, key="selected_coins")

    # ─────────────────────────────────────────────────────────────────────────
    # Timeframe & chart selectors
    # ─────────────────────────────────────────────────────────────────────────
    tf_list   = list(TIMEFRAMES.keys())
    timeframe = st.sidebar.selectbox("Timeframe", tf_list, index=tf_list.index(param_tf) if param_tf in tf_list else 0)
    chart_h   = st.sidebar.selectbox("Historical Chart Type", ["Line","Candlestick"],
                  index=["Line","Candlestick"].index(param_hc) if param_hc in ["Line","Candlestick"] else 0)
    dist_chart= st.sidebar.selectbox("Distribution Chart Type", ["Scatter","Candlestick"],
                  index=["Scatter","Candlestick"].index(param_dc) if param_dc in ["Scatter","Candlestick"] else 0, key="dist_chart")

    # ─────────────────────────────────────────────────────────────────────────
    # Tabs: Overview, Historical, Distribution, Fees
    # ─────────────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["Overview","Historical","Distribution","Fees"])

    # Overview
    with tab1:
        st.markdown('<h2 class="rainbow-text-sm">Overview</h2>', unsafe_allow_html=True)
        if sel:
            ov = df_coins[df_coins["symbol"].isin(sel)].set_index("symbol")[["name","price","change_24h"]]
            ov["price"]      = ov["price"].map(lambda x: f"{x:,.2f}")
            ov["change_24h"] = ov["change_24h"].map(lambda v: f"{'▲' if v>=0 else '▼'} {abs(v):.2f}%")
            ov.columns = ["Name","Price","24h Change"]
            st.dataframe(ov)
            st.download_button("Download Overview CSV", ov.to_csv().encode(), "overview.csv","text/csv")
        else:
            st.info("Select coins.")

    # Historical
    with tab2:
        st.markdown('<h2 class="rainbow-text-sm">Historical Price Trends</h2>', unsafe_allow_html=True)
        merged = None
        with st.spinner("Fetching historical data…"):
            for sym in sel:
                cid = df_coins.loc[df_coins["symbol"]==sym, "id"].iloc[0]
                dfh = get_historical_data(cid, fiat, TIMEFRAMES[timeframe])
                if not dfh.empty:
                    s = dfh.set_index("datetime")["price"].rename(sym)
                    merged = s.to_frame() if merged is None else merged.join(s, how="outer")
        if merged is not None and not merged.empty and HAS_PLOTLY:
            fig = go.Figure()
            if chart_h == "Line":
                for c in merged.columns:
                    fig.add_trace(go.Scatter(x=merged.index, y=merged[c], mode="lines", name=c))
            else:
                o = merged[[sel[0]]].dropna().resample("1h")\
                    .agg({sel[0]:["first","max","min","last"]})
                o.columns = ["open","high","low","close"]
                fig = go.Figure(data=[go.Candlestick(
                    x=o.index, open=o["open"], high=o["high"], low=o["low"], close=o["close"]
                )])
            st.plotly_chart(fig, use_container_width=True)
            img = fig.to_image(format="png")
            st.download_button("Download Historical PNG", img, "historical.png","image/png")
        else:
            st.info("No data or Plotly missing.")

    # Distribution
    with tab3:
        st.markdown('<h2 class="rainbow-text-sm">Price Change Distribution (24h)</h2>', unsafe_allow_html=True)
        ddf = df_coins[df_coins["symbol"].isin(sel)]
        if not ddf.empty and HAS_PLOTLY:
            fig = None
            if dist_chart == "Scatter":
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=ddf["change_24h"], y=ddf["symbol"], mode="markers", marker=dict(size=12)))
            else:
                with st.spinner("Loading 24h candlestick data…"):
                    dfh = get_historical_data(df_coins.loc[df_coins["symbol"]==sel[0],"id"].iloc[0], fiat, TIMEFRAMES["24h"])
                if not dfh.empty and "datetime" in dfh.columns:
                    o = dfh.set_index("datetime").resample("1h")\
                        .agg({"price":["first","max","min","last"]})
                    o.columns = ["open","high","low","close"]
                    fig = go.Figure(data=[go.Candlestick(
                        x=o.index, open=o["open"], high=o["high"], low=o["low"], close=o["close"]
                    )])
                else:
                    st.warning("No 24h data for candlestick.")
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                img = fig.to_image(format="png")
                st.download_button("Download Distribution PNG", img, "distribution.png","image/png")
        else:
            st.info("Select coins or install Plotly.")

    # Fees
    with tab4:
        st.markdown('<h2 class="rainbow-text-sm">Network / Exchange Fees</h2>', unsafe_allow_html=True)
        fees = []
        for p,i in EXCHANGE_PAIRS.items():
            b,q = p.split("_"); B,Q = b.upper(),q.upper()
            if B in sel or Q in sel:
                pr = float(df_coins.loc[df_coins["symbol"]==B,"price"].iloc[0])
                fees.append({
                    "Pair":         f"{B}→{Q}",
                    "Fee (%)":      i["fee_percent"],
                    "Fixed Crypto": i["fee_fixed"],
                    "Fixed USD":    compute_fiat_value(i["fee_fixed"], pr),
                    "Min Crypto":   i["min_amount"],
                    "Min USD":      compute_fiat_value(i["min_amount"], pr)
                })
        if fees:
            fdf = pd.DataFrame(fees).set_index("Pair")
            st.dataframe(fdf)
            st.download_button("Download Fees CSV", fdf.to_csv().encode(), "fees.csv","text/csv")
        else:
            st.info("No exchange pairs.")

    # Permalink write-back
    st.query_params = {
        "fiat":       [fiat],
        "coins":      [",".join(sel)],
        "tf":         [timeframe],
        "hist_chart": [chart_h],
        "dist_chart": [dist_chart],
    }
    st.markdown("🔗 **Copy this URL to share your view!**")

if __name__ == "__main__":
    main()
