# auth.py
from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('10cric_auth')

# Load environment variables from .env file
load_dotenv()

def authenticate(headless=False):
    """
    Authenticate with 10CRIC and extract authentication tokens.
    
    Args:
        headless (bool): Whether to run the browser in headless mode
        
    Returns:
        dict: Credentials including player_id and tokens, or None if authentication fails
    """
    # Get credentials from environment variables
    username = os.getenv("CRIC10_USERNAME")
    password = os.getenv("CRIC10_PASSWORD")
    
    if not username or not password:
        logger.error("Credentials not found in .env file")
        return None
    
    logger.info("Starting authentication process...")
    with sync_playwright() as p:
        # Setup browser
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=100
        )
        
        # Setup context with realistic browser configuration
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        try:
            # Navigate to site and login
            if not navigate_and_login(page, username, password):
                return None
            
            # Navigate to sports page to ensure all tokens are loaded
            logger.info("Navigating to sports page to load tokens...")
            page.goto("https://www.my10cric.com/cricket/indian-premier-league", timeout=30000)
            time.sleep(10)
            
            # Extract and process authentication data
            cookies = context.cookies()
            local_storage_items = get_local_storage(page)
            credentials = extract_credentials(local_storage_items, cookies)
            
            if credentials:
                save_credentials(credentials)
                logger.info(f"Authentication successful. Tokens saved to .credentials.json")
                return credentials
            else:
                save_partial_data(local_storage_items, cookies)
                return None
                
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            capture_screenshot(page, "error_state.png")
            return None
        finally:
            browser.close()

def navigate_and_login(page, username, password):
    """Navigate to 10CRIC and complete the login process."""
    try:
        # Navigate to homepage
        logger.info("Navigating to homepage...")
        response = page.goto("https://www.10cric.com", timeout=60000, wait_until='domcontentloaded')
        
        if not response or not response.ok:
            logger.error(f"Failed to load homepage. Status: {response.status if response else 'No response'}")
            return False
        
        # Open login modal
        logger.info("Opening login modal...")
        page.click('text="Log in"')
        time.sleep(1)
        
        # Wait for login form
        logger.info("Waiting for login form...")
        page.wait_for_selector('input[type="email"], input[placeholder="Email"]', timeout=15000)
        
        # Fill credentials
        logger.info("Filling login form...")
        email_selector = 'input[type="email"], input[placeholder="Email"]'
        password_selector = 'input[type="password"], input[placeholder="********"]'
        
        email_element = page.query_selector(email_selector)
        password_element = page.query_selector(password_selector)
        
        if not email_element or not password_element:
            logger.error("Login form fields not found")
            capture_screenshot(page, "login_form_not_found.png")
            return False
            
        email_element.fill(username)
        password_element.fill(password)
        
        # Submit form using multiple fallback methods
        logger.info("Submitting login form...")
        if not submit_login_form(page):
            return False
        
        # Wait for login to complete
        logger.info("Waiting for login to complete...")
        time.sleep(5)
        
        # Verify login success
        if verify_login_success(page):
            logger.info("Login successful!")
        else:
            logger.warning("Could not verify login visually, will continue checking for tokens")
            
        return True
        
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        capture_screenshot(page, "login_error.png")
        return False

def submit_login_form(page):
    """Submit login form using various fallback methods."""
    try:
        # Method 1: Submit by pressing Enter
        try:
            page.focus('input[type="password"]')
            page.press('input[type="password"]', 'Enter')
            logger.info("Submitted form with Enter key")
            return True
        except Exception as e:
            logger.warning(f"Enter key submission failed: {str(e)}")
        
        # Method 2: Try various selectors with JavaScript
        selectors = [
            'button[data-testid="login button"]',
            'button[data-uat="login-submit"]',
            '.SignInWithLoginType_loginBtn__2DAce',
            'form button',
            'button:has-text("Log in")'
        ]
        
        for selector in selectors:
            try:
                page.evaluate(f"() => document.querySelector('{selector}').click()")
                logger.info(f"Clicked login button using selector: {selector}")
                return True
            except:
                continue
        
        # Method 3: Try removing backdrop and finding button
        try:
            page.evaluate("""() => {
                document.querySelectorAll('.MuiBackdrop-root').forEach(b => b.remove());
                Array.from(document.querySelectorAll('button')).find(
                    button => button.textContent.includes('Log in')
                )?.click();
            }""")
            logger.info("Attempted login after removing backdrop")
            return True
        except Exception as e:
            logger.warning(f"Backdrop removal method failed: {str(e)}")
            
        logger.error("All login submission methods failed")
        return False
    except Exception as e:
        logger.error(f"Error submitting form: {str(e)}")
        return False

def verify_login_success(page):
    """Check if login was successful using visual indicators."""
    success_indicators = [
        '.WalletButton_trigger__xmZ98',
        'button[data-uat="header-multiwallet-trigger"]',
        '.balance',
        '.user-balance',
        '.logged-in',
        '.deposit-button',
        'button:has-text("Deposit")'
    ]
    
    # Try each selector
    for selector in success_indicators:
        try:
            if page.query_selector(selector):
                logger.info(f"Login confirmed with indicator: {selector}")
                return True
        except:
            pass
    
    # Try rupee symbol as fallback
    try:
        rupee_elements = page.evaluate('() => {' +
            'return Array.from(document.querySelectorAll("*"))' +
            '.filter(el => el.textContent.includes("₹")).length;' +
        '}')
        if rupee_elements > 0:
            logger.info(f"Login confirmed with ₹ symbol ({rupee_elements} elements)")
            return True
    except:
        pass
        
    return False

def get_local_storage(page):
    """Get localStorage contents from the page."""
    try:
        local_storage = page.evaluate("() => JSON.stringify(Object.entries(localStorage))")
        return json.loads(local_storage)
    except Exception as e:
        logger.error(f"Error extracting localStorage: {str(e)}")
        return []

def extract_credentials(local_storage_items, cookies):
    """Extract authentication tokens from localStorage and cookies."""
    player_id = None
    sportsbook_token = None
    session_cookie = None
    session_sig = None
    
    # Initialize a dictionary to store all credentials
    all_credentials = {
        "timestamp": datetime.now().isoformat(),
        "localStorage": {},
        "cookies": {}
    }
    
    # Extract all localStorage items
    logger.info("Extracting all localStorage items...")
    for key, value in local_storage_items:
        # Store everything in localStorage
        all_credentials["localStorage"][key] = value.strip('"') if isinstance(value, str) else value
        
        # Also track specific keys we know are important
        if key == "sportsbook:token":
            sportsbook_token = value.strip('"')
            logger.info("Found sportsbook:token")
        elif key == "sportsbookPlayerId":
            player_id = value.strip('"')
            logger.info("Found sportsbookPlayerId")
        elif key == "sportsbookToken" and not sportsbook_token:
            sportsbook_token = value.strip('"')
            logger.info("Found sportsbookToken")
    
    # Fallback: search for token keys
    if not sportsbook_token:
        for key, value in local_storage_items:
            if "token" in key.lower() and "sport" in key.lower():
                sportsbook_token = value.strip('"')
                logger.info(f"Using fallback token from key: {key}")
                break
    
    # Fallback: check for player ID alternatives
    if not player_id:
        for key, value in local_storage_items:
            if key == "apc_user_id":
                player_id = value
                logger.info("Using apc_user_id as player_id")
                break
    
    # Extract all cookies
    logger.info("Extracting all cookies...")
    for cookie in cookies:
        cookie_name = cookie.get("name")
        cookie_value = cookie.get("value")
        
        # Store all cookies
        all_credentials["cookies"][cookie_name] = cookie_value
        
        # Track specific cookies we know are important
        if cookie_name == "session":
            session_cookie = cookie_value
            logger.info("Found session cookie")
        elif cookie_name == "session.sig":
            session_sig = cookie_value
            logger.info("Found session signature cookie")
        elif cookie_name == "player_id" and not player_id:
            player_id = cookie_value
            logger.info("Found player_id in cookie")
    
    # Add critical tokens to the main credentials section
    all_credentials["player_id"] = player_id
    all_credentials["sportsbook_token"] = sportsbook_token
    
    if session_cookie:
        all_credentials["session"] = session_cookie
    if session_sig:
        all_credentials["session_sig"] = session_sig
    
    # Validate that we have the minimum required tokens
    if not player_id or not sportsbook_token:
        if session_cookie and player_id:
            logger.info("Using session cookies as fallback")
        else:
            logger.error("Missing critical authentication tokens")
            return None
    
    return all_credentials

def save_credentials(credentials):
    """Save credentials to file."""
    try:
        with open(".credentials.json", "w") as f:
            json.dump(credentials, f, indent=2)
        
        # Also save a complete copy with all data for reference
        with open(".credentials_complete.json", "w") as f:
            json.dump(credentials, f, indent=2)
        
        # Log summary of what we saved
        logger.info("Credentials saved to .credentials.json and .credentials_complete.json")
        
        # Log critical credentials with truncation for security
        if credentials.get("player_id"):
            player_id = credentials["player_id"]
            logger.info(f"Player ID: {player_id[:8]}...")
        
        if credentials.get("sportsbook_token"):
            token = credentials["sportsbook_token"]
            logger.info(f"Sportsbook Token: {token[:8]}...")
        
        # Log counts of other data collected
        localStorage_count = len(credentials.get("localStorage", {}))
        cookies_count = len(credentials.get("cookies", {}))
        logger.info(f"Saved {localStorage_count} localStorage items and {cookies_count} cookies")
        
    except Exception as e:
        logger.error(f"Error saving credentials: {str(e)}")

def save_partial_data(local_storage_items, cookies):
    """Save partial authentication data for debugging."""
    try:
        with open(".partial_credentials.json", "w") as f:
            json.dump({
                "localStorage": {k: v for k, v in local_storage_items},
                "cookies": {cookie.get("name"): cookie.get("value") for cookie in cookies},
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        logger.info("Partial data saved to .partial_credentials.json")
    except Exception as e:
        logger.error(f"Error saving partial data: {str(e)}")

def capture_screenshot(page, filename):
    """Capture a screenshot for debugging."""
    try:
        page.screenshot(path=filename)
        logger.info(f"Screenshot saved: {filename}")
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {str(e)}")

if __name__ == "__main__":
    authenticate()