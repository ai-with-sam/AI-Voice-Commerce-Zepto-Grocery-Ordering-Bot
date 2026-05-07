from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List
import os

from zepto_bot import run_zepto

app = FastAPI()


class Item(BaseModel):
    name: str
    qty: int


class OrderRequest(BaseModel):
    items: List[Item]
    chat_id: int


def run_order_background(items, chat_id):
    try:
        print("🔥 BACKGROUND JOB STARTED")
        run_zepto(items, chat_id)
        print("✅ BACKGROUND JOB FINISHED")
    except Exception as e:
        print("❌ BACKGROUND ERROR:", e)


@app.post("/order")
async def place_order(order: OrderRequest, background_tasks: BackgroundTasks):

    items = [item.dict() for item in order.items]
    chat_id = order.chat_id

    background_tasks.add_task(run_zepto, items, chat_id)

    return {
        "status": "accepted"
    }