import os
import json
import logging
import datetime
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger('10cric_bet_tracker')

class BetTracker:
    """
    Tracks successful bets and prevents duplicate bet placement.
    """
    def __init__(self, bet_history_file="successful_bets.json"):
        """
        Initialize the bet tracker.
        
        Args:
            bet_history_file: Path to the file storing bet history
        """
        self.bet_history_file = bet_history_file
        self.bet_history = self._load_bet_history()
        
    def _load_bet_history(self) -> List[Dict[str, Any]]:
        """
        Load bet history from file.
        
        Returns:
            List of bet records
        """
        try:
            if os.path.exists(self.bet_history_file):
                with open(self.bet_history_file, "r") as f:
                    return json.load(f)
            else:
                logger.info(f"No existing bet history file found at {self.bet_history_file}. Creating new history.")
                return []
        except Exception as e:
            logger.error(f"Error loading bet history: {e}")
            return []
    
    def _save_bet_history(self):
        """Save bet history to file."""
        try:
            with open(self.bet_history_file, "w") as f:
                json.dump(self.bet_history, f, indent=2)
            logger.info(f"Bet history saved to {self.bet_history_file}")
        except Exception as e:
            logger.error(f"Error saving bet history: {e}")
    
    def is_duplicate_bet(self, event_id: str, market_id: str, selection_id: str, hours_window: int = 24) -> bool:
        """
        Check if a bet is a duplicate within the specified time window.
        
        Args:
            event_id: ID of the event
            market_id: ID of the market
            selection_id: ID of the selection
            hours_window: Time window in hours to consider for duplicates
            
        Returns:
            True if the bet is a duplicate, False otherwise
        """
        current_time = datetime.datetime.now()
        time_threshold = current_time - datetime.timedelta(hours=hours_window)
        
        # Convert threshold to string format for comparison
        time_threshold_str = time_threshold.isoformat()
        
        for bet in self.bet_history:
            # Check if this bet matches our criteria for a duplicate
            if (bet["event_id"] == event_id and 
                bet["market_id"] == market_id and 
                bet["selection_id"] == selection_id and
                bet["timestamp"] > time_threshold_str):
                
                logger.info(f"Duplicate bet found: Event ID {event_id}, Market ID {market_id}, Selection {selection_id}")
                logger.info(f"Previous bet was placed at {bet['timestamp']}")
                return True
                
        return False
    
    def record_successful_bet(self, 
                             bet_id: str,
                             event_id: str, 
                             match_name: str,
                             market_id: str, 
                             market_name: str,
                             market_line_id: str,
                             selection_id: str, 
                             selection_name: str,
                             odds: float,
                             stake: float) -> Dict[str, Any]:
        """
        Record a successful bet placement.
        
        Args:
            bet_id: ID of the placed bet
            event_id: ID of the event
            match_name: Name of the match
            market_id: ID of the market
            market_name: Name of the market
            market_line_id: ID of the market line
            selection_id: ID of the selection
            selection_name: Name of the selection
            odds: Odds of the selection
            stake: Stake amount
            
        Returns:
            The recorded bet entry
        """
        # Create bet record
        bet_record = {
            "bet_id": bet_id,
            "event_id": event_id,
            "match_name": match_name,
            "market_id": market_id,
            "market_name": market_name,
            "market_line_id": market_line_id,
            "selection_id": selection_id,
            "selection_name": selection_name,
            "odds": odds,
            "stake": stake,
            "potential_return": round(stake * odds, 2),
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "placed"
        }
        
        # Add to history
        self.bet_history.append(bet_record)
        
        # Save updated history
        self._save_bet_history()
        
        logger.info(f"Recorded successful bet: {bet_id} on {match_name} - {market_name} - {selection_name}")
        return bet_record
    
    def get_bet_history(self, hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get bet history, optionally filtered by time window.
        
        Args:
            hours: Optional time window in hours
            
        Returns:
            List of bet records
        """
        if hours is None:
            return self.bet_history
            
        time_threshold = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
        return [bet for bet in self.bet_history if bet["timestamp"] > time_threshold]
    
    def get_bet_summary(self) -> Dict[str, Any]:
        """
        Get a summary of betting activity.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.bet_history:
            return {
                "total_bets": 0,
                "total_stake": 0,
                "potential_return": 0
            }
            
        total_bets = len(self.bet_history)
        total_stake = sum(bet["stake"] for bet in self.bet_history)
        potential_return = sum(bet["potential_return"] for bet in self.bet_history)
        
        # Group by status
        status_counts = {}
        for bet in self.bet_history:
            status = bet.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
        # Get recent bets (last 24 hours)
        last_24h = self.get_bet_history(hours=24)
        recent_count = len(last_24h)
        recent_stake = sum(bet["stake"] for bet in last_24h)
        
        return {
            "total_bets": total_bets,
            "total_stake": total_stake,
            "potential_return": potential_return,
            "status_counts": status_counts,
            "recent_bets": {
                "count": recent_count,
                "stake": recent_stake
            }
        }
        
    def update_bet_status(self, bet_id: str, new_status: str) -> bool:
        """
        Update the status of a bet.
        
        Args:
            bet_id: ID of the bet to update
            new_status: New status value
            
        Returns:
            True if the update was successful, False otherwise
        """
        for bet in self.bet_history:
            if bet["bet_id"] == bet_id:
                bet["status"] = new_status
                bet["status_updated"] = datetime.datetime.now().isoformat()
                self._save_bet_history()
                logger.info(f"Updated bet {bet_id} status to {new_status}")
                return True
                
        logger.warning(f"Bet ID {bet_id} not found in history")
        return False 