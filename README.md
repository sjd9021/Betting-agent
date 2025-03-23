# 10CRIC Betting Monitor

A tool for monitoring cricket betting markets on 10CRIC, with a focus on IPL matches.

## Overview

This tool helps you:
- Monitor IPL cricket matches
- Identify available betting markets
- Find sanctioned betting opportunities
- Optionally place bets automatically

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/10cric-betting-monitor.git
cd 10cric-betting-monitor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Your 10CRIC credentials will be requested on first run (or you can create a `.env` file with `CRIC10_USERNAME` and `CRIC10_PASSWORD`).

## Running the Program

### Check Current/Upcoming Matches

To check current matches and available markets:

```bash
./check_ipl_markets.py
```

This will:
- Authenticate with 10CRIC
- Find current ongoing IPL matches
- Fetch available markets
- Identify sanctioned betting opportunities
- Save market data to `data/markets_[event_id].json`
- Save sanctioned bets to `sanctioned_bets.json`

### Check Specific Match

To check a specific match with a known event ID:

```bash
./check_ipl_markets.py --event-id "EVENT_ID_HERE" --match-name "Team A vs Team B"
```

### Authentication Options

Force re-authentication:
```bash
./check_ipl_markets.py --auth
```

Run in headless browser mode:
```bash
./check_ipl_markets.py --headless
```

### Auto-Betting

Enable automatic bet placement on sanctioned markets:
```bash
./check_ipl_markets.py --auto-bet
```

Combine options as needed:
```bash
./check_ipl_markets.py --event-id "EVENT_ID_HERE" --match-name "Team A vs Team B" --auto-bet
```

## Output Files

- `betting_monitor.log` and `ipl_market_check.log`: Detailed logs of all operations
- `data/markets_[event_id].json`: All available markets for a match
- `sanctioned_bets.json`: Bets identified as matching your sanctioning criteria
- `bets/`: Directory containing bet payloads and responses

## Notes

- Auto-betting will place real bets with real money
- Test the system thoroughly before enabling auto-betting
- Use the logs to monitor system behavior

## Disclaimer

This tool is not affiliated with 10CRIC. Use at your own risk and responsibility. Betting may be illegal in some jurisdictions. Always check your local laws and regulations. 