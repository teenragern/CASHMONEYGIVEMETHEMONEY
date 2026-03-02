import os
import requests
import logging
from utils.rate_limiter import can_make_request, record_api_call

# The Odds API keys and config
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4/sports"

# Map our internal league names to The Odds API sport keys
LEAGUE_MAP = {
    "EPL": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
    "Bundesliga": "soccer_germany_bundesliga",
    "Serie A": "soccer_italy_serie_a"
}

def get_pinnacle_odds(league_name: str) -> list:
    """
    Fetches pre-match odds from Pinnacle for the specified league.
    Returns a list of games with 1X2, Over/Under 2.5, and BTTS odds.
    """
    if not can_make_request("odds_api"):
        logging.warning("The Odds API daily limit reached. Skipping request.")
        return []

    sport_key = LEAGUE_MAP.get(league_name)
    if not sport_key:
        logging.error(f"League {league_name} not supported in Odds API mapping.")
        return []

    url = f"{BASE_URL}/{sport_key}/odds/"
    
    # We want Pinnacle specifically as the sharp reference
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu", # Pinnacle is often available under EU or UK
        "markets": "h2h,totals,btts",
        "bookmakers": "pinnacle",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        record_api_call("odds_api")
        
        # Handling the quota limits headers would be nice, but we track locally.
        response.raise_for_status()
        data = response.json()
        
        parsed_games = []
        for game in data:
            match_data = {
                "id": game["id"],
                "home_team": game["home_team"],
                "away_team": game["away_team"],
                "commence_time": game["commence_time"],
                "odds": {
                    "h2h": {},
                    "totals": {},
                    "btts": {}
                }
            }
            
            for bookmaker in game.get("bookmakers", []):
                if bookmaker["key"] == "pinnacle":
                    for market in bookmaker.get("markets", []):
                        market_key = market["key"] # h2h, totals, btts
                        if market_key == "h2h":
                            # typically outcomes are Name of Home, Name of Away, and "Draw"
                            for outcome in market.get("outcomes", []):
                                if outcome["name"] == game["home_team"]:
                                    match_data["odds"]["h2h"]["home"] = outcome["price"]
                                elif outcome["name"] == game["away_team"]:
                                    match_data["odds"]["h2h"]["away"] = outcome["price"]
                                elif outcome["name"] == "Draw":
                                    match_data["odds"]["h2h"]["draw"] = outcome["price"]
                        
                        elif market_key == "totals":
                            # We look for the 2.5 line
                            for outcome in market.get("outcomes", []):
                                if outcome.get("point") == 2.5:
                                    if outcome["name"] == "Over":
                                        match_data["odds"]["totals"]["over_2_5"] = outcome["price"]
                                    elif outcome["name"] == "Under":
                                        match_data["odds"]["totals"]["under_2_5"] = outcome["price"]
                        
                        elif market_key == "btts":
                            for outcome in market.get("outcomes", []):
                                if outcome["name"] == "Yes":
                                    match_data["odds"]["btts"]["yes"] = outcome["price"]
                                elif outcome["name"] == "No":
                                    match_data["odds"]["btts"]["no"] = outcome["price"]

            parsed_games.append(match_data)
            
        return parsed_games

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Odds API data for {league_name}: {e}")
        return []

