import json
import subprocess
import os
import logging
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('10cric_markets')

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
    
    return player_id, sportsbook_token

def get_markets_for_event(event_id: str) -> Dict[str, Any]:
    """
    Get available betting markets for a specific event.
    
    Args:
        event_id: ID of the event
        
    Returns:
        Dictionary containing the event and market data
    """
    player_id, sportsbook_token = get_credentials()
    
    if not player_id or not sportsbook_token:
        logger.error("Missing credentials for fetching markets")
        return {"error": "Missing credentials"}
    
    logger.info(f"Fetching markets for event ID: {event_id}")
    
    # Construct the GraphQL query
    query = {
        "operationName": "lazyEvent",
        "variables": {
            "payload": {
                "eventId": event_id
            }
        },
        "query": """query lazyEvent($payload: LazyEventRequest!) {
          lazyEvent(payload: $payload) {
            sportEvent {
              id
              name
              leagueId
              leagueName
              regionName
              sportId
              sportName
              isLive
              startEventDate
              participantHomeName
              participantAwayName
              expandedMarkets {
                id
                name
                marketLines {
                  id
                  name
                  isSuspended
                  marketLineStatus
                  selections {
                    id
                    name
                    odds
                    isActive
                    __typename
                  }
                  __typename
                }
                __typename
              }
              __typename
            }
            __typename
          }
        }"""
    }
    
    # Construct the curl command
    curl_command = f"""
    curl 'https://www.my10cric.com/graphql' \\
      -H 'content-type: application/json' \\
      -H 'x-player-id: {player_id}' \\
      -H 'x-sportsbook-token: {sportsbook_token}' \\
      -H 'x-tenant: 10CRIC' \\
      --data-raw '{json.dumps(query)}'
    """
    
    # Execute the curl command
    try:
        result = subprocess.run(curl_command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Error executing curl command: {result.stderr}")
            return {"error": "Failed to execute API call"}
            
        response_data = json.loads(result.stdout)
        
        # Check for errors in response
        if "errors" in response_data:
            logger.error(f"API returned errors: {response_data['errors']}")
            return {"error": "API returned errors", "details": response_data["errors"]}
        
        # Extract event data with markets
        event_data = response_data.get("data", {}).get("lazyEvent", {}).get("sportEvent")
        if not event_data:
            logger.error("No event data found in response")
            return {"error": "No event data found"}
        
        logger.info(f"Successfully fetched markets for event: {event_data.get('name')}")
        
        # Save raw response for debugging
        os.makedirs("markets", exist_ok=True)
        with open(f"markets/raw_markets_{event_id}.json", "w") as f:
            json.dump(response_data, f, indent=2)
        
        return {"success": True, "event_data": event_data}
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing response: {e}")
        return {"error": "Failed to parse API response"}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": "Unexpected error", "details": str(e)}

def extract_active_markets(event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract active (non-suspended) markets with their selections.
    
    Args:
        event_data: Dictionary containing event data with markets
        
    Returns:
        List of active markets with selections
    """
    active_markets = []
    
    # Get the data from the correct structure as seen in the raw JSON
    if not event_data:
        logger.warning("No event data provided")
        return []
        
    # Check if data is already in the right format or needs extraction from GraphQL response
    if "data" in event_data and "lazyEvent" in event_data["data"] and "sportEvent" in event_data["data"]["lazyEvent"]:
        event_data = event_data["data"]["lazyEvent"]["sportEvent"]
    
    # Check if event data contains expanded markets
    if "expandedMarkets" not in event_data:
        logger.warning("No expandedMarkets found in event data")
        return []
    
    event_id = event_data.get("id")
    event_name = event_data.get("name")
    sport_id = event_data.get("sportId")
    sport_name = event_data.get("sportName")
    league_id = event_data.get("leagueId")
    league_name = event_data.get("leagueName")
    participant_home = event_data.get("participantHomeName")
    participant_away = event_data.get("participantAwayName")
    
    logger.info(f"Extracting active markets for event: {event_name} (ID: {event_id})")
    
    for market in event_data.get("expandedMarkets", []):
        market_id = market.get("id")
        market_name = market.get("name")
        
        # Skip markets without a name or id
        if not market_id or not market_name:
            continue
        
        for market_line in market.get("marketLines", []):
            market_line_id = market_line.get("id")
            market_line_name = market_line.get("name", market_name)  # Use market name as fallback
            
            # Skip suspended market lines
            if market_line.get("isSuspended", True):
                continue
                
            # Check if market line status is active
            # API returns "MARKET_LINE_STATUS_ACTIVE", not just "ACTIVE"
            if market_line.get("marketLineStatus") != "MARKET_LINE_STATUS_ACTIVE":
                continue
            
            # Extract active selections
            active_selections = []
            for selection in market_line.get("selections", []):
                if selection.get("isActive", False):
                    active_selections.append({
                        "selection_id": selection.get("id"),
                        "name": selection.get("name"),
                        "odds": selection.get("odds")
                    })
            
            # Only add market lines with active selections
            if active_selections:
                active_markets.append({
                    "event_id": event_id,
                    "event_name": event_name,
                    "market_id": market_id,
                    "market_name": market_line_name,  # Use the market line name which contains detailed info
                    "market_line_id": market_line_id,
                    "market_line_name": market_line_name,
                    "market_lines": [market_line],  # Include full market line data for sanction manager
                    "selections": active_selections,
                    "sport_id": sport_id,
                    "sport_name": sport_name,
                    "league_id": league_id,
                    "league_name": league_name,
                    "participant_home": participant_home,
                    "participant_away": participant_away
                })
    
    logger.info(f"Found {len(active_markets)} active market lines")
    return active_markets

def save_active_markets(event_id: str, active_markets: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
    """
    Save active markets to a JSON file.
    
    Args:
        event_id: ID of the event
        active_markets: List of active markets
        filename: Optional filename to save to
        
    Returns:
        Path to the saved file
    """
    if not filename:
        filename = f"active_markets_{event_id}.json"
    
    try:
        os.makedirs("markets", exist_ok=True)
        filepath = os.path.join("markets", filename)
        
        with open(filepath, "w") as f:
            json.dump(active_markets, f, indent=2)
        
        logger.info(f"Saved {len(active_markets)} active markets to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error saving active markets: {e}")
        return ""

def find_market_by_type(active_markets: List[Dict[str, Any]], market_type: str) -> Optional[Dict[str, Any]]:
    """
    Find a market by its type/name.
    
    Args:
        active_markets: List of active markets
        market_type: Type of market to find (e.g., "Match Winner")
        
    Returns:
        Matching market or None if not found
    """
    for market in active_markets:
        if market_type.lower() in market.get("market_name", "").lower():
            logger.info(f"Found matching market: {market.get('market_name')}")
            return market
    
    logger.warning(f"No matching market found for type: {market_type}")
    return None

def find_selection_by_name(market: Dict[str, Any], selection_name: str) -> Optional[Dict[str, Any]]:
    """
    Find a selection by its name within a market.
    
    Args:
        market: Market data
        selection_name: Name of the selection to find
        
    Returns:
        Matching selection or None if not found
    """
    for selection in market.get("selections", []):
        if selection_name.lower() in selection.get("name", "").lower():
            logger.info(f"Found matching selection: {selection.get('name')} @ {selection.get('odds')}")
            return selection
    
    logger.warning(f"No matching selection found for name: {selection_name}")
    return None

def get_selection_details(event_id: str, market_type: str, selection_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific selection.
    
    Args:
        event_id: ID of the event
        market_type: Type of market to search (e.g., "Match Winner")
        selection_name: Optional name of selection to find
        
    Returns:
        Selection details or None if not found
    """
    # Get markets for the event
    result = get_markets_for_event(event_id)
    
    if "error" in result:
        logger.error(f"Error getting markets: {result['error']}")
        return None
    
    event_data = result.get("event_data")
    if not event_data:
        logger.error("No event data found")
        return None
    
    # Extract active markets
    active_markets = extract_active_markets(event_data)
    
    # Find the specified market
    market = find_market_by_type(active_markets, market_type)
    if not market:
        return None
    
    # If selection name provided, find that specific selection
    if selection_name:
        selection = find_selection_by_name(market, selection_name)
        if not selection:
            return None
        
        # Return selection with additional context
        return {
            "event_id": event_id,
            "event_name": market.get("event_name"),
            "market_id": market.get("market_id"),
            "market_name": market.get("market_name"),
            "market_line_id": market.get("market_line_id"),
            "selection_id": selection.get("selection_id"),
            "selection_name": selection.get("name"),
            "odds": selection.get("odds"),
            "sport_id": market.get("sport_id"),
            "sport_name": market.get("sport_name"),
            "league_id": market.get("league_id"),
            "league_name": market.get("league_name")
        }
    
    # If no selection name provided, return the market data
    return market

def display_active_markets(event_id: str) -> None:
    """
    Display active markets in a readable format.
    
    Args:
        event_id: ID of the event
    """
    # Get markets for the event
    result = get_markets_for_event(event_id)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return
    
    event_data = result.get("event_data")
    if not event_data:
        print("No event data found")
        return
    
    # Extract active markets
    active_markets = extract_active_markets(event_data)
    
    # Display event information
    print(f"\nEvent: {event_data.get('name')}")
    print(f"League: {event_data.get('leagueName')}")
    print(f"Teams: {event_data.get('participantHomeName')} vs {event_data.get('participantAwayName')}")
    print("\nAvailable Betting Markets:")
    print("--------------------------")
    
    # Display markets
    for i, market in enumerate(active_markets, 1):
        print(f"\n{i}. {market.get('market_name')} - {market.get('market_line_name')}")
        print(f"   Market ID: {market.get('market_id')}")
        print(f"   Market Line ID: {market.get('market_line_id')}")
        print("   Selections:")
        
        for j, selection in enumerate(market.get("selections", []), 1):
            print(f"     {j}. {selection.get('name')} @ {selection.get('odds')}")
            print(f"        Selection ID: {selection.get('selection_id')}")

if __name__ == "__main__":
    import sys
    
    print("10CRIC Betting Markets Module")
    print("=============================")
    
    if len(sys.argv) > 1:
        event_id = sys.argv[1]
        print(f"Fetching markets for event ID: {event_id}")
        display_active_markets(event_id)
    else:
        print("Usage: python markets.py <event_id>")
        print("\nExample:")
        print("  python markets.py 814176aa-0388-3166-bb54-08fb83020b56")
        
        # Try to load event IDs from file
        try:
            with open("ipl_event_ids.json", "r") as f:
                event_ids = json.load(f)
                if event_ids:
                    print("\nAvailable events from ipl_event_ids.json:")
                    for i, (name, event_id) in enumerate(event_ids.items(), 1):
                        print(f"{i}. {name}: {event_id}")
        except (FileNotFoundError, json.JSONDecodeError):
            print("\nNo stored event IDs found. Run cricket.py first to get event IDs.") 