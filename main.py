import os
import time
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from database import init_db, get_db_connection
from fetchers.football_data import get_upcoming_fixtures
from fetchers.api_football import get_team_stats, get_lineups
from fetchers.the_odds_api import get_pinnacle_odds
from models.poisson_model import calculate_fair_odds
from models.value_calculator import evaluate_market
from utils.telegram import send_bet_alert, send_pass_alert

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TARGET_LEAGUES = os.getenv("TARGET_LEAGUES", "EPL,La Liga,Bundesliga,Serie A").split(',')

def populate_upcoming_matches():
    """Fetches upcoming matches and stores them in the DB."""
    logging.info("Running job: Populate Upcoming Matches")
    conn = get_db_connection()
    c = conn.cursor()
    
    for league in TARGET_LEAGUES:
        fixtures = get_upcoming_fixtures(league.strip(), days_ahead=3)
        for f in fixtures:
            # Upsert match
            c.execute('''
                INSERT OR IGNORE INTO matches (id, league, kickoff, home_team, away_team, status)
                VALUES (?, ?, ?, ?, ?, 'PENDING')
            ''', (str(f['id']), f['league'], f['kickoff'], f['home_team'], f['away_team']))
    
    conn.commit()
    conn.close()

def _estimate_xg(league: str, home_team: str, away_team: str) -> tuple:
    """
    Very basic xG estimation using season stats from API-Football.
    In a real production system, this would be more sophisticated.
    """
    # For now, we mock the xG generation to avoid burning through API-Football's 100/day limit
    # during testing. You would use get_team_stats() here.
    return 1.45, 1.12

def evaluate_t_minus_6(match_id: str):
    """Evaluates a specific match for value 6 hours out."""
    logging.info(f"Running job: Evaluate Match {match_id} (T-6 Hours)")
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute(
        "SELECT * FROM matches WHERE id = ?",
        (match_id,)
    )
    match = c.fetchone()
    
    if not match:
        logging.warning(f"Match {match_id} not found in DB.")
        conn.close()
        return
        
    if match['status'] != 'PENDING':
        logging.info(f"Match {match['home_team']} already evaluated ({match['status']}). Skipping.")
        conn.close()
        return

    league = match['league']
    # 1. Calculate Fair Odds (Poisson Model)
    home_xg, away_xg = _estimate_xg(league, match['home_team'], match['away_team'])
    fair_odds_all = calculate_fair_odds(home_xg, away_xg)
    
    # Update match with xG
    c.execute("UPDATE matches SET home_xg = ?, away_xg = ? WHERE id = ?", 
              (home_xg, away_xg, match['id']))
    
    # 2. Get Bookmaker Odds (The Odds API)
    all_odds = get_pinnacle_odds(league)
    # Find the specific match by name matching (simplified for this example)
    bookie_game = next((g for g in all_odds if g['home_team'] in match['home_team'] or match['home_team'] in g['home_team']), None)
    
    if not bookie_game:
        logging.warning(f"Could not find bookie odds for {match['home_team']} vs {match['away_team']}")
        conn.close()
        return
        
    # 3. Calculate Value
    match_info = {
        "home_team": match['home_team'],
        "away_team": match['away_team'],
        "league": league,
        "kickoff": match['kickoff']
    }
    
    found_bets = []
    for market in ["1X2", "Totals", "BTTS"]:
        market_key = market.lower()
        if market == "1X2":
            b_odds = bookie_game['odds'].get('h2h', {})
        elif market == "Totals":
            b_odds = bookie_game['odds'].get('totals', {})
        else:
            b_odds = bookie_game['odds'].get('btts', {})
            
        bets = evaluate_market(match_info, market, fair_odds_all[market], b_odds)
        found_bets.extend(bets)
        
    # 4. Act on Value
    if found_bets:
        for bet in found_bets:
            # Log to DB
            c.execute('''
                INSERT INTO bets (match_id, market, selection, bookmaker, fair_odds, best_odds, edge, kelly_stake, confidence)
                VALUES (?, ?, ?, 'Pinnacle', ?, ?, ?, ?, ?)
            ''', (match['id'], bet['market'], bet['selection'], bet['fair_odds'], bet['best_odds'], bet['edge'], bet['kelly_stake'], bet['confidence']))
            
            # Alert
            send_bet_alert(match_info, bet['fair_odds'], bet['best_odds'], bet['edge'], bet['kelly_stake'], bet['confidence'])
            
        c.execute("UPDATE matches SET status = 'EVALUATED_BET' WHERE id = ?", (match['id'],))
    else:
        send_pass_alert(match_info, "No edge found >= 3.0%")
        c.execute("UPDATE matches SET status = 'EVALUATED_PASS' WHERE id = ?", (match_id,))
            
    conn.commit()
    conn.close()

def check_lineups_t_minus_1(match_id: str):
    """Checks lineups for a specific match 1 hour out where we bet."""
    logging.info(f"Running job: Check Lineups for {match_id} (T-1 Hour)")
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, home_team, away_team FROM matches 
        WHERE id = ? AND status = 'EVALUATED_BET'
    ''', (match_id,))
    
    match = c.fetchone()
    
    if match:
        # If we had the exact API-Football fixture ID, we'd pass it here.
        # This is a placeholder for where that logic connects.
        logging.info(f"Checking lineups for {match['home_team']} vs {match['away_team']}")
        # lineups = get_lineups(fixture_id)
        # analyze_lineup(lineups)
        
    conn.close()

def settle_finished_matches(match_id: str):
    """Checks a specific match > 2 hours past kickoff and updates results safely."""
    logging.info(f"Running job: Settle Finished Match {match_id}")
    now = datetime.utcnow()
    target_time = now - timedelta(hours=2, minutes=15)
    
    # Ideally, we query football-data or API-football for recent results
    # and update the DB accordingly.
    # Placeholder for Result Logging
    pass

if __name__ == "__main__":
    init_db()
    logging.info("This file is now intended to be called by scheduler.py dynamically.")
    logging.info("Run `python scheduler.py` to trigger the APScheduler logic.")
