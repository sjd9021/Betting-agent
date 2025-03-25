#!/usr/bin/env python3

import os
import json
import logging
import datetime
import pytz
import argparse
import subprocess
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ipl_scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ipl_scheduler')

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
CACHE_DIR = os.path.join(DATA_DIR, 'cache')
MATCH_CACHE_FILE = os.path.join(CACHE_DIR, 'current_match.json')
SCHEDULE_FILE = os.path.join(CACHE_DIR, 'schedule.json')

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

def fetch_upcoming_matches():
    """Fetch upcoming IPL matches from the API and cache them."""
    logger.info("Fetching upcoming IPL matches")
    
    try:
        # Run the check_ipl_markets.py script with the --discover-only flag to just fetch matches
        cmd = ["./check_ipl_markets.py", "--discover-only"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Error running match discovery: {result.stderr}")
            return False
            
        logger.info("Successfully ran match discovery")
        
        # Check if matches were found and stored
        if os.path.exists('ipl_event_ids.json'):
            with open('ipl_event_ids.json', 'r') as f:
                event_ids = json.load(f)
                
            if not event_ids:
                logger.warning("No matches found in event IDs file")
                return False
                
            logger.info(f"Found {len(event_ids)} matches in event IDs file")
            return True
        else:
            logger.warning("Event IDs file not found")
            return False
            
    except Exception as e:
        logger.error(f"Error fetching upcoming matches: {e}")
        return False

def find_todays_match():
    """Find today's IPL match based on schedule."""
    try:
        now_ist = get_current_ist_time()
        today = now_ist.strftime('%Y-%m-%d')
        logger.info(f"Finding matches for today ({today})")
        
        # Standard match times
        weekday_match_time = "19:30:00"  # 7:30 PM IST
        weekend_early_match_time = "15:30:00"  # 3:30 PM IST
        weekend_late_match_time = "19:30:00"  # 7:30 PM IST - late match on weekends
        
        # Check if it's weekend (Saturday is 5, Sunday is 6)
        is_weekend = now_ist.weekday() >= 5
        
        # Determine which match to return based on current time
        current_hour = now_ist.hour
        current_min = now_ist.minute
        
        # Create a list to store today's matches
        todays_matches = []
        
        # Look for scheduled matches first
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'r') as f:
                schedule = json.load(f)
                
            logger.info(f"Loaded {len(schedule)} matches from schedule")
            
            # Find all of today's matches from the schedule
            for match in schedule:
                start_time = match.get('start_time', '')
                match_date = start_time.split('T')[0] if 'T' in start_time else ''
                
                if match_date == today:
                    logger.info(f"Found scheduled match for today: {match.get('match_name')} at {start_time}")
                    todays_matches.append(match)
            
            # If we found matches in the schedule, use those
            if todays_matches:
                # If there are multiple matches, determine which one to return based on current time
                if len(todays_matches) > 1:
                    logger.info(f"Found {len(todays_matches)} matches for today")
                    
                    # Sort matches by start time
                    todays_matches.sort(key=lambda m: m.get('start_time', ''))
                    
                    # Choose the appropriate match based on current time
                    for i, match in enumerate(todays_matches):
                        start_time = match.get('start_time', '')
                        if 'T' in start_time:
                            match_time = start_time.split('T')[1]
                            match_hour = int(match_time.split(':')[0])
                            match_min = int(match_time.split(':')[1])
                            
                            # If it's after this match's start time but before next match (or it's the last match)
                            if (current_hour > match_hour or 
                                (current_hour == match_hour and current_min >= match_min)):
                                # If there's another match after this one
                                if i + 1 < len(todays_matches):
                                    next_match_time = todays_matches[i+1].get('start_time', '').split('T')[1]
                                    next_match_hour = int(next_match_time.split(':')[0])
                                    next_match_min = int(next_match_time.split(':')[1])
                                    
                                    # If it's still before the next match, return this one
                                    if (current_hour < next_match_hour or 
                                        (current_hour == next_match_hour and current_min < next_match_min)):
                                        return match
                                else:
                                    # It's the last match of the day
                                    return match
                    
                    # If we didn't find a match based on time, return the first one
                    # This handles the case where it's before any match has started
                    return todays_matches[0]
                else:
                    # Just one match today
                    return todays_matches[0]
        else:
            logger.info("No schedule file found")
        
        # If no scheduled match is found, create matches from event IDs
        if not todays_matches and os.path.exists('ipl_event_ids.json'):
            with open('ipl_event_ids.json', 'r') as f:
                event_ids = json.load(f)
                
            if event_ids:
                # Get unique match names (removing reversed team order duplicates)
                match_names = set()
                for match_name in event_ids.keys():
                    teams = match_name.split(' vs ')
                    if len(teams) == 2:
                        # Ensure consistent team ordering
                        normalized_name = ' vs '.join(sorted([teams[0], teams[1]]))
                        match_names.add(normalized_name)
                    else:
                        match_names.add(match_name)
                
                logger.info(f"Found {len(match_names)} unique matches in event IDs file")
                
                # Create match objects for each unique match
                for match_name in match_names:
                    # Use original match name from event_ids
                    original_name = match_name  # Default
                    for key in event_ids.keys():
                        teams_key = set(key.split(' vs '))
                        teams_match = set(match_name.split(' vs '))
                        if teams_key == teams_match:
                            original_name = key
                            break
                    
                    event_id = event_ids[original_name]
                    
                    # Create different matches for weekend (early and late)
                    if is_weekend:
                        # Create early match (3:30 PM)
                        early_match = {
                            'event_id': event_id,
                            'match_name': original_name,
                            'start_time': f"{today}T{weekend_early_match_time}",
                            'is_estimated_time': True  # Flag indicating this time is estimated
                        }
                        todays_matches.append(early_match)
                        
                        # Create late match (7:30 PM)
                        late_match = {
                            'event_id': event_id,
                            'match_name': original_name,
                            'start_time': f"{today}T{weekend_late_match_time}",
                            'is_estimated_time': True  # Flag indicating this time is estimated
                        }
                        todays_matches.append(late_match)
                    else:
                        # Weekday - just one match at 7:30 PM
                        match = {
                            'event_id': event_id,
                            'match_name': original_name,
                            'start_time': f"{today}T{weekday_match_time}",
                            'is_estimated_time': True  # Flag indicating this time is estimated
                        }
                        todays_matches.append(match)
                
                # If we created matches, decide which one to return based on time
                if todays_matches:
                    # Sort matches by start time
                    todays_matches.sort(key=lambda m: m.get('start_time', ''))
                    
                    # Choose the appropriate match based on current time
                    for i, match in enumerate(todays_matches):
                        start_time = match.get('start_time', '')
                        match_time = start_time.split('T')[1]
                        match_hour = int(match_time.split(':')[0])
                        match_min = int(match_time.split(':')[1])
                        
                        # If current time is after or equal to this match's start time
                        if (current_hour > match_hour or 
                            (current_hour == match_hour and current_min >= match_min)):
                            # If there's another match after this one
                            if i + 1 < len(todays_matches):
                                next_match_time = todays_matches[i+1].get('start_time', '').split('T')[1]
                                next_match_hour = int(next_match_time.split(':')[0])
                                next_match_min = int(next_match_time.split(':')[1])
                                
                                # If it's still before the next match, return this one
                                if (current_hour < next_match_hour or 
                                    (current_hour == next_match_hour and current_min < next_match_min)):
                                    logger.info(f"Using match from event IDs: {match['match_name']} at {match['start_time']}")
                                    return match
                            else:
                                # It's the last match of the day
                                logger.info(f"Using match from event IDs: {match['match_name']} at {match['start_time']}")
                                return match
                    
                    # If we didn't find a match based on time, return the first one
                    # This handles the case where it's before any match has started
                    logger.info(f"Using first match from event IDs: {todays_matches[0]['match_name']} at {todays_matches[0]['start_time']}")
                    return todays_matches[0]
                
        if not todays_matches:
            logger.info("No matches found for today")
            return None
        
        # This should not be reached, but as a fallback return the first match if any were found
        if todays_matches:
            return todays_matches[0]
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding today's match: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def cache_current_match(match):
    """Cache the current match details for betting scripts to use."""
    try:
        if not match:
            logger.warning("No match to cache")
            return False
            
        # Save to cache
        with open(MATCH_CACHE_FILE, 'w') as f:
            json.dump(match, f, indent=2)
            
        # Also update the event IDs file
        event_id = match.get('event_id')
        match_name = match.get('match_name')
        
        if event_id and match_name:
            # Normalize team names
            teams = match_name.split(' vs ')
            event_id_map = {}
            
            if len(teams) == 2:
                # Create entries for both orderings
                event_id_map[match_name] = event_id
                event_id_map[f"{teams[1]} vs {teams[0]}"] = event_id
            else:
                event_id_map[match_name] = event_id
                
            # Save to event IDs file
            with open('ipl_event_ids.json', 'w') as f:
                json.dump(event_id_map, f, indent=2)
                
        logger.info(f"Cached match: {match_name} (ID: {event_id})")
        return True
        
    except Exception as e:
        logger.error(f"Error caching match: {e}")
        return False

def prefetch_markets(match):
    """Prefetch markets for a match and cache them."""
    try:
        if not match:
            logger.warning("No match to prefetch markets for")
            return False
            
        event_id = match.get('event_id')
        match_name = match.get('match_name')
        
        if not event_id:
            logger.warning("No event ID for prefetching markets")
            return False
            
        # Run the check_ipl_markets.py script to prefetch markets
        cmd = ["./check_ipl_markets.py", "--event-id", event_id, "--match-name", match_name, "--prefetch-only"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Error prefetching markets: {result.stderr}")
            return False
            
        logger.info(f"Successfully prefetched markets for {match_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error prefetching markets: {e}")
        return False

def get_match_info_for_betting():
    """Get the current match information for the betting script to use."""
    try:
        if os.path.exists(MATCH_CACHE_FILE):
            with open(MATCH_CACHE_FILE, 'r') as f:
                match = json.load(f)
                
            event_id = match.get('event_id')
            match_name = match.get('match_name')
            
            logger.info(f"Loaded match from cache: {match_name} (ID: {event_id})")
            return match
        else:
            logger.warning("No cached match found")
            return None
            
    except Exception as e:
        logger.error(f"Error getting match info: {e}")
        return None

def should_bet_now(match):
    """Determine if it's time to bet on this match."""
    try:
        if not match:
            return False
            
        now_ist = get_current_ist_time()
        match_time_str = match.get('start_time', '')
        
        if not match_time_str:
            logger.warning("No start time in match data")
            return False
            
        # Parse the match time
        match_time = datetime.datetime.fromisoformat(match_time_str.replace('Z', '+00:00'))
        match_time_ist = match_time.astimezone(pytz.timezone('Asia/Kolkata'))
        
        logger.info(f"Match time: {format_ist_time(match_time_ist)}")
        logger.info(f"Current time: {format_ist_time(now_ist)}")
        
        # Calculate time difference
        time_diff = now_ist - match_time_ist
        
        # Betting window: from match start to 3 hours after start
        if time_diff.total_seconds() >= 0 and time_diff.total_seconds() <= 10800:  # 3 hours = 10800 seconds
            logger.info(f"Match is ongoing (started {time_diff.total_seconds()/60:.1f} minutes ago)")
            return True
        elif time_diff.total_seconds() < 0:
            logger.info(f"Match hasn't started yet (starts in {-time_diff.total_seconds()/60:.1f} minutes)")
            return False
        else:
            logger.info(f"Match is over (ended {(time_diff.total_seconds()-10800)/60:.1f} minutes ago)")
            return False
            
    except Exception as e:
        logger.error(f"Error checking if should bet: {e}")
        return False

def run_prefetch_mode():
    """Run in prefetch mode to discover and cache match data."""
    logger.info("Running in prefetch mode")
    
    # Fetch upcoming matches
    fetch_success = fetch_upcoming_matches()
    
    if not fetch_success:
        logger.warning("Failed to fetch upcoming matches")
    
    # Find today's match
    match = find_todays_match()
    
    if match:
        # Cache the match
        cache_success = cache_current_match(match)
        
        if cache_success:
            # Prefetch markets
            prefetch_success = prefetch_markets(match)
            
            if prefetch_success:
                logger.info("Successfully completed prefetch")
            else:
                logger.warning("Failed to prefetch markets")
        else:
            logger.warning("Failed to cache match")
    else:
        logger.warning("No match found for today")

def run_betting_mode():
    """Run in betting mode to place bets on current match."""
    logger.info("Running in betting mode")
    
    # Get match info
    match = get_match_info_for_betting()
    
    if not match:
        logger.warning("No match info available for betting")
        return
    
    # Check if we should be betting now
    if not should_bet_now(match):
        logger.info("Not betting time")
        return
    
    # Get event ID and match name
    event_id = match.get('event_id')
    match_name = match.get('match_name')
    
    if not event_id or not match_name:
        logger.warning("Missing event ID or match name")
        return
    
    # Run the betting script
    cmd = ["./check_ipl_markets.py", "--event-id", event_id, "--match-name", match_name, "--auto-bet"]
    logger.info(f"Running betting command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Error running betting: {result.stderr}")
        else:
            logger.info("Successfully ran betting")
            
    except Exception as e:
        logger.error(f"Error executing betting command: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="IPL Match Scheduler")
    parser.add_argument("--prefetch", action="store_true", help="Run in prefetch mode to discover and cache match data")
    parser.add_argument("--bet", action="store_true", help="Run in betting mode to place bets on current match")
    parser.add_argument("--mock-time", help="Mock time for testing (format: YYYY-MM-DDTHH:MM:SS)")
    
    args = parser.parse_args()
    
    # Set mock time if provided
    global MOCK_TIME
    if args.mock_time:
        MOCK_TIME = args.mock_time
        logger.info(f"Using mock time: {MOCK_TIME}")
    
    if args.prefetch:
        run_prefetch_mode()
    elif args.bet:
        run_betting_mode()
    else:
        logger.error("No mode specified. Use --prefetch or --bet")
        print("Error: No mode specified. Use --prefetch or --bet")

if __name__ == "__main__":
    main() 