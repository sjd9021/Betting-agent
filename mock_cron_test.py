#!/usr/bin/env python3

import os
import json
import shutil
import logging
import subprocess
import datetime
import pytz
import argparse
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/mock_cron_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('mock_cron_test')

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
CACHE_DIR = os.path.join(DATA_DIR, 'cache')
MOCK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mock_data')
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def setup_mock_environment():
    """Set up the mock environment for testing."""
    logger.info("Setting up mock environment")
    
    # Copy mock schedule to cache
    mock_schedule_path = os.path.join(MOCK_DIR, 'mock_schedule.json')
    cache_schedule_path = os.path.join(CACHE_DIR, 'schedule.json')
    
    if os.path.exists(mock_schedule_path):
        shutil.copy(mock_schedule_path, cache_schedule_path)
        logger.info(f"Copied mock schedule to {cache_schedule_path}")
    else:
        logger.warning(f"Mock schedule not found at {mock_schedule_path}")
    
    # Create mock market caches for each event in the schedule
    try:
        with open(mock_schedule_path, 'r') as f:
            schedule = json.load(f)
        
        # Mock markets data source
        mock_markets_path = os.path.join(MOCK_DIR, 'markets_data.json')
        if os.path.exists(mock_markets_path):
            with open(mock_markets_path, 'r') as f:
                markets_data = json.load(f)
        else:
            logger.warning(f"Mock markets data not found at {mock_markets_path}")
            markets_data = {"markets": []}
        
        # Create event_ids file
        event_ids = {}
        
        for match in schedule:
            event_id = match.get('event_id')
            match_name = match.get('match_name')
            
            if event_id and match_name:
                # Create market cache for this event
                cache_market_path = os.path.join(CACHE_DIR, f"markets_{event_id}_cache.json")
                with open(cache_market_path, 'w') as f:
                    json.dump(markets_data, f, indent=2)
                
                logger.info(f"Created mock market cache for event {event_id}")
                
                # Add to event_ids
                event_ids[match_name] = event_id
                
                # Add reverse order for match name (for flexible matching)
                teams = match_name.split(' vs ')
                if len(teams) == 2:
                    reverse_name = f"{teams[1]} vs {teams[0]}"
                    event_ids[reverse_name] = event_id
        
        # Save event_ids
        event_ids_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ipl_event_ids.json')
        with open(event_ids_path, 'w') as f:
            json.dump(event_ids, f, indent=2)
        
        logger.info(f"Created ipl_event_ids.json with {len(event_ids)} entries")
    
    except Exception as e:
        logger.error(f"Error setting up mock environment: {e}")
        import traceback
        logger.error(traceback.format_exc())

def simulate_datetime(time_str):
    """Convert time string to datetime object."""
    return datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))

def run_cron_job(job_type, simulated_time):
    """Run the specified cron job with simulated time."""
    logger.info(f"Running {job_type} job at simulated time: {simulated_time}")
    
    if job_type == 'prefetch':
        cmd = ["./ipl_scheduler.py", "--prefetch", "--mock-time", simulated_time]
        logger.info(f"Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Error running prefetch job: {result.stderr}")
            else:
                logger.info(f"Prefetch job completed successfully")
                logger.info(f"Output: {result.stdout}")
                
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error executing prefetch command: {e}")
            return False
            
    elif job_type == 'bet':
        cmd = ["./ipl_scheduler.py", "--bet", "--mock-time", simulated_time]
        logger.info(f"Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Error running betting job: {result.stderr}")
            else:
                logger.info(f"Betting job completed successfully")
                logger.info(f"Output: {result.stdout}")
                
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error executing betting command: {e}")
            return False
    
    else:
        logger.error(f"Unknown job type: {job_type}")
        return False

def test_weekday_schedule():
    """Test the weekday cron schedule."""
    logger.info("Testing weekday schedule")
    
    # Set up the test date (a Wednesday)
    test_date = "2025-03-25"
    
    # Prefetch job at 17:00 IST (5:00 PM)
    prefetch_time = f"{test_date}T17:00:00"
    run_cron_job('prefetch', prefetch_time)
    
    # Betting jobs during the match (19:30 to 22:30)
    betting_times = [
        f"{test_date}T19:30:00",  # Match start
        f"{test_date}T20:00:00",  # 30 minutes in
        f"{test_date}T20:30:00",  # 1 hour in
        f"{test_date}T21:00:00",  # 1.5 hours in
        f"{test_date}T21:30:00",  # 2 hours in
        f"{test_date}T22:00:00",  # 2.5 hours in
        f"{test_date}T22:30:00"   # 3 hours in
    ]
    
    for time_str in betting_times:
        run_cron_job('bet', time_str)
    
    logger.info("Weekday test completed")

def test_weekend_schedule():
    """Test the weekend cron schedule."""
    logger.info("Testing weekend schedule")
    
    # Set up the test date (a Saturday)
    test_date = "2025-03-29"
    
    # First match
    
    # Prefetch job at 13:00 IST (1:00 PM)
    prefetch_time_1 = f"{test_date}T13:00:00"
    run_cron_job('prefetch', prefetch_time_1)
    
    # Betting jobs during the first match (15:30 to 18:30)
    betting_times_1 = [
        f"{test_date}T15:30:00",  # Match start
        f"{test_date}T16:00:00",  # 30 minutes in
        f"{test_date}T16:30:00",  # 1 hour in
        f"{test_date}T17:00:00",  # 1.5 hours in
        f"{test_date}T17:30:00",  # 2 hours in
        f"{test_date}T18:00:00",  # 2.5 hours in
        f"{test_date}T18:30:00"   # 3 hours in
    ]
    
    for time_str in betting_times_1:
        run_cron_job('bet', time_str)
    
    # Second match
    
    # Prefetch job at 17:00 IST (5:00 PM)
    prefetch_time_2 = f"{test_date}T17:00:00"
    run_cron_job('prefetch', prefetch_time_2)
    
    # Betting jobs during the second match (19:30 to 22:30)
    betting_times_2 = [
        f"{test_date}T19:30:00",  # Match start
        f"{test_date}T20:00:00",  # 30 minutes in
        f"{test_date}T20:30:00",  # 1 hour in
        f"{test_date}T21:00:00",  # 1.5 hours in
        f"{test_date}T21:30:00",  # 2 hours in
        f"{test_date}T22:00:00",  # 2.5 hours in
        f"{test_date}T22:30:00"   # 3 hours in
    ]
    
    for time_str in betting_times_2:
        run_cron_job('bet', time_str)
    
    logger.info("Weekend test completed")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Mock Cron Test")
    parser.add_argument("--weekday", action="store_true", help="Test weekday schedule")
    parser.add_argument("--weekend", action="store_true", help="Test weekend schedule")
    parser.add_argument("--clear-mock", action="store_true", help="Clear mock environment before testing")
    
    args = parser.parse_args()
    
    # Clear mock environment if requested
    if args.clear_mock:
        logger.info("Clearing mock environment")
        
        # Remove cache files
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                logger.info(f"Removed {file_path}")
        
        # Remove event IDs file
        event_ids_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ipl_event_ids.json')
        if os.path.exists(event_ids_path):
            os.remove(event_ids_path)
            logger.info(f"Removed {event_ids_path}")
    
    # Set up mock environment
    setup_mock_environment()
    
    # Run tests
    if args.weekday:
        test_weekday_schedule()
    
    if args.weekend:
        test_weekend_schedule()
    
    if not args.weekday and not args.weekend:
        logger.warning("No test specified. Use --weekday or --weekend")
        print("Error: No test specified. Use --weekday or --weekend")
    
    logger.info("Mock cron test completed")

if __name__ == "__main__":
    main() 