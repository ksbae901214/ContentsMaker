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

# Reference images
DATA_REFERENCES_DIR = DATA_DIR / "references"

# Analyzer settings
DATA_SCRIPTS_DIR = DATA_DIR / "scripts"
DATA_AUDIO_DIR = DATA_DIR / "audio"
CLAUDE_TIMEOUT_SECONDS = 300
MAX_SCENES = 15
TARGET_DURATION_MIN = 30
TARGET_DURATION_MAX = 60

# Video generation
DATA_VIDEOS_DIR = DATA_DIR / "videos"

# deevid.ai browser automation
DEEVID_PROFILE_DIR = PROJECT_ROOT / ".cache" / "deevid_profile"
DEEVID_URL = "https://deevid.ai/"
DEEVID_HEADLESS = False  # headed by default; set true after stable

# freepik.com browser automation
FREEPIK_PROFILE_DIR = PROJECT_ROOT / ".cache" / "freepik_profile"
FREEPIK_VIDEO_URL = "https://www.freepik.com/ai/video-generator"
FREEPIK_HEADLESS = False  # headed by default; set true after stable

# Auto crawler settings (P2)
CRAWL_DELAY_SECONDS = 5
CRAWL_TIMEOUT_SECONDS = 30
