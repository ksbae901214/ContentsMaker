from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"

# Scraper settings
MAX_COMMENTS = 10
MIN_BODY_LENGTH = 10
BLIND_DOMAIN = "teamblind.com"

# Auto crawler settings (P2)
CRAWL_DELAY_SECONDS = 5
CRAWL_TIMEOUT_SECONDS = 30
