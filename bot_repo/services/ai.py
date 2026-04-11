import os
import time
import re
from typing import Optional, List, Any
import google.generativeai as genai

from core.logger import logger
from core.exceptions import AIProcessingError
from services.tmdb import build_moviefarming_url
from services.video import extract_frames

def upload_to_gemini(path: str, mime_type: Optional[str] = None) -> Any:
    """
    Uploads a file to Gemini.
    
    Args:
        path (str): The local path to the file.
        mime_type (Optional[str]): The MIME type of the file.
        
    Returns:
        Any: The uploaded Gemini file object.
    """
    file = genai.upload_file(path, mime_type=mime_type)
    logger.debug(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def wait_for_files_active(files: List[Any]) -> None:
    """
    Waits for the uploaded files to be active in Gemini.
    
    Args:
        files (List[Any]): A list of Gemini file objects.
        
    Raises:
        AIProcessingError: If a file fails to process or times out.
    """
    logger.debug("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise AIProcessingError(f"File {file.name} failed to process")
    print()

def generate_caption(video_path: str, custom_prompt: Optional[str] = None, username: Optional[str] = None) -> str:
    """
    Generates a caption for the video using Gemini, identifying the movie and injecting a URL.
    
    Args:
        video_path (str): Path to the video file.
        custom_prompt (Optional[str]): A custom prompt to guide the AI.
        username (Optional[str]): The account username for logging context.
        
    Returns:
        str: The generated caption.
        
    Raises:
        AIProcessingError: If caption generation fails.
    """
    logger.ai("Generating caption using Gemini 1.5 Flash...", account=username)
    
    gemini_files = []
    
    try:
        # --- STEP 1: EXTRACT AND UPLOAD FRAMES ---
        frames = extract_frames(video_path, num_frames=8)
        
        # Also try to upload the thumbnail if it exists
        thumb_path = video_path.replace(".mp4", "_thumb.jpg")
        if not os.path.exists(thumb_path):
            thumb_path = video_path.replace(".mp4", ".jpg")
            
        if os.path.exists(thumb_path):
             frames.append(thumb_path)
             
        if not frames:
            raise AIProcessingError("No frames or thumbnail available for AI analysis.")

        logger.step(1, 4, f"Uploading {len(frames)} frames to Gemini...", account=username)
        for frame in frames:
            gemini_files.append(upload_to_gemini(frame, mime_type="image/jpeg"))
            
        wait_for_files_active(gemini_files)
        
        # --- STEP 2: BUILD PROMPT ---
        base_prompt = """
        Analyze these frames from a short-form video (Reel/TikTok).
        
        TASK 1: Identify the movie or TV show.
        TASK 2: Write a highly engaging, viral caption for Instagram.
        
        CRITICAL RULES FOR CAPTION:
        - DO NOT use hashtags.
        - DO NOT use emojis.
        - DO NOT use bullet points, bold text, or markdown formatting.
        - Write ONLY the raw text of the caption.
        - Use a controversial or curiosity-inducing hook.
        - Keep it under 3 sentences.
        
        OUTPUT FORMAT:
        You must output EXACTLY in this format, with nothing else:
        
        TITLE: [Insert Movie/Show Title Here]
        CAPTION:
        [Insert your raw caption text here]
        """
        
        prompt = custom_prompt if custom_prompt else base_prompt
        
        # --- STEP 3: CALL AI ---
        logger.step(2, 4, "Analyzing frames and generating text...", account=username)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.9,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
        
        response = model.generate_content(gemini_files + [prompt])
        raw_text = response.text
        
        # --- STEP 4: CLEAN FILLER ---
        # Sometimes Gemini ignores instructions and adds "Here is the caption:"
        raw_text = re.sub(r'^(Here is|Sure|Okay).*?:?\n', '', raw_text, flags=re.IGNORECASE | re.MULTILINE)
        
        # --- STEP 5: EXTRACT MOVIE TITLE & BUILD MOVIEFARMING URL ---
        logger.step(3, 4, "Extracting movie title and building URL...", account=username)
        
        title_match = re.search(r'TITLE:\s*(.*?)\n', raw_text, re.IGNORECASE)
        caption_match = re.search(r'CAPTION:\s*(.*)', raw_text, re.IGNORECASE | re.DOTALL)
        
        movie_title = title_match.group(1).strip() if title_match else "Unknown Movie"
        caption_text = caption_match.group(1).strip() if caption_match else raw_text.strip()
        
        # Clean up any remaining markdown or quotes in the caption
        caption_text = caption_text.replace('**', '').replace('"', '')
        
        # Build URL
        if movie_title and movie_title.lower() != "unknown movie":
             logger.debug(f"Identified Movie: {movie_title}", account=username)
             movie_url = build_moviefarming_url(movie_title)
        else:
             logger.warning("Could not identify movie title. Using generic URL.", account=username)
             movie_url = "https://pwolimovies.vercel.app"
             
        # --- STEP 6: INJECT URL INTO CAPTION ---
        logger.step(4, 4, "Finalizing caption...", account=username)
        
        # We want to inject the URL naturally.
        # Let's append it to the end with a call to action.
        final_caption = f"{caption_text}\n.\n.\n.\n🍿 Watch full movie here: {movie_url}"
        
        logger.success("Caption generated successfully.", account=username)
        return final_caption

    except Exception as e:
        logger.error(f"Gemini AI failed: {e}", account=username)
        # Fallback caption
        return "Wait for it 🤯\n.\n.\n.\n🍿 Watch full movie here: https://pwolimovies.vercel.app"
        
    finally:
        # Cleanup Gemini files
        for f in gemini_files:
            try:
                genai.delete_file(f.name)
            except:
                pass
