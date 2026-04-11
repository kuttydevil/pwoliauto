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
