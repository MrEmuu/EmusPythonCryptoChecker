# run_crypto.py

# 1) Try importing Streamlit. If available, run the web UI; otherwise, fall back to CLI.
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

# ───────────────────────────────────────────────────
# 2) STREAMLIT SECTION (executes only if HAS_STREAMLIT=True)
# ───────────────────────────────────────────────────
if HAS_STREAMLIT:
    from streamlit_app import run_streamlit_dashboard

    # Streamlit will handle its own “if __name__ == '__main__'” via `streamlit run`.
    # We just call our function here.
    run_streamlit_dashboard()

# ───────────────────────────────────────────────────
# 3) CONSOLE/FALLBACK SECTION (executes if no Streamlit)
# ───────────────────────────────────────────────────
else:
    from CryptoChecker import main_session, COLORS

    if __name__ == "__main__":
        try:
            while True:
                main_session()
        except KeyboardInterrupt:
            print(f"\n{COLORS['red']}Exiting…{COLORS['reset']}")
