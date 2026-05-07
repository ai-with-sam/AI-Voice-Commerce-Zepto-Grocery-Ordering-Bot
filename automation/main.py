from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import subprocess
import json
import sys

app = FastAPI()


# ===== SCHEMA =====
class Item(BaseModel):
    name: str
    qty: int


class Order(BaseModel):
    items: List[Item]
    chat_id: int


# ===== HEALTH CHECK =====
@app.get("/")
def home():
    return {"status": "Server is running 🚀"}


# ===== ORDER API =====
@app.post("/order")
def place_order(order: Order):
    print("📦 Order received:", order)

    try:
        # Convert to dict
        items = [item.dict() for item in order.items]

        # Convert to JSON string
        items_json = json.dumps(items)

        print("🔥 Starting Playwright subprocess...")

        result = subprocess.run(
            [
                sys.executable,       # 🔥 IMPORTANT FIX
                "zepto_bot.py",
                items_json,
                str(order.chat_id)
            ],
            capture_output=True,
            text=True
        )

        print("Return code:", result.returncode)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        return {
            "status": "success",
            "output": result.stdout,
            "chat_id": order.chat_id
        }

    except Exception as e:
        print("❌ ERROR:", e)

        return {
            "status": "error",
            "message": str(e),
            "chat_id": order.chat_id
        }