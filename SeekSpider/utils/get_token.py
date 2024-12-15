import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlencode

# Set up logger
logger = logging.getLogger(__name__)

def get_login_url():
    """
    Generate the SEEK login URL with all required parameters
    """
    # Base URL
    base_url = "https://login.seek.com/login"

    # OAuth related parameters
    oauth_params = {
        "state": "hKFo2SAxWm5HRkk2SXRrdV9MbVJCMDlSanRnT25KUTI2TUxQT6FupWxvZ2luo3RpZNkgS2NxbnNPcFJ3b2hjazNsMXc4X210dkJzSnF1c3RpY3ajY2lk2SB5R0JWZ2U2Nks1TkpwU041dTcxZlU5MFZjVGxFQVNOdQ",
        "client": "yGBVge66K5NJpSN5u71fU90VcTlEASNu",
        "protocol": "oauth2",
        "redirect_uri": "https://www.seek.com.au/oauth/callback/",
        "scope": "openid profile email offline_access",
        "audience": "https://seek/api/candidate",
        "fragment": "/oauth/login?locale=au&language=en&realm=Username-Password-Authentication&da_cdt=visid_0193ca29fffa001b674d12d70ff105075004e06d00bd0-sesid_1734263570427-hbvid_343632b1_80c7_4dd4_b86b_c06c742dd53b-tempAcqSessionId_1734263007912-tempAcqVisitorId_343632b180c74dd4b86bc06c742dd53b",
        "ui_locales": "en",
        "JobseekerSessionId": "7414413c-ae74-4fdc-8aa2-23eea861b700",
        "language": "en-AU",
        "response_type": "code",
        "response_mode": "query",
        "nonce": "dkhJNE5vazAyUHV+dnp6ZHFKc1Foc0V2fi1XRG1SZDJjTjdhaDVxcExSZA==",
        "code_challenge": "O_laoBNR7C689MmojgR_Fl-7aHc_YgVw1qYoZ1CvEgw",
        "code_challenge_method": "S256",
        "auth0Client": "eyJuYW1lIjoiYXV0aDAtc3BhLWpzIiwidmVyc2lvbiI6IjEuMjIuMyJ9"
    }

    # Additional parameters after hash
    hash_params = {
        "locale": "au",
        "language": "en",
        "realm": "Username-Password-Authentication",
        "da_cdt": "visid_0193ca29fffa001b674d12d70ff105075004e06d00bd0-sesid_1734263570427-hbvid_343632b1_80c7_4dd4_b86b_c06c742dd53b-tempAcqSessionId_1734263007912-tempAcqVisitorId_343632b180c74dd4b86bc06c742dd53b"
    }

    # Construct URL
    url = f"{base_url}?{urlencode(oauth_params)}#{urlencode(hash_params)}"
    return url


def login_seek(username, password):
    """
    Login to SEEK using Selenium WebDriver

    Args:
        username (str): Your SEEK account username/email
        password (str): Your SEEK account password

    Returns:
        webdriver: Browser session if login successful
    """
    try:
        # Initialize Chrome WebDriver with proper service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)

        # Navigate to SEEK login page
        login_url = get_login_url()
        driver.get(login_url)

        # Wait for the login form to be loaded (maximum 20 seconds)
        wait = WebDriverWait(driver, 20)

        # Wait and find email input field using ID
        email_input = wait.until(
            EC.presence_of_element_located((By.ID, "emailAddress"))
        )
        email_input.send_keys(username)

        # Find password input field using ID
        password_input = wait.until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_input.send_keys(password)

        # Find and click the sign in button using data-cy attribute
        sign_in_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-cy='login']"))
        )
        sign_in_button.click()

        # Wait for successful login (check for typical element on logged-in page)
        try:
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-automation="account name"]'))
            )
            logger.info("Successfully logged in!")
            return driver

        except TimeoutException:
            logger.error("Login might have failed - please check credentials")
            driver.quit()
            return None

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return None


def get_auth_token(username, password):
    """
    Get authentication token from SEEK
    
    Args:
        username (str): SEEK account username/email
        password (str): SEEK account password
        
    Returns:
        str: Authentication token if successful, None otherwise
    """
    browser_session = None
    try:
        browser_session = login_seek(username, password)
        if browser_session:
            auth0_token = browser_session.execute_script(
                "var items = {}; "
                "for (var i = 0, len = localStorage.length; i < len; ++i) { "
                "    var key = localStorage.key(i); "
                "    if(key.startsWith('@@auth0spajs@@')) { "
                "        items[key] = localStorage.getItem(key); "
                "    } "
                "} "
                "return items;"
            )
            
            for value in auth0_token.values():
                try:
                    import json
                    token_data = json.loads(value)
                    access_token = token_data.get('body', {}).get('access_token')
                    if access_token:
                        logger.info("Successfully obtained authentication token")
                        return f"Bearer {access_token}"
                except json.JSONDecodeError:
                    logger.error("Error parsing JSON token data")
                    continue
                except Exception as e:
                    logger.error(f"Error processing token: {str(e)}")
                    continue
                    
            logger.error("No valid token found in browser session")
            return None
    finally:
        if browser_session:
            browser_session.quit()

