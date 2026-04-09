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
# Claude CLI timeout. Normal runs finish in 30–120 s. We cap at 5 minutes so
# stuck runs fail fast instead of hanging the browser request for 30 minutes
# (the previous 1800s setting caused the web UI to appear frozen and then
# show "Load failed"). User can always retry if it legitimately needs longer.
CLAUDE_TIMEOUT_SECONDS = 300  # 5분
MAX_SCENES = 15
TARGET_DURATION_MIN = 30
TARGET_DURATION_MAX = 60

# Maximum seconds per scene — constrained so each scene fits in one Kling 2.5
# clip (5-10s range). We use 5.0s as a hard ceiling because:
#   1. It gives the shortest lowest-common-denominator across all Premium+
#      unlimited video models (Kling 2.5 / Wan 2.2 / MiniMax 2.3).
#   2. Shorter scenes → more visual variety, faster pacing for shorts.
# Scripts generated via build_shorts_script() must obey this ceiling. Pre-
# existing scripts can be split via scene_ops.split_scenes_to_max_duration().
MAX_SCENE_DURATION_SECONDS = 5.0

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
    "Wan 2.2",                   # 480p, FREE with start image (confirmed 2026-04-09)
    "MiniMax Hailuo 2.3 Fast",   # 768p, fallback (costs credits without start image)
    "Kling 2.5",                 # 768p, fallback (720p removed by Freepik)
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
