from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlencode
import time
from SeekSpider.core.logger import Logger

logger = Logger('get_token')

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
    try:
        # Initialize Chrome WebDriver with proper service and headless mode
        from subprocess import check_output

        # Get system architecture
        arch = check_output(['uname', '-m']).decode().strip()

        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        if arch == 'aarch64':
            # For ARM64 architecture
            logger.info("Detected ARM64 architecture...")
            options.binary_location = "/usr/bin/chromium-browser"
            service = Service('/usr/bin/chromedriver')
        else:
            # For other architectures, use WebDriver Manager
            logger.info(f"Detected {arch} architecture...")
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=options)

        # Set page load timeout
        driver.set_page_load_timeout(30)
        logger.info("Browser initialized...")

        # Navigate to login page and handle form...
        login_url = get_login_url()
        driver.get(login_url)
        
        wait = WebDriverWait(driver, 30)
        logger.info("Navigating to login page...")

        try:
            email_input = wait.until(EC.presence_of_element_located((By.ID, "emailAddress")))
            logger.info("Email input field found...")
            email_input.clear()
            email_input.send_keys(username)
            logger.info("Email entered...")
        except TimeoutException:
            logger.error("Email input field not found - please check the login page")
            driver.quit()
            return None

        try:
            password_input = wait.until(EC.presence_of_element_located((By.ID, "password")))
            logger.info("Password input field found...")
            password_input.clear()
            password_input.send_keys(password)
            logger.info("Password entered...")

            time.sleep(2)
        except TimeoutException:
            logger.error("Password input field not found - please check the login page")
            driver.quit()
            return None

        try:
            sign_in_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-cy='login']"))
            )
            logger.info("Login button found...")
            sign_in_button.click()
            logger.info("Login button clicked...")
            
            time.sleep(5)
            logger.info("Waiting for login to complete...")
        except TimeoutException:
            logger.error("Login button not found - please check the login page")
            driver.quit()
            return None

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-automation="account name"]')))
            
            # Get and print auth0 token info
            logger.info("\nAuth0 Token:")
            auth0_token = driver.execute_script(
                "var items = {}; "
                "for (var i = 0, len = localStorage.length; i < len; ++i) { "
                "    var key = localStorage.key(i); "
                "    if(key.startsWith('@@auth0spajs@@')) { "
                "        items[key] = localStorage.getItem(key); "
                "    } "
                "} "
                "return items;"
            )
            for key, value in auth0_token.items():
                try:
                    import json
                    token_data = json.loads(value)
                    access_token = token_data.get('body', {}).get('access_token')
                    logger.info("\nAccess Token:")
                    logger.info(access_token)
                except json.JSONDecodeError:
                    logger.error("Error parsing JSON token data")
                except Exception as e:
                    logger.error(f"Error processing token: {str(e)}")

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
        logger.info("Getting authorization token...")
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
                    
            logger.warning("No valid token found in browser session")
            return None
    finally:
        if browser_session:
            browser_session.quit()

