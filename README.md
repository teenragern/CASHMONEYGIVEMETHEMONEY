# Soccer Value Betting Bot

An automated Python bot that fetches live soccer data, calculates fair odds using a Poisson Goal Model, compares them to Pinnacle's lines, and sends +EV (Expected Value) alerts to a Telegram chat.

## Features
- **The Odds API Integration**: Scans Pinnacle for 1X2, Over/Under 2.5, and BTTS markets.
- **Football-Data.org Integration**: Fetches upcoming fixtures and basic league standings.
- **API-Football Integration**: Fetches detailed Team Statistics (xG inputs) and lineups.
- **SQLite Database**: Tracks daily API usage natively to strictly protect the 100/day API-Football limit and logs all evaluated matches and placed bets to track ROI.
- **Kelly Criterion Staking**: Automatically calculates optimal bet size based on edge and true probability.
- **Telegram Alerts**: Pushes `BET` and `PASS` alerts.
- **Background Scheduler**: 
  - `T-6 Hours`: Value Edge detection.
  - `T-1 Hour`: Lineup Check (mocked connection setup).
  - `Post-Match`: Result Settlement (mocked connection setup).

## Project Structure
```text
soccer_betting_bot/
│
├── data/
│   ├── api_football.py    # Fetches detailed stats and lineups 
│   ├── football_data.py   # Fetches upcoming fixtures
│   └── the_odds_api.py    # Fetches Pinnacle odds
│
├── models/
│   ├── poisson_model.py   # Bivariate Poisson distribution for expected goals
│   └── value_calculator.py# Edge %, Fractional Kelly Stake, Confidence evaluation
│
├── utils/
│   ├── rate_limiter.py    # SQLite-backed daily rate limit tracking  
│   └── telegram.py        # Telegram BOT API integration
│
├── database.py            # SQLite schema initialization (bets, matches, api_usage)
├── main.py                # APScheduler Orchestrator
├── .env                   # API Keys and Variables
├── requirements.txt       # Python Dependencies
├── Procfile               # Railway deployment process command
└── railway.toml           # Railway configuration mapping
```

## How to Configure API Keys

Your API keys must be injected into the system environment. We handle this securely via a `.env` file for local development, and Railway Config Variables for deployment.

1. Create a `.env` file in the root directory.
2. Add the following keys (they have been pre-populated for you in your local workspace):

```text
# API Keys
API_FOOTBALL_KEY=your_key_here
FOOTBALL_DATA_TOKEN=your_token_here
ODDS_API_KEY=your_key_here

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# App Config
TARGET_LEAGUES=EPL,La Liga,Bundesliga,Serie A
DB_PATH=bets.db
```

### Explaining the Limits
- `API-Football`: Hard-capped at 100 calls/day. `utils/rate_limiter.py` intercepts requests to this API and tracks it in `bets.db -> api_usage`. If 100 calls are reached, it safety aborts further requests until midnight.
- `Football-Data.org`: Safe at ~500 calls/day.
- `The Odds API`: $30 tier provides ~30,000 requests/month (1,000/day). Capped locally at 500/day iteratively.

## Deployment (Railway)

1. Connect this folder to a GitHub repository.
2. Link the repository to Railway.
3. Railway will use Nixpacks via the `railway.toml` and execute the `Procfile` (`worker: python main.py`).
4. **CRITICAL**: In your Railway Project Dashboard, go to **Variables**, and copy all the keys from your `.env` file into the Railway Variables tab so your app can read them in production.
5. Railway provides persistent storage via a Volume. Attach a Volume to `/app` (or change `DB_PATH` in Railway Variables to `/app/data/bets.db`) to ensure your SQLite database persists across deployments.
