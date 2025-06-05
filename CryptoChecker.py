import sys

# ————— Import check for ‘requests’ —————
try:
    import requests
except ImportError:
    print("Error: 'requests' library not found. Please install it by running:\n")
    print("    pip install requests\n")
    print("Then rerun this script.")
    sys.exit(1)
# ————————————————————————————————

import time
import os
from datetime import datetime

# Configuration
REFRESH_RATE          = 60    # seconds between automatic top-100 refreshes
HIST_CACHE_TTL        = 3     # seconds to keep historical data before re-fetch

last_update           = 0
coins_list            = []
current_page          = 0
COINS_PER_PAGE        = 10

# Which API is preferred first for top-100 coin list
coinlist_primary_api  = "CoinGecko"

# Which API was last used successfully for get_coins_list()
active_api            = None

# Tracking which API to try first for historical data
historical_primary_api = "CoinGecko"

# Cache for historical data: { coin_id: { 'ts': timestamp, 'prices': [...] } }
historical_cache      = {}

# Globals to track first run and chosen currency
#   We will set:
#     globals()['platform_type']
#     globals()['user_currency']
#   on the first invocation of main_session().

# ANSI color codes
COLORS = {
    'red':     '\033[91m',
    'green':   '\033[92m',
    'yellow':  '\033[93m',
    'blue':    '\033[94m',
    'magenta': '\033[95m',
    'cyan':    '\033[96m',
    'white':   '\033[97m',
    'reset':   '\033[0m'
}

# Emoji map for popular coins
EMOJI_MAP = {
    'btc': '₿', 'bitcoin': '₿',
    'eth': 'Ξ', 'ethereum': 'Ξ',
    'xmr': 'Ⓜ', 'monero': 'Ⓜ',
    'avax': 'ⓐ', 'avalanche': 'ⓐ',
    'sol': '◎', 'solana': '◎',
    'doge': '🐕', 'dogecoin': '🐕',
    'shib': '🐕', 'shiba-inu': '🐕',
    'shit': '💩', 'shitcoin': '💩',
    'ada': '𝔸', 'cardano': '𝔸',
    'dot': '●', 'polkadot': '●',
    'ltc': 'Ł', 'litecoin': 'Ł',
    'xrp': '✕', 'ripple': '✕',
    'trx': '₮', 'tron': '₮',
    'matic': '🟣', 'polygon': '🟣',
    'link': '🔗', 'chainlink': '🔗',
    'atom': '⚛', 'cosmos': '⚛',
    'uni': '🦄', 'uniswap': '🦄',
    'bch': 'Ƀ', 'bitcoin-cash': 'Ƀ',
    'etc': 'ξ', 'ethereum-classic': 'ξ',
    'xlm': '★', 'stellar': '★',
    'algo': '▵', 'algorand': '▵',
    'vet': '✔', 'vechain': '✔',
    'icp': '∞', 'internet-computer': '∞',
    'fil': '📁', 'filecoin': '📁',
    'ape': '🦍', 'apecoin': '🦍',
    'mana': '🎮', 'decentraland': '🎮',
    'sand': '🏖', 'the-sandbox': '🏖',
    'hbar': 'ⓗ', 'hedera': 'ⓗ'
}

# Supported fiat currency codes (uppercase) for CoinGecko
SUPPORTED_CURRENCIES = [
    'AED','ARS','AUD','BDT','BHD','BNB','BRL','BTC','CAD','CHF','CLP','CNY','CZK',
    'DKK','EUR','GBP','HKD','HUF','IDR','ILS','INR','JPY','KRW','KWD','LKR','MMK',
    'MXN','MYR','NGN','NOK','NZD','PHP','PKR','PLN','RUB','SAR','SEK','SGD','THB',
    'TWD','TRY','UAH','USD','VEF','VND','ZAR'
]

# Popular exchange pairs with typical fees
EXCHANGE_PAIRS = {
    'xmr_btc':  {'fee_percent': 0.5, 'fee_fixed': 0.0005, 'min_amount': 0.01},
    'btc_eth':  {'fee_percent': 0.3, 'fee_fixed': 0.0003, 'min_amount': 0.001},
    'eth_usdt': {'fee_percent': 0.2, 'fee_fixed': 1.0,    'min_amount': 0.1},
    # Add more pairs if needed
}

# Network fee sources
FEE_API_ENDPOINTS = {
    'btc': 'https://mempool.space/api/v1/fees/recommended',
    'eth': 'https://ethgasstation.info/api/ethgasAPI.json',
    'xmr': 'https://localmonero.co/blocks/api/get_stats',
}


def detect_platform():
    """Detect if running on Windows or Android (Pydroid)."""
    try:
        if 'pydroid' in sys.executable.lower():
            return 'android'
    except:
        pass
    if os.name == 'nt':
        return 'windows'
    return 'other'


def any_key():
    """Universal 'press any key' implementation."""
    print("\nPress Enter to continue…")
    input()


def first_run_setup():
    """Handle first-run platform detection and setup."""
    platform_type = detect_platform()
    if platform_type in ('android', 'windows'):
        return platform_type

    clear_screen()
    print(f"{COLORS['yellow']}┌──────────────────────────────┐")
    print("│   PLATFORM DETECTION         │")
    print("└──────────────────────────────┘{COLORS['reset']}")
    print("\n1. Windows")
    print("2. Android (Pydroid)")
    print("3. Other")

    while True:
        choice = input("\nSelect your platform: ").strip()
        if choice == '1':
            return 'windows'
        elif choice == '2':
            return 'android'
        elif choice == '3':
            return 'other'
        print(f"{COLORS['red']}Invalid choice!{COLORS['reset']}")


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_price(price: float) -> str:
    """
    Format a float price with thousands separators and exactly two decimal places.
    Examples:
      103159.0       → "103,159.00"
      0.5            → "0.50"
      104054.9144115 → "104,054.91"
    """
    return f"{price:,.2f}"


def get_coins_list():
    """
    Fetch top 100 cryptocurrencies in the user’s selected currency.
    1) Try primary API (CoinGecko or CoinCap).
    2) If that fails, try the other.
    3) If both fail but we have a cached coins_list, warn and return cached.
    4) If no cache, print error and exit.
    """
    global last_update, coins_list, active_api, coinlist_primary_api

    user_currency = globals().get('user_currency', 'usd')

    # If we have a cached list that is still “fresh,” return it
    if time.time() - last_update < REFRESH_RATE and coins_list:
        return coins_list

    def try_coin_gecko():
        """Attempt CoinGecko for top-100."""
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    'vs_currency': user_currency,
                    'order':      'market_cap_desc',
                    'per_page':   100,
                    'page':       1,
                    'sparkline':  'false'
                },
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            result = []
            for coin in data:
                symbol           = coin['symbol'].upper()
                name             = coin['name']
                price            = coin['current_price']
                emoji            = EMOJI_MAP.get(coin['id'], EMOJI_MAP.get(coin['symbol'], symbol))
                price_change_24h = coin.get('price_change_percentage_24h', 0)
                result.append({
                    'id':               coin['id'],
                    'name':             name,
                    'symbol':           symbol,
                    'price':            price,
                    'emoji':            emoji,
                    'price_change_24h': price_change_24h
                })
            return result
        except Exception:
            return []

    def try_coincap():
        """Attempt CoinCap for top-100."""
        try:
            url   = "https://api.coincap.io/v2/assets"
            resp  = requests.get(url, params={'limit': 100}, timeout=10)
            resp.raise_for_status()
            data  = resp.json().get('data', [])
            result = []
            for entry in data:
                coin_id = entry.get('id', '')
                symbol  = entry.get('symbol', '').upper()
                name    = entry.get('name', symbol)
                price   = float(entry.get('priceUsd', 0) or 0)
                change  = float(entry.get('changePercent24Hr', 0) or 0)
                emoji   = EMOJI_MAP.get(coin_id, EMOJI_MAP.get(symbol.lower(), symbol))
                result.append({
                    'id':               coin_id,
                    'name':             name,
                    'symbol':           symbol,
                    'price':            price,
                    'emoji':            emoji,
                    'price_change_24h': change
                })
            return result
        except Exception:
            return []

    # Attempt primary first, then fallback
    new_list = []
    if coinlist_primary_api == "CoinGecko":
        new_list = try_coin_gecko()
        if new_list:
            active_api = "CoinGecko"
        else:
            new_list = try_coincap()
            if new_list:
                active_api = "CoinCap"
    else:  # primary is CoinCap
        new_list = try_coincap()
        if new_list:
            active_api = "CoinCap"
        else:
            new_list = try_coin_gecko()
            if new_list:
                active_api = "CoinGecko"

    if not new_list:
        if coins_list:
            print(f"{COLORS['yellow']}⚠️ Warning: Both CoinGecko and CoinCap failed. Using cached data.{COLORS['reset']}")
            return coins_list
        else:
            print(f"{COLORS['red']}❌ Both CoinGecko and CoinCap failed and no cached data available. Exiting.{COLORS['reset']}")
            sys.exit(1)

    coins_list = new_list
    last_update = time.time()
    return coins_list


def animated_loading():
    """Simple “loading” animation."""
    for i in range(10):
        time.sleep(0.1)
        sys.stdout.write('\r[' + '■' * i + ' ' * (10 - i) + ']')
        sys.stdout.flush()
    print()


def display_coins_page(page, coins):
    """Display a page of coins (paginated)."""
    start_idx  = page * COINS_PER_PAGE
    end_idx    = start_idx + COINS_PER_PAGE
    page_coins = coins[start_idx:end_idx]
    total_pages = (len(coins) + COINS_PER_PAGE - 1) // COINS_PER_PAGE

    print(f"\n{COLORS['yellow']}📖 Page {page+1}/{total_pages}{COLORS['reset']}")
    print(f"{COLORS['green']}┌{'─' * 40}┐{COLORS['reset']}")

    for i, coin in enumerate(page_coins):
        num = start_idx + i + 1
        trend_color  = COLORS['green'] if coin['price_change_24h'] >= 0 else COLORS['red']
        trend_symbol = '▲' if coin['price_change_24h'] >= 0 else '▼'
        price_display = format_price(coin['price'])
        print(f"{num:2}. {coin['emoji']} {coin['name'][:20]:<20} {price_display:>12} {trend_color}{trend_symbol}{COLORS['reset']}")

    print(f"{COLORS['green']}└{'─' * 40}┘{COLORS['reset']}")
    print(f"\n{COLORS['cyan']}N: Next Page  P: Prev Page  S: Search  Q: Quit{COLORS['reset']}")


def search_coins(query, coins):
    """
    Improved search:
      • Exact ticker      (e.g. “xmr” → coin['symbol'].lower())
      • Exact ID          (e.g. “monero” → coin['id'])
      • Name substring    (e.g. “mon” → coin['name'].lower())
    Returns up to COINS_PER_PAGE matches.
    """
    query = query.strip().lower()
    results = []

    for coin in coins:
        symbol_lower = coin['symbol'].lower()
        id_lower     = coin['id']
        name_lower   = coin['name'].lower()

        if (query == symbol_lower) or (query == id_lower) or (query in name_lower):
            results.append(coin)
            if len(results) >= COINS_PER_PAGE:
                break

    return results


def get_historical_data(coin_id, days):
    """
    1) Check a short (3s) cache. If fresh, return cached.
    2) Otherwise, try whichever API is currently primary:
       – If days == "max", use CoinGecko only.
       – If historical_primary_api == "CoinGecko": attempt CoinGecko (with one retry).
         If that fails, attempt CoinCap (for numeric days).
       – If historical_primary_api == "CoinCap": attempt CoinCap first (numeric days).
         If that fails, attempt CoinGecko.
    3) Whichever yields data first becomes new primary (except "max" always CG). Cache and return data.
    4) If both fail, return [] → “Data unavailable.”
    """
    global historical_primary_api

    now = time.time()
    entry = historical_cache.get(f"{coin_id}_{days}")
    if entry and (now - entry['ts'] < HIST_CACHE_TTL):
        return entry['prices']

    user_currency = globals().get('user_currency', 'usd')

    # CoinGecko URL
    if days == "max":
        cg_url    = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        cg_params = {'vs_currency': user_currency, 'days': 'max'}
    else:
        cg_url    = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        cg_params = {'vs_currency': user_currency, 'days': days}

    def try_coin_gecko():
        """Attempt CoinGecko, with one retry on failure."""
        try:
            resp = requests.get(cg_url, params=cg_params, timeout=10)
            resp.raise_for_status()
            return resp.json().get('prices', [])
        except Exception:
            time.sleep(0.5)
            try:
                resp = requests.get(cg_url, params=cg_params, timeout=10)
                resp.raise_for_status()
                return resp.json().get('prices', [])
            except Exception:
                return []

    def try_coincap():
        """
        Attempt CoinCap’s “history” endpoint for numeric days only.
        Interval logic based on days:
          • days < 1  → 1-hour case (use 'm1' and start = now-ms * days * 86400000)
          • days == 1 → 24-hour case (use 'h1')
          • days >= 7 → daily case (use 'd1')
          • if days > 365*2, CoinCap may not return full range, but we attempt.
        """
        if days == "max":
            return []  # CoinCap does not support "max" directly

        now_ms     = int(time.time() * 1000)
        ms_per_day = 86400000
        start_ms   = now_ms - int(days * ms_per_day)

        if days < 1:
            interval = 'm1'
        elif days == 1:
            interval = 'h1'
        else:
            interval = 'd1'

        url = f"https://api.coincap.io/v2/assets/{coin_id}/history"
        try:
            resp = requests.get(
                url,
                params={'interval': interval, 'start': start_ms, 'end': now_ms},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json().get('data', [])
            prices = []
            for point in data:
                price = float(point.get('priceUsd', 0) or 0)
                time_ms = int(point.get('time', 0))
                prices.append([time_ms, price])
            return prices
        except Exception:
            return []

    prices = []

    # If requesting all-time, skip CoinCap fallback
    if days == "max":
        prices = try_coin_gecko()
        if prices:
            historical_primary_api = "CoinGecko"
    else:
        if historical_primary_api == "CoinGecko":
            prices = try_coin_gecko()
            if prices:
                pass
            else:
                prices = try_coincap()
                if prices:
                    historical_primary_api = "CoinCap"
        else:  # primary == "CoinCap"
            prices = try_coincap()
            if prices:
                pass
            else:
                prices = try_coin_gecko()
                if prices:
                    historical_primary_api = "CoinGecko"

    historical_cache[f"{coin_id}_{days}"] = {'ts': now, 'prices': prices}
    return prices


def calculate_price_change(prices):
    """Calculate percentage price change between first and last data points."""
    if len(prices) < 2:
        return 0
    start_price = prices[0][1]
    end_price   = prices[-1][1]
    return ((end_price - start_price) / start_price) * 100


def display_coin_details(coin):
    """Display details for a single coin, including its 24h change and historical trends."""
    clear_screen()
    print(f"\n{COLORS['yellow']}┌───────────────────────────────────┐")
    print(f"│   {coin['emoji']} {coin['name']} ({coin['symbol']})   │")
    print(f"└───────────────────────────────────┘{COLORS['reset']}")

    trend_color   = COLORS['green'] if coin['price_change_24h'] >= 0 else COLORS['red']
    trend_symbol  = '▲' if coin['price_change_24h'] >= 0 else '▼'
    user_currency = globals().get('user_currency', 'usd').upper()
    price_display = format_price(coin['price'])
    print(f"\nCurrent Price: {COLORS['white']}{price_display} {user_currency}{COLORS['reset']}")
    print(f"24h Change:    {trend_color}{trend_symbol} {abs(coin['price_change_24h']):.2f}%{COLORS['reset']}")

    print(f"\n{COLORS['blue']}Historical Trends ({historical_primary_api} primary):{COLORS['reset']}")
    # Timeframes now match CoinGecko: 24h, 7d, 1m, 3m, 1y, Max
    time_frames = [
        ('24h', 'Past 24h',    1),
        ('7d',  'Past 7d',     7),
        ('1m',  'Past 1m',    30),
        ('3m',  'Past 3m',    90),
        ('1y',  'Past 1y',   365),
        ('max','All Time',   'max')
    ]

    for timeframe, label, days in time_frames:
        prices = get_historical_data(coin['id'], days)
        if not prices:
            continue

        price_change   = calculate_price_change(prices)
        trend_color    = COLORS['green'] if price_change >= 0 else COLORS['red']
        trend_symbol   = '▲' if price_change >= 0 else '▼'
        start_price    = prices[0][1]
        end_price      = prices[-1][1]
        start_display  = format_price(start_price)
        end_display    = format_price(end_price)

        # Keep spaces around arrow but ensure % stays adjacent to number
        print(f"{label}: {trend_color}{trend_symbol} {abs(price_change):.2f}%{COLORS['reset']} "
              f"(Start: {start_display} → End: {end_display})")


def get_network_fee(coin_id):
    """
    Get current network fees for transactions (in the coin’s native units).
    Returns a dict with keys 'fast', 'medium', 'slow'.
    """
    try:
        if coin_id == 'btc':
            response = requests.get(FEE_API_ENDPOINTS['btc'], timeout=5)
            response.raise_for_status()
            data = response.json()
            return {
                'fast':   data['fastestFee'],
                'medium': data['halfHourFee'],
                'slow':   data['hourFee']
            }
        elif coin_id == 'eth':
            response = requests.get(FEE_API_ENDPOINTS['eth'], timeout=5)
            response.raise_for_status()
            data = response.json()
            return {
                'fast':   data['fast'] / 10,
                'medium': data['average'] / 10,
                'slow':   data['safeLow'] / 10
            }
        elif coin_id == 'xmr':
            response = requests.get(FEE_API_ENDPOINTS['xmr'], timeout=5)
            response.raise_for_status()
            data = response.json()
            return {
                'fast':   data['fee_per_byte'] * 2500 / 1e12,
                'medium': data['fee_per_byte'] * 2000 / 1e12,
                'slow':   data['fee_per_byte'] * 1500 / 1e12
            }
        else:
            return None
    except Exception as e:
        print(f"{COLORS['red']}⚠️ Fee API Error: {str(e)}{COLORS['reset']}")
        return None


def get_exchange_fees(pair):
    """
    Get current exchange fees for trading pairs (returns a dict with
    fee_percent, fee_fixed, min_amount—all in the pair’s native crypto units).
    """
    try:
        if pair in EXCHANGE_PAIRS:
            fee_data = EXCHANGE_PAIRS[pair].copy()
            # Apply a small random factor so fees “vary” over time
            fee_data['fee_percent'] *= (0.9 + 0.2 * (time.time() % 1))
            fee_data['fee_fixed']   *= (0.8 + 0.4 * (time.time() % 1))
            return fee_data
        return None
    except Exception as e:
        print(f"{COLORS['red']}⚠️ Exchange Fee Error: {str(e)}{COLORS['reset']}")
        return None


def display_fee_info(coin):
    """
    1) Build a small menu of all “coin → other” exchange pairs.
    2) Let the user pick one (1..N).
    3) Show that pair’s fees (variable%, fixed + fiat equivalent, min + fiat equivalent).
    4) “3” is used to go back to the coin details.
    """
    clear_screen()
    user_currency = globals().get('user_currency', 'usd').upper()
    print(f"\n{COLORS['yellow']}┌───────────────────────────────────┐")
    print(f"│   {coin['emoji']} {coin['name']} ({coin['symbol']}) Fees   │")
    print(f"└───────────────────────────────────┘{COLORS['reset']}")

    direct_pairs = []
    for pair_key in EXCHANGE_PAIRS:
        base_id, quote_id = pair_key.split('_')
        if base_id == coin['id']:
            base_coin  = next((c for c in coins_list if c['id'] == base_id), None)
            quote_coin = next((c for c in coins_list if c['id'] == quote_id), None)
            if base_coin and quote_coin:
                direct_pairs.append((pair_key, base_coin, quote_coin))

    if not direct_pairs:
        print(f"\n{COLORS['yellow']}No direct exchange pairs found for {coin['symbol']}.{COLORS['reset']}")
        any_key()
        return

    while True:
        print(f"\n{COLORS['blue']}Select an exchange pair to view fees:{COLORS['reset']}")
        for idx, (_, base_coin, quote_coin) in enumerate(direct_pairs, start=1):
            print(f"  {idx}. {base_coin['symbol']} → {quote_coin['symbol']}")
        print(f"  3. Go Back")

        choice = input(f"\n{COLORS['cyan']}Choice (1-{len(direct_pairs)}, 3): {COLORS['reset']}").strip()
        if choice == '3':
            return

        try:
            sel = int(choice)
            if 1 <= sel <= len(direct_pairs):
                pair_key, base_coin, quote_coin = direct_pairs[sel - 1]
                fee_data = get_exchange_fees(pair_key)
                if not fee_data:
                    print(f"{COLORS['red']}Error: could not fetch fees for that pair.{COLORS['reset']}")
                    any_key()
                    clear_screen()
                    print(f"\n{COLORS['yellow']}┌───────────────────────────────────┐")
                    print(f"│   {coin['emoji']} {coin['name']} ({coin['symbol']}) Fees   │")
                    print(f"└───────────────────────────────────┘{COLORS['reset']}")
                    continue

                fixed_fee_crypto   = fee_data['fee_fixed']
                fixed_fee_fiat     = fixed_fee_crypto * quote_coin['price']
                min_amount_crypto  = fee_data['min_amount']
                min_amount_fiat    = min_amount_crypto * base_coin['price']

                clear_screen()
                print(f"\n{COLORS['yellow']}┌───────────────────────────────────┐")
                print(f"│   {base_coin['emoji']} {base_coin['symbol']} → {quote_coin['emoji']} {quote_coin['symbol']}   │")
                print(f"└───────────────────────────────────┘{COLORS['reset']}\n")

                print(f"{COLORS['cyan']}Variable fee:{COLORS['reset']} {fee_data['fee_percent']:.2f}%")
                print(
                    f"{COLORS['cyan']}Fixed fee:   {COLORS['reset']}"
                    f"{fixed_fee_crypto:.6f} {quote_coin['symbol']} "
                    f"(≈ {user_currency} {format_price(fixed_fee_fiat)})"
                )
                print(
                    f"{COLORS['cyan']}Min amount:  {COLORS['reset']}"
                    f"{min_amount_crypto:.6f} {base_coin['symbol']} "
                    f"(≈ {user_currency} {format_price(min_amount_fiat)})"
                )
                any_key()

                clear_screen()
                print(f"\n{COLORS['yellow']}┌───────────────────────────────────┐")
                print(f"│   {coin['emoji']} {coin['name']} ({coin['symbol']}) Fees   │")
                print(f"└───────────────────────────────────┘{COLORS['reset']}\n")

            else:
                print(f"{COLORS['red']}Invalid selection!{COLORS['reset']}")
                any_key()
                clear_screen()
                print(f"\n{COLORS['yellow']}┌───────────────────────────────────┐")
                print(f"│   {coin['emoji']} {coin['name']} ({coin['symbol']}) Fees   │")
                print(f"└───────────────────────────────────┘{COLORS['reset']}\n")
        except ValueError:
            print(f"{COLORS['red']}Enter a number between 1 and {len(direct_pairs)}, or 3 to go back.{COLORS['reset']}")
            any_key()
            clear_screen()
            print(f"\n{COLORS['yellow']}┌───────────────────────────────────┐")
            print(f"│   {coin['emoji']} {coin['name']} ({coin['symbol']}) Fees   │")
            print(f"└───────────────────────────────────┘{COLORS['reset']}\n")


def convert_currency(coin):
    """
    Handle currency conversion (from user_currency to the selected coin).
    “3” is Go Back, instead of “B”.
    """
    try:
        user_currency = globals().get('user_currency', 'usd').upper()
        while True:
            display_coin_details(coin)
            print(f"\n{COLORS['cyan']}Options:")
            print(f"1. Convert {user_currency} to {coin['symbol']}")
            print(f"2. View Network/Exchange Fees")
            print(f"3. Go Back{COLORS['reset']}")

            choice = input(f"\n{COLORS['blue']}Select option: {COLORS['reset']}").strip()
            if choice == '3':
                return
            elif choice == '1':
                prompt = f"\n{COLORS['blue']}Amount in {user_currency}: {COLORS['reset']}"
                amount_input = input(prompt)
                try:
                    amount_fiat = float(amount_input)
                    if amount_fiat <= 0:
                        print(f"{COLORS['red']}💸 Positive amounts only!{COLORS['reset']}")
                        any_key()
                        continue

                    print(f"\n{COLORS['yellow']}Converting to {coin['symbol']}…{COLORS['reset']}")
                    animated_loading()

                    crypto_amount = amount_fiat / coin['price']
                    crypto_display = f"{crypto_amount:,.8f}".rstrip("0").rstrip(".")
                    print(f"\n{COLORS['green']}{coin['emoji']} {crypto_display} {coin['symbol']}{COLORS['reset']}")
                    print(f"{COLORS['cyan']}⏱️ {datetime.now().strftime('%H:%M:%S')}{COLORS['reset']}")
                    print(f"{COLORS['blue']}{user_currency} {format_price(amount_fiat)} → {coin['emoji']} {crypto_display} {coin['symbol']}{COLORS['reset']}")
                    any_key()
                except ValueError:
                    print(f"{COLORS['red']}🔢 Numbers only please!{COLORS['reset']}")
                    any_key()

            elif choice == '2':
                display_fee_info(coin)

            else:
                print(f"{COLORS['red']}Invalid choice!{COLORS['reset']}")
                any_key()

    except Exception as e:
        print(f"{COLORS['red']}Error: {str(e)}{COLORS['reset']}")
        any_key()


def switch_api_menu():
    """
    Submenu to let the user pick which API to use first for top-100 coin list.
    """
    global coinlist_primary_api, coins_list, current_page, last_update, active_api

    clear_screen()
    print(f"{COLORS['yellow']}┌──────────────────────────────┐")
    print("│   SWITCH PRIMARY API         │")
    print(f"└──────────────────────────────┘{COLORS['reset']}")
    print("\nCurrent primary API:", coinlist_primary_api)
    print("1. CoinGecko")
    print("2. CoinCap")
    print("Press Enter to keep current.\n")

    choice = input(f"{COLORS['blue']}Choice (1-2 or Enter): {COLORS['reset']}").strip()
    if choice == '1':
        coinlist_primary_api = "CoinGecko"
    elif choice == '2':
        coinlist_primary_api = "CoinCap"
    # Else keep current if Enter or invalid

    # Force a refresh by resetting last_update, so active_api updates immediately
    last_update = 0
    full_coins = get_coins_list()
    coins_list = full_coins[:]
    current_page = 0

    print(f"\nNew primary API: {coinlist_primary_api}")
    any_key()


def main_session():
    """
    Single session of the converter. On the very first call, prompts for:
      1) Platform (Windows / Android / Other)
      2) Prompt for user’s local currency (default USD)
    Then enters a loop to display top coins, search, paginate, select, etc.
    Every REFRESH_RATE seconds, the top-100 list is re-fetched automatically.
    We display “API SELECTED = <API>” just under the header (in blue),
    and show “Last refresh / Next refresh” plus “A: Switch API” at the bottom."""
    global current_page, last_update, coins_list, active_api

    # --- First-run block (only executes once) ---
    if 'platform_type' not in globals():
        # 1) Platform detection
        globals()['platform_type'] = first_run_setup()

        # 2) Prompt for currency once, now with full supported list
        clear_screen()
        print(f"{COLORS['yellow']}┌──────────────────────────────────────────────┐")
        print("│   SELECT YOUR LOCAL CURRENCY (FIRST RUN)   │")
        print(f"└──────────────────────────────────────────────┘{COLORS['reset']}")
        print("\nBelow is the list of 3-letter fiat codes supported by CoinGecko.")
        print("Type one of those codes and press Enter, or press Enter alone to default to USD.\n")

        # Display in rows of 8 codes each
        per_row = 8
        for i in range(0, len(SUPPORTED_CURRENCIES), per_row):
            chunk = SUPPORTED_CURRENCIES[i:i+per_row]
            print("  " + "   ".join(chunk))
        print()

        choice = input(f"{COLORS['blue']}Currency: {COLORS['reset']}").strip().upper()
        if choice == '' or choice not in SUPPORTED_CURRENCIES:
            user_currency = 'usd'
        else:
            user_currency = choice.lower()
        globals()['user_currency'] = user_currency

        # Mark first run as done
        globals()['first_run'] = False

    # --- End first-run block ---

    # Initial load of coins_list
    full_coins = get_coins_list()
    coins = full_coins[:]
    current_page = 0

    while True:
        # If REFRESH_RATE has passed since last_update, re-fetch top 100
        if time.time() - last_update >= REFRESH_RATE:
            full_coins = get_coins_list()
            coins = full_coins[:]
            current_page = 0

        clear_screen()

        # Header
        uc = globals().get('user_currency', 'usd').upper()
        if globals()['platform_type'] == 'android':
            print(f"\n{COLORS['yellow']}🪙 CRYPTO CONVERTER (Top 100, {uc}){COLORS['reset']}")
        else:
            print(f"\n{COLORS['yellow']}🪙  CRYPTO CONVERTER (Top 100 Coins, {uc}){COLORS['reset']}")

        # Display which API was used last for top-100
        api_display = active_api if active_api else "N/A"
        print(f"{COLORS['blue']}API SELECTED = \"{api_display}\"{COLORS['reset']}")
        print(f"{COLORS['green']}━{'━' * 40}{COLORS['reset']}")

        # Show coins
        display_coins_page(current_page, coins)

        # Show timestamps at the bottom
        last_ts = datetime.fromtimestamp(last_update).strftime('%H:%M:%S')
        next_ts = datetime.fromtimestamp(last_update + REFRESH_RATE).strftime('%H:%M:%S')
        print(f"\n{COLORS['blue']}Last refresh: {last_ts} | Next refresh: {next_ts}{COLORS['reset']}")
        print(f"{COLORS['blue']}A: Switch API{COLORS['reset']}")

        # Main input (prompt now in cyan)
        choice = input(f"\n{COLORS['cyan']}Select option (1-{COINS_PER_PAGE}, N/P/S/Q/A): {COLORS['reset']}").strip().lower()

        if choice == 'n':
            total_pages = (len(coins) + COINS_PER_PAGE - 1) // COINS_PER_PAGE
            if current_page < total_pages - 1:
                current_page += 1
            continue

        elif choice == 'p':
            if current_page > 0:
                current_page -= 1
            continue

        elif choice == 's':
            search_term = input(f"{COLORS['blue']}Search coin: {COLORS['reset']}").strip()
            results = search_coins(search_term, full_coins)
            if results:
                coins = results
                current_page = 0
            else:
                print(f"{COLORS['red']}No coins found!{COLORS['reset']}")
                any_key()
            continue

        elif choice == 'a':
            switch_api_menu()
            # After switching, full_coins & active_api are already updated
            coins = coins_list[:]
            current_page = 0
            continue

        elif choice == 'q':
            print(f"\n{COLORS['blue']}🚀 Happy trading!{COLORS['reset']}")
            any_key()
            return True

        # If the user typed a number, attempt to select that coin
        try:
            choice_num = int(choice)
            start_idx  = current_page * COINS_PER_PAGE
            end_idx    = start_idx + COINS_PER_PAGE

            if 1 <= choice_num <= COINS_PER_PAGE:
                coin_index = start_idx + choice_num - 1
                if coin_index < len(coins):
                    selected_coin = coins[coin_index]
                    convert_currency(selected_coin)
                    # After returning, reset the list so searches/pagination clear
                    coins = full_coins[:]
                    current_page = 0
                    continue

            print(f"{COLORS['red']}⚠️ Invalid selection!{COLORS['reset']}")
            any_key()

        except ValueError:
            print(f"{COLORS['red']}🔢 Enter a number or command!{COLORS['reset']}")
            any_key()


if __name__ == "__main__":
    try:
        while True:
            main_session()
    except KeyboardInterrupt:
        print(f"\n{COLORS['red']}👋 Exiting…{COLORS['reset']}")
