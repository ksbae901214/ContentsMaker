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
FREEPIK_VIDEO_URL = "https://www.freepik.com/pikaso/ai-video-generator"
FREEPIK_IMAGE_URL = "https://www.freepik.com/pikaso/ai-image-generator"
FREEPIK_HEADLESS = False  # headed by default; set true after stable

# Premium+ unlimited video models — tried in order, falling back on failure.
# All three are "unlimited" on Premium+ per freepik.com/가격 (2026-04-08).
FREEPIK_VIDEO_MODEL_PRIORITY = [
    "Kling 2.5",                 # 720p-1080p, 5-10s — best quality
    "MiniMax Hailuo 2.3 Fast",   # 768p-1080p, 6-10s — fallback 1
    "Wan 2.2",                   # 480p-720p, 5-10s  — fallback 2
]

# Premium+ unlimited image models for manga mode (Freepik browser automation).
# Names must match IMAGE_MODEL_DATA_CY keys in freepik_image_selectors.py.
FREEPIK_IMAGE_MODEL_PRIORITY = [
    "Google Nano Banana Pro",    # 1K/2K unlimited — top quality
    "GPT Image 1.5",             # high quality fallback
    "Flux.2 Max",                # fallback
]

# Default image generation backend. "freepik" uses browser automation (unlimited
# on Premium+). "gpt" uses the OpenAI GPT Image API ($0.005/image).
DEFAULT_IMAGE_PROVIDER = "freepik"

# Auto crawler settings (P2)
CRAWL_DELAY_SECONDS = 5
CRAWL_TIMEOUT_SECONDS = 30
