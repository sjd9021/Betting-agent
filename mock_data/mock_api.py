#!/usr/bin/env python3
import os
import json
import logging
import random
import argparse
import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('mock_10cric_api')

class Mock10CricAPI:
    """
    Mock API for 10CRIC to facilitate testing of the betting system.
    """
    def __init__(self, data_dir="mock_data"):
        """
        Initialize the mock API.
        
        Args:
            data_dir: Directory containing mock data files
        """
        self.data_dir = Path(data_dir)
        self.load_mock_data()
    
    def load_mock_data(self):
        """Load all mock data files."""
        try:
            # Load match events
            with open(self.data_dir / "match_events.json", "r") as f:
                self.match_events = json.load(f)
            
            # Load markets data
            with open(self.data_dir / "markets_data.json", "r") as f:
                self.markets_data = json.load(f)
            
            # Load sanctioned bets
            with open(self.data_dir / "sanctioned_bets.json", "r") as f:
                self.sanctioned_bets = json.load(f)
            
            # Load successful bets
            with open(self.data_dir / "successful_bets.json", "r") as f:
                self.successful_bets = json.load(f)
                
            # Load bet placement responses
            with open(self.data_dir / "bet_placement_response.json", "r") as f:
                self.bet_responses = json.load(f)
                
            logger.info("Successfully loaded all mock data")
        except Exception as e:
            logger.error(f"Error loading mock data: {e}")
            raise
    
    def get_upcoming_matches(self):
        """
        Get a list of upcoming matches.
        
        Returns:
            List of match data
        """
        logger.info("Getting upcoming matches")
        return self.match_events["data"]["listWidgetEvents"]["events"]
    
    def get_markets_for_event(self, event_id):
        """
        Get markets for a specific event.
        
        Args:
            event_id: ID of the event
            
        Returns:
            Market data for the event
        """
        logger.info(f"Getting markets for event: {event_id}")
        
        # Check if the event_id matches our mock data
        if self.markets_data["data"]["lazyEvent"]["sportEvent"]["id"] == event_id:
            return {
                "event_data": self.markets_data["data"]["lazyEvent"]["sportEvent"]
            }
        else:
            # For other event IDs, return an error or empty data
            return {
                "error": "No markets found for this event",
                "event_data": None
            }
    
    def place_bet(self, selection_id, event_id, market_id, market_line_id, stake, odds):
        """
        Place a bet.
        
        Args:
            selection_id: ID of the selection
            event_id: ID of the event
            market_id: ID of the market
            market_line_id: ID of the market line
            stake: Bet stake amount
            odds: Bet odds
            
        Returns:
            Response containing the result of the bet placement
        """
        logger.info(f"Placing bet on selection {selection_id} for event {event_id}")
        
        # Randomly decide whether the bet is successful or not
        if random.random() < 0.8:  # 80% success rate
            success_resp = self.bet_responses["success_response"]
            
            # Generate a new bet ID
            bet_id = f"10cric-bet-{random.randint(100000, 999999)}"
            success_resp["bet_id"] = bet_id
            
            # Update details
            success_resp["details"]["event_id"] = event_id
            success_resp["details"]["market_id"] = market_id
            success_resp["details"]["selection_id"] = selection_id
            success_resp["details"]["stake"] = stake
            success_resp["details"]["odds"] = odds
            success_resp["details"]["potential_return"] = round(stake * odds, 2)
            success_resp["details"]["timestamp"] = datetime.datetime.now().isoformat()
            
            logger.info(f"Bet placed successfully. Bet ID: {bet_id}")
            return success_resp
        else:
            # Return a random error response
            error_resp = random.choice(self.bet_responses["error_responses"])
            logger.warning(f"Bet placement failed: {error_resp['error']}")
            return error_resp
    
    def get_sanctioned_bets(self):
        """
        Get the list of sanctioned bets.
        
        Returns:
            Sanctioned bets configuration and selections
        """
        logger.info("Getting sanctioned bets")
        return self.sanctioned_bets
    
    def get_bet_history(self):
        """
        Get the history of placed bets.
        
        Returns:
            List of placed bets
        """
        logger.info("Getting bet history")
        return self.successful_bets

def main():
    """Main function to run the mock API for testing."""
    parser = argparse.ArgumentParser(description="10CRIC Mock API for Testing")
    parser.add_argument("--list-matches", action="store_true", help="List upcoming matches")
    parser.add_argument("--show-markets", help="Show markets for a specific event ID")
    parser.add_argument("--show-sanctioned", action="store_true", help="Show sanctioned bets")
    parser.add_argument("--show-history", action="store_true", help="Show bet history")
    parser.add_argument("--simulate-bet", action="store_true", help="Simulate placing a bet")
    
    args = parser.parse_args()
    
    # Initialize mock API
    api = Mock10CricAPI()
    
    if args.list_matches:
        matches = api.get_upcoming_matches()
        print(json.dumps(matches, indent=2))
    
    if args.show_markets:
        markets = api.get_markets_for_event(args.show_markets)
        print(json.dumps(markets, indent=2))
    
    if args.show_sanctioned:
        sanctioned = api.get_sanctioned_bets()
        print(json.dumps(sanctioned, indent=2))
    
    if args.show_history:
        history = api.get_bet_history()
        print(json.dumps(history, indent=2))
    
    if args.simulate_bet:
        # Use sample data for simulation
        event_id = "cf27dbc5-2269-334f-993f-694ded1c64d3"
        market_id = "592d8ee0-2fd9-342b-8fd2-30a9e690cfb7"
        market_line_id = "a21928ef-8d62-30c0-b2aa-8840a659de0e"
        selection_id = "2f41d627-55ab-394b-8b58-8a13c150a72d"
        
        result = api.place_bet(
            selection_id=selection_id,
            event_id=event_id,
            market_id=market_id,
            market_line_id=market_line_id,
            stake=100,
            odds=2.25
        )
        
        print(json.dumps(result, indent=2))
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()

if __name__ == "__main__":
    main() 