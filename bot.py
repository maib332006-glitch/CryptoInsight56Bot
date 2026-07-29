import os
import logging
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Config ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

EDUCATIONAL_TIPS = [
    "🔐 *Not your keys, not your coins* — always control your private keys or use a reputable custodian.",
    "📊 *DYOR* — always research a project's fundamentals before investing.",
    "⚖️ *Diversification* — spreading investments across assets can help manage risk.",
    "🧊 *Cold storage* — hardware wallets keep your crypto offline and safer from hacks.",
    "📉 *Volatility is normal* — crypto markets can swing 10-20% in a day; plan accordingly.",
    "🕵️ *Beware of scams* — no legitimate project will ever DM you asking for your seed phrase.",
    "⛓️ *Blockchain basics* — a blockchain is a distributed ledger maintained by a network of nodes.",
    "💰 *Market cap ≠ price* — a coin's price alone doesn't tell you its total value; check market cap too.",
    "🔄 *Dollar-cost averaging (DCA)* — buying fixed amounts at regular intervals can reduce timing risk.",
    "📜 *Smart contracts* — self-executing code on a blockchain that runs automatically when conditions are met.",
    "🌐 *Gas fees* — the cost paid to have a transaction processed on a blockchain network.",
    "🏦 *CEX vs DEX* — centralized exchanges are custodial and easier to use; decentralized exchanges let you keep control of your funds.",
]

# ---------- Helpers ----------

def fetch_json(url, params=None, timeout=10):
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"Request failed for {url}: {e}")
        return None


def search_coin_id(query: str):
    data = fetch_json(f"{COINGECKO_BASE}/search", params={"query": query})
    if not data or not data.get("coins"):
        return None
    coin = data["coins"][0]
    return coin["id"], coin["symbol"], coin["name"]


def get_coin_price(coin_id: str):
    data = fetch_json(
        f"{COINGECKO_BASE}/simple/price",
        params={
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
        },
    )
    if not data or coin_id not in data:
        return None
    return data[coin_id]


def get_top_coins(n=10):
    return fetch_json(
        f"{COINGECKO_BASE}/coins/markets",
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": n,
            "page": 1,
            "sparkline": "false",
        },
    )


def get_trending():
    data = fetch_json(f"{COINGECKO_BASE}/search/trending")
    if not data:
        return None
    return data.get("coins", [])


def get_global_market():
    data = fetch_json(f"{COINGECKO_BASE}/global")
    if not data:
        return None
    return data.get("data")


# ---------- Command Handlers ----------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Welcome to CryptoInsight!*\n\n"
        "I bring you crypto insights, market updates, and educational content "
        "to help you stay informed in the world of digital assets.\n\n"
        "*Commands:*\n"
        "/price <coin> — Live price (e.g. /price bitcoin)\n"
        "/top — Top 10 coins by market cap\n"
        "/trending — Trending coins right now\n"
        "/market — Global market overview\n"
        "/tip — Random educational tip\n"
        "/help — Show this message again"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /price <coin name or symbol>\nExample: /price bitcoin"
        )
        return

    query = " ".join(context.args).lower()
    await update.message.chat.send_action("typing")

    result = search_coin_id(query)
    if not result:
        await update.message.reply_text(f"❌ Couldn't find a coin matching '{query}'.")
        return

    coin_id, symbol, name = result
    price_data = get_coin_price(coin_id)
    if not price_data or "usd" not in price_data:
        await update.message.reply_text("⚠️ Couldn't fetch price data right now. Try again shortly.")
        return

    price = price_data.get("usd", 0)
    change = price_data.get("usd_24h_change") or 0
    mcap = price_data.get("usd_market_cap")

    change_emoji = "🟢" if change >= 0 else "🔴"
    mcap_line = f"🏦 Market Cap: ${mcap:,.0f}\n" if mcap else ""

    text = (
        f"*{name}* ({symbol.upper()})\n"
        f"💵 Price: ${price:,.4f}\n"
        f"{change_emoji} 24h Change: {change:.2f}%\n"
        f"{mcap_line}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    coins = get_top_coins(10)
    if not coins:
        await update.message.reply_text("⚠️ Couldn't fetch market data right now. Try again shortly.")
        return

    lines = ["📊 *Top 10 Cryptocurrencies by Market Cap*\n"]
    for i, c in enumerate(coins, start=1):
        change = c.get("price_change_percentage_24h") or 0
        emoji = "🟢" if change >= 0 else "🔴"
        lines.append(
            f"{i}. *{c['name']}* ({c['symbol'].upper()}) — ${c['current_price']:,.2f} {emoji} {change:.2f}%"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    coins = get_trending()
    if not coins:
        await update.message.reply_text("⚠️ Couldn't fetch trending data right now. Try again shortly.")
        return

    lines = ["🔥 *Trending Coins Right Now*\n"]
    for i, item in enumerate(coins[:7], start=1):
        c = item.get("item", {})
        rank = c.get("market_cap_rank", "N/A")
        lines.append(f"{i}. *{c.get('name')}* ({c.get('symbol', '').upper()}) — Rank #{rank}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    data = get_global_market()
    if not data:
        await update.message.reply_text("⚠️ Couldn't fetch global market data right now. Try again shortly.")
        return

    total_mcap = data.get("total_market_cap", {}).get("usd", 0)
    total_vol = data.get("total_volume", {}).get("usd", 0)
    btc_dom = data.get("market_cap_percentage", {}).get("btc", 0)
    eth_dom = data.get("market_cap_percentage", {}).get("eth", 0)
    change = data.get("market_cap_change_percentage_24h_usd", 0) or 0

    emoji = "🟢" if change >= 0 else "🔴"
    text = (
        "🌍 *Global Crypto Market Overview*\n\n"
        f"💰 Total Market Cap: ${total_mcap:,.0f}\n"
        f"{emoji} 24h Change: {change:.2f}%\n"
        f"📈 24h Volume: ${total_vol:,.0f}\n"
        f"🟠 BTC Dominance: {btc_dom:.1f}%\n"
        f"🔵 ETH Dominance: {eth_dom:.1f}%"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def tip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tip = random.choice(EDUCATIONAL_TIPS)
    await update.message.reply_text(f"💡 *Crypto Tip*\n\n{tip}", parse_mode=ParseMode.MARKDOWN)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ I didn't recognize that command. Type /help to see what I can do."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    # Log the error but never let it crash the bot process.
    logger.error("Exception while handling an update:", exc_info=context.error)


# ---------- Tiny health-check server ----------
# Railway (and most PaaS platforms) is happiest when a process binds to $PORT.
# This avoids the bot being flagged as unhealthy/crashed even though Telegram
# polling itself doesn't need an open port.

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"CryptoInsight56Bot is running.")

    def log_message(self, format, *args):
        return  # keep logs clean


def run_health_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        server.serve_forever()
    except Exception as e:
        logger.error(f"Health server failed: {e}")


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set. Set it in Railway's Variables tab.")
        raise SystemExit(1)

    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("trending", trending_command))
    app.add_handler(CommandHandler("market", market_command))
    app.add_handler(CommandHandler("tip", tip_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    app.add_error_handler(error_handler)

    logger.info("CryptoInsight56Bot starting (polling mode)...")
    app.run_polling(drop_pending_updates=True, close_loop=False)


if __name__ == "__main__":
    main()
