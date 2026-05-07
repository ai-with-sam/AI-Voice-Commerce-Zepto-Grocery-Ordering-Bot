from fastapi import FastAPI
import subprocess
import json

app = FastAPI()

@app.post("/order")
def place_order(data: dict):
    items = data["items"]
    chat_id = str(data["chat_id"])

    print("Received order:", items)

    subprocess.Popen([
        "python",
        "zepto_automation.py",
        json.dumps(items),
        chat_id
    ])

    return {"status": "started"}