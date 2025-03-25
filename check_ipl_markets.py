#!/usr/bin/env python3
import os
import logging
import argparse
from auth import authenticate, refresh_auth_if_needed
from market_monitor import SimpleMarketMonitor

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
    
    args = parser.parse_args()
    
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
    
    # Setup authentication
    if not setup_authentication(force_refresh=args.auth, headless=args.headless):
        return
    
    # Display auto-betting status
    if args.auto_bet:
        logger.info("🎲 Auto-betting is ENABLED - sanctioned bets will be placed automatically")
    else:
        logger.info("Auto-betting is disabled (use --auto-bet to enable)")
    
    # Run the market monitor
    monitor.run(event_id=args.event_id, match_name=args.match_name)
    
    # Show bet history if requested (after checking markets)
    if args.show_history:
        logger.info("\nDisplaying bet history")
        monitor.display_bet_history(hours=args.history_hours)
    
    logger.info("Market check completed")

if __name__ == "__main__":
    main() 