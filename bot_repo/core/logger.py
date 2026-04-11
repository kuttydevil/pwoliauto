import datetime
from typing import Optional, Any

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
