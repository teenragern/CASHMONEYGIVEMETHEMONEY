import datetime
import logging
from database import get_db_connection

# Define Daily limits map
LIMITS = {
    "api_football": 100,  # Strict free tier
    "football_data": 500, # Varies by tier, safe at 500
    "odds_api": 500       # $30 tier gives ~30k calls/mo -> ~1000/day. Safe limit 500.
}

def can_make_request(service_name: str) -> bool:
    """
    Checks if a request can be made based on daily API limits via SQLite tracking.
    """
    if service_name not in LIMITS:
        return True # Non-tracked service
        
    today = datetime.date.today().isoformat()
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Ensure a record for today exists
        c.execute(
            "INSERT OR IGNORE INTO api_usage (service, call_date, call_count) VALUES (?, ?, ?)",
            (service_name, today, 0)
        )
        
        c.execute(
            "SELECT call_count FROM api_usage WHERE service = ? AND call_date = ?",
            (service_name, today)
        )
        result = c.fetchone()
        current_calls = result['call_count'] if result else 0
        
        conn.commit()
    except Exception as e:
        logging.error(f"Database error in can_make_request ({service_name}): {e}")
        current_calls = 0 # Default to allowing request if DB fails temporarily
    finally:
        if 'conn' in locals() and conn:
            conn.close()

    if current_calls >= LIMITS[service_name]:
        logging.warning(f"RATE LIMIT REACHED for {service_name}. {current_calls}/{LIMITS[service_name]} calls made today.")
        return False
        
    return True

def record_api_call(service_name: str):
    """
    Increments the daily call counter for a given service.
    Should be called *after* a successful (or rate-limit triggering) API request.
    """
    if service_name not in LIMITS:
        return
        
    today = datetime.date.today().isoformat()
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute(
            "UPDATE api_usage SET call_count = call_count + 1 WHERE service = ? AND call_date = ?",
            (service_name, today)
        )
        
        conn.commit()
    except Exception as e:
        logging.error(f"Database error in record_api_call ({service_name}): {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_remaining_calls(service_name: str) -> int:
    """Helper to check remaining calls."""
    if service_name not in LIMITS:
        return -1
        
    today = datetime.date.today().isoformat()
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute(
        "SELECT call_count FROM api_usage WHERE service = ? AND call_date = ?",
        (service_name, today)
    )
    result = c.fetchone()
    current_calls = result['call_count'] if result else 0
    conn.close()
    
    return max(0, LIMITS[service_name] - current_calls)

