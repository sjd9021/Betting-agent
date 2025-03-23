import json
import subprocess
import os
from typing import List, Dict, Any
from datetime import datetime

def get_player_credentials() -> tuple:
   
   """Get the player ID and sportsbook token from environment variables."""
   player_id = os.getenv("PLAYER_ID", "e66e21ed-b736-4f5c-ac59-cb3d07a05037")
   sportsbook_token = os.getenv("SPORTSBOOK_TOKEN", "5a1f760c-ece5-4090-b6db-e17f67a94bda")
   return player_id, sportsbook_token

def fetch_upcoming_cricket_events(player_id: str, sportsbook_token: str, sport_id: str) -> Dict[str, Any]:
    """Fetch upcoming cricket events using the GraphQL API."""
    curl_command = f"""
    curl 'https://www.my10cric.com/graphql' \\
      -H 'content-type: application/json' \\
      -H 'x-player-id: {player_id}' \\
      -H 'x-sportsbook-token: {sportsbook_token}' \\
      -H 'x-tenant: 10CRIC' \\
      --data-raw '{{
        "operationName":"listWidgetEvents",
        "variables":{{
          "payload":{{
            "sportId":"{sport_id}",
            "widgetType":"WIDGET_TYPE_UPCOMING_EVENTS"
          }}
        }},
        "query":"query listWidgetEvents($payload: ListWidgetEventsRequest!) {{ listWidgetEvents(payload: $payload) {{ events {{ id name leagueName startEventDate }} }} }}"
      }}'
    """
    
    result = subprocess.run(curl_command, shell=True, capture_output=True, text=True)
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error parsing API response: {result.stdout}")
        return {"data": {"listWidgetEvents": {"events": []}}}

def filter_ipl_matches(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filter the response data to get only IPL matches."""
    try:
        events = response_data.get("data", {}).get("listWidgetEvents", {}).get("events", [])
        
        ipl_matches = [
            {
                'id': event['id'],
                'name': event['name'],
                'leagueName': event['leagueName'],
                'startEventDate': event['startEventDate'],
                'timestamp': datetime.fromtimestamp(int(event['startEventDate'])/1000).strftime('%Y-%m-%d %H:%M:%S')
            }
            for event in events
            if "Indian Premier League" in event.get("leagueName", "")
        ]
        
        return ipl_matches
    except Exception as e:
        print(f"Error filtering IPL matches: {str(e)}")
        return []

def store_event_ids(matches: List[Dict[str, Any]]) -> Dict[str, str]:
    """Create a mapping of match names to event IDs and store them."""
    event_id_map = {match['name']: match['id'] for match in matches}
    
    # Save to a file for persistence
    with open('ipl_event_ids.json', 'w') as f:
        json.dump(event_id_map, f, indent=2)
    
    return event_id_map

def display_matches(matches: List[Dict[str, Any]]) -> None:
    """Display the matches in a readable format."""
    print(f"Found {len(matches)} IPL matches:")
    for match in matches:
        print(f"Match: {match['name']}")
        print(f"ID: {match['id']}")
        print(f"League: {match['leagueName']}")
        print(f"Start Date: {match['timestamp']} (Unix: {match['startEventDate']})")
        print("---")

def main():
    # Constants
    SPORT_ID = os.getenv("SPORT_ID", "51ba17ce-bf66-352f-a3bc-1e8984e1d4a7")
    
    # Get credentials
    player_id, sportsbook_token = get_player_credentials()
    
    # Fetch upcoming events
    response_data = fetch_upcoming_cricket_events(player_id, sportsbook_token, SPORT_ID)
    
    # Filter for IPL matches
    ipl_matches = filter_ipl_matches(response_data)
    
    # Store event IDs
    event_id_map = store_event_ids(ipl_matches)
    
    # Display matches
    display_matches(ipl_matches)
    
    return event_id_map

if __name__ == "__main__":
    event_ids = main()
    print("\nEvent ID mapping stored in 'ipl_event_ids.json'")
    print(f"Event IDs dictionary: {event_ids}")