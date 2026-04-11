import time
import random
import os
from typing import Any
import undetected_chromedriver as uc
from fake_useragent import UserAgent
from core.logger import logger

def human_delay(min_sec: float = 1.5, max_sec: float = 4.5) -> float:
    """
    Random delay to simulate human behavior.
    
    Args:
        min_sec (float): Minimum delay in seconds.
        max_sec (float): Maximum delay in seconds.
        
    Returns:
        float: The actual delay time.
    """
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay

def human_type(element: Any, text: str, min_delay: float = 0.05, max_delay: float = 0.15) -> None:
    """
    Type text character by character like a human.
    
    Args:
        element (Any): The Selenium WebElement to type into.
        text (str): The text to type.
        min_delay (float): Minimum delay between keystrokes.
        max_delay (float): Maximum delay between keystrokes.
    """
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))

def random_scroll(driver: Any) -> None:
    """
    Scrolls the page randomly to simulate human browsing.
    
    Args:
        driver (Any): The Selenium WebDriver instance.
    """
    scroll_amount = random.randint(300, 800)
    driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
    human_delay(1, 3)

def get_driver(profile_path: str) -> Any:
    """
    Initializes and returns an undetected_chromedriver instance with stealth settings.
    
    Args:
        profile_path (str): Path to the Chrome profile directory for this session.
        
    Returns:
        Any: The initialized Selenium WebDriver instance.
    """
    logger.info("Initializing undetected_chromedriver...")
    
    options = uc.ChromeOptions()
    
    ua = UserAgent(os='windows', browsers=['chrome'])
    user_agent = ua.random
    logger.debug(f"Using User-Agent: {user_agent}")
    
    options.add_argument(f'--user-agent={user_agent}')
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,800")
    
    # --- ANTI-DETECTION FLAGS ---
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    
    # Try to initialize UC
    driver = None
    for attempt in range(3):
        try:
            logger.debug(f"UC Init Attempt {attempt+1}/3...")
            driver = uc.Chrome(options=options, version_main=None) # Auto-detect version
            break
        except Exception as e:
            logger.warning(f"UC Init failed: {e}")
            time.sleep(2)
            
    if not driver:
        logger.error("Failed to initialize undetected_chromedriver. Falling back to standard Chrome.")
        from selenium import webdriver
        driver = webdriver.Chrome(options=options)

    # --- JAVASCRIPT STEALTH INJECTION ---
    stealth_js = """
    Object.defineProperty(navigator, 'webdriver', {
      get: () => undefined
    });
    window.navigator.chrome = {
      runtime: {}
    };
    Object.defineProperty(navigator, 'languages', {
      get: () => ['en-US', 'en']
    });
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3]
    });
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": stealth_js
    })
    
    driver.implicitly_wait(10)
    return driver
