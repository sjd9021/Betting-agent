#!/usr/bin/env python3
import os
import logging
import argparse
from auth import authenticate, refresh_auth_if_needed
from market_monitor import SimpleMarketMonitor
import json
import sys
import time
import random
import datetime
import pytz
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ipl_market_check.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ipl_market_check')

# Constants
DATA_DIR = 'data'
CACHE_DIR = os.path.join(DATA_DIR, 'cache')
MOCK_DIR = 'mock_data'
SANCTIONED_BETS_FILE = os.path.join(DATA_DIR, 'sanctioned_bets.json')
EVENT_IDS_FILE = 'ipl_event_ids.json'
CONFIG_FILE = 'config.json'

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Global variable to store mock time for testing
MOCK_TIME = None

def get_current_ist_time():
    """Get current time in IST timezone."""
    ist_tz = pytz.timezone('Asia/Kolkata')
    
    # Use mock time if set (for testing)
    if MOCK_TIME:
        try:
            # Parse the mock time and convert to IST
            if isinstance(MOCK_TIME, str):
                dt = datetime.datetime.fromisoformat(MOCK_TIME.replace('Z', '+00:00'))
                return dt.astimezone(ist_tz)
        except Exception as e:
            logger.warning(f"Error parsing mock time: {e}, using real time")
    
    # Use real time
    now_ist = datetime.datetime.now(ist_tz)
    return now_ist

def format_ist_time(dt):
    """Format datetime object to IST time string."""
    return dt.strftime('%Y-%m-%d %H:%M:%S %Z')

def setup_authentication(force_refresh=False, headless=False):
    """
    Setup or refresh authentication.
    
    Args:
        force_refresh: Whether to force authentication refresh
        headless: Whether to run the browser in headless mode
    """
    # Use the refresh_auth_if_needed function for better credential management
    credentials = refresh_auth_if_needed(force_refresh=force_refresh, headless=headless)
    
    if not credentials:
        logger.error("Authentication failed")
        return False
        
    logger.info("Authentication successful")
    return True

def main():
    """Main entry point for the IPL market check."""
    parser = argparse.ArgumentParser(description="IPL Market Checker")
    parser.add_argument("--auth", action="store_true", help="Force authentication refresh")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--event-id", help="Specific event ID to check")
    parser.add_argument("--match-name", help="Match name for display purposes")
    parser.add_argument("--auto-bet", action="store_true", help="Automatically place bets on sanctioned markets")
    
    # Add bet history options
    parser.add_argument("--show-history", action="store_true", help="Display bet history")
    parser.add_argument("--history-hours", type=int, help="Filter history by hours (e.g., 24 for last day)")
    
    # Add new flags for automated scheduler
    parser.add_argument("--discover-only", action="store_true", help="Only discover matches, don't check markets or place bets")
    parser.add_argument("--prefetch-only", action="store_true", help="Only prefetch markets, don't place bets")
    parser.add_argument("--use-mock", action="store_true", help="Use mock data for testing")
    parser.add_argument("--mock-time", help="Mock time for testing (format: YYYY-MM-DDTHH:MM:SS)")
    
    args = parser.parse_args()
    
    # Set mock time if provided
    global MOCK_TIME
    if args.mock_time:
        MOCK_TIME = args.mock_time
        logger.info(f"Using mock time: {MOCK_TIME}")
    
    # Force use mock data if specified
    if args.use_mock:
        config = load_config()
        config["use_mock_data"] = True
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Forced use of mock data")
    
    logger.info("Starting IPL Market Checker")
    
    # Create market monitor instance
    monitor = SimpleMarketMonitor(auto_betting=args.auto_bet)
    
    # Always show a brief betting summary at startup
    bet_summary = monitor.bet_tracker.get_bet_summary()
    logger.info("\n=== Betting Summary ===")
    logger.info(f"Total bets placed: {bet_summary['total_bets']}")
    logger.info(f"Total stake: {bet_summary['total_stake']}")
    logger.info(f"Recent bets (24h): {bet_summary['recent_bets']['count']}")
    
    # If just showing history, no need for authentication
    if args.show_history and not args.event_id:
        logger.info("Displaying bet history")
        monitor.display_bet_history(hours=args.history_hours)
        return
    
    # Discovery mode - just find matches and exit
    if args.discover_only:
        logger.info("Running in discover-only mode")
        from cricket import get_upcoming_ipl_matches
        matches = get_upcoming_ipl_matches()
        
        if matches:
            logger.info(f"Found {len(matches)} IPL matches")
            for idx, match in enumerate(matches, 1):
                logger.info(f"{idx}. {match.get('name')} (ID: {match.get('id')})")
            return
        else:
            logger.warning("No IPL matches found")
            return
    
    # Setup authentication
    if not setup_authentication(force_refresh=args.auth, headless=args.headless):
        return
    
    # Display auto-betting status
    if args.auto_bet:
        logger.info("🎲 Auto-betting is ENABLED - sanctioned bets will be placed automatically")
    else:
        logger.info("Auto-betting is disabled (use --auto-bet to enable)")
    
    # Prefetch mode - just get market data and exit (no betting)
    if args.prefetch_only and args.event_id:
        logger.info(f"Running in prefetch-only mode for event {args.event_id}")
        monitor.check_markets(args.event_id, args.match_name, prefetch_only=True)
        return
    
    # Run the market monitor
    monitor.run(event_id=args.event_id, match_name=args.match_name)
    
    # Show bet history if requested (after checking markets)
    if args.show_history:
        logger.info("\nDisplaying bet history")
        monitor.display_bet_history(hours=args.history_hours)
    
    logger.info("Market check completed")

if __name__ == "__main__":
    main() 