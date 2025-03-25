# 10CRIC API Mock Data

This directory contains mock data files and a command-line utility for testing the 10CRIC API wrapper without making actual API calls to the 10CRIC platform.

## Contents

- `match_events.json` - Sample data for upcoming cricket matches
- `markets_data.json` - Sample data for markets available for betting
- `sanctioned_bets.json` - Configuration and list of sanctioned bets
- `successful_bets.json` - History of successfully placed bets
- `bet_placement_response.json` - Sample responses for bet placement requests
- `mock_api.py` - A command-line utility for interacting with mock data

## Using the Mock API

The `mock_api.py` utility can be used to simulate API calls for testing. It provides commands for listing matches, viewing markets, showing sanctioned bets, and simulating bet placement.

### Available Commands

```bash
# Make the script executable (if needed)
chmod +x mock_api.py

# Show help
./mock_api.py

# List all upcoming matches
./mock_api.py --list-matches

# Show markets for a specific event
./mock_api.py --show-markets cf27dbc5-2269-334f-993f-694ded1c64d3

# Show sanctioned bets configuration
./mock_api.py --show-sanctioned

# Show bet history
./mock_api.py --show-history

# Simulate placing a bet
./mock_api.py --simulate-bet
```

## Integration with Testing

You can use this mock data in your tests by modifying your code to load these files instead of making actual API calls during test runs.

### Example Usage in Tests

```python
import unittest
from mock_data.mock_api import Mock10CricAPI

class TestMarketMonitor(unittest.TestCase):
    def setUp(self):
        self.mock_api = Mock10CricAPI()
        
    def test_get_markets(self):
        event_id = "cf27dbc5-2269-334f-993f-694ded1c64d3"
        markets = self.mock_api.get_markets_for_event(event_id)
        self.assertIsNotNone(markets["event_data"])
        
    def test_place_bet(self):
        result = self.mock_api.place_bet(
            selection_id="2f41d627-55ab-394b-8b58-8a13c150a72d",
            event_id="cf27dbc5-2269-334f-993f-694ded1c64d3",
            market_id="592d8ee0-2fd9-342b-8fd2-30a9e690cfb7",
            market_line_id="a21928ef-8d62-30c0-b2aa-8840a659de0e",
            stake=100,
            odds=2.25
        )
        # Test will pass ~80% of the time (success rate in mock API)
        if result["status"] == "success":
            self.assertIn("bet_id", result)
        else:
            self.assertIn("error", result)

if __name__ == "__main__":
    unittest.main()
```

## Modifying the Mock Data

You can edit any of the JSON files to add, modify, or remove data as needed for your testing scenarios. The `mock_api.py` utility will load the updated data the next time it's run. 