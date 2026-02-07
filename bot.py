import re
import os
import time
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")

STAR_PRICE = 0.015

CURRENCY_MAP = {
    "ton": "ton",
    "t": "ton",

    "usdt": "usdt",
    "usd": "usdt",
    "u": "usdt",

    "inr": "inr",
    "rs": "inr",
    "i": "inr",
    "₹": "inr",

    "star": "star",
    "stars": "star",
    "s" : "star",
}

# -------- PRICE CACHE --------
PRICE_CACHE = {
    "ton_usdt": None,
    "usd_inr": None,
    "last_update": 0
}
CACHE_TTL = 60  # seconds


def get_prices():
    now = time.time()

    # return cached prices if fresh
    if now - PRICE_CACHE["last_update"] < CACHE_TTL:
        return PRICE_CACHE["ton_usdt"], PRICE_CACHE["usd_inr"]

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "the-open-network",
        "vs_currencies": "usd,inr"
    }

    data = requests.get(url, params=params, timeout=10).json()

    ton_usdt = data["the-open-network"]["usd"]
    ton_inr = data["the-open-network"]["inr"]

    usd_inr = ton_inr / ton_usdt

    PRICE_CACHE.update({
        "ton_usdt": ton_usdt,
        "usd_inr": usd_inr,
        "last_update": now
    })

    return ton_usdt, usd_inr


async def price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()

    # STRICT match (no sentences)
    match = re.fullmatch(
        r"([\d.]+)\s*(ton|t|usdt|usd|u|inr|rs|i|₹|star|stars)",
        text
    )
    if not match:
        return

    amount = float(match.group(1))
    raw_currency = match.group(2)

    currency = CURRENCY_MAP.get(raw_currency)
    if not currency:
        return

    ton_price, usd_inr = get_prices()

    if currency == "ton":
        ton = amount
        usdt = ton * ton_price

    elif currency == "usdt":
        usdt = amount
        ton = usdt / ton_price

    elif currency == "inr":
        usdt = amount / usd_inr
        ton = usdt / ton_price

    else:  # star
        usdt = amount * STAR_PRICE
        ton = usdt / ton_price

    inr = usdt * usd_inr
    star = usdt / STAR_PRICE

    reply = (
        f"💎 TON : {ton:.2f}\n"
        f"💵 USDT : {usdt:.2f}\n"
        f"🇮🇳 INR : {inr:.2f}\n"
        f"⭐ STAR : {star:.2f}"
    )

    await update.message.reply_text(reply)


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(
    MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        price_handler
    )
)

print("Converter bot running fast ⚡")
app.run_polling()
