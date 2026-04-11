import os
import json
from typing import Optional, Set
from core.logger import logger

def load_ledger(ledger_file: str) -> Set[str]:
    """
    Loads the set of processed reel IDs from the ledger file.
    
    Args:
        ledger_file (str): Path to the ledger JSON file.
        
    Returns:
        Set[str]: A set of processed reel IDs.
    """
    if os.path.exists(ledger_file):
        try:
            with open(ledger_file, "r") as f:
                return set(json.load(f))
        except Exception as e:
            logger.error(f"Error loading ledger: {e}")
    return set()

def save_ledger(ledger: Set[str], ledger_file: str) -> None:
    """
    Saves the set of processed reel IDs to the ledger file.
    
    Args:
        ledger (Set[str]): The set of processed reel IDs.
        ledger_file (str): Path to the ledger JSON file.
    """
    try:
        with open(ledger_file, "w") as f:
            json.dump(list(ledger), f)
    except Exception as e:
        logger.error(f"Error saving ledger: {e}")

def load_checkpoint(checkpoint_file: str) -> Optional[str]:
    """
    Loads the last processed reel ID from the checkpoint file.
    
    Args:
        checkpoint_file (str): Path to the checkpoint JSON file.
        
    Returns:
        Optional[str]: The last processed reel ID, or None if not found.
    """
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r") as f:
                data = json.load(f)
                return data.get("last_reel_id")
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
    return None

def save_checkpoint(reel_id: str, checkpoint_file: str) -> None:
    """
    Saves the last processed reel ID to the checkpoint file.
    
    Args:
        reel_id (str): The reel ID to save as the checkpoint.
        checkpoint_file (str): Path to the checkpoint JSON file.
    """
    try:
        with open(checkpoint_file, "w") as f:
            json.dump({"last_reel_id": reel_id}, f)
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")
