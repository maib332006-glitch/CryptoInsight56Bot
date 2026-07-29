# CryptoInsight56Bot

A Telegram bot delivering crypto insights, market updates, and educational content, built for
deployment on Railway via GitHub.

## Features
- `/price <coin>` — live price, 24h change, and market cap (e.g. `/price bitcoin`)
- `/top` — top 10 coins by market cap
- `/trending` — trending coins right now
- `/market` — global market cap, volume, BTC/ETH dominance
- `/tip` — random educational tip about crypto
- `/help` — command list

Data comes from the free, no-key-required [CoinGecko API](https://www.coingecko.com/en/api).

## 1. Create the bot on Telegram
1. Open Telegram and message **@BotFather**.
2. Run `/newbot`, follow the prompts, and set the username to `CryptoInsight56Bot` (or your chosen name).
3. Copy the **token** BotFather gives you — you'll need it in step 3.

## 2. Push this code to GitHub
```bash
cd cryptoinsight-bot
git init
git add .
git commit -m "Initial commit: CryptoInsight56Bot"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

## 3. Deploy on Railway
1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
2. Select this repository.
3. Open the service → **Variables** tab → add:
   - `BOT_TOKEN` = the token from BotFather
4. Railway will detect Python automatically (via `requirements.txt` + `Procfile`) and deploy.
5. Check the **Deployments** logs — you should see `CryptoInsight56Bot starting (polling mode)...`.

That's it — message your bot on Telegram and try `/start`.

## Why this won't crash on Railway
- **No hardcoded token** — it's read from the `BOT_TOKEN` environment variable, and the bot
  exits with a clear log message if it's missing, instead of failing with a cryptic error.
- **All network calls are wrapped in try/except** — if CoinGecko is slow or down, the bot
  replies with a friendly error instead of throwing an unhandled exception.
- **Global error handler** — any unexpected error during update handling is logged, not raised,
  so one bad request can't take the whole process down.
- **Health-check server** — a lightweight HTTP server binds to Railway's `$PORT` so the platform
  sees an active, healthy process (some PaaS platforms flag services with no open port as
  unhealthy, even background workers like this one).
- **`drop_pending_updates=True`** — avoids the bot choking on a backlog of old messages after a
  redeploy or restart.

## Local testing
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # then edit .env and add your real token
export $(cat .env | xargs)     # Windows: set BOT_TOKEN=your_token manually
python bot.py
```

## Extending the bot
- Add more commands in `bot.py` following the existing pattern (`CommandHandler`).
- Add scheduled market updates using `python-telegram-bot`'s `JobQueue` (`app.job_queue.run_repeating(...)`).
- Swap CoinGecko for another data source by editing the `fetch_json` calls.
