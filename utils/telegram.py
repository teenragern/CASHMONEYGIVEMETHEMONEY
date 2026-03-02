import os
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str, parse_mode: str = "HTML") -> bool:
    """
    Sends a message to the configured Telegram chat.
    
    Args:
        message (str): The message text to send.
        parse_mode (str): Formatting mode, 'HTML' or 'MarkdownV2'. defaults to 'HTML'.
        
    Returns:
        bool: True if message sent successfully, False otherwise.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("Telegram credentials missing in environment variables.")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send Telegram message: {e}")
        return False

def send_bet_alert(match_info: dict, fair_odds: float, best_odds: float, edge: float, kelly_stake: float, confidence: str):
    """
    Formats and sends a BET alert.
    """
    message = (
        f"🚨 <b>BET ALERT</b> 🚨\n\n"
        f"⚽ <b>{match_info['home_team']} vs {match_info['away_team']}</b>\n"
        f"🏆 {match_info['league']}\n"
        f"⏰ {match_info['kickoff']}\n\n"
        f"🎯 <b>Market:</b> {match_info['market']}\n"
        f"📈 <b>Selection:</b> {match_info['selection']}\n"
        f"📊 <b>Our Fair Odds:</b> {fair_odds:.2f}\n"
        f"💰 <b>Best Available Odds (Pinnacle):</b> {best_odds:.2f}\n\n"
        f"🔥 <b>Edge:</b> {edge:.1f}%\n"
        f"💵 <b>Recommended Stake:</b> {kelly_stake:.2f}% (Kelly)\n"
        f"🧠 <b>Confidence:</b> {confidence}"
    )
    return send_telegram_message(message)

def send_pass_alert(match_info: dict, reason: str):
    """
    Formats and sends a PASS alert for logging/monitoring.
    Can be disabled later if it becomes too spammy.
    """
    message = (
        f"⏭️ <b>PASS</b>\n"
        f"⚽ {match_info['home_team']} vs {match_info['away_team']}\n"
        f"🎯 Market: {match_info['market']}\n"
        f"ℹ️ Reason: {reason}"
    )
    return send_telegram_message(message)
