import os
import cv2
import json
import random
import subprocess
from typing import List, Optional, Any, Dict
from core.logger import logger
from core.config import PROMOTION_IMAGES_DIR

import static_ffmpeg
static_ffmpeg.add_paths()

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

def get_video_info(input_path: str) -> Optional[Dict[str, Any]]:
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
