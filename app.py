import streamlit as st
import yfinance as yf
import sqlite3
import pandas as pd

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Pro Stock Analyser", layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("stock_app.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS watchlist (username TEXT, stock TEXT)")
conn.commit()

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

# ---------------- FUNCTIONS ----------------
def add_user(username, password):
    try:
        c.execute("INSERT INTO users VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except:
        return False

def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return c.fetchone()

def add_watch(username, stock):
    c.execute("INSERT INTO watchlist VALUES (?, ?)", (username, stock))
    conn.commit()

def remove_watch(username, stock):
    c.execute("DELETE FROM watchlist WHERE username=? AND stock=?", (username, stock))
    conn.commit()

def get_watch(username):
    c.execute("SELECT stock FROM watchlist WHERE username=?", (username,))
    return c.fetchall()

# ---------------- THEME STYLE ----------------
# ---------------- THEME STYLE ----------------

if st.session_state.theme == "Dark":
    bg_color = "#0E1117"
    card_color = "#1c1f26"
    text_color = "white"
    navbar_color = "#121417"
else:
    bg_color = "#F5F7FA"
    card_color = "white"
    text_color = "#111111"
    navbar_color = "#E3E8EF"

st.markdown(f"""
<style>
.stApp {{
    background-color: {bg_color};
    color: {text_color};
}}

.metric-card {{
    padding:20px;
    border-radius:15px;
    background-color:{card_color};
    margin-bottom:15px;
    transition:0.3s;
    box-shadow:0 4px 15px rgba(0,0,0,0.08);
}}

.metric-card:hover {{
    transform:scale(1.03);
}}

.navbar {{
    background-color:{navbar_color};
    padding:15px;
    border-radius:10px;
    margin-bottom:20px;
    box-shadow:0 4px 10px rgba(0,0,0,0.05);
}}
</style>
""", unsafe_allow_html=True)

# ---------------- NAVBAR ----------------
st.markdown('<div class="navbar"><h2>📈 Pro Stock Analyser</h2></div>', unsafe_allow_html=True)

# ---------------- LOGIN / REGISTER ----------------
if not st.session_state.logged_in:

    menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

    if menu == "Register":
        st.subheader("Create Account")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Register"):
            if add_user(u, p):
                st.success("Account Created")
            else:
                st.error("Username Exists")

    else:
        st.subheader("Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if login_user(u, p):
                st.session_state.logged_in = True
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Invalid Credentials")

# ---------------- MAIN APP ----------------
else:

    # Sidebar Controls
    st.sidebar.success(f"Welcome {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.sidebar.subheader("Appearance")
    st.session_state.theme = st.sidebar.radio("Theme", ["Dark", "Light"])

    section = st.radio("Select Section", ["Stock Search", "Watchlist", "Compare"])

    # ================= STOCK SEARCH =================
    if section == "Stock Search":

        symbol = st.text_input("Enter Stock Symbol (e.g., IDEA.NS)")

        if symbol:
            stock = yf.Ticker(symbol)
            data = stock.history(period="6mo")
            info = stock.info

            if not data.empty:

                # LOGO
                if "logo_url" in info:
                    st.image(info["logo_url"], width=120)

                price = info.get("currentPrice", 0)
                prev = info.get("previousClose", 0)
                change = price - prev

                color = "green" if change >= 0 else "red"

                st.markdown(f"""
                <div class="metric-card">
                <h2>{symbol}</h2>
                <h3 style='color:{color};'>₹ {price} ({round(change,2)})</h3>
                </div>
                """, unsafe_allow_html=True)

                col1, col2, col3 = st.columns(3)
                col1.metric("Market Cap", info.get("marketCap","N/A"))
                col2.metric("P/E Ratio", info.get("trailingPE","N/A"))
                col3.metric("EPS", info.get("trailingEps","N/A"))

                col1.metric("52W High", info.get("fiftyTwoWeekHigh","N/A"))
                col2.metric("52W Low", info.get("fiftyTwoWeekLow","N/A"))
                col3.metric("Volume", info.get("volume","N/A"))

                st.line_chart(data["Close"])

                if st.button("Add to Watchlist"):
                    add_watch(st.session_state.username, symbol)
                    st.success("Added to Watchlist")

            else:
                st.error("Invalid Symbol")

    # ================= WATCHLIST =================
    elif section == "Watchlist":

        watch = get_watch(st.session_state.username)

        if watch:
            for s in watch:
                col1, col2 = st.columns(2)
                col1.write(s[0])
                if col2.button(f"Remove {s[0]}"):
                    remove_watch(st.session_state.username, s[0])
                    st.rerun()
        else:
            st.info("No stocks added.")

    # ================= COMPARE =================
    elif section == "Compare":

        s1 = st.text_input("First Stock")
        s2 = st.text_input("Second Stock")

        if s1 and s2:
            d1 = yf.Ticker(s1).history(period="6mo")
            d2 = yf.Ticker(s2).history(period="6mo")

            if not d1.empty and not d2.empty:
                df = pd.DataFrame({
                    s1: d1["Close"],
                    s2: d2["Close"]
                })
                st.line_chart(df)
            else:
                st.error("Invalid Symbol(s)")
