import os
import time
import requests
import pyperclip
import json
from typing import Any, Optional, List, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import yt_dlp

from core.logger import logger
from core.exceptions import InstagramLoginError, VideoDownloadError, NetHunterException
from core.config import SELECTORS, CLIPBOARD_LOCK
from scraper.browser import human_delay, human_type, random_scroll
from services.video import process_video_ffmpeg

def selenium_login(driver: Any, username: str, password: str) -> None:
    """
    Logs into Instagram using the provided credentials.
    Handles 'Save Info' and 'Notifications' popups.
    """
    driver.get("https://www.instagram.com/")
    human_delay(4, 7)
    
    login_s = SELECTORS.get('login', {})
    
    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//a[@href='/direct/inbox/']")))
        logger.info("Already logged in.")
        return
    except TimeoutException:
        pass

    logger.info("Logging in...")
    try:
        sel_username = login_s.get('username', "//input[@name='username']")
        sel_password = login_s.get('password', "//input[@name='password']")
        sel_submit = login_s.get('submit_btn', "//button[@type='submit']")
        
        logger.debug("Waiting 5s for page load...")
        time.sleep(5)

        username_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, sel_username)))
        password_input = driver.find_element(By.XPATH, sel_password)
        
        human_type(username_input, username)
        human_delay(0.5, 1.5)
        human_type(password_input, password)
        
        login_btn = driver.find_element(By.XPATH, sel_submit)
        human_delay(0.5, 1.5)
        login_btn.click()
        
        human_delay(6, 10)
        
        # Handle "Save Info"
        try:
            sel_save_info = login_s.get('save_info_not_now', "//button[text()='Not now']")
            save_info_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, sel_save_info)))
            save_info_btn.click()
            time.sleep(2)
        except: pass
            
        # Handle "Notifications"
        try:
            sel_notifications = login_s.get('notifications_not_now', "//button[text()='Not Now']")
            not_now_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, sel_notifications)))
            not_now_btn.click()
        except: pass

        logger.success("Login sequence complete.")

    except Exception as e:
        logger.error(f"Login failed: {e}")
        try:
             logger.error(f"Current URL at failure: {driver.current_url}")
        except: pass
        raise InstagramLoginError(f"Login failed: {e}")

def save_cookies_netscape(driver: Any, filepath: str) -> None:
    """Save Selenium cookies to a Netscape format file for yt-dlp."""
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
    """Downloads a video using yt-dlp with cookies from Selenium."""
    save_cookies_netscape(driver, cookie_file)
    
    ydl_opts = {
        'outtmpl': os.path.join(output_folder, '%(id)s.%(ext)s'),
        'cookiefile': cookie_file,
        'quiet': True,
        'no_warnings': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if not filename.endswith('.mp4'):
                base = os.path.splitext(filename)[0]
                os.rename(filename, base + '.mp4')
                filename = base + '.mp4'
            return filename
    except Exception as e:
        logger.error(f"yt-dlp failed: {e}")
        return None

def selenium_download_video(driver: Any, reel_link: str, output_folder: str, cookie_file: str, grid_thumbnail_url: Optional[str] = None) -> Optional[str]:
    """Downloads an Instagram reel video."""
    logger.download(f"Downloading: {reel_link}")
    
    # 1. Try yt-dlp first
    filepath = download_with_ytdlp(driver, reel_link, output_folder, cookie_file)
    if filepath and os.path.exists(filepath):
        logger.success(f"Downloaded via yt-dlp: {filepath}")
        return process_video_ffmpeg(filepath)
        
    logger.warning("yt-dlp failed, falling back to network log scanning...")
    
    # 2. Fallback: Network Logs
    driver.get(reel_link)
    human_delay(3, 5)
    
    video_url = None
    thumbnail_url = grid_thumbnail_url
    
    logs = driver.get_log("performance")
    for entry in logs:
         try:
             message = json.loads(entry.get("message"))
             method = message.get("message", {}).get("method")
             if method == "Network.responseReceived":
                 resp = message.get("message", {}).get("params", {}).get("response", {})
                 mime = resp.get("mimeType", "")
                 url = resp.get("url", "")
                 
                 if "video/mp4" in mime:
                     if '.mp4?' in url or url.endswith('.mp4'):
                          video_url = url
                          break
         except: pass

    if not video_url:
        logger.error("Failed to find video URL in network logs.")
        raise VideoDownloadError("Could not extract video URL.")

    try:
        filename = reel_link.rstrip('/').split('/')[-1] + ".mp4"
        filepath = os.path.join(output_folder, filename)
        
        s = requests.Session()
        s.headers.update({
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Referer": "https://www.instagram.com/"
        })
        for cookie in driver.get_cookies():
            s.cookies.set(cookie['name'], cookie['value'])
            
        r = s.get(video_url, stream=True)
        r.raise_for_status()
        
        if 'video' not in r.headers.get('Content-Type', ''):
             return None

        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(filepath)
        if file_size < 100000:
             os.remove(filepath)
             return None
                
        # Download thumbnail if available
        if thumbnail_url:
            try:
                thumb_filename = reel_link.rstrip('/').split('/')[-1] + "_thumb.jpg"
                thumbnail_path = os.path.join(output_folder, thumb_filename)
                thumb_r = s.get(thumbnail_url, stream=True)
                thumb_r.raise_for_status()
                with open(thumbnail_path, 'wb') as f:
                    for chunk in thumb_r.iter_content(chunk_size=8192):
                        f.write(chunk)
            except: pass
        
        return process_video_ffmpeg(filepath)
    except Exception as e:
        logger.error(f"Failed to download video: {e}")
        raise VideoDownloadError(f"Download failed: {e}")

def selenium_upload_reel(driver: Any, video_path: str, caption: str, thumbnail_path: Optional[str] = None) -> None:
    """Uploads a reel via the Instagram Web UI."""
    logger.info("Starting upload process...")
    
    nav_s = SELECTORS.get('navigation', {})
    up_s = SELECTORS.get('upload_flow', {})
    
    try:
        # 1. Click 'Create' button
        try:
            sel = nav_s.get('sidebar_create_btn', "//*[@aria-label='New post']")
            create_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, sel)))
            try:
                create_btn.click() 
            except:
                create_btn.find_element(By.XPATH, "./ancestor::a | ./ancestor::div[@role='button']").click()
        except TimeoutException:
            driver.get("https://www.instagram.com/")
            human_delay(2, 4)
            sel = nav_s.get('sidebar_create_btn', "//*[@aria-label='New post']")
            create_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, sel)))
            create_btn.click()

        human_delay(2, 4)
        
        # 2. File Input
        sel_input = up_s.get('file_input', "//input[@accept='image/jpeg,image/png,image/heic,image/heif,video/mp4,video/quicktime']")
        file_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, sel_input)))
        file_input.send_keys(os.path.abspath(video_path))
        logger.debug("Video file injected into input.")
        
        human_delay(5, 8)
        
        # 3. Crop Menu
        try:
            sel_crop = up_s.get('crop_menu_btn', "//*[@aria-label='Select crop']")
            crop_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, sel_crop)))
            crop_btn.click()
            human_delay(1, 2)
            
            sel_orig = up_s.get('crop_original_btn', "//*[text()='Original']")
            original_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, sel_orig)))
            original_btn.click()
            human_delay(1, 2)
        except Exception as e:
            logger.warning(f"Could not set crop to Original: {e}")

        # 4. Next (to Edit)
        sel_next = up_s.get('next_btn', "//div[text()='Next']")
        next_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, sel_next)))
        next_btn.click()
        human_delay(2, 4)
        
        # 5. Next (to Caption)
        next_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, sel_next)))
        next_btn.click()
        human_delay(3, 5)
        
        # 6. Caption Injection
        caption_area = None
        selectors_to_try = [
            up_s.get('caption_area', "//*[@aria-label='Write a caption...']"),
            "//div[@contenteditable='true' and @role='textbox']",
            "//div[contains(@aria-label, 'caption')]"
        ]
        
        for sel in selectors_to_try:
            try:
                caption_area = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, sel)))
                if caption_area: break
            except: continue
        
        if not caption_area:
            raise NetHunterException("CRITICAL: Could not find caption textarea with any selector!")
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", caption_area)
        human_delay(1, 2)
        
        caption_injected = False
        
        def is_box_filled(el: Any) -> bool:
            try:
                val = (el.text or el.get_attribute('textContent') or el.get_attribute('innerText') or "").strip()
                if val == "Write a caption..." or not val: return False
                return len(val) > 10
            except: return False

        # Layer 1: ActionChains
        try:
            ActionChains(driver).move_to_element(caption_area).click().perform()
            human_delay(0.5, 1.5)
            with CLIPBOARD_LOCK:
                pyperclip.copy(caption)
                ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            human_delay(1, 2)
            if is_box_filled(caption_area): caption_injected = True
        except: pass

        # Layer 2: send_keys
        if not caption_injected:
            try:
                caption_area.clear()
                caption_area.send_keys(caption)
                human_delay(1, 2)
                if is_box_filled(caption_area): caption_injected = True
            except: pass

        # Layer 3: JS Injection
        if not caption_injected:
            try:
                driver.execute_script("arguments[0].innerText = arguments[1];", caption_area, caption)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", caption_area)
                human_delay(1, 2)
                if is_box_filled(caption_area): caption_injected = True
            except: pass

        if not caption_injected:
            logger.warning("All caption injection methods failed. Proceeding without caption.")

        # 7. Share
        sel_share = up_s.get('share_btn', "//div[text()='Share']")
        share_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, sel_share)))
        share_btn.click()
        
        logger.info("Waiting for upload to complete...")
        
        # 8. Wait for success
        sel_success = up_s.get('success_img', "//img[contains(@alt, 'Animated checkmark')]")
        WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.XPATH, sel_success)))
        logger.success("Upload successful!")
        
        # Close modal
        try:
            sel_close = up_s.get('close_modal_btn', "//*[@aria-label='Close']")
            close_btn = driver.find_element(By.XPATH, sel_close)
            close_btn.click()
        except: pass
        
        human_delay(2, 4)

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        driver.save_screenshot(os.path.join(os.getcwd(), "upload_error.png"))
        raise NetHunterException(f"Upload failed: {e}")

def get_reels_from_profile(driver: Any, username: str, max_count: int = 10) -> List[Tuple[str, Optional[str]]]:
    """Scrapes reel URLs from a profile."""
    url = f"https://www.instagram.com/{username}/reels/"
    driver.get(url)
    human_delay(3, 5)
    
    reels = []
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while len(reels) < max_count:
        elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/reel/')]")
        
        for el in elements:
            link = el.get_attribute("href")
            if link and link not in [r[0] for r in reels]:
                thumb_url = None
                try:
                    img = el.find_element(By.TAG_NAME, "img")
                    thumb_url = img.get_attribute("src")
                except: pass
                reels.append((link, thumb_url))
                if len(reels) >= max_count:
                    break
                    
        if len(reels) >= max_count:
            break
            
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        human_delay(2, 4)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        
    return reels
