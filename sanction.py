import json
import os
import logging
import re
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('10cric_sanction')

class BettingSanctionManager:
    """Manages sanctioned betting criteria and matches them against available markets."""
    
    def __init__(self, sanction_file="sanctioned_bets.json"):
        """Initialize with a file containing sanctioned bet definitions."""
        self.sanction_file = sanction_file
        self.sanctioned_bets = self._load_sanctioned_bets()
        
    def _load_sanctioned_bets(self) -> Dict[str, Any]:
        """Load sanctioned bets from JSON file."""
        try:
            if os.path.exists(self.sanction_file):
                with open(self.sanction_file, "r") as f:
                    return json.load(f)
            else:
                # Create default sanction file if it doesn't exist
                default_sanctions = {
                    "settings": {
                        "first_overs_range": [1, 2, 3, 4, 5, 6],
                        "last_overs_range": [17, 18, 19, 20],
                        "stake": 100,
                        "active": True
                    },
                    "selected_bets": []  # This will store the selected bets from each run
                }
                
                with open(self.sanction_file, "w") as f:
                    json.dump(default_sanctions, f, indent=2)
                
                return default_sanctions
        except Exception as e:
            logger.error(f"Error loading sanctioned bets: {e}")
            return {"settings": {"first_overs_range": [1, 2, 3, 4, 5, 6], "last_overs_range": [17, 18, 19, 20], "stake": 100, "active": True}, "selected_bets": []}
    
    def _extract_innings_details(self, market_name: str) -> Dict[str, Any]:
        """
        Extract innings number, over number, and team name from market name.
        Only matches full over markets, not per-ball markets.
        
        Args:
            market_name: Name of the market, e.g., "1st innings over 2 - Chennai Super Kings total"
            
        Returns:
            Dictionary with innings, over, and team details
        """
        # Skip per-ball markets (contains "delivery" in the name)
        if "delivery" in market_name.lower():
            return {
                "innings": None,
                "over": None,
                "team": None,
                "valid": False
            }
            
        # Skip over ranges (contains "overs x to y" in the name)
        if re.search(r'overs \d+ to \d+', market_name.lower()):
            return {
                "innings": None,
                "over": None,
                "team": None,
                "valid": False
            }
        
        # Standard pattern matching for single over markets
        innings_match = re.search(r'(\d+)(?:st|nd|rd|th) innings', market_name)
        over_match = re.search(r'over (\d+)', market_name)
        team_match = re.search(r'- (.+?) total', market_name)
        
        # Ensure this is a full over market (matches pattern exactly)
        is_valid_format = bool(
            innings_match and over_match and team_match and
            f"{innings_match.group(0)} over {over_match.group(1)} - {team_match.group(1)} total" in market_name
        )
        
        return {
            "innings": int(innings_match.group(1)) if innings_match else None,
            "over": int(over_match.group(1)) if over_match else None,
            "team": team_match.group(1) if team_match else None,
            "valid": is_valid_format
        }
    
    def find_sanctioned_bets(self, available_markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find matches between available markets and sanctioned bets.
        Only considers full over markets (not per-ball or over ranges).
        
        Args:
            available_markets: List of available market data from the API
            
        Returns:
            List of matched markets with betting details
        """
        settings = self.sanctioned_bets.get("settings", {})
        first_overs_range = settings.get("first_overs_range", [1, 2, 3, 4, 5, 6])
        last_overs_range = settings.get("last_overs_range", [17, 18, 19, 20])
        default_stake = settings.get("stake", 100)
        is_active = settings.get("active", True)
        
        if not is_active:
            logger.info("Betting sanctions are currently inactive")
            return []
        
        # Log the number of markets we're checking
        logger.info(f"Checking {len(available_markets)} markets for sanctioned bets")
        
        # Group markets by innings, over, and team
        grouped_markets = {}
        skipped_markets = 0
        considered_markets = 0
        
        for market in available_markets:
            # Get the market name - this could be in market_name or market_line_name
            market_name = market.get("market_name", market.get("market_line_name", ""))
            
            # Skip markets that don't relate to over totals
            if "over" not in market_name.lower() or "total" not in market_name.lower():
                skipped_markets += 1
                continue
                
            # Extract details and check if this is a valid market format
            details = self._extract_innings_details(market_name)
            if not details["valid"]:
                skipped_markets += 1
                continue
                
            # Only consider overs in our specified ranges
            over_num = details["over"]
            if over_num not in first_overs_range and over_num not in last_overs_range:
                skipped_markets += 1
                continue
                
            # Log that we're considering this market
            logger.info(f"Considering market: {market_name}")
            considered_markets += 1
                
            # Create a key for grouping
            key = f"{details['innings']}_{details['over']}_{details['team']}"
            
            if key not in grouped_markets:
                grouped_markets[key] = []
                
            grouped_markets[key].append(market)
        
        # Log the grouped markets we found
        logger.info(f"Found {len(grouped_markets)} grouped markets matching our criteria")
        logger.info(f"Skipped {skipped_markets} markets, considered {considered_markets} markets")
        
        # Find the highest over bet for each group
        selected_bets = []
        
        for key, markets in grouped_markets.items():
            highest_over_value = -1
            selected_market = None
            selected_selection = None
            
            # Process each market in this group
            for market in markets:
                # Get the selections from the market
                for selection in market.get("selections", []):
                    selection_name = selection.get("name", "")
                    
                    if "over" in selection_name.lower():
                        # Extract the numerical value from "Over X.5"
                        value_match = re.search(r'Over (\d+\.?\d*)', selection_name)
                        if value_match:
                            value = float(value_match.group(1))
                            
                            # Keep track of the highest over value
                            if value > highest_over_value:
                                highest_over_value = value
                                selected_market = market
                                selected_selection = selection
                                logger.info(f"New highest over value: {value} for {market.get('market_name')}")
            
            # If we found a valid selection, add it to our list
            if selected_market and selected_selection:
                # Extract the details for easier reference
                details = self._extract_innings_details(selected_market.get("market_name", ""))
                
                bet_info = {
                    "innings": details["innings"],
                    "over": details["over"],
                    "team": details["team"],
                    "selection_name": selected_selection.get("name", ""),
                    "odds": selected_selection.get("odds", 0),
                    "stake": default_stake,
                    "market_id": selected_market.get("market_id", ""),
                    "market_line_id": selected_market.get("market_line_id", ""),
                    "selection_id": selected_selection.get("selection_id", ""),
                    "market_name": selected_market.get("market_name", "")
                }
                
                selected_bets.append(bet_info)
                logger.info(f"Selected bet: {bet_info['market_name']} - {bet_info['selection_name']} @ {bet_info['odds']}")
        
        # Save the selected bets for reference
        if selected_bets:
            self.sanctioned_bets["selected_bets"] = selected_bets
            with open(self.sanction_file, "w") as f:
                json.dump(self.sanctioned_bets, f, indent=2)
                
            logger.info(f"Found and saved {len(selected_bets)} sanctioned bets")
        else:
            logger.info("No sanctioned bets found")
        
        # Format results for the betting system
        formatted_bets = []
        for bet in selected_bets:
            # Format in the structure expected by the betting system
            formatted_bets.append({
                "market": {
                    "market_id": bet["market_id"],
                    "market_name": bet["market_name"],
                    "market_line_id": bet["market_line_id"]
                },
                "selection": {
                    "selection_id": bet["selection_id"],
                    "name": bet["selection_name"],
                    "odds": bet["odds"]
                },
                "stake": bet["stake"],
                "sanction": {
                    "innings": bet["innings"],
                    "over": bet["over"],
                    "team": bet["team"]
                }
            })
        
        return formatted_bets 