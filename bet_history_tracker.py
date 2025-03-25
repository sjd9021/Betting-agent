#!/usr/bin/env python3

import json
import requests
import logging
import os
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
from auth import refresh_auth_if_needed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bet_history')

# File paths
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
HISTORY_FILE = os.path.join(DATA_DIR, 'bet_history_log.json')
PERFORMANCE_FILE = os.path.join(DATA_DIR, 'bet_performance.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def load_credentials():
    """Load credentials from .credentials.json file."""
    try:
        cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.credentials.json')
        with open(cred_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading credentials: {str(e)}")
        return {}

def get_bet_history(hours=24, debug=False):
    """Get bet history from 10CRIC API."""
    try:
        # Ensure valid credentials
        refresh_auth_if_needed()
        
        credentials = load_credentials()
        player_id = credentials.get('player_id')
        session_cookie = credentials.get('session')
        sportsbook_token = credentials.get('sportsbook_token')
        
        if not (player_id and session_cookie):
            logger.error("Missing player_id or session cookie in credentials")
            return None
        
        # Prepare cookies and headers
        cookies = {
            'session': session_cookie,
            'player_id': player_id,
        }
        
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'apollo-require-preflight': 'true',
            'apollographql-client-name': 'frontoffice-client',
            'content-type': 'application/json',
            'origin': 'https://www.10crics.com',
            'referer': 'https://www.10crics.com/betting-history/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'x-language': 'en',
            'x-player-id': player_id,
            'x-sportsbook-token': sportsbook_token if sportsbook_token else '',
            'x-tenant': '10CRIC',
        }
        
        # GraphQL query for bet history
        query = {
            "operationName": "GetBetPage",
            "variables": {
                "payload": {
                    "filter": {
                        "oddsType": "ODDS_TYPE_DECIMAL",
                        "hours": hours
                    },
                    "pagination": {
                        "page": 1,
                        "itemsPerPage": 50
                    }
                }
            },
            "query": """query GetBetPage($payload: ListBetPageRequest!) {
              listBetPage(payload: $payload) {
                bets {
                  internalBetUuid
                  ticketId
                  purchaseTime
                  betType
                  betTypeName
                  odds
                  stake {
                    value
                    currency
                    __typename
                  }
                  status
                  updateTime
                  events {
                    name
                    homeTeam
                    awayTeam
                    userBet
                    eventType
                    odds
                    status
                    __typename
                  }
                  payout {
                    value
                    currency
                    __typename
                  }
                  __typename
                }
                hasNext
                totalCount
                __typename
              }
            }"""
        }
        
        # Try domains in order of preference
        domains = [
            'https://www.10crics.com',
            'https://www.my10cric.com',
            'https://www.10cric10.com'
        ]
        
        for domain in domains:
            try:
                url = f"{domain}/graphql"
                logger.info(f"Fetching bet history from {domain}")
                
                response = requests.post(
                    url,
                    headers=headers,
                    cookies=cookies,
                    json=query,
                    timeout=15
                )
                
                if debug:
                    logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'data' in data and data['data'] and 'listBetPage' in data['data'] and data['data']['listBetPage'] and 'bets' in data['data']['listBetPage']:
                        logger.info(f"Successfully retrieved bet history with {len(data['data']['listBetPage']['bets'])} bets")
                        return data['data']['listBetPage']
            except Exception as e:
                logger.warning(f"Error with {domain}: {str(e)}")
                continue
        
        # If all API calls fail, try using mock data
        logger.warning("Failed to get bet history from any domain, trying to create mock data")
        mock_data = create_mock_from_successful_bets()
        if mock_data:
            return mock_data
            
        return None
    except Exception as e:
        logger.error(f"Error getting bet history: {str(e)}")
        return None

def create_mock_from_successful_bets():
    """Create mock bet history from successful_bets.json file."""
    try:
        app_bet_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'successful_bets.json')
        if not os.path.exists(app_bet_path):
            return None
            
        with open(app_bet_path, 'r') as f:
            data = json.load(f)
            
        # Transform app bets to match API format
        mock_bets = []
        for bet in data:
            try:
                # Handle different timestamp formats
                purchase_time = ""
                timestamp = bet.get('timestamp', '2025-03-25 00:00:00')
                
                # Try different formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                    try:
                        purchase_time = str(int(datetime.strptime(timestamp, fmt).timestamp() * 1000))
                        break
                    except ValueError:
                        continue
                
                if not purchase_time:
                    # If all formats fail, use current time
                    purchase_time = str(int(datetime.now().timestamp() * 1000))
                
                # Create a mock bet object
                mock_bet = {
                    "internalBetUuid": bet.get('bet_id', f"mock-{len(mock_bets)}"),
                    "ticketId": bet.get('ticket_id', f"mock-{len(mock_bets)}"),
                    "purchaseTime": purchase_time,
                    "betType": "BET_TYPE_SINGLE_BET",
                    "betTypeName": "Single bet",
                    "odds": str(bet.get('odds', "2.0")),
                    "stake": {
                        "value": str(bet.get('stake', 100)),
                        "currency": bet.get('currency', "INR"),
                        "__typename": "SportMoney"
                    },
                    "payout": {
                        "value": str(float(bet.get('stake', 100)) * float(bet.get('odds', 2.0)) if bet.get('status', '').upper() == 'WON' else "0.00"),
                        "currency": bet.get('currency', "INR"),
                        "__typename": "SportMoney"
                    },
                    "status": f"BET_STATUS_{bet.get('status', 'PENDING').upper()}",
                    "updateTime": str(int(datetime.now().timestamp() * 1000)),
                    "events": [
                        {
                            "name": bet.get('event', bet.get('match_name', 'Unknown Event')),
                            "homeTeam": bet.get('home_team', 'Home Team'),
                            "awayTeam": bet.get('away_team', 'Away Team'),
                            "userBet": bet.get('selection', bet.get('selection_name', 'Unknown Selection')),
                            "eventType": bet.get('market', bet.get('market_name', 'Unknown Market')),
                            "odds": str(bet.get('odds', "2.0")),
                            "status": f"BET_STATUS_{bet.get('status', 'PENDING').upper()}",
                            "__typename": "ProviderEventV2"
                        }
                    ],
                    "__typename": "ProviderBetV2"
                }
                mock_bets.append(mock_bet)
            except Exception as e:
                logger.warning(f"Error processing bet {bet.get('bet_id', 'unknown')}: {str(e)}")
                continue
            
        if not mock_bets:
            logger.warning("No valid bets found in successful_bets.json")
            return None
            
        logger.info(f"Created {len(mock_bets)} mock bets from successful_bets.json")
        return {
            "bets": mock_bets,
            "hasNext": False,
            "totalCount": len(mock_bets),
            "__typename": "ListBetPageResponse"
        }
    except Exception as e:
        logger.warning(f"Error creating mock data: {str(e)}")
        import traceback
        logger.warning(f"Traceback: {traceback.format_exc()}")
        return None

def update_bet_history_log(bets):
    """Update bet history log file with new bets."""
    # Load existing history
    history = {}
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
    except Exception as e:
        logger.warning(f"Error loading history file: {str(e)}")
    
    # Add new bets to history
    for bet in bets:
        bet_id = bet['internalBetUuid']
        
        # Skip if bet already in history and status hasn't changed
        if bet_id in history and history[bet_id]['status'] == bet['status']:
            continue
        
        # Format the event details
        events = []
        for event in bet['events']:
            events.append({
                'name': event['name'],
                'teams': f"{event['homeTeam']} vs {event['awayTeam']}",
                'selection': event['userBet'],
                'market': event['eventType'],
                'odds': event['odds'],
                'status': event['status'],
            })
        
        # Create history entry
        history[bet_id] = {
            'ticketId': bet['ticketId'],
            'purchaseTime': bet['purchaseTime'],
            'purchaseDate': datetime.fromtimestamp(int(bet['purchaseTime'])/1000).strftime('%Y-%m-%d %H:%M:%S'),
            'betType': bet['betTypeName'],
            'odds': bet['odds'],
            'stake': bet['stake']['value'],
            'payout': bet['payout']['value'],
            'status': bet['status'],
            'events': events,
            'updateTime': bet['updateTime'],
            'placedByApp': bet_id.startswith('mock-')  # Assuming all mock bets are from our app
        }
        
        logger.info(f"Added/updated bet {bet_id} in history")
    
    # Save updated history
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving history file: {str(e)}")
    
    return history

def calculate_performance(history):
    """Calculate betting performance metrics."""
    # Initialize metrics
    performance = {
        'total_bets': 0,
        'total_stake': 0,
        'total_won': 0,
        'total_lost': 0,
        'pending': 0,
        'win_percentage': 0,
        'profit_loss': 0,
        'roi': 0,
        'markets': {},
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Process each bet
    for bet_id, bet in history.items():
        # Skip if not a clear status
        if bet['status'] not in ['BET_STATUS_WON', 'BET_STATUS_LOST', 'BET_STATUS_PENDING']:
            continue
        
        stake = float(bet['stake'])
        payout = float(bet['payout'])
        profit = payout - stake
        
        # Update total metrics
        performance['total_bets'] += 1
        performance['total_stake'] += stake
        
        if bet['status'] == 'BET_STATUS_WON':
            performance['total_won'] += 1
            performance['profit_loss'] += profit
        elif bet['status'] == 'BET_STATUS_LOST':
            performance['total_lost'] += 1
            performance['profit_loss'] -= stake
        elif bet['status'] == 'BET_STATUS_PENDING':
            performance['pending'] += 1
        
        # Update market performance
        for event in bet['events']:
            market_key = event['market']
            if market_key not in performance['markets']:
                performance['markets'][market_key] = {
                    'bets': 0, 'won': 0, 'stake': 0, 'profit_loss': 0
                }
            
            performance['markets'][market_key]['bets'] += 1
            performance['markets'][market_key]['stake'] += stake
            
            if bet['status'] == 'BET_STATUS_WON':
                performance['markets'][market_key]['won'] += 1
                performance['markets'][market_key]['profit_loss'] += profit
            elif bet['status'] == 'BET_STATUS_LOST':
                performance['markets'][market_key]['profit_loss'] -= stake
    
    # Calculate percentages
    if performance['total_won'] + performance['total_lost'] > 0:
        performance['win_percentage'] = (performance['total_won'] / (performance['total_won'] + performance['total_lost'])) * 100
    
    if performance['total_stake'] > 0:
        performance['roi'] = (performance['profit_loss'] / performance['total_stake']) * 100
    
    # Save performance data
    try:
        with open(PERFORMANCE_FILE, 'w') as f:
            json.dump(performance, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving performance file: {str(e)}")
    
    return performance

def generate_performance_report(performance):
    """Generate a readable performance report."""
    report = []
    
    # Overall stats
    report.append("========== BETTING PERFORMANCE SUMMARY ==========")
    report.append(f"Total Bets: {performance['total_bets']}")
    report.append(f"Win Rate: {performance['win_percentage']:.2f}%")
    report.append(f"Total Stake: {performance['total_stake']:.2f}")
    report.append(f"Profit/Loss: {performance['profit_loss']:.2f}")
    report.append(f"ROI: {performance['roi']:.2f}%")
    report.append(f"Pending Bets: {performance['pending']}")
    report.append("")
    
    # Market stats
    report.append("========== MARKET PERFORMANCE ==========")
    for market, stats in sorted(performance['markets'].items(), key=lambda x: x[1]['profit_loss'], reverse=True):
        if stats['bets'] > 0:
            win_rate = (stats['won'] / stats['bets']) * 100 if stats['bets'] > 0 else 0
            roi = (stats['profit_loss'] / stats['stake']) * 100 if stats['stake'] > 0 else 0
            report.append(f"{market}: {stats['bets']} bets, {win_rate:.1f}% win rate, {stats['profit_loss']:.2f} P/L, {roi:.2f}% ROI")
    
    return "\n".join(report)

def main():
    """Main function to retrieve and process bet history."""
    parser = argparse.ArgumentParser(description='10CRIC Bet History Tracker')
    parser.add_argument('--hours', type=int, default=24, help='Hours of history to fetch')
    parser.add_argument('--all', action='store_true', help='Fetch all available history (overrides hours)')
    parser.add_argument('--report', action='store_true', help='Show performance report')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    
    # Set hours to a large value if --all is specified
    hours = 8760 if args.all else args.hours  # 8760 hours = 1 year
    
    logger.info(f"Fetching bet history for the past {hours} hours")
    bet_data = get_bet_history(hours=hours, debug=args.debug)
    
    if not bet_data:
        logger.error("Failed to fetch bet history")
        return
    
    bets = bet_data.get('bets', [])
    logger.info(f"Retrieved {len(bets)} bets")
    
    # Update bet history log
    history = update_bet_history_log(bets)
    
    # Calculate performance metrics
    performance = calculate_performance(history)
    logger.info(f"Calculated performance metrics for {performance['total_bets']} bets")
    
    # Show report if requested
    if args.report:
        report = generate_performance_report(performance)
        print(report)

if __name__ == "__main__":
    main() 