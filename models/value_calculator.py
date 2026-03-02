import logging

KELLY_FRACTION = 0.25 # Quarter Kelly
MAX_BET_PERCENT = 5.0 # Max 5% of bankroll per bet
MIN_EDGE = 3.0 # Minimum 3% edge to trigger a bet

def calculate_edge(fair_odds: float, bookie_odds: float) -> float:
    """
    Calculates the edge percentage.
    Edge = (True Probability * Bookie Odds) - 1
    True Probability = 1 / Fair Odds
    """
    true_prob = 1.0 / fair_odds
    edge = (true_prob * bookie_odds) - 1.0
    return edge * 100.0 # Return as percentage

def calculate_kelly_stake(fair_odds: float, bookie_odds: float) -> float:
    """
    Calculates recommended stake size using Fractional Kelly Criterion.
    """
    true_prob = 1.0 / fair_odds
    b = bookie_odds - 1.0
    q = 1.0 - true_prob
    
    # Kelly fraction: f = (bp - q) / b
    kelly_f = (b * true_prob - q) / b
    
    if kelly_f <= 0:
        return 0.0 # No edge, no bet
        
    recommended_stake = kelly_f * KELLY_FRACTION * 100.0 # Convert to %
    
    # Cap at MAX_BET_PERCENT
    return min(recommended_stake, MAX_BET_PERCENT)

def get_confidence_level(edge: float, stake: float) -> str:
    """
    Returns a string confidence level based on edge and stake size.
    """
    if edge >= 10.0 and stake >= 3.0:
        return "⭐⭐⭐ (High)"
    elif edge >= 5.0 and stake >= 1.5:
        return "⭐⭐ (Medium)"
    elif edge >= MIN_EDGE:
        return "⭐ (Low)"
    else:
        return "None (Pass)"

def evaluate_market(match_info: dict, market_name: str, fair_odds_dict: dict, bookie_odds_dict: dict) -> list:
    """
    Evaluates all outcomes in a specific market (e.g. 1X2, Over/Under)
    and returns a list of actionable bets.
    
    Args:
        match_info: dict containing home_team, away_team, kickoff, etc.
        market_name: string e.g. "1X2"
        fair_odds_dict: dict e.g. {"home": 2.1, "draw": 3.4, "away": 3.5}
        bookie_odds_dict: dict e.g. {"home": 2.2, "draw": 3.4, "away": 3.3}
        
    Returns:
        List of bet dictionaries to be executed/logged.
    """
    bets = []
    
    for outcome, f_odds in fair_odds_dict.items():
        b_odds = bookie_odds_dict.get(outcome)
        
        if not b_odds:
            continue
            
        edge = calculate_edge(f_odds, b_odds)
        
        if edge >= MIN_EDGE:
            stake = calculate_kelly_stake(f_odds, b_odds)
            confidence = get_confidence_level(edge, stake)
            
            if stake > 0:
                bets.append({
                    "match_info": match_info, # Includes teams, competition, time
                    "market": market_name,
                    "selection": outcome,
                    "fair_odds": round(f_odds, 2),
                    "best_odds": b_odds,
                    "edge": round(edge, 1),
                    "kelly_stake": round(stake, 2),
                    "confidence": confidence
                })
                logging.info(f"Value found: {match_info['home_team']} vs {match_info['away_team']} - {market_name} {outcome} at {b_odds}")
                
    return bets
