import streamlit as st
import json
import os

st.set_page_config(page_title="AI Grocery Dashboard", layout="wide")

st.title("🛒 AI Grocery Bot Dashboard")

# 📂 Path to orders
file_path = "data/orders.json"


# 🟡 Load data
if not os.path.exists(file_path):
    st.warning("⚠️ No orders found yet. Place an order from Telegram.")
    st.stop()

with open(file_path, "r") as f:
    orders = json.load(f)

if not orders:
    st.warning("No orders yet")
    st.stop()

# 🔥 Latest first
orders = list(reversed(orders))

# ================= LATEST ORDER =================
st.header("📦 Latest Order")

latest = orders[0]

col1, col2 = st.columns(2)

with col1:
    st.subheader("🛒 Items")
    for item in latest["items"]:
        st.write(f"• {item['name']} x{item['qty']}")

    st.subheader("💰 Total")
    st.success(latest["total"])

    st.subheader("⏱ Time")
    st.write(latest["time"])

with col2:
    st.subheader("📸 Payment QR")

    if os.path.exists(latest["screenshot"]):
        st.image(latest["screenshot"], use_container_width=True)
    else:
        st.error("Screenshot not found")

# ================= HISTORY =================
st.header("📜 Order History")

for order in orders:
    with st.expander(f"{order['time']} — {order['total']}"):
        for item in order["items"]:
            st.write(f"{item['name']} x{item['qty']}")

# ================= LOG PANEL =================
st.header("🧠 System Info")

st.write(f"Total Orders: {len(orders)}")