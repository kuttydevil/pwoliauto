import requests
import re
from typing import Optional, Tuple
from core.logger import logger
from core.config import TMDB_API_KEY, TMDB_BASE

def slugify(text: str) -> str:
    """
    Convert a title to an SEO-friendly slug.
    
    Args:
        text (str): The text to slugify.
        
    Returns:
        str: The slugified text.
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')

def search_tmdb_movie(title: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Search TMDB for a movie by title and return its slug, original title, and release year.
    
    Args:
        title (str): The movie title to search for.
        
    Returns:
        Tuple[Optional[str], Optional[str], Optional[int]]: A tuple containing the slug, 
        original title, and release year. Returns (None, None, None) if not found or on error.
    """
    try:
        url = f"{TMDB_BASE}/search/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "query": title,
            "page": 1,
            "include_adult": "false"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            first_result = data["results"][0]
            original_title = first_result.get("original_title") or first_result.get("title")
            release_date = first_result.get("release_date", "")
            year = int(release_date.split("-")[0]) if release_date else None
            
            slug = slugify(original_title)
            if year:
                slug = f"{slug}-{year}"
                
            return slug, original_title, year
            
        return None, None, None
    except Exception as e:
        logger.error(f"TMDB search failed for '{title}': {e}")
        return None, None, None

def build_moviefarming_url(title: str) -> str:
    """
    Builds a MovieFarming URL for the given movie title.
    
    Args:
        title (str): The movie title.
        
    Returns:
        str: The constructed MovieFarming URL.
    """
    slug, original_title, year = search_tmdb_movie(title)
    if slug:
        return f"https://pwolimovies.vercel.app/movie/{slug}"
    else:
        fallback_slug = slugify(title)
        return f"https://pwolimovies.vercel.app/movie/{fallback_slug}"
