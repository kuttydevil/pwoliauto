import os
import json
import threading
from typing import Any
from core.logger import logger

# --- THREADING LOCKS ---
DRIVER_LOCK = threading.Lock()
CLIPBOARD_LOCK = threading.Lock()

# --- CONFIGURATION & ENV ---
os.environ['INSTAGRAM_USERNAME'] = "splcy.den"
os.environ['INSTAGRAM_PASSWORD'] = "9847187662"
os.environ['TARGET_USERNAME'] = "filmatic"
os.environ['GEMINI_API_KEY'] = "AIzaSyALWsDj4gj7YqcwZojaHqv-IQ0CWC-eq8s"
os.environ['MAX_REELS'] = "3000"
os.environ['REPOST_INTERVAL'] = "2000"

INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.environ.get("INSTAGRAM_PASSWORD")
TARGET_USERNAME = os.environ.get("TARGET_USERNAME")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MAX_REELS = int(os.environ.get("MAX_REELS", 3000))
REPOST_INTERVAL = int(os.environ.get("REPOST_INTERVAL", 2000))

# Global Settings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNTS_DATA_DIR = os.path.join(BASE_DIR, "accounts_data")
PROMOTION_IMAGES_DIR = os.path.join(BASE_DIR, "promotion_images")

def setup_account_env(username: str) -> dict[str, str]:
    """
    Creates isolated directory structure for the account and returns path dict.
    
    Args:
        username (str): The Instagram username for the account.
        
    Returns:
        dict[str, str]: A dictionary containing paths for the account's data.
    """
    base_dir = os.path.join(ACCOUNTS_DATA_DIR, username)
    reels_dir = os.path.join(base_dir, "reels")
    
    os.makedirs(reels_dir, exist_ok=True)
    
    paths: dict[str, str] = {
        "base_dir": base_dir,
        "reels_dir": reels_dir,
        "ledger_file": os.path.join(base_dir, "processed_reels.json"),
        "checkpoint_file": os.path.join(base_dir, "checkpoint.json"),
        "cookies_file": os.path.join(base_dir, "cookies.txt"),
        "profile_path": os.path.join(base_dir, f"selenium_session_{username}")
    }
    return paths

# Load Selectors
SELECTORS_FILE = os.path.join(BASE_DIR, "instagram_selectors.json")
SELECTORS: dict[str, Any] = {}
if os.path.exists(SELECTORS_FILE):
    try:
        with open(SELECTORS_FILE, 'r') as f:
            SELECTORS = json.load(f)
        logger.info(f"Loaded selectors from config: {SELECTORS_FILE}")
        logger.debug(f"  Loaded sections: {list(SELECTORS.keys())}")
    except Exception as e:
        logger.error(f"Error loading selectors: {e}")
else:
    logger.warning(f"Selectors file not found at: {SELECTORS_FILE}")

# --- TMDB CONFIG ---
TMDB_API_KEY: str = "9b92d50baa23664db9f1455d0bbc74fc"
TMDB_BASE: str = "https://api.themoviedb.org/3"
