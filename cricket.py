import json
import subprocess
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('10cric_cricket')

def get_credentials() -> Tuple[str, str]:
    """
    Get player ID and sportsbook token from environment or credentials file.
    
    Returns:
        Tuple containing player_id and sportsbook_token
    """
    # Try to get from environment variables first
    player_id = os.getenv("PLAYER_ID")
    sportsbook_token = os.getenv("SPORTSBOOK_TOKEN")
    
    # If not in environment, try to load from credentials file
    if not player_id or not sportsbook_token:
        try:
            with open(".credentials.json", "r") as f:
                credentials = json.load(f)
                player_id = credentials.get("player_id")
                sportsbook_token = credentials.get("sportsbook_token")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load credentials from file: {e}")
    
    # Use fallback values if still not found
    if not player_id:
        player_id = os.getenv("PLAYER_ID", "e66e21ed-b736-4f5c-ac59-cb3d07a05037")
        logger.warning("Using fallback player ID")
    
    if not sportsbook_token:
        sportsbook_token = os.getenv("SPORTSBOOK_TOKEN", "5a1f760c-ece5-4090-b6db-e17f67a94bda")
        logger.warning("Using fallback sportsbook token")
    
    return player_id, sportsbook_token

def fetch_upcoming_cricket_events(sport_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch upcoming cricket events using the GraphQL API.
    
    Args:
        sport_id: Optional sport ID to use (defaults to environment variable or Cricket ID)
        
    Returns:
        List of upcoming cricket events
    """
    player_id, sportsbook_token = get_credentials()
    
    if not player_id or not sportsbook_token:
        logger.error("Missing credentials for fetching events")
        return []
    
    # Use provided sport_id or get from environment
    if not sport_id:
        sport_id = os.getenv("sport_id", "51ba17ce-bf66-352f-a3bc-1e8984e1d4a7")
    
    logger.info(f"Fetching upcoming cricket events for sport ID: {sport_id}")
    
    # Construct GraphQL query
    query = {
        "operationName": "listWidgetEvents",
        "variables": {
            "payload": {
                "sportId": sport_id,
                "widgetType": "WIDGET_TYPE_UPCOMING_EVENTS"
            }
        },
        "query": "query listWidgetEvents($payload: ListWidgetEventsRequest!) { listWidgetEvents(payload: $payload) { events { id name leagueName startEventDate } } }"
    }
    
    # Construct curl command
    curl_command = f"""
    curl 'https://www.10crics.com/graphql' \\
      -H 'content-type: application/json' \\
      -H 'x-player-id: {player_id}' \\
      -H 'x-sportsbook-token: {sportsbook_token}' \\
      -H 'x-tenant: 10CRIC' \\
      -H 'x-apollo-operation-name: listWidgetEvents' \\
      -H 'apollo-require-preflight: true' \\
      --data-raw '{json.dumps(query)}'
    """
    
    # Execute curl command
    try:
        logger.info("Executing API request")
        result = subprocess.run(curl_command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Error executing curl command: {result.stderr}")
            return []
        
        # Parse response
        response_data = json.loads(result.stdout)
        events = response_data.get("data", {}).get("listWidgetEvents", {}).get("events", [])
        logger.info(f"Fetched {len(events)} cricket events")
        
        # Format events
        formatted_events = []
        for event in events:
            event_id = event.get("id")
            name = event.get("name")
            league_name = event.get("leagueName")
            start_date = event.get("startEventDate")
            
            if event_id and name and start_date:
                # Convert timestamp to human-readable format
                try:
                    timestamp = datetime.fromtimestamp(int(start_date)/1000).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError, OverflowError):
                    timestamp = "Unknown"
                
                formatted_events.append({
                    'id': event_id,
                    'name': name,
                    'leagueName': league_name,
                    'startEventDate': start_date,
                    'timestamp': timestamp
                })
        
        return formatted_events
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing API response: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching events: {e}")
        return []

def filter_ipl_matches(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter events to get only IPL matches.
    
    Args:
        events: List of event data
        
    Returns:
        List of IPL matches
    """
    try:
        logger.info(f"Filtering {len(events)} events for IPL matches")
        
        ipl_matches = [
            event for event in events
            if "Indian Premier League" in event.get("leagueName", "")
        ]
        
        logger.info(f"Found {len(ipl_matches)} IPL matches")
        return ipl_matches
    except Exception as e:
        logger.error(f"Error filtering IPL matches: {e}")
        return []

def store_event_ids(matches: List[Dict[str, Any]], filename: str = 'ipl_event_ids.json') -> Dict[str, str]:
    """
    Create a mapping of match names to event IDs and store them.
    
    Args:
        matches: List of match data
        filename: Name of file to store event IDs
        
    Returns:
        Dictionary mapping match names to event IDs
    """
    event_id_map = {match['name']: match['id'] for match in matches}
    
    try:
        # Save to a file for persistence
        with open(filename, 'w') as f:
            json.dump(event_id_map, f, indent=2)
        
        logger.info(f"Saved {len(event_id_map)} event IDs to {filename}")
        return event_id_map
    except Exception as e:
        logger.error(f"Error saving event IDs: {e}")
        return event_id_map

def display_matches(matches: List[Dict[str, Any]]) -> None:
    """
    Display the matches in a readable format.
    
    Args:
        matches: List of match data to display
    """
    if not matches:
        print("No matches found.")
        return
        
    print(f"\nFound {len(matches)} matches:")
    print("------------------------")
    
    for i, match in enumerate(matches, 1):
        print(f"{i}. Match: {match['name']}")
        print(f"   ID: {match['id']}")
        print(f"   League: {match.get('leagueName', 'Unknown')}")
        print(f"   Start Date: {match.get('timestamp', 'Unknown')}")
        print("   ------------------------")

def get_upcoming_ipl_matches() -> List[Dict[str, Any]]:
    """
    Get upcoming IPL matches.
    
    Returns:
        List of upcoming IPL matches
    """
    sport_id = os.getenv("sport_id", "51ba17ce-bf66-352f-a3bc-1e8984e1d4a7")
    
    # Fetch all cricket events
    all_events = fetch_upcoming_cricket_events(sport_id)
    
    # Filter for IPL matches
    ipl_matches = filter_ipl_matches(all_events)
    
    # Store event IDs
    store_event_ids(ipl_matches)
    
    return ipl_matches

def get_match_by_id(match_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific match by ID.
    
    Args:
        match_id: ID of the match to retrieve
        
    Returns:
        Match data or None if not found
    """
    matches = fetch_upcoming_cricket_events()
    
    for match in matches:
        if match.get("id") == match_id:
            return match
    
    return None

def get_match_by_name(match_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific match by name.
    
    Args:
        match_name: Name of the match to retrieve (partial match supported)
        
    Returns:
        Match data or None if not found
    """
    matches = fetch_upcoming_cricket_events()
    
    for match in matches:
        if match_name.lower() in match.get("name", "").lower():
            return match
    
    return None

def load_stored_event_ids(filename: str = 'ipl_event_ids.json') -> Dict[str, str]:
    """
    Load stored event IDs from file.
    
    Args:
        filename: Name of file to load event IDs from
        
    Returns:
        Dictionary mapping match names to event IDs
    """
    try:
        with open(filename, 'r') as f:
            event_id_map = json.load(f)
        
        logger.info(f"Loaded {len(event_id_map)} event IDs from {filename}")
        return event_id_map
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading event IDs: {e}")
        return {}

if __name__ == "__main__":
    print("10CRIC Cricket Events Module")
    print("============================")
    
    # Get upcoming IPL matches
    ipl_matches = get_upcoming_ipl_matches()
    
    # Display matches
    display_matches(ipl_matches)
    
    # Load stored event IDs
    event_id_map = load_stored_event_ids()
    
    # Show example usage
    print("\nEvent ID mapping stored in 'ipl_event_ids.json'")
    if event_id_map:
        print("Example usage:")
        print("from cricket import get_match_by_id, get_match_by_name")
        print("match = get_match_by_id('match-id')")
        print("match = get_match_by_name('team1 vs team2')")
    else:
        print("No event IDs stored. Run script again to fetch and store event IDs.")