# AI Voice-Based Grocery Ordering Automation System

An AI-powered voice commerce automation bot that allows users to place grocery orders on Zepto using Telegram voice messages.

## Features

* Voice-based grocery ordering
* OpenAI Whisper speech-to-text transcription
* NLP item & quantity extraction
* Telegram Bot integration
* Playwright browser automation
* Persistent login sessions
* QR-based payment workflow
* Automated cart handling
* Screenshot-based order confirmation

---

## Tech Stack

* Python
* Playwright
* Telegram Bot API
* OpenAI Whisper
* Asyncio
* FFmpeg

---

## Workflow

1. User sends voice note on Telegram
2. Whisper converts speech to text
3. NLP extracts grocery items and quantities
4. Playwright automates Zepto ordering
5. Cart screenshots and QR payment are generated
6. User completes payment

---

## Project Structure

```bash
project/
│
├── bot/
├── automation/
├── data/
├── screenshots/
├── audio/
├── requirements.txt
├── .env.example
└── README.md
```

---

## Installation

```bash
git clone <repo-url>

cd project

pip install -r requirements.txt
```

---

## Setup

Create `.env`

```env
TELEGRAM_TOKEN=your_bot_token
```

---

## Run

```bash
python bot.py
```

---

## Demo

(Add your demo GIF/video here)

---

## Future Improvements

* Multi-user scalability
* Async Playwright migration
* Better product matching
* Cloud deployment
* Real payment verification

---

## Disclaimer

This project is built for educational and automation learning purposes.
