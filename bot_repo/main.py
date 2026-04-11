import os
import time
import json
import random
import threading
from typing import Any, Dict

import google.generativeai as genai

from core.logger import logger
from core.exceptions import InstagramLoginError, AIProcessingError, NetHunterException
from core.config import (
    setup_account_env, 
    GEMINI_API_KEY, 
    INSTAGRAM_USERNAME, 
    INSTAGRAM_PASSWORD, 
    TARGET_USERNAME, 
    MAX_REELS, 
    REPOST_INTERVAL,
    BASE_DIR
)
from scraper.browser import get_driver
from scraper.instagram import selenium_login, selenium_download_video, selenium_upload_reel, get_reels_from_profile
from services.ai import generate_caption
from utils.state import load_ledger, save_ledger, save_checkpoint

# Configure the AI for generating captions globally
genai.configure(api_key=GEMINI_API_KEY)

def run_account_worker(account_config: Dict[str, Any]) -> None:
    """
    Main worker loop for a single Instagram account.
    
    Args:
        account_config (Dict[str, Any]): Dictionary containing account credentials and settings.
    """
    username = account_config['username']
    password = account_config['password']
    target_username = account_config['target_username']
    max_reels = account_config.get('max_reels', 3000)
    repost_interval = account_config.get('repost_interval', 2000)
    custom_prompt = account_config.get('custom_prompt')
    
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
            
            for reel_url, grid_thumbnail_url in reels_data:
                reel_id = reel_url.rstrip('/').split('/')[-1]
                
                if reel_id in ledger:
                    logger.info(f"Skipping already processed reel {reel_id}", account=username)
                    continue
                    
                logger.info(f"Processing Reel: {reel_id}", account=username)
                
                try:
                    # 1. Download
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
    
    ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts_config.json")
    
    accounts = []
    
    # Check for config file
    if os.path.exists(ACCOUNTS_FILE):
        logger.info(f"Loading accounts from {ACCOUNTS_FILE}...")
        try:
            with open(ACCOUNTS_FILE, "r") as f:
                accounts = json.load(f)
        except Exception as e:
            logger.error(f"Error loading accounts config: {e}")
    
    # Fallback to Env Vars if no config
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
