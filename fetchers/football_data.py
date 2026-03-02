import os
import requests
import logging
from datetime import datetime, timedelta
from utils.rate_limiter import can_make_request, record_api_call

FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
BASE_URL = "https://api.football-data.org/v4"

# Map internal league names to football-data.org competition codes
LEAGUE_MAP = {
    "EPL": "PL",
    "La Liga": "PD",
    "Bundesliga": "BL1",
    "Serie A": "SA"
}

def get_upcoming_fixtures(league_name: str, days_ahead: int = 3) -> list:
    """
    Fetches upcoming fixtures for the given league in the next X days.
    """
    if not can_make_request("football_data"):
        logging.warning("football-data.org API limit reached.")
        return []

    comp_code = LEAGUE_MAP.get(league_name)
    if not comp_code:
        logging.error(f"League {league_name} not supported in football-data mapping.")
        return []

    date_from = datetime.utcnow().strftime("%Y-%m-%d")
    date_to = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/competitions/{comp_code}/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
    params = {
        "status": "SCHEDULED",
        "dateFrom": date_from,
        "dateTo": date_to
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        record_api_call("football_data")
        response.raise_for_status()
        
        data = response.json()
        matches = []
        for match in data.get("matches", []):
            matches.append({
                "id": match["id"],
                "home_team": match["homeTeam"]["name"],
                "away_team": match["awayTeam"]["name"],
                "kickoff": match["utcDate"],
                "matchday": match["matchday"],
                "league": league_name
            })
        return matches

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching upcoming fixtures for {league_name}: {e}")
        return []

def get_standings_and_form(league_name: str) -> dict:
    """
    Fetches current standings and basic form for teams.
    Used as an input for attack/defense strength if needed.
    """
    if not can_make_request("football_data"):
        return {}

    comp_code = LEAGUE_MAP.get(league_name)
    url = f"{BASE_URL}/competitions/{comp_code}/standings"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        record_api_call("football_data")
        response.raise_for_status()
        
        data = response.json()
        standings_dict = {}
        for standing in data.get("standings", []):
            if standing["type"] == "TOTAL":
                for row in standing.get("table", []):
                    team_name = row["team"]["name"]
                    standings_dict[team_name] = {
                        "position": row["position"],
                        "played": row["playedGames"],
                        "goals_for": row["goalsFor"],
                        "goals_against": row["goalsAgainst"],
                        "form": row.get("form", "")
                    }
        return standings_dict

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching standings for {league_name}: {e}")
        return {}
