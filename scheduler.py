import os
import logging
from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from database import init_db
from main import (
    populate_upcoming_matches,
    evaluate_t_minus_6,
    check_lineups_t_minus_1,
    settle_finished_matches,
    get_db_connection
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
EST = pytz.timezone('America/New_York')

def schedule_daily_matches():
    """
    Fetches matches for the day and dynamically schedules the 3 jobs
    (Pre-scan, Lineup check, Result logger) per match.
    """
    logging.info("Starting Daily Match Scheduling (EST)")
    
    # 1. Update the database with the latest upcoming fixtures
    populate_upcoming_matches()
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get today's start and end in UTC (since DB stores UTC)
    now_est = datetime.now(EST)
    today_start_est = now_est.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end_est = today_start_est + timedelta(days=1)
    
    today_start_utc = today_start_est.astimezone(pytz.UTC)
    today_end_utc = today_end_est.astimezone(pytz.UTC)
    
    c.execute(
        "SELECT id, home_team, away_team, kickoff, league FROM matches WHERE kickoff > ? AND kickoff < ?",
        (today_start_utc.isoformat(), today_end_utc.isoformat())
    )
    matches_today = c.fetchall()
    conn.close()
    
    if not matches_today:
        logging.info("No matches found for today.")
        return
        
    logging.info(f"Found {len(matches_today)} matches today. Building dynamic schedule...")
    
    scheduler = BlockingScheduler(timezone=EST)
    
    for match in matches_today:
        try:
            # Parse DB UTC time to EST datetime object
            # format looks like: 2026-03-01T15:00:00Z
            kickoff_utc = datetime.fromisoformat(match['kickoff'].replace("Z", "+00:00"))
            kickoff_est = kickoff_utc.astimezone(EST)
            
            match_name = f"{match['home_team']} vs {match['away_team']}"
            match_id = match['id']
            
            # --- T-6 Hours: Pre-scan ---
            scan_time = kickoff_est - timedelta(hours=6)
            if scan_time > now_est:
                job_id = f"prescan_{match_id}"
                scheduler.add_job(
                    func=evaluate_t_minus_6, # We will modify main.py slightly to accept match_id
                    trigger='date',
                    run_date=scan_time,
                    args=[match_id],
                    id=job_id,
                    replace_existing=True
                )
                logging.info(f"Scheduled Pre-Scan for {match_name} at {scan_time.strftime('%I:%M %p %Z')}")
            else:
                logging.info(f"Skipping Pre-Scan for {match_name} (Time {scan_time.strftime('%I:%M %p')} is in the past)")
                
            # --- T-1 Hour: Lineup Check ---
            lineup_time = kickoff_est - timedelta(hours=1)
            if lineup_time > now_est:
                job_id = f"lineup_{match_id}"
                scheduler.add_job(
                    func=check_lineups_t_minus_1,
                    trigger='date',
                    run_date=lineup_time,
                    args=[match_id],
                    id=job_id,
                    replace_existing=True
                )
                logging.info(f"Scheduled Lineup Check for {match_name} at {lineup_time.strftime('%I:%M %p %Z')}")
            else:
                logging.info(f"Skipping Lineup Check for {match_name} (Time {lineup_time.strftime('%I:%M %p')} is in the past)")
                
            # --- Post-Match: Result Logger (T+2 Hours 15 Mins) ---
            result_time = kickoff_est + timedelta(hours=2, minutes=15)
            if result_time > now_est:
                job_id = f"result_{match_id}"
                scheduler.add_job(
                    func=settle_finished_matches,
                    trigger='date',
                    run_date=result_time,
                    args=[match_id],
                    id=job_id,
                    replace_existing=True
                )
                logging.info(f"Scheduled Result Logger for {match_name} at {result_time.strftime('%I:%M %p %Z')}")
            else:
                logging.info(f"Skipping Result Logger for {match_name} (Time {result_time.strftime('%I:%M %p')} is in the past)")
                
        except Exception as e:
            logging.error(f"Failed to schedule jobs for {match['home_team']}: {e}")
            
    # Check if we actually added any future jobs before blocking
    if scheduler.get_jobs():
        logging.info("Staring BlockingScheduler. Waiting for jobs to execute...")
        scheduler.start()
    else:
        logging.info("All dynamic jobs for today are in the past. Exiting script gracefully.")


if __name__ == "__main__":
    init_db()
    schedule_daily_matches()
