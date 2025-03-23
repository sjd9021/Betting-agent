# 10CRIC API Wrapper

A Python wrapper for interacting with the 10CRIC betting platform's GraphQL API. This package provides a robust set of modules to authenticate, discover cricket events, retrieve betting markets, and place bets programmatically.

## Features

- **Authentication** - Browser-based authentication to obtain API tokens
- **Cricket Events** - Fetch upcoming cricket matches (with focus on IPL)
- **Betting Markets** - Get available markets for specific matches
- **Bet Placement** - Create and submit bet payloads (with dry-run option)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/10cric-api-wrapper.git
cd 10cric-api-wrapper
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your 10CRIC credentials:
```
CRIC10_USERNAME=your_email@example.com
CRIC10_PASSWORD=your_password
```

## Module Overview

### Authentication (`auth.py`)

Handles browser-based authentication to obtain API tokens.

```python
from auth import authenticate

# Authenticate and save credentials
credentials = authenticate(headless=False)  # Set to True to run without browser UI

# Or use the convenience function
from auth import authenticate_and_get_credentials
authenticate_and_get_credentials()
```

### Cricket Events (`cricket.py`) 

Fetches upcoming cricket matches with a focus on IPL events.

```python
from cricket import get_upcoming_ipl_matches, display_matches

# Get and display upcoming IPL matches
matches = get_upcoming_ipl_matches()
display_matches(matches)

# Find a specific match
from cricket import get_match_by_id, get_match_by_name
match = get_match_by_name("Mumbai Indians vs Chennai Super Kings")
```

### Betting Markets (`markets.py`)

Retrieves available betting markets for specific events.

```python
from markets import get_markets_for_event, display_active_markets

# Get markets for a specific event and display them
event_id = "814176aa-0388-3166-bb54-08fb83020b56"  # Example ID
display_active_markets(event_id)

# Find a specific market type and selection
from markets import get_selection_details
selection = get_selection_details(
    event_id="814176aa-0388-3166-bb54-08fb83020b56",
    market_type="Match Winner",
    selection_name="Mumbai Indians"
)
```

### Bet Placement (`betting.py`)

Creates and places bets (with dry-run option).

```python
from betting import place_bet

# Place a bet (with dry-run enabled)
result = place_bet(
    selection_id="selection-id-from-markets",
    event_id="event-id-from-cricket",
    market_id="market-id-from-markets",
    market_line_id="market-line-id-from-markets",
    stake=100,  # Betting amount
    odds=1.85,  # Odds for the selection
    dry_run=True  # Set to False to actually place the bet
)
```

## Workflow Example

This example shows a complete workflow from authentication to placing a bet:

```python
# 1. Authenticate and get credentials
from auth import authenticate
credentials = authenticate(headless=True)

# 2. Get upcoming IPL matches
from cricket import get_upcoming_ipl_matches, display_matches
matches = get_upcoming_ipl_matches()
display_matches(matches)

# 3. Select a match and get its event ID
match = matches[0]  # First match in the list
event_id = match['id']

# 4. Get available betting markets for the match
from markets import get_markets_for_event, extract_active_markets
result = get_markets_for_event(event_id)
active_markets = extract_active_markets(result['event_data'])

# 5. Find a specific market (Match Winner)
from markets import find_market_by_type, find_selection_by_name
market = find_market_by_type(active_markets, "Match Winner")
selection = find_selection_by_name(market, "Mumbai Indians")

# 6. Place a bet (dry run)
from betting import place_bet
bet_result = place_bet(
    selection_id=selection['selection_id'],
    event_id=event_id,
    market_id=market['market_id'],
    market_line_id=market['market_line_id'],
    stake=100,
    odds=float(selection['odds']),
    dry_run=True  # Set to False to actually place the bet
)
```

## Environment Variables

The wrapper uses these environment variables:

- `CRIC10_USERNAME`: Your 10CRIC account email
- `CRIC10_PASSWORD`: Your 10CRIC account password
- `PLAYER_ID`: (Optional) Your player ID (automatically extracted during authentication)
- `SPORTSBOOK_TOKEN`: (Optional) Your sportsbook token (automatically extracted during authentication)
- `sport_id`: (Optional) Cricket sport ID (default: "51ba17ce-bf66-352f-a3bc-1e8984e1d4a7")
- `league_id`: (Optional) IPL league ID (default: "30a6e759-f406-33ac-ba2c-a11c9d161898")
- `league_name`: (Optional) League name (default: "Indian Premier League")
- `sport_name`: (Optional) Sport name (default: "Cricket")
- `currency`: (Optional) Currency for bets (default: "INR")

## Notes

- The authentication module requires Playwright to automate browser interaction
- This wrapper is designed for educational and personal use
- Always use the `dry_run=True` parameter when testing bet placement to avoid placing actual bets
- The wrapper saves credentials in `.credentials.json` and `.credentials_complete.json` files
- Generated data is saved in `markets/` and `bets/` directories

## Disclaimer

This package is not affiliated with 10CRIC. Use at your own risk and responsibility. Betting may be illegal in some jurisdictions. Always check your local laws and regulations.

## License

MIT 