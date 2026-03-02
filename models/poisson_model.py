import numpy as np
from scipy.stats import poisson

def calc_match_probabilities(home_xg: float, away_xg: float, max_goals: int = 7) -> dict:
    """
    Given the expected goals for the Home and Away teams, calculates probabilities 
    for 1X2, Over/Under 2.5, and BTTS using the bivariate Poisson distribution.
    
    Args:
        home_xg: Home team expected goals
        away_xg: Away team expected goals
        max_goals: Maximum goals to calculate probabilities up to (default 7)
        
    Returns:
        dict: Probabilities for each market outcome
    """
    
    # Generate arrays of probabilities for 0 to max_goals
    home_probs = [poisson.pmf(i, home_xg) for i in range(max_goals + 1)]
    away_probs = [poisson.pmf(i, away_xg) for i in range(max_goals + 1)]
    
    # Create a 2D matrix where matrix[i][j] = prob of Home scoring i and Away scoring j
    prob_matrix = np.outer(home_probs, away_probs)
    
    # 1X2 Probabilities
    home_win_prob = np.sum(np.tril(prob_matrix, -1)) # Lower triangle
    draw_prob = np.sum(np.diag(prob_matrix))         # Diagonal
    away_win_prob = np.sum(np.triu(prob_matrix, 1))  # Upper triangle
    
    # Over/Under 2.5 Probabilities
    under_2_5_prob = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            if i + j < 2.5:
                under_2_5_prob += prob_matrix[i, j]
                
    over_2_5_prob = 1.0 - under_2_5_prob
    
    # BTTS (Both Teams To Score) Probabilities
    # BTTS No means either Home scored 0, Away scored 0, or both scored 0.
    # It's the sum of the first row and first column, minus the intersection (0,0)
    btts_no_prob = np.sum(prob_matrix[0, :]) + np.sum(prob_matrix[:, 0]) - prob_matrix[0, 0]
    btts_yes_prob = 1.0 - btts_no_prob

    return {
        "1X2": {
            "home": home_win_prob,
            "draw": draw_prob,
            "away": away_win_prob
        },
        "Totals": {
            "over_2_5": over_2_5_prob,
            "under_2_5": under_2_5_prob
        },
        "BTTS": {
            "yes": btts_yes_prob,
            "no": btts_no_prob
        }
    }

def probs_to_fair_odds(probs: dict) -> dict:
    """
    Converts a dictionary of probabilities to fair decimal odds (1 / P).
    """
    fair_odds = {}
    for market, outcomes in probs.items():
        fair_odds[market] = {}
        for outcome, prob in outcomes.items():
            if prob > 0:
                fair_odds[market][outcome] = 1.0 / prob
            else:
                fair_odds[market][outcome] = 999.0 # Max cap to avoid div by zero
    
    return fair_odds

def calculate_fair_odds(home_xg: float, away_xg: float) -> dict:
    """
    Main entrypoint: takes xG and returns Fair Odds using Poisson.
    """
    probs = calc_match_probabilities(home_xg, away_xg)
    return probs_to_fair_odds(probs)
