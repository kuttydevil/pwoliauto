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
from typing import Optional, List, Set, Any, Tuple, Dict

import google.generativeai as genai
from tqdm import tqdm
import yt_dlp
import static_ffmpeg
static_ffmpeg.add_paths()

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# --- EXCEPTIONS ---
class NetHunterException(Exception):
    """Base exception for NetHunter."""
    pass

class InstagramLoginError(NetHunterException):
    """Raised when Instagram login fails."""
    pass

class VideoDownloadError(NetHunterException):
    """Raised when video download fails."""
    pass

class VideoProcessingError(NetHunterException):
    """Raised when FFmpeg processing fails."""
    pass

class AIProcessingError(NetHunterException):
    """Raised when AI caption generation fails."""
    pass

# --- LOGGING SETUP ---
class Logger:
    """
    Professional-grade structured logger for NetHunter.
    Provides colored console output with Unicode icons and session statistics.
    """
    # ANSI Colors
    RESET: str = "\033[0m"
    CYAN: str = "\033[96m"
    GREEN: str = "\033[92m"
    YELLOW: str = "\033[93m"
    RED: str = "\033[91m"
    GRAY: str = "\033[90m"
    WHITE: str = "\033[97m"
    MAGENTA: str = "\033[95m"
    BLUE: str = "\033[94m"
    BOLD: str = "\033[1m"
    DIM: str = "\033[2m"
    
    # Icons (Unicode)
    ICON_INFO: str = "ℹ"
    ICON_SUCCESS: str = "✓"
    ICON_WARN: str = "⚠"
    ICON_ERROR: str = "✗"
    ICON_DEBUG: str = "⚙"
    ICON_DOWNLOAD: str = "↓"
    ICON_UPLOAD: str = "↑"
    ICON_AI: str = "🤖"
    ICON_VIDEO: str = "🎬"
    ICON_CLOCK: str = "⏱"
    ICON_ROCKET: str = "🚀"
    
    # Stats tracking
    _stats: dict[str, Any] = {
        "reels_processed": 0,
        "uploads_success": 0,
        "uploads_failed": 0,
        "start_time": None
    }
    
    @staticmethod
    def _timestamp() -> str:
        """Returns the current timestamp in YYYY-MM-DD HH:MM:SS format."""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def _short_time() -> str:
        """Returns the current time in HH:MM:SS format."""
        return datetime.datetime.now().strftime("%H:%M:%S")

    @classmethod
    def _format_account(cls, account: Optional[str]) -> str:
        """Formats the account name for logging."""
        if account:
            return f"{cls.MAGENTA}[@{account}]{cls.RESET}"
        return ""

    @classmethod
    def info(cls, msg: str, account: Optional[str] = None) -> None:
        """Logs an informational message."""
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.CYAN}{cls.ICON_INFO} INFO{cls.RESET}   {acc} {cls.WHITE}{msg}{cls.RESET}")

    @classmethod
    def success(cls, msg: str, account: Optional[str] = None) -> None:
        """Logs a success message."""
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.GREEN}{cls.ICON_SUCCESS} OK{cls.RESET}     {acc} {cls.GREEN}{msg}{cls.RESET}")

    @classmethod
    def warning(cls, msg: str, account: Optional[str] = None) -> None:
        """Logs a warning message."""
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.YELLOW}{cls.ICON_WARN} WARN{cls.RESET}   {acc} {cls.YELLOW}{msg}{cls.RESET}")

    @classmethod
    def error(cls, msg: str, account: Optional[str] = None) -> None:
        """Logs an error message."""
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.RED}{cls.ICON_ERROR} ERROR{cls.RESET}  {acc} {cls.RED}{msg}{cls.RESET}")
    
    @classmethod
    def debug(cls, msg: str, account: Optional[str] = None) -> None:
        """Logs a debug message."""
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}] {cls.ICON_DEBUG} DEBUG  {acc} {msg}{cls.RESET}")

    @classmethod
    def download(cls, msg: str, account: Optional[str] = None) -> None:
        """Logs a download-related message."""
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.BLUE}{cls.ICON_DOWNLOAD} DWNLD{cls.RESET}  {acc} {cls.BLUE}{msg}{cls.RESET}")

    @classmethod
    def upload(cls, msg: str, account: Optional[str] = None) -> None:
        """Logs an upload-related message."""
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.MAGENTA}{cls.ICON_UPLOAD} UPLD{cls.RESET}   {acc} {cls.MAGENTA}{msg}{cls.RESET}")

    @classmethod
    def ai(cls, msg: str, account: Optional[str] = None) -> None:
        """Logs an AI-related message."""
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.CYAN}{cls.ICON_AI} AI{cls.RESET}     {acc} {cls.CYAN}{msg}{cls.RESET}")

    @classmethod
    def video(cls, msg: str, account: Optional[str] = None) -> None:
        """Logs a video processing message."""
        acc = f" {cls._format_account(account)}" if account else ""
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.YELLOW}{cls.ICON_VIDEO} VIDEO{cls.RESET}  {acc} {cls.WHITE}{msg}{cls.RESET}")

    @classmethod
    def step(cls, step_num: int, total: int, msg: str, account: Optional[str] = None) -> None:
        """Logs a step in a multi-step process with a progress bar."""
        acc = f" {cls._format_account(account)}" if account else ""
        progress = f"[{step_num}/{total}]"
        bar_filled = int((step_num / total) * 10)
        bar = f"{cls.GREEN}{'█' * bar_filled}{cls.GRAY}{'░' * (10 - bar_filled)}{cls.RESET}"
        print(f"{cls.GRAY}[{cls._short_time()}]{cls.RESET} {cls.BOLD}{cls.WHITE}{progress}{cls.RESET} {bar}{acc} {msg}")

    @classmethod
    def section(cls, title: str) -> None:
        """Logs a section header."""
        width = 50
        print(f"\n{cls.CYAN}{'─' * width}{cls.RESET}")
        print(f"{cls.CYAN}{cls.BOLD}  {cls.ICON_ROCKET} {title.upper()}{cls.RESET}")
        print(f"{cls.CYAN}{'─' * width}{cls.RESET}")

    @classmethod
    def stats(cls, accounts_count: int = 0, reels_processed: int = 0, success: int = 0, failed: int = 0) -> None:
        """Logs the current session statistics."""
        width = 50
        print(f"\n{cls.GRAY}{'═' * width}{cls.RESET}")
        print(f"{cls.BOLD}{cls.WHITE}  📊 SESSION STATS{cls.RESET}")
        print(f"{cls.GRAY}{'─' * width}{cls.RESET}")
        print(f"  {cls.WHITE}Accounts Active  : {cls.CYAN}{accounts_count}{cls.RESET}")
        print(f"  {cls.WHITE}Reels Processed  : {cls.YELLOW}{reels_processed}{cls.RESET}")
        print(f"  {cls.WHITE}Uploads Success  : {cls.GREEN}{success}{cls.RESET}")
        print(f"  {cls.WHITE}Uploads Failed   : {cls.RED}{failed}{cls.RESET}")
        print(f"{cls.GRAY}{'═' * width}{cls.RESET}\n")

    @classmethod
    def banner(cls) -> None:
        """Logs the application banner."""
        cls._stats["start_time"] = datetime.datetime.now()
        print(f"\n{cls.CYAN}{cls.BOLD}")
        print(r"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██████╗ ██╗    ██╗ ██████╗ ██╗     ██╗                      ║
    ║   ██╔══██╗██║    ██║██╔═══██╗██║     ██║                      ║
    ║   ██████╔╝██║ █╗ ██║██║   ██║██║     ██║                      ║
    ║   ██╔═══╝ ██║███╗██║██║   ██║██║     ██║                      ║
    ║   ██║     ╚███╔███╔╝╚██████╔╝███████╗██║                      ║
    ║   ╚═╝      ╚══╝╚══╝  ╚═════╝ ╚══════╝╚═╝                      ║
    ║                                                               ║
    ║   ░█▀█░█░█░▀█▀░█▀█░░░█▀▄░█▀▀░█▀█░█▀█░█▀▀░▀█▀░█▀▀░█▀▄░        ║
    ║   ░█▀█░█░█░░█░░█░█░░░█▀▄░█▀▀░█▀▀░█░█░▀▀█░░█░░█▀▀░█▀▄░        ║
    ║   ░▀░▀░▀▀▀░░▀░░▀▀▀░░░▀░▀░▀▀▀░▀░░░▀▀▀░▀▀▀░░▀░░▀▀▀░▀░▀░        ║
    ║                                                               ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  🎬 Instagram Automation Bot  │  v3.0 PRO                     ║
    ║  🔗 pwolimovies.vercel.app    │  Multi-Account Engine         ║
    ╚═══════════════════════════════════════════════════════════════╝
        """)
        print(f"{cls.RESET}")
        print(f"  {cls.GRAY}Started at: {cls._timestamp()}{cls.RESET}")
        print(f"  {cls.GRAY}{'─' * 50}{cls.RESET}\n")

logger = Logger()

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

# Other Settings
# Global Settings
ACCOUNTS_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accounts_data")
PROMOTION_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "promotion_images")

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

import subprocess

# Use absolute path for selectors file (relative to script location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SELECTORS_FILE = os.path.join(SCRIPT_DIR, "instagram_selectors.json")

# Load Selectors
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

# Configure the AI for generating captions
genai.configure(api_key=GEMINI_API_KEY)

# --- TMDB CONFIG ---
TMDB_API_KEY: str = "9b92d50baa23664db9f1455d0bbc74fc"
TMDB_BASE: str = "https://api.themoviedb.org/3"


# --- TMDB HELPERS ---
def slugify(text: str) -> str:
    """
    Convert a title to an SEO-friendly slug.
    
    Args:
        text (str): The raw text to slugify.
        
    Returns:
        str: The slugified text.
    """
    import re
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text

def search_tmdb_movie(title: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Search TMDB for a movie or TV show by title.
    
    Args:
        title (str): The title of the movie or TV show to search for.
        
    Returns:
        Tuple[Optional[str], Optional[str], Optional[int]]: A tuple containing:
            - media_type ('movie' or 'tv')
            - slug (SEO-friendly URL slug)
            - tmdb_id (The TMDB ID)
            Returns (None, None, None) on failure.
    """
    if not title or title.strip().lower() in ('unknown', 'n/a', ''):
        return None, None, None
    try:
        # Try movie first
        url = f"{TMDB_BASE}/search/movie?api_key={TMDB_API_KEY}&query={requests.utils.quote(title)}&page=1"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            results = resp.json().get('results', [])
            if results:
                top = results[0]
                tmdb_id = top.get('id')
                raw_title = top.get('title') or title
                slug = slugify(raw_title) + '-watch-online-free'
                return 'movie', slug, tmdb_id
        # Try TV
        url = f"{TMDB_BASE}/search/tv?api_key={TMDB_API_KEY}&query={requests.utils.quote(title)}&page=1"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            results = resp.json().get('results', [])
            if results:
                top = results[0]
                tmdb_id = top.get('id')
                raw_title = top.get('name') or title
                slug = slugify(raw_title) + '-watch-online-free'
                return 'tv', slug, tmdb_id
    except Exception as e:
        logger.warning(f"TMDB search failed for '{title}': {e}")
    return None, None, None

def build_moviefarming_url(title: str) -> str:
    """
    Returns the full moviefarming.com URL for a given movie/tv title.
    Falls back to a generic search URL if TMDB lookup fails.
    
    Args:
        title (str): The title of the movie or TV show.
        
    Returns:
        str: The full moviefarming URL.
    """
    media_type, slug, tmdb_id = search_tmdb_movie(title)
    if media_type and slug and tmdb_id:
        return f"https://moviefarming.com/{media_type}/{slug}/{tmdb_id}"
    # Generic fallback
    return "https://moviefarming.com"


# --- GEMINI HELPERS ---
def upload_to_gemini(path: str, mime_type: Optional[str] = None) -> Any:
    """
    Uploads the given file to Gemini.
    
    Args:
        path (str): The local path to the file.
        mime_type (Optional[str]): The MIME type of the file.
        
    Returns:
        Any: The uploaded Gemini file object.
    """
    file = genai.upload_file(path, mime_type=mime_type)
    logger.info(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def wait_for_files_active(files: List[Any]) -> None:
    """
    Waits for the given Gemini files to be active.
    
    Args:
        files (List[Any]): A list of Gemini file objects.
        
    Raises:
        AIProcessingError: If a file fails to process.
    """
    logger.info("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        wait_time = random.uniform(8, 15)
        with tqdm(total=wait_time, unit="s", desc="AI Processing", bar_format="{desc}:{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as progress_bar:
          while file.state.name == "PROCESSING":
              time.sleep(1)
              progress_bar.update(1)
              file = genai.get_file(name)
          if file.state.name != "ACTIVE":
              raise AIProcessingError(f"File {file.name} failed to process: {file.state.name}")
    logger.success("...all files ready")

import cv2
import pyperclip
from selenium.webdriver.common.keys import Keys

def extract_frames(video_path: str, num_frames: int = 10) -> List[str]:
    """
    Extracts 'num_frames' equally spaced frames from the video.
    
    Args:
        video_path (str): The path to the video file.
        num_frames (int): The number of frames to extract.
        
    Returns:
        List[str]: A list of file paths to the extracted frames.
    """
    logger.debug(f"Extracting {num_frames} frames from {video_path}...")
    frames = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Error: Could not open video for frame extraction.")
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        logger.error("Error: Video has 0 frames.")
        return []

    interval = total_frames // num_frames
    output_dir = os.path.dirname(video_path)
    base_name = os.path.splitext(os.path.basename(video_path))[0]

    for i in range(num_frames):
        frame_idx = i * interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            frame_path = os.path.join(output_dir, f"{base_name}_frame_{i}.jpg")
            cv2.imwrite(frame_path, frame)
            frames.append(frame_path)
    
    cap.release()
    logger.debug(f"Extracted {len(frames)} frames.")
    return frames

def generate_caption(video_path: str, custom_prompt: Optional[str] = None, username: Optional[str] = None) -> str:
    """
    Generate a caption for the video using Gemini AI.
    Uses the per-account custom_prompt if provided.
    Identifies the movie and appends the MovieFarming URL.
    Returns a fallback caption on failure.
    
    Args:
        video_path (str): Path to the video file.
        custom_prompt (Optional[str]): Custom prompt to override the default.
        username (Optional[str]): The account username for logging.
        
    Returns:
        str: The generated caption text.
    """
    logger.info("Generating caption with Gemini...", account=username)
    
    uploaded_files: List[Any] = []
    frame_paths: List[str] = []
    
    try:
        # --- STEP 1: EXTRACT AND UPLOAD FRAMES ---
        logger.info("Extracting frames for AI analysis...", account=username)
        frames = extract_frames(video_path, num_frames=10)
        frame_paths = frames[:]
        
        if frames:
            logger.info(f"Uploading {len(frames)} frames to Gemini...", account=username)
            for frame_path in frames:
                try:
                    f = upload_to_gemini(frame_path, mime_type="image/jpeg")
                    uploaded_files.append(f)
                except Exception as e:
                    logger.warning(f"Failed to upload frame {frame_path}: {e}", account=username)
        
        if not uploaded_files:
            # Fallback: try single thumbnail
            thumbnail_path = video_path.replace(".mp4", "_thumb.jpg")
            if os.path.exists(thumbnail_path):
                logger.warning("Frame upload failed. Using single thumbnail.", account=username)
                uploaded_files.append(upload_to_gemini(thumbnail_path, mime_type="image/jpeg"))
            else:
                raise AIProcessingError("No frames or thumbnail available for AI analysis.")

        wait_for_files_active(uploaded_files)

        # --- STEP 2: BUILD PROMPT ---
        # Default MovieFarming dark psychology prompt (Maximum CTR Edition)
        default_prompt = """
You are a Viral Growth Manipulator for MovieFarming — a hidden, decentralized 4K streaming archive that mainstream platforms are actively trying to delete from the internet.
Your job: EXPLOIT human psychology to force a click to moviefarming.com.

PSYCHOLOGICAL WEAPONS:
1. THE LOOPHOLE (Reactance): Frame the site as a "shadowbanned loophole." Use words like "illegal," "hidden," "before it's gone," "they're trying to patch this."
2. ZEIGARNIK EFFECT (The Gap): State the intense conflict in the scene, then CUT it off. Refuse to tell them what happens next. Make the outcome the "reward" for clicking.
3. TRIBALISM (Elite vs. Sheep): People paying for Netflix/Prime are "sheep" or "victims." MovieFarming users are "insiders" who have escaped the system.
4. LOSS AVERSION: Every second they watch ads or pay for subs, they are LOSING life and money. movieFarming is the gain.

STRUCTURE:
[LINE 1]: THE CURIOSITY VOID — 3-6 words that punch the viewer in the gut. Reference the tension, but don't resolve it. (e.g., "the silence after he did it... 💀")
[LINE 2]: blank line
[LINE 3]: THE EXPOSE — Reveal the "secret" source. Use unhinged/conspiratorial tone. Mention "MovieFarming" or "The Archive."
[LINE 4]: THE SEARCH CTA — "Search 'MovieFarming' on Google if the link is banned. No ads, No signup, 100% Free."
[LINE 5]: Movie: [Name] ([Year])
[LINE 6]: Hashtags (max 6, high velocity)

MOVIE TITLE FORMAT (CRITICAL):
On the LAST LINE, write exactly: MOVIE_TITLE: [The movie name]

RULES:
- SOUND LIKE A HUMAN texting a group chat at 3 AM. No grammar perfection. Use slang like "bro," "fr," "nah," "actually."
- AVOID BOT WORDS: "Discover," "Unlock," "Cinematic," "Experience," "Masterpiece." If you use these, you fail.
- USE UNICODE EMOJIS SPARINGLY: 💀 🔥 😱 🤫 � 🎬 ⬇️
- Max 2200 chars.

EXAMPLE:
nah he actually went through with it... 💀
.
netflix tried to ban the site i used to watch this. the loophole still works for now.
search 'moviefarming' on google to find the secret archive. no ads. no fees.
.
Movie: [Name]
.
#movies #fyp #viral #moviefarming
MOVIE_TITLE: [Name]

Analyze frames, identify the movie tension, generate ONE unhinged caption.
"""

        prompt_text = custom_prompt if custom_prompt else default_prompt

        # --- STEP 3: CALL AI ---
        model = genai.GenerativeModel(
            model_name="gemma-3-27b-it",
            generation_config={
                "temperature": random.uniform(0.85, 1.2),
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1500,
                "response_mime_type": "text/plain",
            },
        )

        chat_session = model.start_chat(
            history=[{"role": "user", "parts": uploaded_files + [prompt_text]}]
        )
        time.sleep(random.uniform(1, 3))
        response = chat_session.send_message("Generate the caption now. Follow the format exactly.")
        raw_response = response.text.strip()
        logger.debug(f"Raw AI response (first 200 chars): {raw_response[:200]}", account=username)

        # --- STEP 4: CLEAN FILLER ---
        lines = raw_response.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip().lower()
            if stripped.startswith(("okay", "here is", "here's", "sure,", "caption:", "certainly", "of course")):
                continue
            cleaned_lines.append(line)
        final_caption = "\n".join(cleaned_lines).strip()

        # --- STEP 5: EXTRACT MOVIE TITLE & BUILD MOVIEFARMING URL ---
        import re
        movie_title = None
        # Look for the MOVIE_TITLE: tag first (our structured output)
        match = re.search(r'MOVIE_TITLE:\s*(.+)', final_caption, re.IGNORECASE)
        if match:
            movie_title = match.group(1).strip()
            # Remove the MOVIE_TITLE line from the visible caption
            final_caption = re.sub(r'\nMOVIE_TITLE:\s*.+', '', final_caption).strip()
            logger.info(f"Extracted movie title: '{movie_title}'", account=username)
        else:
            # Fallback: look for "Movie:" line
            match2 = re.search(r'Movie:\s*([^\n]+)', final_caption, re.IGNORECASE)
            if match2:
                movie_title = match2.group(1).strip()
                # Clean year from title e.g. "Dune Part Two (2024)" -> "Dune Part Two"
                movie_title = re.sub(r'\s*\(\d{4}\)', '', movie_title).strip()
                logger.info(f"Extracted movie title (fallback): '{movie_title}'", account=username)

        # Build URL
        mf_url = None
        if movie_title:
            logger.info(f"Looking up '{movie_title}' on TMDB...", account=username)
            mf_url = build_moviefarming_url(movie_title)
            logger.success(f"MovieFarming URL: {mf_url}", account=username)
        else:
            logger.warning("Could not extract movie title from AI response. Using generic URL.", account=username)
            mf_url = "https://moviefarming.com"

        # --- STEP 6: INJECT URL INTO CAPTION ---
        # Replace any leftover old domain references
        final_caption = re.sub(r'pwolimovies\.vercel\.app', mf_url, final_caption, flags=re.IGNORECASE)
        final_caption = re.sub(r'pwolimovies\.com', mf_url, final_caption, flags=re.IGNORECASE)
        
        # Append MovieFarming URL if not already present
        if 'moviefarming.com' not in final_caption:
            final_caption = final_caption.rstrip() + f"\n.\n🎬 Watch FREE in 4K → {mf_url}"

        logger.success(f"Final caption ({len(final_caption)} chars): {final_caption[:120]}...", account=username)
        return final_caption

    except Exception as e:
        logger.error(f"Caption generation failed: {e}", account=username)
        # FALLBACK CAPTION — always returns something usable
        fallback = (
            "this scene actually broke me 💀\n"
            ".\n"
            "Full 4K version is free on the secret archive — no ads, no signup.\n"
            "⬇️ Link in bio → moviefarming.com\n"
            ".\n"
            "#movies #viral #fyp #freestream #4k #cinema"
        )
        logger.warning("Using fallback caption.", account=username)
        return fallback
    finally:
        # Clean up uploaded frame files
        for fp in frame_paths:
            try:
                if os.path.exists(fp):
                    os.remove(fp)
            except:
                pass


def get_video_info(input_path: str) -> Optional[dict[str, Any]]:
    """
    Returns width, height, duration, r_frame_rate, sample_rate, bit_rate
    
    Args:
        input_path (str): Path to the video file.
        
    Returns:
        Optional[dict[str, Any]]: A dictionary containing video stream information, or None on failure.
    """
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-select_streams", "v:0", 
        "-show_entries", "stream=width,height,r_frame_rate,duration,bit_rate", 
        "-of", "json", 
        input_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        stream = info['streams'][0]
        return stream
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return None

def process_video_ffmpeg(input_path: str) -> str:
    """
    Applies HDR filter, Audio modification, and appends a 3-second promo outro.
    
    Args:
        input_path (str): Path to the original video file.
        
    Returns:
        str: Path to the processed video file.
    """
    logger.info(f"Processing video: {input_path}")
    
    # Ensure promo image directory exists
    if not os.path.exists(PROMOTION_IMAGES_DIR):
        try:
            os.makedirs(PROMOTION_IMAGES_DIR)
            print(f"Created promotion images directory: {PROMOTION_IMAGES_DIR}")
        except Exception as e:
            logger.error(f"Failed to create promotion dir: {e}")

    # Check for promo image
    promo_image = None
    if os.path.exists(PROMOTION_IMAGES_DIR):
        images = [f for f in os.listdir(PROMOTION_IMAGES_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if images:
            promo_image = os.path.join(PROMOTION_IMAGES_DIR, random.choice(images))
            logger.info(f"Selected promo image: {os.path.basename(promo_image)}")
    
    if not promo_image:
        logger.warning("No promo image found. Applying only audio/visual filters.")
    
    output_path = os.path.splitext(input_path)[0] + "_processed.mp4"
    
    # Get Info
    info = get_video_info(input_path)
    if not info:
        print("Could not get video info. Skipping processing.")
        return input_path

    width = info.get('width')
    height = info.get('height')
    
    # Build Filter Complex
    
    cmd = ["ffmpeg", "-y", "-i", input_path]
    
    filter_complex = []
    
    # 1. Main Video Processing
    # Force standard framerate (30fps) to avoid variable framerate issues
    filter_complex.append(f"[0:v]fps=30,eq=saturation=1.3:contrast=1.1:brightness=0.02[v_main]")
    
    # Audio Processing (Obfuscation)
    # asetrate changes pitch and speed. 1.05x pitch.
    # atempo compensates speed.
    filter_complex.append(f"[0:a]asetrate=44100*1.03,atempo=1/1.03,volume=1.05[a_main]")
    
    if promo_image:
        cmd.extend(["-loop", "1", "-t", "3", "-i", promo_image])
        
        # Scale image to video resolution (Crop to fill)
        # Force 30fps for the image too
        filter_complex.append(f"[1:v]fps=30,scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1[v_promo]")
        
        # Generate silent audio for the 3s outro
        filter_complex.append(f"anullsrc=r=44100:cl=stereo:d=3[a_promo]")
        
        # Concat with unsafe=1 to handle potentially slight timestamp mismatches
        filter_complex.append(f"[v_main][a_main][v_promo][a_promo]concat=n=2:v=1:a=1:unsafe=1[outv][outa]")
        
        cmd.extend([
            "-filter_complex", ";".join(filter_complex),
            "-map", "[outv]", "-map", "[outa]"
        ])
    else:
        # Just filters
        cmd.extend([
            "-filter_complex", ";".join(filter_complex),
            "-map", "[v_main]", "-map", "[a_main]"
        ])
        
    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-vsync", "2", # Duplicate or drop frames to match constant framerate
        output_path
    ])
    
    print(f"Running ffmpeg with command: {' '.join(cmd)}")
    try:
        # We need to ensure ffmpeg is in path. static_ffmpeg adds it.
        # Don't capture output, let it flow to console for progress bar
        subprocess.run(cmd, check=True) 
        logger.success(f"Processing complete: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed with error code {e.returncode}!")
        return input_path # Fallback to original



# --- SELENIUM SETUP (ANTI-DETECTION) ---
import undetected_chromedriver as uc
from fake_useragent import UserAgent

# Human-like delay helper
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
    Random scroll to simulate human browsing.
    
    Args:
        driver (Any): The Selenium WebDriver instance.
    """
    scroll_amount = random.randint(100, 500)
    driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
    time.sleep(random.uniform(0.5, 1.5))

def get_driver(profile_path: str) -> Any:
    """
    Initialize undetected Chrome with maximum anti-bot detection evasion.
    
    Args:
        profile_path (str): Path to the Chrome user data directory for persistence.
        
    Returns:
        Any: The initialized Selenium WebDriver instance.
    """
    logger.section("INITIALIZING STEALTH BROWSER")
    
    # Desktop-only User Agents (NO mobile - breaks XPath selectors)
    DESKTOP_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    ]
    user_agent = random.choice(DESKTOP_USER_AGENTS)
    logger.info(f"User-Agent: {user_agent[:60]}...")

    # Create options
    options = uc.ChromeOptions()
    
    # --- ANTI-DETECTION FLAGS ---
    options.add_argument('--headless=new')  # New headless mode (less detectable)
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    options.add_argument('--no-first-run')
    options.add_argument('--no-service-autorun')
    options.add_argument('--password-store=basic')
    options.add_argument(f'--user-agent={user_agent}')
    
    # Realistic window size (common resolution)
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    # Performance flags
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--mute-audio')
    
    # Persistent profile
    os.makedirs(profile_path, exist_ok=True)
    options.add_argument(f'--user-data-dir={profile_path}')
    
    # Enable performance logging for network capture
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    # Acquire DRIVER_LOCK to prevent parallel Chrome launch crashes
    # Multiple threads launching Chrome simultaneously causes "chrome not reachable"
    with DRIVER_LOCK:
        logger.info("Acquired DRIVER_LOCK, launching Chrome...")
        for attempt in range(1, 4):  # 3 attempts
            try:
                driver = uc.Chrome(options=options, use_subprocess=True, version_main=145)
                logger.success(f"Undetected Chrome initialized (Forced v145, attempt {attempt})!")
                break
            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {e}")
                if attempt < 3:
                    logger.warning(f"Retrying Chrome init in 10s...")
                    time.sleep(10)
                else:
                    logger.warning("All UC attempts failed. Falling back to standard ChromeDriver...")
                    try:
                        from webdriver_manager.chrome import ChromeDriverManager
                        chromedriver_path = ChromeDriverManager().install()
                        service = Service(executable_path=chromedriver_path)
                        driver = webdriver.Chrome(service=service, options=options)
                        logger.success("Standard ChromeDriver initialized.")
                    except Exception as e2:
                        logger.error(f"ChromeDriver fallback also failed: {e2}")
                        raise e2
        # Give Chrome time to fully stabilize before releasing lock
        time.sleep(5)
    
    # --- JAVASCRIPT STEALTH INJECTION ---
    stealth_js = """
    // Overwrite the 'webdriver' property
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    
    // Overwrite the 'plugins' property
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    
    // Overwrite the 'languages' property
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    
    // Chrome runtime mock
    window.chrome = {
        runtime: {}
    };
    
    // Permissions mock
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    
    // Console log for verification
    console.log('[STEALTH] Anti-detection scripts injected successfully');
    """
    
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': stealth_js})
        logger.success("Stealth JS injected!")
    except Exception as e:
        logger.warning(f"CDP stealth injection failed: {e}")
        # Fallback: execute after page load
        try:
            driver.execute_script(stealth_js)
        except:
            pass
    
    driver.set_window_size(1920, 1080)
    logger.info(f"Profile: {profile_path}")
    logger.success("Browser ready with MAXIMUM anti-detection!")
    
    return driver

# --- SELENIUM ACTIONS ---

def selenium_login(driver: Any, username: str, password: str) -> None:
    """
    Logs into Instagram using the provided credentials.
    Handles 'Save Info' and 'Notifications' popups.
    
    Args:
        driver (Any): The Selenium WebDriver instance.
        username (str): Instagram username.
        password (str): Instagram password.
    """
    driver.get("https://www.instagram.com/")
    human_delay(4, 7)  # Human-like wait for page load
    
    # Load login selectors from config
    login_s = SELECTORS.get('login', {})
    
    # Check if already logged in
    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//a[@href='/direct/inbox/']")))
        logger.info("Already logged in.")
        return
    except TimeoutException:
        pass

    logger.info("Logging in...")
    try:
        # Use selectors from JSON, fallback to defaults
        sel_username = login_s.get('username', "//input[@name='username']")
        sel_password = login_s.get('password', "//input[@name='password']")
        sel_submit = login_s.get('submit_btn', "//button[@type='submit']")
        
        logger.debug("Waiting 5s for page load...")
        time.sleep(5)

        username_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, sel_username)))
        logger.debug(f"Found username input with {sel_username}")
        password_input = driver.find_element(By.XPATH, sel_password)
        logger.debug(f"Found password input with {sel_password}")
        
        human_type(username_input, username)  # Type like a human
        human_delay(0.5, 1.5)
        human_type(password_input, password)  # Type like a human
        logger.debug("Credentials entered (human-like typing).")
        
        login_btn = driver.find_element(By.XPATH, sel_submit)
        logger.debug(f"Found submit button with {sel_submit}")
        human_delay(0.5, 1.5)  # Small delay before click
        login_btn.click()
        logger.debug("Clicked login button.")
        
        human_delay(6, 10)  # Wait for login to process
        
        # Handle "Save Info"
        try:
            sel_save_info = login_s.get('save_info_not_now', "//button[text()='Not now']")
            save_info_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, sel_save_info)))
            save_info_btn.click()
            logger.debug("Clicked 'Not Now' on Save Info.")
            time.sleep(2)
        except:
            logger.debug("Save info popup not found or skipped.")
            pass
            
        # Handle "Notifications"
        try:
            sel_notifications = login_s.get('notifications_not_now', "//button[text()='Not Now']")
            not_now_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, sel_notifications)))
            not_now_btn.click()
            logger.debug("Clicked 'Not Now' on Notifications.")
        except:
            logger.debug("Notifications popup not found or skipped.")
            pass

        logger.success("Login sequence complete.")

    except Exception as e:
        logger.error(f"Login failed: {e}")
        # Capture critical page source or current URL before quitting/continuing
        try:
             logger.error(f"Current URL at failure: {driver.current_url}")
        except: pass
        raise InstagramLoginError(f"Login failed: {e}")


# --- DOWNLOAD HELPERS ---
def save_cookies_netscape(driver: Any, filepath: str) -> None:
    """
    Save Selenium cookies to a Netscape format file for yt-dlp.
    
    Args:
        driver (Any): The Selenium WebDriver instance.
        filepath (str): Path to save the cookies file.
    """
    with open(filepath, 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        for cookie in driver.get_cookies():
            domain = cookie.get('domain', '')
            flag = 'TRUE' if domain.startswith('.') else 'FALSE'
            path = cookie.get('path', '/')
            secure = 'TRUE' if cookie.get('secure') else 'FALSE'
            expiration = str(int(cookie.get('expiry', time.time() + 3600)))
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")

def download_with_ytdlp(driver: Any, url: str, output_folder: str, cookie_file: str) -> Optional[str]:
    """
    Attempt to download a video using yt-dlp with Selenium cookies.
    
    Args:
        driver (Any): The Selenium WebDriver instance.
        url (str): The URL of the video to download.
        output_folder (str): Directory to save the video.
        cookie_file (str): Path to the temporary cookie file.
        
    Returns:
        Optional[str]: Path to the downloaded video, or None if failed.
    """
    logger.info(f"Attempting download with yt-dlp: {url}")
    # cookie_file is passed explicitly now
    try:
        save_cookies_netscape(driver, cookie_file)
        
        ydl_opts = {
            'outtmpl': os.path.join(output_folder, '%(id)s.%(ext)s'),
            'format': 'bestvideo+bestaudio/best', 
            'merge_output_format': 'mp4',
            'cookiefile': cookie_file,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.debug("Extracting info...")
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            final_filename = base + ".mp4" # Enforced by merge_output_format
            
            if os.path.exists(final_filename):
                 logger.success(f"yt-dlp success: {final_filename}")
                 return final_filename
            elif os.path.exists(filename):
                 return filename
            
    except Exception as e:
        logger.warning(f"yt-dlp failed: {e}")
    finally:
        if os.path.exists(cookie_file):
            try: os.remove(cookie_file)
            except: pass
    return None

def selenium_download_video(driver: Any, reel_link: str, output_folder: str, cookie_file: str, grid_thumbnail_url: Optional[str] = None) -> Optional[str]:
    """
    Downloads a reel by intercepting the network traffic to find the MP4 URL.
    Strictly filters for video/mp4 mimeType to avoid downloading images.
    Also downloads the thumbnail image (preferring grid thumbnail if provided).
    
    Args:
        driver (Any): The Selenium WebDriver instance.
        reel_link (str): The URL of the Instagram reel.
        output_folder (str): Directory to save the downloaded files.
        cookie_file (str): Path to the temporary cookie file.
        grid_thumbnail_url (Optional[str]): URL of the thumbnail image.
        
    Returns:
        Optional[str]: Path to the downloaded and processed video, or None if failed.
    """
    logger.info(f"Attempting to download {reel_link}")
    
    # Clear previous logs
    driver.get_log('performance')
    
    driver.get(reel_link)
    time.sleep(8) # Wait for video to start buffering
    
    video_url = None
    
    # Use grid thumbnail if provided, otherwise try to extract from meta tag
    if grid_thumbnail_url:
        thumbnail_url = grid_thumbnail_url
        logger.debug(f"Using grid thumbnail: {thumbnail_url[:50]}...")
    else:
        thumbnail_url = None
        try:
            thumbnail_url = driver.find_element(By.XPATH, "//meta[@property='og:image']").get_attribute("content")
            logger.debug(f"Found thumbnail URL: {thumbnail_url[:50]}...")
        except:
            logger.debug("Could not find thumbnail meta tag.")

    # [NEW] Try yt-dlp first (Best for Audio/Video merge)
    ytdlp_path = download_with_ytdlp(driver, reel_link, output_folder, cookie_file)
    if ytdlp_path:
        # If yt-dlp worked, we still ensure thumbnail is downloaded below if needed, 
        # or we just assume yt-dlp might have got it? 
        # Actually, let's keep the manual thumbnail download logic at the end or do it here.
        # The original code did thumbnail downloading at the very end. 
        # Let's verify if we need to run that logic.
        
        # Download thumbnail if found and not using yt-dlp's thumb
        if thumbnail_url:
             try:
                # Use same basename as ytdlp file
                base, _ = os.path.splitext(ytdlp_path)
                thumb_path = base + "_thumb.jpg"
                if not os.path.exists(thumb_path):
                    with open(thumb_path, 'wb') as f:
                        f.write(requests.get(thumbnail_url).content)
                    print(f"Thumbnail saved to {thumb_path}")
             except Exception as e:
                 print(f"Error saving thumbnail: {e}")
                 
        return process_video_ffmpeg(ytdlp_path)

    # 1. Scan network logs for mp4 response (Fallback)
    try:
        logs = driver.get_log('performance')
        for entry in logs:
            try:
                message = json.loads(entry['message'])['message']
                if message['method'] == 'Network.responseReceived':
                    response = message['params']['response']
                    mime_type = response.get('mimeType', '')
                    url = response.get('url', '')
                    
                    if 'video' in mime_type or 'mp4' in mime_type:
                        # Ensure it's not a small blob or segment if possible, but usually main video comes this way
                        if 'cdninstagram.com' in url:
                            # Strip byte-range parameters to get the full video, not just chunks
                            import re
                            url = re.sub(r'[&?]bytestart=\d+', '', url)
                            url = re.sub(r'[&?]byteend=\d+', '', url)
                            video_url = url
                            print(f"Found video URL via Network Response (Mime: {mime_type}): {video_url[:50]}...")
                            break
            except:
                continue
                     
    except Exception as e:
        print(f"Error analyzing logs: {e}")

    # Fallback: Check for requests if response capture failed (less reliable but useful)
    if not video_url:
         try:
            for entry in logs:
                try:
                    message = json.loads(entry['message'])['message']
                    if message['method'] == 'Network.requestWillBeSent':
                        url = message['params']['request']['url']
                        # Strict extension check
                        if '.mp4?' in url or url.endswith('.mp4'):
                             video_url = url
                             print(f"Found video URL via Network Request: {video_url[:50]}...")
                             break
                except: continue
         except: pass

    if not video_url:
        print("Failed to find video URL in network logs. Skipping.")
        return None

    try:
        # Download using requests
        filename = reel_link.rstrip('/').split('/')[-1] + ".mp4"
        filepath = os.path.join(output_folder, filename)
        
        s = requests.Session()
        s.headers.update({
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Referer": "https://www.instagram.com/"
        })
        for cookie in driver.get_cookies():
            s.cookies.set(cookie['name'], cookie['value'])
            
        print("Downloading content...")
        r = s.get(video_url, stream=True)
        r.raise_for_status()
        
        # Validate content type again
        if 'video' not in r.headers.get('Content-Type', ''):
             print(f"Warning: Downloaded content type is {r.headers.get('Content-Type')}, not video.")
             return None

        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(filepath)
        if file_size < 100000: # Less than 100KB is probably wrong (thumbnail or error)
             print(f"Downloaded file is too small ({file_size} bytes). likely not the video.")
             os.remove(filepath)
             return None
                
        print(f"Downloaded directly to {filepath} ({file_size/1024/1024:.2f} MB)")
        
        # Download thumbnail if available
        thumbnail_path = None
        if thumbnail_url:
            try:
                thumb_filename = reel_link.rstrip('/').split('/')[-1] + "_thumb.jpg"
                thumbnail_path = os.path.join(output_folder, thumb_filename)
                
                thumb_r = s.get(thumbnail_url, stream=True)
                thumb_r.raise_for_status()
                
                with open(thumbnail_path, 'wb') as f:
                    for chunk in thumb_r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                print(f"Downloaded thumbnail to {thumbnail_path}")
            except Exception as e:
                print(f"Failed to download thumbnail: {e}")
                thumbnail_path = None
        
        return process_video_ffmpeg(filepath)
    except Exception as e:
        print(f"Failed to download video: {e}")
        return None

def selenium_upload_reel(driver: Any, video_path: str, caption: str, thumbnail_path: Optional[str] = None) -> None:
    """
    Uploads a reel via the Instagram Web UI.
    
    Args:
        driver (Any): The Selenium WebDriver instance.
        video_path (str): Path to the processed video file.
        caption (str): The caption to inject.
        thumbnail_path (Optional[str]): Path to a custom thumbnail (not currently used in UI flow).
        
    Raises:
        Exception: If the upload process fails.
    """
    logger.info("Starting upload process...")
    
    # helper for selectors
    nav_s = SELECTORS.get('navigation', {})
    up_s = SELECTORS.get('upload_flow', {})
    
    try:
        # 1. Click 'Create' button (Sidebar)
        try:
            sel = nav_s.get('sidebar_create_btn', "//*[@aria-label='New post']")
            create_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, sel)))
            # Sometimes we click the parent a tag
            try:
                create_btn.click() 
            except:
                create_btn.find_element(By.XPATH, "./ancestor::a | ./ancestor::div[@role='button']").click()
            print("Clicked Create button.")
        except TimeoutException:
            # Try alt
            sel_alt = nav_s.get('sidebar_create_btn_alt', "//span[contains(text(), 'Create')]")
            print("Trying alternate Create button selector...")
            create_btn = driver.find_element(By.XPATH, sel_alt)
            create_btn.click()
            
        time.sleep(3)
        
        # 1.5 Handle 'Post' menu selection
        try:
            print("Checking for 'Post' menu option...")
            sel_post = nav_s.get('create_menu_post', "//span[contains(text(), 'Post')]")
            post_option = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, sel_post))
            )
            post_option.click()
            print("Clicked 'Post' from Create menu.")
            time.sleep(3)
        except:
            print("'Post' option not found or not needed. Assuming modal is open.")

        # 2. Select from computer (Input file)
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Create new post')]")))
            print("Create Modal is open.")
        except:
            print("Warning: Modal header not found, attempting input search anyway.")
            
        try:
            sel_input = nav_s.get('file_input', "//input[@type='file']")
            file_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, sel_input)))
        except TimeoutException:
            print("Input not found instantly. Trying to click 'Select from computer' first.")
            sel_select_btn = nav_s.get('select_from_computer_btn', "//button[contains(text(), 'Select from computer')]")
            driver.find_element(By.XPATH, sel_select_btn).click()
            time.sleep(1)
            file_input = driver.find_element(By.XPATH, nav_s.get('file_input', "//input[@type='file']"))
            
        file_input.send_keys(os.path.abspath(video_path))
        logger.debug(f"File {os.path.basename(video_path)} sent to input.")
        time.sleep(5) 

        # 2.5 Handle "Video posts are now shared as reels" OK button
        try:
             logger.debug("Checking for informational popup...")
             sel_ok = up_s.get('popup_reels_ok', "//button[text()='OK']")
             ok_btn = WebDriverWait(driver, 5).until(
                 EC.element_to_be_clickable((By.XPATH, sel_ok))
             )
             ok_btn.click()
             logger.debug("Dismissed 'Video posts are now shared as reels' popup.")
             time.sleep(2)
        except:
             logger.debug("No informational popup found.")
        
        # 3. Crop / Next
        logger.info("Waiting for Crop/Next screen...")
        
        # 3.1 Select "Original" Crop
        try:
             from selenium.webdriver.common.action_chains import ActionChains
             logger.debug("Setting crop to Original...")
             time.sleep(4)  # Generous wait for crop screen
             
             # --- STEP 1: OPEN CROP MENU ---
             crop_btn = None
             selectors_btn = [
                 up_s.get('crop_select_btn', "//button[@type='button'][.//svg[@aria-label='Select crop']]"),
                 up_s.get('crop_select_btn_classes', "//button[contains(@class, '_aswp')]"),
                 up_s.get('crop_select_btn_absolute', "/html/body/div[4]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[2]/div[1]/div/div/div/div/div[1]/div/div[2]/div")
             ]
             
             found_btn = False
             for sel in selectors_btn:
                 try:
                     crop_btn = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, sel)))
                     logger.debug(f"Found crop button with selector: {sel}")
                     found_btn = True
                     break
                 except:
                     continue
             
             if not found_btn:
                 raise Exception("Could not find Crop Button with any selector.")

             # Click Crop Button (Try ActionChains, then JS)
             try:
                 ActionChains(driver).move_to_element(crop_btn).pause(0.5).click().perform()
             except:
                 driver.execute_script("arguments[0].click();", crop_btn)
             time.sleep(2)
             
             # --- STEP 2: VERIFY MENU OPENED ---
             # We check if the 'Original' text is visible.
             is_menu_open = False
             try:
                 WebDriverWait(driver, 2).until(EC.visibility_of_element_located((By.XPATH, "//span[contains(text(), 'Original')]")))
                 is_menu_open = True
                 logger.debug("Crop menu verified open.")
             except:
                 logger.warning("Menu verify failed. Retrying click with JS...")
                 driver.execute_script("arguments[0].click();", crop_btn)
                 time.sleep(2)

             # --- STEP 3: SELECT ORIGINAL ---
             selectors_orig = [
                 up_s.get('crop_original_option', "//span[contains(text(), 'Original')]/ancestor::div[@role='button']"),
                 up_s.get('crop_original_option_text', "//span[text()='Original']"),
                 up_s.get('crop_original_option_absolute', "/html/body/div[4]/div[1]/div/div[3]/div/div/div/div/div/div/div/div[2]/div[1]/div/div/div/div/div[1]/div/div[1]/div/div[1]")
             ]
             
             original_option = None
             found_orig = False
             for sel in selectors_orig:
                 try:
                     original_option = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, sel)))
                     logger.debug(f"Found Original option with selector: {sel}")
                     found_orig = True
                     break
                 except:
                     continue

             if not found_orig:
                 raise Exception("Could not find 'Original' option! Menu might not be open.")

             # Click Original Option
             try:
                 ActionChains(driver).move_to_element(original_option).pause(0.5).click().perform()
             except:
                 driver.execute_script("arguments[0].click();", original_option)
             
             logger.success("Successfully selected 'Original' crop.")
             time.sleep(2)

        except Exception as e:
             logger.error(f"CRITICAL ERROR SETTING CROP: {e}")
             driver.save_screenshot(os.path.join(os.getcwd(), "crop_critical_final.png"))
             # STOP HERE if allowed, or sleep to let user intervene?
             # For now, we will wait a long time so user can see it failed, or they can manually click.
             logger.warning("!!! PAUSING FOR 60 SECONDS SO YOU CAN FIX CROP MANUALLY !!!")
             time.sleep(60)
             # Proceeding after manual fix...


        # Click "Next" (Crop screen)
        sel_next = up_s.get('next_btn', "//div[text()='Next']")
        next_btn_1 = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, sel_next)))
        next_btn_1.click()
        logger.debug("Clicked Next (Crop).")
        time.sleep(3)
        
        # Click "Next" (Edit screen)
        # Usually same selector works
        sel_edit_next = up_s.get('edit_next_btn', "//div[text()='Next']")
        next_btn_2 = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, sel_edit_next)))
        next_btn_2.click()
        logger.debug("Clicked Next (Edit).")
        time.sleep(3)
        
        # 4. Caption & Share
        # Caption area is a contenteditable div - MUST click first then inject
        logger.info("Waiting for caption input area...")
        
        caption_area = None
        caption_selectors = [
            up_s.get('caption_area', "//div[@data-lexical-editor='true']"),
            up_s.get('caption_area_alt', "//div[@role='textbox' and contains(@aria-label, 'Write a caption')]"),
            up_s.get('caption_area_legacy', "//div[contains(@class, 'notranslate') and @role='textbox']"),
            "//div[@role='textbox']",
            "//*[@aria-label='Write a caption...']",
            "//div[contains(@class, 'notranslate')]",
        ]
        for sel in caption_selectors:
            try:
                caption_area = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, sel)))
                logger.debug(f"Caption area found with: {sel}")
                break
            except:
                continue
        
        if not caption_area:
            raise NetHunterException("CRITICAL: Could not find caption textarea with any selector!")
        
        # Scroll to and focus the caption area
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", caption_area)
        time.sleep(0.5)
        caption_area.click()
        time.sleep(1)
        
        # --- BULLETPROOF CAPTION INJECTION (3-layer fallback) ---
        logger.info(f"Injecting caption ({len(caption)} chars)...", account=getattr(driver, 'account_name', 'default'))
        caption_injected = False
        
        # Helper to check if box is REALLY filled
        def is_box_filled(el: Any) -> bool:
            try:
                # contenteditable text is messy, check all sources
                val = (el.text or el.get_attribute('textContent') or el.get_attribute('innerText') or "").strip()
                # Exclude placeholder "Write a caption..."
                if val == "Write a caption..." or not val:
                    return False
                return len(val) > 10
            except:
                return False

        # LAYER 1: Clipboard paste (best for emojis + newlines)
        with CLIPBOARD_LOCK:
            try:
                logger.debug("LAYER 1: Attempting Clipboard Paste...")
                pyperclip.copy(caption)
                time.sleep(0.5)
                # Clear existing
                caption_area.send_keys(Keys.CONTROL + 'a')
                time.sleep(0.1)
                caption_area.send_keys(Keys.DELETE)
                time.sleep(0.1)
                # Paste
                actions = ActionChains(driver)
                actions.click(caption_area).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                time.sleep(2.5)
                
                if is_box_filled(caption_area):
                    logger.success("Caption pasted OK via Clipboard.")
                    caption_injected = True
                else:
                    logger.warning("Paste verification failed. Retrying with fresh click...")
                    caption_area.click()
                    time.sleep(0.5)
                    ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                    time.sleep(2)
                    if is_box_filled(caption_area):
                        logger.success("Caption pasted OK on second attempt.")
                        caption_injected = True
            except Exception as e:
                logger.warning(f"Clipboard paste layer failed: {e}")
        
        # LAYER 2: JS direct injection (fallback for clipboard failures)
        if not caption_injected:
            logger.warning("LAYER 2: Attempting JS injection...")
            try:
                driver.execute_script("""
                    var el = arguments[0];
                    var txt = arguments[1];
                    el.focus();
                    el.innerText = txt;
                    // Fire all events to wake up React/Redux
                    el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, data: txt }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key: ' ', code: 'Space' }));
                    el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, cancelable: true, key: ' ', code: 'Space' }));
                """, caption_area, caption)
                time.sleep(2)
                if is_box_filled(caption_area):
                    logger.success("JS injection successful.")
                    caption_injected = True
            except Exception as e:
                logger.warning(f"JS injection layer failed: {e}")
        
        # LAYER 3: Human-type fallback (slowest, most reliable direct keys)
        if not caption_injected:
            logger.warning("LAYER 3: Attempting Direct Keys (slow)...")
            try:
                caption_area.click()
                time.sleep(0.5)
                # Filter out problematic emojis for direct send_keys if needed
                # For now just try chunks
                chunk_size = 30
                for i in range(0, len(caption), chunk_size):
                    chunk = caption[i:i + chunk_size]
                    try:
                        caption_area.send_keys(chunk)
                        time.sleep(random.uniform(0.1, 0.3))
                    except:
                        # Fallback for that specific chunk to clipboard
                        with CLIPBOARD_LOCK:
                            pyperclip.copy(chunk)
                            ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                            time.sleep(0.5)
                
                if is_box_filled(caption_area):
                    logger.success("Direct keys successful.")
                    caption_injected = True
            except Exception as e:
                logger.error(f"Direct keys fallback failed: {e}")
        
        if not caption_injected:
            logger.error("!!! ALL INJECTION METHODS FAILED !!!")
        
        # IMPORTANT: Small delay to let Instagram process the text before the Share button becomes active/records the text
        time.sleep(3)
        
        # Click Share (with explicit wait - was previously broken with driver.find_element)
        sel_share = up_s.get('share_btn', "//div[text()='Share']")
        share_btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, sel_share)))
        share_btn.click()
        logger.info("Clicked Share. Waiting for upload to finish...")
        
        # 5. Wait for 'Reel shared' confirmation
        sel_confirm = up_s.get('upload_confirm', "//span[contains(text(), 'shared')] | //img[contains(@alt, 'Animated checkmark')]")
        WebDriverWait(driver, 300).until(EC.presence_of_element_located((By.XPATH, sel_confirm)))
        logger.success("Upload confirmed!")
        
        # Close the modal
        try:
            sel_close = up_s.get('close_modal_btn', "//*[@aria-label='Close']")
            close_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, sel_close)))
            close_btn.click()
        except:
            print("Could not close modal via button. Reloading page.")
            driver.get("https://www.instagram.com/")

    except Exception as e:
        print(f"Upload failed: {e}")
        driver.save_screenshot(os.path.join(os.getcwd(), "upload_error.png"))
        raise NetHunterException(f"Upload failed: {e}")

# --- STATE MANAGEMENT ---
def load_ledger(ledger_file: str) -> set[str]:
    """
    Load the set of processed reel IDs from the ledger file.
    
    Args:
        ledger_file (str): Path to the ledger JSON file.
        
    Returns:
        set[str]: A set of processed reel IDs.
    """
    try:
        with open(ledger_file, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_ledger(ledger: set[str], ledger_file: str) -> None:
    """
    Save the set of processed reel IDs to the ledger file.
    
    Args:
        ledger (set[str]): The set of processed reel IDs.
        ledger_file (str): Path to the ledger JSON file.
    """
    with open(ledger_file, "w") as f:
        json.dump(list(ledger), f, indent=4)

def load_checkpoint(checkpoint_file: str) -> Optional[str]:
    """
    Load the last processed reel ID from the checkpoint file.
    
    Args:
        checkpoint_file (str): Path to the checkpoint JSON file.
        
    Returns:
        Optional[str]: The last processed reel ID, or None.
    """
    try:
        with open(checkpoint_file, "r") as f:
            return json.load(f).get("last_processed_reel_id")
    except:
        return None

def save_checkpoint(reel_id: str, checkpoint_file: str) -> None:
    """
    Save the last processed reel ID to the checkpoint file.
    
    Args:
        reel_id (str): The reel ID to save.
        checkpoint_file (str): Path to the checkpoint JSON file.
    """
    with open(checkpoint_file, "w") as f:
        json.dump({"last_processed_reel_id": str(reel_id)}, f)

# --- WORKER LOGIC ---
def get_reels_from_profile(driver: Any, username: str, max_count: int = 10) -> List[Tuple[str, Optional[str]]]:
    """
    Scrapes reel URLs and their thumbnail URLs from a user profile.
    
    Args:
        driver (Any): The Selenium WebDriver instance.
        username (str): The target Instagram username to scrape.
        max_count (int): Maximum number of reels to scrape.
        
    Returns:
        List[Tuple[str, Optional[str]]]: A list of tuples containing (reel_url, thumbnail_url).
    """
    print(f"Scraping reels from {username}...")
    driver.get(f"https://www.instagram.com/{username}/reels/")
    time.sleep(5)
    
    reels_data = {}  # {reel_url: thumbnail_url}
    scroll_attempts = 0
    max_scrolls = 5
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while len(reels_data) < max_count and scroll_attempts < max_scrolls:
        # Find all reel links and their associated images
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/reel/')]")
        for link in links:
            try:
                href = link.get_attribute("href")
                # Try to find the thumbnail image within this link
                try:
                    img = link.find_element(By.TAG_NAME, "img")
                    thumbnail_url = img.get_attribute("src")
                    reels_data[href] = thumbnail_url
                except:
                    # If no image found, store without thumbnail
                    if href not in reels_data:
                        reels_data[href] = None
            except:
                continue
        
        if len(reels_data) >= max_count:
            break
            
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            scroll_attempts += 1
        last_height = new_height
        
        last_height = new_height
        
    logger.info(f"Found {len(reels_data)} reels.", account=username)
    # Return as list of tuples: (reel_url, thumbnail_url)
    return list(reels_data.items())[:max_count]

def run_account_worker(account_config: dict[str, Any]) -> None:
    """
    Worker function to run the bot for a specific account in its own thread.
    
    Args:
        account_config (dict[str, Any]): Configuration dictionary for the account.
    """
    username = account_config.get("username")
    password = account_config.get("password")
    target_username = account_config.get("target_username")
    max_reels = int(account_config.get("max_reels", 100))
    repost_interval = int(account_config.get("repost_interval", 2000))
    custom_prompt = account_config.get("custom_prompt")

    if not username or not password:
        print(f"Error: Missing credentials for account config: {account_config}")
        logger.error(f"Missing credentials for account config: {account_config}")
        return

    # Setup Isolated Environment
    paths = setup_account_env(username)
    
    logger.info("Starting worker...", account=username)
    logger.debug(f"Data Dir: {paths['base_dir']}", account=username)

    driver = None
    try:
        # Initialize Driver with unique profile path
        driver = get_driver(paths['profile_path'])
        driver.account_name = username
        
        # Login
        selenium_login(driver, username, password)
        
        while True:
            # Load Ledger
            ledger = load_ledger(paths['ledger_file'])
            
            # Scrape
            reels_data = get_reels_from_profile(driver, target_username, max_count=max_reels)
            # reels_data is list of tuples (url, thumbnail)
            
            for reel_url, grid_thumbnail_url in reels_data:
                reel_id = reel_url.rstrip('/').split('/')[-1]
                
                if reel_id in ledger:
                    logger.info(f"Skipping already processed reel {reel_id}", account=username)
                    continue
                    
                logger.info(f"Processing Reel: {reel_id}", account=username)
                
                try:
                    # 1. Download
                    # Pass reels directory and specific cookies file
                    video_path = selenium_download_video(driver, reel_url, paths['reels_dir'], paths['cookies_file'], grid_thumbnail_url)
                    if not video_path:
                        logger.warning("Download failed, skipping.", account=username)
                        continue
                    
                    # 2. Generate Caption
                    caption = generate_caption(video_path, custom_prompt=custom_prompt, username=username)
                    
                    # 3. Upload
                    selenium_upload_reel(driver, video_path, caption)
                    
                    # 4. Update Ledger
                    ledger.add(reel_id)
                    save_ledger(ledger, paths['ledger_file'])
                    save_checkpoint(reel_id, paths['checkpoint_file'])
                    
                    # 5. Cleanup
                    try:
                        os.remove(video_path)
                        base_name = os.path.splitext(os.path.basename(video_path))[0]
                        frames_dir = os.path.dirname(video_path)
                        for file in os.listdir(frames_dir):
                            if file.startswith(f"{base_name}_frame_") and file.endswith(".jpg"):
                                os.remove(os.path.join(frames_dir, file))
                                
                        thumb_path = video_path.replace(".mp4", ".jpg")
                        if os.path.exists(thumb_path): os.remove(thumb_path)
                        thumb_path_2 = video_path.replace(".mp4", "_thumb.jpg")
                        if os.path.exists(thumb_path_2): os.remove(thumb_path_2)

                    except Exception as e:
                        logger.warning(f"Cleanup warning: {e}", account=username)
                    
                    # Sleep
                    wait_check = random.uniform(repost_interval - 500, repost_interval + 500)
                    wait_check = max(60, wait_check) # Min 1 minute
                    logger.info(f"Sleeping for {wait_check} seconds...", account=username)
                    time.sleep(wait_check)

                except InstagramLoginError as e:
                    logger.error(f"Login error for {reel_id}: {e}", account=username)
                    time.sleep(300) # Wait longer for login issues
                except AIProcessingError as e:
                    logger.error(f"AI processing error for {reel_id}: {e}", account=username)
                    time.sleep(60)
                except NetHunterException as e:
                    logger.error(f"NetHunter error processing {reel_id}: {e}", account=username)
                    time.sleep(60)
                except Exception as e:
                    logger.error(f"Unexpected error processing {reel_id}: {e}", account=username)
                    time.sleep(60)
            
            logger.info("Finished processing current batch. Waiting before next profile scan...", account=username)
            time.sleep(3600) # Check profile again after 1 hour

    except Exception as e:
        logger.error(f"CRITICAL WORKER ERROR: {e}", account=username)
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        logger.success("Worker finished.", account=username)


if __name__ == "__main__":
    logger.banner()
    
    ACCOUNTS_FILE = os.path.join(SCRIPT_DIR, "accounts_config.json")
    
    accounts = []
    
    # Check for config file
    if os.path.exists(ACCOUNTS_FILE):
        logger.info(f"Loading accounts from {ACCOUNTS_FILE}...")
        try:
            with open(ACCOUNTS_FILE, "r") as f:
                accounts = json.load(f)
        except Exception as e:
            logger.error(f"Error loading accounts config: {e}")
    
    # Fallback to Env Vars if no config (backward compatibility)
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
            stagger = 90  # Allow previous Chrome to fully boot + stabilize before next
            logger.info(f"Waiting {stagger}s before starting next account...")
            time.sleep(stagger)
        
    for t in workers:
        t.join()
        
    logger.success("All accounts finished.")