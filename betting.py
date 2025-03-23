import json
import subprocess
import os
import uuid
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('10cric_betting')

def get_credentials() -> tuple:
    """
    Get player ID and sportsbook token from environment or credentials file.
    
    Returns:
        tuple: (player_id, sportsbook_token)
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

def get_constants() -> Dict[str, str]:
    """
    Get constant values from environment variables.
    
    Returns:
        Dictionary of constant values
    """
    constants = {
        "sport_id": os.getenv("sport_id", "51ba17ce-bf66-352f-a3bc-1e8984e1d4a7"),
        "league_id": os.getenv("league_id", "30a6e759-f406-33ac-ba2c-a11c9d161898"),
        "league_name": os.getenv("league_name", "Indian Premier League"),
        "sport_name": os.getenv("sport_name", "Cricket"),
        "currency": os.getenv("currency", "INR")
    }
    return constants

def create_bet_payload(
    selection_id: str,
    event_id: str,
    market_id: str,
    market_line_id: str,
    stake: float,
    odds: float,
    bet_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create the payload for placing a bet.
    
    Args:
        selection_id: ID of the selected option
        event_id: ID of the event
        market_id: ID of the market
        market_line_id: ID of the market line
        stake: Bet amount
        odds: The odds of the selection
        bet_id: Optional bet ID (generated if not provided)
        
    Returns:
        Dictionary containing the bet payload
    """
    player_id, sportsbook_token = get_credentials()
    constants = get_constants()
    
    if not player_id or not sportsbook_token:
        logger.error("Missing player credentials")
        return {}
    
    # Calculate potential return (stake * odds)
    potential_return = round(stake * odds, 2)
    
    # Generate a unique bet ID if not provided
    if not bet_id:
        bet_id = str(uuid.uuid4())
    
    # Create the bet payload
    payload = {
        "operationName": "placeBet",
        "variables": {
            "payload": {
                "bet": {
                    "id": bet_id,
                    "stake": str(stake),
                    "oddsType": "ODDS_TYPE_DECIMAL",
                    "betType": "BET_TYPE_SINGLE_BET",
                    "odds": str(odds),
                    "potentialReturn": str(potential_return),
                    "selections": [
                        {
                            "id": selection_id,
                            "eventId": event_id,
                            "leagueId": constants["league_id"],
                            "leagueName": constants["league_name"],
                            "marketId": market_id,
                            "marketLineId": market_line_id,
                            "sportId": constants["sport_id"],
                            "sportName": constants["sport_name"],
                            "odds": str(odds),
                            "pageSource": "PAGE_SOURCE_EVENT_PAGE",
                            "earlyPayoutId": 3
                        }
                    ],
                    "oddsChangeStrategy": "ODDS_CHANGE_STRATEGY_NONE",
                    "loyaltyPoints": None
                },
                "currency": constants["currency"],
                "sportToken": sportsbook_token,
                "playerId": player_id
            }
        },
        "query": "mutation placeBet($payload: PlaceBetRequest!) {\n  placeBet(payload: $payload) {\n    betId\n    __typename\n  }\n}"
    }
    
    return payload

def place_bet(
    selection_id: str,
    event_id: str,
    market_id: str,
    market_line_id: str,
    stake: float,
    odds: float,
    bet_id: Optional[str] = None,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Place a bet using the GraphQL API.
    
    Args:
        selection_id: ID of the selected option
        event_id: ID of the event
        market_id: ID of the market
        market_line_id: ID of the market line
        stake: Bet amount
        odds: The odds of the selection
        bet_id: Optional bet ID (generated if not provided)
        dry_run: If True, just save the payload without making the API call
        
    Returns:
        Dictionary containing the API response or error
    """
    player_id, sportsbook_token = get_credentials()
    
    if not player_id or not sportsbook_token:
        logger.error("Missing player credentials")
        return {"error": "Missing player credentials"}
    
    # Create bet payload
    payload = create_bet_payload(
        selection_id=selection_id,
        event_id=event_id,
        market_id=market_id,
        market_line_id=market_line_id,
        stake=stake,
        odds=odds,
        bet_id=bet_id
    )
    
    # Save payload for reference
    os.makedirs("bets", exist_ok=True)
    with open(f"bets/bet_payload_{bet_id or 'new'}.json", "w") as f:
        json.dump(payload, f, indent=2)
    
    logger.info(f"Bet payload created with ID: {payload['variables']['payload']['bet']['id']}")
    logger.info(f"Stake: {stake}, Odds: {odds}, Potential Return: {payload['variables']['payload']['bet']['potentialReturn']}")
    
    # If dry run, don't actually place the bet
    if dry_run:
        logger.info("DRY RUN: Bet not placed. Payload saved to file.")
        return {"status": "dry_run", "payload": payload}
    
    # Construct the curl command
    curl_command = f"""
    curl 'https://www.my10cric.com/graphql' \\
      -H 'content-type: application/json' \\
      -H 'x-player-id: {player_id}' \\
      -H 'x-sportsbook-token: {sportsbook_token}' \\
      -H 'x-tenant: 10CRIC' \\
      --data-raw '{json.dumps(payload)}'
    """
    
    # Execute the curl command
    try:
        logger.info("Placing bet...")
        result = subprocess.run(curl_command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Error executing curl command: {result.stderr}")
            return {"error": "Failed to execute API call", "details": result.stderr}
            
        response_data = json.loads(result.stdout)
        
        # Save the response for reference
        with open(f"bets/bet_response_{bet_id or 'new'}.json", "w") as f:
            json.dump(response_data, f, indent=2)
        
        # Check if bet was placed successfully
        bet_id = response_data.get("data", {}).get("placeBet", {}).get("betId")
        if bet_id:
            logger.info(f"Bet placed successfully! Bet ID: {bet_id}")
            return {"status": "success", "bet_id": bet_id, "response": response_data}
        else:
            logger.error(f"Bet placement failed: {response_data}")
            return {"status": "error", "response": response_data}
            
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing response: {e}")
        return {"error": "Failed to parse API response", "details": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": "Unexpected error", "details": str(e)}

def validate_selection(selection_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate selection data to ensure it has all required fields.
    
    Args:
        selection_data: Dictionary containing selection information
        
    Returns:
        Dictionary of validation errors or empty dict if valid
    """
    errors = {}
    required_fields = {
        "selection_id": "Selection ID",
        "event_id": "Event ID",
        "market_id": "Market ID",
        "market_line_id": "Market Line ID",
        "odds": "Odds"
    }
    
    for field, name in required_fields.items():
        if field not in selection_data or not selection_data[field]:
            errors[field] = f"{name} is required"
    
    return errors

if __name__ == "__main__":
    print("10CRIC Betting Module")
    print("=====================")
    print("This module is designed to be imported and used by other scripts.")
    print("Example usage:")
    print("")
    print("from betting import place_bet")
    print("")
    print("result = place_bet(")
    print("    selection_id='selection-id',")
    print("    event_id='event-id',")
    print("    market_id='market-id',")
    print("    market_line_id='market-line-id',")
    print("    stake=100,")
    print("    odds=1.5,")
    print("    dry_run=True  # Set to False to actually place the bet")
    print(")")
    
    # Example of using the module with test data
    # Note: This won't run by default, but you can uncomment to test
    """
    # Test data for a bet
    test_bet = {
        "selection_id": "14f9da87-e5f4-3242-a898-271c9aa0a06d",
        "event_id": "814176aa-0388-3166-bb54-08fb83020b56",
        "market_id": "fd47a863-e290-3cab-b5fc-5b988ae81581",
        "market_line_id": "6a27d529-b2b2-3c7b-848b-a7d71db66cb3",
        "stake": 20,
        "odds": 1.16
    }
    
    # Validate the selection
    errors = validate_selection(test_bet)
    if errors:
        for field, error in errors.items():
            print(f"Error: {error}")
    else:
        # Place the bet (dry run)
        result = place_bet(
            selection_id=test_bet["selection_id"],
            event_id=test_bet["event_id"],
            market_id=test_bet["market_id"],
            market_line_id=test_bet["market_line_id"],
            stake=test_bet["stake"],
            odds=test_bet["odds"],
            dry_run=True  # Set to False to actually place the bet
        )
        
        print(f"Result: {result['status']}")
    """
