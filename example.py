#!/usr/bin/env python3
"""
10CRIC API Wrapper Example Script

This script demonstrates a complete workflow from authentication to placing a bet.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('10cric_example')

# Load environment variables
load_dotenv()

def main():
    """Run the complete 10CRIC API workflow example."""
    # Step 1: Authenticate with 10CRIC
    logger.info("Step 1: Authenticating with 10CRIC")
    from auth import authenticate
    
    credentials = authenticate(headless=False)  # Set to True to run without browser UI
    if not credentials:
        logger.error("Authentication failed. Check your credentials in .env file.")
        return
    
    logger.info("Authentication successful!")
    
    # Step 2: Get upcoming IPL matches
    logger.info("\nStep 2: Fetching upcoming IPL matches")
    from cricket import get_upcoming_ipl_matches, display_matches
    
    matches = get_upcoming_ipl_matches()
    if not matches:
        logger.error("No upcoming IPL matches found.")
        return
    
    display_matches(matches)
    
    # Step 3: Select a match and get its event ID
    logger.info("\nStep 3: Selecting a match")
    match = matches[0]  # First match in the list
    event_id = match['id']
    match_name = match['name']
    
    logger.info(f"Selected match: {match_name} (ID: {event_id})")
    
    # Step 4: Get available betting markets for the match
    logger.info("\nStep 4: Fetching betting markets for the selected match")
    from markets import get_markets_for_event, extract_active_markets
    
    result = get_markets_for_event(event_id)
    if "error" in result:
        logger.error(f"Error fetching markets: {result['error']}")
        return
    
    event_data = result.get("event_data")
    if not event_data:
        logger.error("No event data found")
        return
    
    active_markets = extract_active_markets(event_data)
    logger.info(f"Found {len(active_markets)} active markets")
    
    # Step 5: Find a specific market (e.g., Match Winner)
    logger.info("\nStep 5: Finding a specific market (Match Winner)")
    from markets import find_market_by_type, find_selection_by_name
    
    market_type = "Match Winner"
    market = find_market_by_type(active_markets, market_type)
    
    if not market:
        logger.error(f"No {market_type} market found for this match")
        return
    
    logger.info(f"Found market: {market.get('market_name')}")
    logger.info("Available selections:")
    
    for idx, selection in enumerate(market.get("selections", []), 1):
        logger.info(f"  {idx}. {selection.get('name')} @ {selection.get('odds')}")
    
    # For this example, let's use the first selection
    selection = market.get("selections", [])[0] if market.get("selections") else None
    
    if not selection:
        logger.error("No selections available for this market")
        return
    
    # Step 6: Place a bet (dry run only)
    logger.info("\nStep 6: Placing a bet (dry run)")
    from betting import place_bet
    
    bet_result = place_bet(
        selection_id=selection.get('selection_id'),
        event_id=event_id,
        market_id=market.get('market_id'),
        market_line_id=market.get('market_line_id'),
        stake=100,  # Betting amount
        odds=float(selection.get('odds')),
        dry_run=True  # Always use dry run for testing!
    )
    
    logger.info(f"Bet placement result: {bet_result.get('status', 'error')}")
    
    # Show bet details
    if bet_result.get('status') == 'dry_run':
        payload = bet_result.get('payload', {})
        bet_details = payload.get('variables', {}).get('payload', {}).get('bet', {})
        
        logger.info("\nBet Details (DRY RUN):")
        logger.info(f"Bet ID: {bet_details.get('id')}")
        logger.info(f"Selection: {selection.get('name')}")
        logger.info(f"Stake: {bet_details.get('stake')}")
        logger.info(f"Odds: {bet_details.get('odds')}")
        logger.info(f"Potential Return: {bet_details.get('potentialReturn')}")
    
    logger.info("\nWorkflow completed successfully!")
    logger.info("Note: This was a dry run. No actual bet was placed.")

if __name__ == "__main__":
    main() 