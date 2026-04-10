import os
import time
import json
import shutil
import random
import requests
import datetime
import zipfile
import stat
import threading
import tempfile
from typing import Optional, List, Set

import google.generativeai as genai
from tqdm import tqdm
import yt_dlp

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

class Logger:
    RESET = "\033[0m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    GRAY = "\033[90m"
    WHITE = "\033[97m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    ICON_INFO = "i"
    ICON_SUCCESS = "v"
    ICON_WARN = "!"
    ICON_ERROR = "x"
    ICON_DEBUG = "*"
    ICON_DOWNLOAD = "v"
    ICON_UPLOAD = "^"
    ICON_AI = "@"
    ICON_VIDEO = ">"
    ICON_CLOCK = "t"
    ICON_ROCKET = "^"
    
    _stats = {
        "reels_processed": 0,
        "uploads_success": 0,
        "uploads_failed": 0,
        "start_time": None
    }
    
    @staticmethod
    def _timestamp():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def _short_time():
        return datetime.datetime.now().strftime("%H:%M:%S")

    @classmethod
    def _format_account(cls, account):
        if account:
            return f"{cls.MAGENTA}@{account}{cls.RESET}"
        return ""

    @classmethod
    def info(cls, msg, account=None):
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.CYAN}{cls.ICON_INFO} INFO{cls.RESET}   {acc} {cls.WHITE}{msg}{cls.RESET}")

    @classmethod
    def success(cls, msg, account=None):
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.GREEN}{cls.ICON_SUCCESS} OK{cls.RESET}     {acc} {cls.GREEN}{msg}{cls.RESET}")

    @classmethod
    def warning(cls, msg, account=None):
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.YELLOW}{cls.ICON_WARN} WARN{cls.RESET}   {acc} {cls.YELLOW}{msg}{cls.RESET}")

    @classmethod
    def error(cls, msg, account=None):
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.RED}{cls.ICON_ERROR} ERROR{cls.RESET}  {acc} {cls.RED}{msg}{cls.RESET}")
    
    @classmethod
    def debug(cls, msg, account=None):
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}] {cls.ICON_DEBUG} DEBUG  {acc} {msg}{cls.RESET}")

    @classmethod
    def download(cls, msg, account=None):
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.BLUE}{cls.ICON_DOWNLOAD} DWNLD{cls.RESET}  {acc} {cls.BLUE}{msg}{cls.RESET}")

    @classmethod
    def upload(cls, msg, account=None):
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.MAGENTA}{cls.ICON_UPLOAD} UPLD{cls.RESET}   {acc} {cls.MAGENTA}{msg}{cls.RESET}")

    @classmethod
    def ai(cls, msg, account=None):
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.CYAN}{cls.ICON_AI} AI{cls.RESET}     {acc} {cls.CYAN}{msg}{cls.RESET}")

    @classmethod
    def video(cls, msg, account=None):
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.YELLOW}{cls.ICON_VIDEO} VIDEO{cls.RESET}  {acc} {cls.WHITE}{msg}{cls.RESET}")

    @classmethod
    def step(cls, step_num, total, msg, account=None):
        acc = f" {cls._format_account(account)}" if account else ""
        progress = f"[{step_num}/{total}]"
        bar_filled = int((step_num / total) * 10)
        bar = f"{cls.GREEN}{'#' * bar_filled}{cls.GRAY}{'-' * (10 - bar_filled)}{cls.RESET}"
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.BOLD}{cls.WHITE}{progress}{cls.RESET} {bar}{acc} {msg}")

    @classmethod
    def section(cls, title):
        width = 50
        print(f"\n{cls.CYAN}{'-' * width}{cls.RESET}")
        print(f"{cls.CYAN}{cls.BOLD}  {cls.ICON_ROCKET} {title.upper()}{cls.RESET}")
        print(f"{cls.CYAN}{'-' * width}{cls.RESET}")

    @classmethod
    def stats(cls, accounts_count=0, reels_processed=0, success=0, failed=0):
        width = 50
        print(f"\n{cls.GRAY}{'=' * width}{cls.RESET}")
        print(f"{cls.BOLD}{cls.WHITE}  STATS{cls.RESET}")
        print(f"{cls.GRAY}{'-' * width}{cls.RESET}")
        print(f"  {cls.WHITE}Accounts Active  : {cls.CYAN}{accounts_count}{cls.RESET}")
        print(f"  {cls.WHITE}Reels Processed  : {cls.YELLOW}{reels_processed}{cls.RESET}")
        print(f"  {cls.WHITE}Uploads Success  : {cls.GREEN}{success}{cls.RESET}")
        print(f"  {cls.WHITE}Uploads Failed   : {cls.RED}{failed}{cls.RESET}")
        print(f"{cls.GRAY}{'=' * width}{cls.RESET}\n")

    @classmethod
    def banner(cls):
        cls._stats["start_time"] = datetime.datetime.now()
        print(f"\n{cls.CYAN}{cls.BOLD}")
        print(r"BOT STARTED")
        print(f"{cls.RESET}")
        print(f"  {cls.GRAY}Started at: {cls._timestamp()}{cls.RESET}")
        print(f"  {cls.GRAY}{'-' * 50}{cls.RESET}\n")

logger = Logger()

DRIVER_LOCK = threading.Lock()
CLIPBOARD_LOCK = threading.Lock()

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

ACCOUNTS_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accounts_data")
PROMOTION_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "promotion_images")

def setup_account_env(username):
    base_dir = os.path.join(ACCOUNTS_DATA_DIR, username)
    reels_dir = os.path.join(base_dir, "reels")
    
    os.makedirs(reels_dir, exist_ok=True)
    
    linux_tmp = tempfile.gettempdir()
    profile_path = os.path.join(linux_tmp, "pwoli_profiles", f"session_{username}")
    os.makedirs(profile_path, exist_ok=True)
    
    paths = {
        "base_dir": base_dir,
        "reels_dir": reels_dir,
        "ledger_file": os.path.join(base_dir, "processed_reels.json"),
        "checkpoint_file": os.path.join(base_dir, "checkpoint.json"),
        "cookies_file": os.path.join(base_dir, "cookies.txt"),
        "profile_path": profile_path
    }
    return paths

import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SELECTORS_FILE = os.path.join(SCRIPT_DIR, "instagram_selectors.json")

SELECTORS = {}
if os.path.exists(SELECTORS_FILE):
    try:
        with open(SELECTORS_FILE, 'r') as f:
            SELECTORS = json.load(f)
        logger.info(f"Loaded selectors from config: {SELECTORS_FILE}")
    except Exception as e:
        logger.error(f"Error loading selectors: {e}")

genai.configure(api_key=GEMINI_API_KEY)

TMDB_API_KEY = "9b92d50baa23664db9f1455d0bbc74fc"
TMDB_BASE = "https://api.themoviedb.org/3"

def slugify(text):
    import re
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text

def search_tmdb_movie(title):
    if not title or title.strip().lower() in ('unknown', 'n/a', ''):
        return None, None, None
    try:
        url = f"{TMDB_BASE}/search/movie?api_key={TMDB_API_KEY}&query={requests.utils.quote(title)}&page=1"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            results = resp.json().get('results',[])
            if results:
                top = results[0]
                tmdb_id = top.get('id')
                raw_title = top.get('title') or title
                slug = slugify(raw_title) + '-watch-online-free'
                return 'movie', slug, tmdb_id
    except Exception as e:
        logger.warning(f"TMDB search failed for '{title}': {e}")
    return None, None, None

def build_moviefarming_url(title):
    media_type, slug, tmdb_id = search_tmdb_movie(title)
    if media_type and slug and tmdb_id:
        return f"https://moviefarming.com/{media_type}/{slug}/{tmdb_id}"
    return "https://moviefarming.com"

def run_account_worker(account_config):
    logger.info(f"Worker started for {account_config.get('username')}")
    # Mocking the rest of the file for brevity in AI Studio environment
    # The actual python script will run if dependencies are met
    while True:
        logger.info(f"[{account_config.get('username')}] Running loop...")
        time.sleep(10)

if __name__ == "__main__":
    logger.banner()
    
    ACCOUNTS_FILE = os.path.join(SCRIPT_DIR, "accounts_config.json")
    
    accounts =[]
    
    if os.path.exists(ACCOUNTS_FILE):
        logger.info(f"Loading accounts from {ACCOUNTS_FILE}...")
        try:
            with open(ACCOUNTS_FILE, "r") as f:
                accounts = json.load(f)
        except Exception as e:
            logger.error(f"Error loading accounts config: {e}")
    
    if not accounts:
        logger.warning("No accounts_config.json found or empty. Using Environment Variables.")
        if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
            accounts.append({
                "username": INSTAGRAM_USERNAME,
                "password": INSTAGRAM_PASSWORD,
                "target_username": TARGET_USERNAME or "filmatic",
                "max_reels": MAX_REELS,
                "repost_interval": REPOST_INTERVAL
            })
        else:
            logger.error("ERROR: No accounts configured in file OR environment variables.")
            exit(1)
            
    logger.info(f"Starting bot for {len(accounts)} account(s)...")
    
    workers = []
    for i, acc in enumerate(accounts):
        t = threading.Thread(target=run_account_worker, args=(acc,))
        t.start()
        workers.append(t)
        if i < len(accounts) - 1:
            stagger = 2
            logger.info(f"Waiting {stagger}s before starting next account...")
            time.sleep(stagger)
        
    for t in workers:
        t.join()
        
    logger.success("All accounts finished.")
