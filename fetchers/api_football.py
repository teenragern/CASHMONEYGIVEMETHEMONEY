import os
import requests
import logging
from utils.rate_limiter import can_make_request, record_api_call

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY
}

# Map internal league names to API-Football League IDs
LEAGUE_MAP = {
    "EPL": 39,
    "La Liga": 140,
    "Bundesliga": 78,
    "Serie A": 135
}

def get_team_stats(league_name: str, season: int, team_id: int) -> dict:
    """
    Fetches aggregate team statistics for the season (goals, xG, form).
    This costs 1 API call per team. Cache this or only run once daily.
    """
    if not can_make_request("api_football"):
        logging.warning("API-Football limit reached.")
        return {}

    league_id = LEAGUE_MAP.get(league_name)
    url = f"{BASE_URL}/teams/statistics"
    params = {
        "league": league_id,
        "season": season,
        "team": team_id
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        record_api_call("api_football")
        response.raise_for_status()
        
        data = response.json()
        if not data.get("response"):
            return {}
            
        stats = data["response"]
        
        return {
            "form": stats.get("form"),
            "goals_for_home": stats.get("goals", {}).get("for", {}).get("total", {}).get("home", 0),
            "goals_for_away": stats.get("goals", {}).get("for", {}).get("total", {}).get("away", 0),
            "goals_against_home": stats.get("goals", {}).get("against", {}).get("total", {}).get("home", 0),
            "goals_against_away": stats.get("goals", {}).get("against", {}).get("total", {}).get("away", 0),
            "matches_played_home": stats.get("fixtures", {}).get("played", {}).get("home", 0),
            "matches_played_away": stats.get("fixtures", {}).get("played", {}).get("away", 0),
        }

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching team stats for team {team_id}: {e}")
        return {}


def get_h2h(team_1_id: int, team_2_id: int) -> list:
    """
    Fetches recent Head-to-Head between two teams.
    """
    if not can_make_request("api_football"):
        return []

    url = f"{BASE_URL}/fixtures/headtohead"
    params = {"h2h": f"{team_1_id}-{team_2_id}", "last": 5} # Get last 5 meetings

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        record_api_call("api_football")
        response.raise_for_status()
        
        data = response.json()
        return data.get("response", [])

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching H2H for {team_1_id} vs {team_2_id}: {e}")
        return []

def get_lineups(fixture_id: int) -> list:
    """
    Used at T-1 Hour to check confirmed lineups.
    """
    if not can_make_request("api_football"):
        return []

    url = f"{BASE_URL}/fixtures/lineups"
    params = {"fixture": fixture_id}

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        record_api_call("api_football")
        response.raise_for_status()
        
        data = response.json()
        return data.get("response", [])

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching lineups for fixture {fixture_id}: {e}")
        return []
