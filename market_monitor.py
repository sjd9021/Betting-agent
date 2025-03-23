import os
import json
import logging
import datetime
from typing import Dict, Any, List, Optional

from cricket import get_upcoming_ipl_matches
from markets import get_markets_for_event, extract_active_markets
from sanction import BettingSanctionManager
from betting import place_bet

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("betting_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('10cric_monitor')

class SimpleMarketMonitor:
    """Simple monitor to check current IPL matches and available markets."""
    
    def __init__(self, auto_betting=False):
        """
        Initialize the market monitor.
        
        Args:
            auto_betting: Whether to automatically place bets on sanctioned markets
        """
        self.sanction_manager = BettingSanctionManager()
        self.auto_betting = auto_betting
        
    def find_current_match(self):
        """Find the current ongoing IPL match."""
        try:
            matches = get_upcoming_ipl_matches()
            
            if not matches:
                logger.info("No upcoming IPL matches found")
                return None
            
            # Display all matches with start times
            logger.info("Available IPL matches:")
            for idx, match in enumerate(matches, 1):
                start_time_str = match.get("startEventDate", "Unknown")
                name = match.get("name", "Unknown match")
                logger.info(f"{idx}. {name} - Start: {start_time_str}")
                
            # Find matches that are happening now
            now = datetime.datetime.now()
            current_matches = []
            
            for match in matches:
                start_time_str = match.get("startEventDate")
                if not start_time_str:
                    continue
                    
                # Parse the start time
                try:
                    start_time = datetime.datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    
                    # Check if match has started (within last 4 hours)
                    time_diff = now - start_time
                    if datetime.timedelta(0) <= time_diff <= datetime.timedelta(hours=4):
                        logger.info(f"Found ongoing match: {match.get('name')}")
                        current_matches.append(match)
                except Exception as e:
                    logger.error(f"Error parsing match time: {e}")
            
            if not current_matches:
                logger.info("No ongoing IPL matches found")
                return None
                
            # If multiple matches, ask user to select
            if len(current_matches) > 1:
                logger.info("Multiple ongoing matches found. Please select one:")
                for idx, match in enumerate(current_matches, 1):
                    logger.info(f"{idx}. {match.get('name')}")
                
                selection = input("Enter match number: ")
                try:
                    selected_idx = int(selection) - 1
                    if 0 <= selected_idx < len(current_matches):
                        return current_matches[selected_idx]
                    else:
                        logger.error("Invalid selection")
                        return None
                except ValueError:
                    logger.error("Invalid input")
                    return None
            else:
                return current_matches[0]
            
        except Exception as e:
            logger.error(f"Error finding current match: {e}")
            return None
    
    def check_markets(self, event_id):
        """Check available markets for a given event."""
        try:
            logger.info(f"Checking markets for event: {event_id}")
            
            # Get current markets
            result = get_markets_for_event(event_id)
            
            if "error" in result:
                logger.error(f"Error fetching markets: {result['error']}")
                return
                
            event_data = result.get("event_data")
            if not event_data:
                logger.error("No event data found")
                return
                
            # Extract active markets
            active_markets = extract_active_markets(event_data)
            logger.info(f"Found {len(active_markets)} active markets")
            
            # Categorize markets for better display
            single_over_markets = []
            over_range_markets = []
            per_ball_markets = []
            other_markets = []
            
            for market in active_markets:
                market_name = market.get("market_name", "").lower()
                
                if "over" in market_name and "total" in market_name:
                    if "delivery" in market_name:
                        per_ball_markets.append(market)
                    elif "overs" in market_name and "to" in market_name:
                        over_range_markets.append(market)
                    else:
                        single_over_markets.append(market)
                else:
                    other_markets.append(market)
            
            # Display markets by category
            logger.info("\n=== Single Over Markets (Sanctionable) ===")
            for idx, market in enumerate(single_over_markets, 1):
                market_name = market.get("market_name", "")
                logger.info(f"{idx}. {market_name}")
                for sel in market.get("selections", []):
                    sel_name = sel.get("name", "")
                    sel_odds = sel.get("odds", "")
                    logger.info(f"   - {sel_name} @ {sel_odds}")
            
            logger.info("\n=== Over Range Markets (Not Sanctionable) ===")
            for idx, market in enumerate(over_range_markets, 1):
                market_name = market.get("market_name", "")
                logger.info(f"{idx}. {market_name}")
                
            logger.info("\n=== Per-Ball Markets (Not Sanctionable) ===")
            for idx, market in enumerate(per_ball_markets, 1):
                market_name = market.get("market_name", "")
                logger.info(f"{idx}. {market_name}")
                
            logger.info("\n=== Other Markets ===")
            for idx, market in enumerate(other_markets, 1):
                market_name = market.get("market_name", "")
                logger.info(f"{idx}. {market_name}")
            
            # Categorize over markets for reference 
            first_6_overs = []
            last_overs = []
            other_overs = []
            
            # Group markets by over number for reference
            for market in single_over_markets:
                market_name = market.get("market_name", "").lower()
                import re
                over_match = re.search(r'over (\d+)', market_name)
                if over_match:
                    over_num = int(over_match.group(1))
                    if 1 <= over_num <= 6:
                        first_6_overs.append(market)
                    elif 17 <= over_num <= 20:
                        last_overs.append(market)
                    else:
                        other_overs.append(market)
            
            # Display summary of over markets
            logger.info(f"\n=== Sanctionable Markets Summary ===")
            logger.info(f"Found {len(single_over_markets)} single over markets total")
            logger.info(f"Found {len(first_6_overs)} first 6 overs markets (sanctionable)")
            logger.info(f"Found {len(last_overs)} last overs (17-20) markets (sanctionable)")
            logger.info(f"Found {len(other_overs)} other overs markets (not in target ranges)")
            
            # Find sanctioned bets - passing ALL markets to the sanction manager
            sanctioned_matches = self.sanction_manager.find_sanctioned_bets(active_markets)
            
            if sanctioned_matches:
                logger.info("\n=== Sanctioned Bets Found ===")
                for idx, match in enumerate(sanctioned_matches, 1):
                    selection = match["selection"]
                    market = match["market"]
                    stake = match["stake"]
                    logger.info(f"{idx}. Market: {market.get('market_name')}")
                    logger.info(f"   Selection: {selection.get('name')} @ {selection.get('odds')}")
                    logger.info(f"   Stake: {stake}")
                    logger.info(f"   Details: Market ID: {market.get('market_id')}, Selection ID: {selection.get('selection_id')}")
                    
                    # Auto-bet if enabled
                    if self.auto_betting:
                        logger.info(f"   🎲 Attempting to place bet automatically...")
                        
                        bet_result = place_bet(
                            selection_id=selection.get("selection_id"),
                            event_id=event_data.get("id"),
                            market_id=market.get("market_id"),
                            market_line_id=market.get("market_line_id"),
                            stake=stake,
                            odds=selection.get("odds"),
                            dry_run=False  # Set to False to actually place the bet
                        )
                        
                        if bet_result.get("status") == "success":
                            logger.info(f"   ✅ Bet placed successfully! Bet ID: {bet_result.get('bet_id')}")
                        else:
                            error_msg = bet_result.get("error", "Unknown error")
                            logger.error(f"   ❌ Failed to place bet: {error_msg}")
                            if "details" in bet_result:
                                logger.error(f"   Details: {bet_result['details']}")
            else:
                logger.info("\nNo sanctioned bets found matching current markets")
            
            # Save market data for reference
            os.makedirs("data", exist_ok=True)
            with open(f"data/markets_{event_id}.json", "w") as f:
                json.dump(active_markets, f, indent=2)
                
            logger.info(f"Markets saved to data/markets_{event_id}.json")
            
            return active_markets
            
        except Exception as e:
            logger.error(f"Error checking markets: {e}")
            return None
    
    def run(self, event_id=None, match_name=None):
        """
        Run the market monitor once.
        
        Args:
            event_id: Optional event ID to check directly
            match_name: Optional match name for display purposes
        """
        try:
            # If event_id is provided, use it directly without calling fetch match APIs
            if event_id:
                logger.info(f"Using provided event ID: {event_id}")
                if match_name:
                    logger.info(f"Match: {match_name}")
                else:
                    logger.info("Match name not provided")
                
                # Check markets for the provided event ID
                active_markets = self.check_markets(event_id)
                
                if not active_markets:
                    logger.info("No active markets found")
                    
                logger.info("Market check complete")
                return
            
            # Otherwise, find current match
            match = self.find_current_match()
            
            if not match:
                logger.info("No match to monitor")
                return
                
            event_id = match.get("id")
            match_name = match.get("name")
            
            logger.info(f"Selected match: {match_name} (ID: {event_id})")
            
            # Check markets
            active_markets = self.check_markets(event_id)
            
            if not active_markets:
                logger.info("No active markets found")
                
            logger.info("Market check complete")
            
        except Exception as e:
            logger.error(f"Error in market monitor: {e}") 