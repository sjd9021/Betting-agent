#!/usr/bin/env python3
import logging
import argparse
from bet_tracker import BetTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('test_bet_tracker')

def add_mock_bets(tracker, count=3):
    """Add some mock bets to test the tracker."""
    logger.info(f"Adding {count} mock bets for testing")
    
    # Some sample event and market data
    events = [
        {
            "id": "3f1afc68-a19f-309b-837a-e32ad565ee9d",
            "name": "Delhi Capitals vs. Lucknow Super Giants"
        },
        {
            "id": "01f9f6e3-b53f-3dcc-966d-12740ee5ae7d",
            "name": "Chennai Super Kings vs. Mumbai Indians"
        }
    ]
    
    markets = [
        {
            "id": "24607457-d105-312a-a9f1-f1c8487c4ac6",
            "name": "1st innings over 1 - Delhi Capitals total",
            "line_id": "market-line-1",
            "selection_id": "181fe4d8-ad0f-3247-b340-2e826d2ab3b9",
            "selection_name": "Over 7.5",
            "odds": 2.15
        },
        {
            "id": "592d8ee0-2fd9-342b-8fd2-30a9e690cfb7",
            "name": "1st innings over 6 - Chennai Super Kings total",
            "line_id": "market-line-2",
            "selection_id": "cf463fba-731f-370e-819b-7535facf115d",
            "selection_name": "Over 10.5",
            "odds": 2.0
        },
        {
            "id": "34607421-c105-318a-a9f1-f1c8487c4bd8",
            "name": "1st innings over 2 - Delhi Capitals total",
            "line_id": "market-line-3",
            "selection_id": "fe341a8b-3b4f-399a-abfb-944ceda8c637",
            "selection_name": "Over 8.5",
            "odds": 1.9
        }
    ]
    
    # Add a few mock bets
    for i in range(min(count, len(markets))):
        event = events[i % len(events)]
        market = markets[i]
        
        bet_id = f"mock-bet-{i+1}"
        stake = 100 * (i + 1)
        
        tracker.record_successful_bet(
            bet_id=bet_id,
            event_id=event["id"],
            match_name=event["name"],
            market_id=market["id"],
            market_name=market["name"],
            market_line_id=market["line_id"],
            selection_id=market["selection_id"],
            selection_name=market["selection_name"],
            odds=market["odds"],
            stake=stake
        )
        
        logger.info(f"Added mock bet {i+1}: {market['name']} - {market['selection_name']} @ {market['odds']}")
    
    return count

def main():
    """Test the bet tracker functionality."""
    parser = argparse.ArgumentParser(description="Bet Tracker Test Utility")
    parser.add_argument("--add-mock", type=int, default=0, help="Add mock bets for testing (specify count)")
    parser.add_argument("--history", action="store_true", help="Show bet history")
    parser.add_argument("--hours", type=int, help="Filter history by hours")
    parser.add_argument("--summary", action="store_true", help="Show betting summary")
    parser.add_argument("--clear", action="store_true", help="Clear all bet history")
    
    args = parser.parse_args()
    
    logger.info("Starting Bet Tracker Test")
    
    tracker = BetTracker()
    
    # Handle clear history option
    if args.clear:
        confirm = input("Are you sure you want to clear all bet history? (y/n): ")
        if confirm.lower() == 'y':
            tracker.bet_history = []
            tracker._save_bet_history()
            logger.info("Bet history cleared")
        else:
            logger.info("Clear operation cancelled")
    
    # Handle add mock bets option
    if args.add_mock > 0:
        added = add_mock_bets(tracker, args.add_mock)
        logger.info(f"Added {added} mock bets to history")
    
    # Handle show history option
    if args.history:
        history = tracker.get_bet_history(hours=args.hours)
        
        if not history:
            logger.info("No betting history found")
        else:
            time_frame = f"last {args.hours} hours" if args.hours else "all time"
            logger.info(f"\n=== Betting History ({time_frame}) ===")
            logger.info(f"Total bets: {len(history)}")
            
            for idx, bet in enumerate(history, 1):
                logger.info(f"{idx}. {bet['match_name']}")
                logger.info(f"   Market: {bet['market_name']}")
                logger.info(f"   Selection: {bet['selection_name']} @ {bet['odds']}")
                logger.info(f"   Stake: {bet['stake']}, Potential Return: {bet['potential_return']}")
                logger.info(f"   Status: {bet['status']}")
                logger.info(f"   Bet ID: {bet['bet_id']}")
                logger.info(f"   Timestamp: {bet['timestamp']}")
                logger.info("   ---")
    
    # Handle show summary option
    if args.summary:
        summary = tracker.get_bet_summary()
        logger.info("\n=== Betting Summary ===")
        logger.info(f"Total bets: {summary['total_bets']}")
        logger.info(f"Total stake: {summary['total_stake']}")
        logger.info(f"Potential return: {summary['potential_return']}")
        
        if 'status_counts' in summary:
            logger.info("\nBet Status:")
            for status, count in summary['status_counts'].items():
                logger.info(f"  {status}: {count}")
        
        if 'recent_bets' in summary:
            logger.info("\nRecent betting (24h):")
            logger.info(f"  Count: {summary['recent_bets']['count']}")
            logger.info(f"  Stake: {summary['recent_bets']['stake']}")
    
    logger.info("Bet Tracker Test Completed")

if __name__ == "__main__":
    main() 