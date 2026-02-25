import streamlit as st
import yfinance as yf
import sqlite3
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Pro Stock Analyser", layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("stock_app.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS watchlist (username TEXT, stock TEXT)")
c.execute("""CREATE TABLE IF NOT EXISTS portfolio
             (username TEXT, stock TEXT, quantity REAL, buy_price REAL)""")
conn.commit()

# ---------------- SESSION ----------------
if "logged" not in st.session_state:
    st.session_state.logged = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

# ---------------- THEME ----------------
if st.session_state.theme == "Dark":
    bg = "#0f172a"
    glass = "rgba(255,255,255,0.05)"
else:
    bg = "#f1f5f9"
    glass = "rgba(255,255,255,0.7)"

st.markdown(f"""
<style>
.stApp {{ background:{bg}; }}
.navbar {{
    background: linear-gradient(90deg,#1e3a8a,#2563eb);
    padding:15px;
    border-radius:15px;
    color:white;
    font-size:22px;
    margin-bottom:20px;
}}
.glass {{
    background:{glass};
    backdrop-filter: blur(15px);
    border-radius:20px;
    padding:25px;
    margin-bottom:20px;
}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="navbar">📈 Pro Stock Analyser</div>', unsafe_allow_html=True)

# ---------------- AUTH ----------------
def add_user(u,p):
    try:
        c.execute("INSERT INTO users VALUES (?,?)",(u,p))
        conn.commit()
        return True
    except:
        return False

def login_user(u,p):
    c.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p))
    return c.fetchone()

# ---------------- LOGIN / REGISTER ----------------
if not st.session_state.logged:

    menu = st.sidebar.selectbox("Menu",["Login","Register"])

    if menu=="Register":
        u = st.text_input("Username")
        p = st.text_input("Password",type="password")
        if st.button("Register"):
            if add_user(u,p):
                st.success("Account Created")
            else:
                st.error("User Exists")

    else:
        u = st.text_input("Username")
        p = st.text_input("Password",type="password")
        if st.button("Login"):
            if login_user(u,p):
                st.session_state.logged=True
                st.session_state.user=u
                st.rerun()
            else:
                st.error("Invalid Credentials")

# ---------------- MAIN APP ----------------
else:

    st.sidebar.success(f"Welcome {st.session_state.user}")

    if st.sidebar.button("Logout"):
        st.session_state.logged=False
        st.rerun()

    st.sidebar.radio("Theme",["Dark","Light"],key="theme")

    section = st.sidebar.selectbox("Section",
                                   ["Dashboard","Watchlist","Portfolio","Compare","AI Prediction"])

    # ================= DASHBOARD =================
    if section=="Dashboard":

        symbol = st.text_input("Stock Symbol (e.g., TCS.NS)")

        if symbol:
            stock = yf.Ticker(symbol)
            data = stock.history(period="6mo")
            info = stock.info

            if not data.empty:

                if "logo_url" in info:
                    st.image(info["logo_url"],width=100)

                price = info.get("currentPrice",0)
                prev = info.get("previousClose",0)
                change = price-prev
                percent = (change/prev*100) if prev else 0
                color = "lime" if change>=0 else "red"

                st.markdown(f"""
                <div class="glass">
                <h2>{symbol}</h2>
                <h1 style="color:{color}">
                ₹ {price} ({round(percent,2)}%)
                </h1>
                </div>
                """,unsafe_allow_html=True)

                fig = go.Figure(data=[go.Candlestick(
                    x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close']
                )])

                fig.update_layout(
                    template="plotly_dark" if st.session_state.theme=="Dark" else "plotly_white",
                    height=600
                )
                st.plotly_chart(fig,use_container_width=True)

                vol_fig = go.Figure()
                vol_fig.add_trace(go.Bar(x=data.index,y=data["Volume"]))
                vol_fig.update_layout(
                    template="plotly_dark" if st.session_state.theme=="Dark" else "plotly_white",
                    height=300
                )
                st.plotly_chart(vol_fig,use_container_width=True)

                if st.button("Add to Watchlist"):
                    c.execute("INSERT INTO watchlist VALUES (?,?)",
                              (st.session_state.user,symbol))
                    conn.commit()
                    st.success("Added")

            else:
                st.error("Invalid Symbol")

    # ================= WATCHLIST =================
    elif section=="Watchlist":

        c.execute("SELECT stock FROM watchlist WHERE username=?",
                  (st.session_state.user,))
        rows = c.fetchall()

        for r in rows:
            col1,col2 = st.columns([3,1])
            col1.write(r[0])
            if col2.button(f"Remove {r[0]}"):
                c.execute("DELETE FROM watchlist WHERE username=? AND stock=?",
                          (st.session_state.user,r[0]))
                conn.commit()
                st.rerun()

    # ================= PORTFOLIO =================
    elif section=="Portfolio":

        symbol = st.text_input("Stock Symbol")
        qty = st.number_input("Quantity",min_value=1.0)
        buy = st.number_input("Buy Price",min_value=0.0)

        if st.button("Add"):
            c.execute("INSERT INTO portfolio VALUES (?,?,?,?)",
                      (st.session_state.user,symbol,qty,buy))
            conn.commit()

        c.execute("SELECT * FROM portfolio WHERE username=?",
                  (st.session_state.user,))
        rows = c.fetchall()

        total_inv=0
        total_cur=0

        for r in rows:
            data = yf.Ticker(r[1]).history(period="1d")
            if not data.empty:
                current = data["Close"].iloc[-1]
                inv = r[2]*r[3]
                cur = r[2]*current
                pl = cur-inv
                total_inv+=inv
                total_cur+=cur
                color="lime" if pl>=0 else "red"

                st.markdown(f"""
                <div class="glass">
                <h3>{r[1]}</h3>
                <p>P/L: <span style="color:{color}">₹ {round(pl,2)}</span></p>
                </div>
                """,unsafe_allow_html=True)

        total_pl = total_cur-total_inv
        total_color="lime" if total_pl>=0 else "red"

        st.markdown(f"""
        <div class="glass">
        <h2>Total P/L: <span style="color:{total_color}">
        ₹ {round(total_pl,2)}</span></h2>
        </div>
        """,unsafe_allow_html=True)

    # ================= COMPARE =================
    elif section=="Compare":

        st.subheader("Compare Two Stocks")

        stock1 = st.text_input("First Stock (e.g., TCS.NS)")
        stock2 = st.text_input("Second Stock (e.g., INFY.NS)")

        if stock1 and stock2:

            data1 = yf.Ticker(stock1).history(period="6mo")
            data2 = yf.Ticker(stock2).history(period="6mo")

            if not data1.empty and not data2.empty:

                df = pd.DataFrame({
                    stock1: data1["Close"],
                    stock2: data2["Close"]
                })

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df.index,y=df[stock1],mode="lines",name=stock1))
                fig.add_trace(go.Scatter(x=df.index,y=df[stock2],mode="lines",name=stock2))

                fig.update_layout(
                    template="plotly_dark" if st.session_state.theme=="Dark"
                    else "plotly_white",
                    height=600
                )

                st.plotly_chart(fig,use_container_width=True)

            else:
                st.error("Invalid Symbols")

    # ================= AI =================
    elif section=="AI Prediction":

        symbol = st.text_input("Stock Symbol for AI")

        if symbol:
            data = yf.Ticker(symbol).history(period="1y")

            if not data.empty:
                df = data.reset_index()
                df["Day"] = np.arange(len(df))

                X = df[["Day"]]
                y = df["Close"]

                model = LinearRegression()
                model.fit(X,y)

                future = np.arange(len(df),len(df)+7).reshape(-1,1)
                pred = model.predict(future)

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["Date"],y=df["Close"],mode="lines",name="Historical"))
                fig.add_trace(go.Scatter(
                    x=pd.date_range(df["Date"].iloc[-1],periods=8)[1:],
                    y=pred,
                    mode="lines+markers",
                    name="Prediction"))

                fig.update_layout(
                    template="plotly_dark" if st.session_state.theme=="Dark"
                    else "plotly_white"
                )

                st.plotly_chart(fig,use_container_width=True)

            else:
                st.error("Invalid Symbol")
