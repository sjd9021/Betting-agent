#!/usr/bin/env python3

import os
import sys
import json
import logging
import argparse
import requests
import subprocess
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('debug_auth')

def load_credentials():
    """Load credentials from file."""
    try:
        with open(".credentials.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading credentials: {e}")
        return None

def test_curl_validation(credentials):
    """Test validation using curl."""
    player_id = credentials.get("player_id")
    sportsbook_token = credentials.get("sportsbook_token")
    
    if not player_id or not sportsbook_token:
        logger.error("Missing player_id or sportsbook_token in credentials")
        return False
    
    # Extract cookie data from credentials if available
    cookies_data = credentials.get("cookies", {})
    session_cookie = cookies_data.get("session", "")
    session_sig = cookies_data.get("session.sig", "")
    
    # Prepare cookie string
    cookie_string = ""
    if session_cookie:
        cookie_string += f"session={session_cookie}; "
    if session_sig:
        cookie_string += f"session.sig={session_sig}; "
    
    # Use the CheckLoggedIn query to validate credentials
    query = {
        "operationName": "CheckLoggedIn",
        "variables": {},
        "query": "query CheckLoggedIn { checkLoggedIn }"
    }
    
    curl_command = f"""
    curl 'https://www.10crics.com/graphql' \\
      -v \\
      -H 'content-type: application/json' \\
      -H 'x-player-id: {player_id}' \\
      -H 'x-sportsbook-token: {sportsbook_token}' \\
      -H 'x-tenant: 10CRIC' \\
      -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36' \\
      -b '{cookie_string}' \\
      --data-raw '{json.dumps(query)}'
    """
    
    logger.info("Testing curl validation...")
    logger.info(f"Player ID: {player_id[:8]}... Token: {sportsbook_token[:8]}...")
    
    result = subprocess.run(curl_command, shell=True, capture_output=True, text=True)
    
    logger.info(f"Curl return code: {result.returncode}")
    logger.info(f"Response length: {len(result.stdout)} characters")
    
    if result.stdout:
        preview = result.stdout[:200] + ("..." if len(result.stdout) > 200 else "")
        logger.info(f"Response preview: {preview}")
        
        if "<html" in result.stdout.lower() or "<!doctype" in result.stdout.lower():
            logger.error("Received HTML response instead of JSON")
        
        try:
            response = json.loads(result.stdout)
            logger.info(f"Parsed JSON response: {json.dumps(response, indent=2)}")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            
            # Try to guess what's wrong with the response
            if len(result.stdout.strip()) == 0:
                logger.error("Response is empty - API might be down or blocking requests")
            elif result.stdout.strip()[0] not in "{[":
                logger.error("Response doesn't start with JSON - might be an error page or redirect")
    
    logger.info("Curl stderr:")
    logger.info(result.stderr)
    return False

def test_requests_validation(credentials):
    """Test validation using requests library."""
    player_id = credentials.get("player_id")
    sportsbook_token = credentials.get("sportsbook_token")
    
    if not player_id or not sportsbook_token:
        logger.error("Missing player_id or sportsbook_token in credentials")
        return False
    
    # Extract cookie data from credentials if available
    cookies_data = credentials.get("cookies", {})
    session_cookie = cookies_data.get("session", "")
    session_sig = cookies_data.get("session.sig", "")
    
    # Prepare cookies
    cookies = {}
    if session_cookie:
        cookies['session'] = session_cookie
    if session_sig:
        cookies['session.sig'] = session_sig
    
    # Use the CheckLoggedIn query to validate credentials
    query = {
        "operationName": "CheckLoggedIn",
        "variables": {},
        "query": "query CheckLoggedIn { checkLoggedIn }"
    }
    
    headers = {
        'content-type': 'application/json',
        'x-player-id': player_id,
        'x-sportsbook-token': sportsbook_token,
        'x-tenant': '10CRIC',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'
    }
    
    logger.info("Testing requests validation...")
    logger.info(f"Player ID: {player_id[:8]}... Token: {sportsbook_token[:8]}...")
    logger.info(f"Headers: {headers}")
    logger.info(f"Cookies: {cookies}")
    
    try:
        response = requests.post(
            'https://www.10crics.com/graphql',
            json=query,
            headers=headers,
            cookies=cookies
        )
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response length: {len(response.text)} characters")
        
        if response.text:
            preview = response.text[:200] + ("..." if len(response.text) > 200 else "")
            logger.info(f"Response preview: {preview}")
            
            if "<html" in response.text.lower() or "<!doctype" in response.text.lower():
                logger.error("Received HTML response instead of JSON")
            
            try:
                data = response.json()
                logger.info(f"Parsed JSON response: {json.dumps(data, indent=2)}")
                return True
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
        else:
            logger.error("Empty response")
            
    except Exception as e:
        logger.error(f"Request error: {e}")
    
    return False

def test_direct_api(credentials):
    """Test direct API calls to verify tokens."""
    player_id = credentials.get("player_id")
    sportsbook_token = credentials.get("sportsbook_token")
    
    if not player_id or not sportsbook_token:
        logger.error("Missing player_id or sportsbook_token in credentials")
        return False
    
    # Test endpoints
    endpoints = [
        {
            "name": "Get Casino Games",
            "url": "https://www.10crics.com/api/casino/games",
            "headers": {
                "x-player-id": player_id,
                "x-tenant": "10CRIC"
            }
        },
        {
            "name": "Check Balance",
            "url": f"https://www.10crics.com/api/wallet/balance",
            "headers": {
                "x-player-id": player_id,
                "x-tenant": "10CRIC",
                "x-sportsbook-token": sportsbook_token
            }
        }
    ]
    
    success_count = 0
    
    for endpoint in endpoints:
        try:
            logger.info(f"Testing endpoint: {endpoint['name']} - {endpoint['url']}")
            headers = {**endpoint['headers'], 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            
            logger.info(f"Request headers: {headers}")
            response = requests.get(endpoint['url'], headers=headers)
            
            logger.info(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("Endpoint returned 200 OK")
                preview = response.text[:100] + ("..." if len(response.text) > 100 else "")
                logger.info(f"Response preview: {preview}")
                success_count += 1
            else:
                logger.error(f"Endpoint failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"Error testing endpoint: {e}")
    
    return success_count > 0

def check_network():
    """Check if the website is accessible."""
    try:
        logger.info("Testing network connectivity to 10CRIC...")
        response = requests.get("https://www.10cric.com", 
                               headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response length: {len(response.text)} characters")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Network error: {e}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Debug 10CRIC Authentication")
    parser.add_argument("--curl", action="store_true", help="Test curl validation")
    parser.add_argument("--requests", action="store_true", help="Test requests validation")
    parser.add_argument("--api", action="store_true", help="Test direct API calls")
    parser.add_argument("--network", action="store_true", help="Test network connectivity")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # If no arguments, run all tests
    run_all = args.all or not (args.curl or args.requests or args.api or args.network)
    
    logger.info("Starting authentication debug")
    logger.info(f"Time: {datetime.now().isoformat()}")
    
    # Load credentials
    credentials = load_credentials()
    if not credentials:
        logger.error("No credentials found, cannot continue")
        sys.exit(1)
    
    # Print credential timestamp
    if "timestamp" in credentials:
        logger.info(f"Credentials timestamp: {credentials['timestamp']}")
        
    # Check if credentials exist
    logger.info(f"player_id exists: {bool(credentials.get('player_id'))}")
    logger.info(f"sportsbook_token exists: {bool(credentials.get('sportsbook_token'))}")
    logger.info(f"session cookie exists: {bool(credentials.get('cookies', {}).get('session'))}")
    
    # Run tests
    if run_all or args.network:
        logger.info("\n=== Network Test ===")
        if check_network():
            logger.info("Network test passed")
        else:
            logger.error("Network test failed")
    
    if run_all or args.curl:
        logger.info("\n=== Curl Validation Test ===")
        if test_curl_validation(credentials):
            logger.info("Curl validation test passed")
        else:
            logger.error("Curl validation test failed")
    
    if run_all or args.requests:
        logger.info("\n=== Requests Validation Test ===")
        if test_requests_validation(credentials):
            logger.info("Requests validation test passed")
        else:
            logger.error("Requests validation test failed")
    
    if run_all or args.api:
        logger.info("\n=== Direct API Test ===")
        if test_direct_api(credentials):
            logger.info("API test passed")
        else:
            logger.error("API test failed")
    
    logger.info("\nDebug complete")

if __name__ == "__main__":
    main() 