"""CSS selectors for freepik.com AI video generator UI.

Best-guess selectors based on the publicly visible DOM structure.
These MUST be verified on first login via DevTools — freepik.com uses
React with dynamic class names so text-based and data-attribute selectors
are preferred over class names.

To debug after a UI change:
  python3 -m src.main freepik_login   # opens headed browser
  → Open DevTools, inspect the elements and update keys below.
"""
from __future__ import annotations

# URL for the text-to-video generator page
FREEPIK_VIDEO_URL = "https://www.freepik.com/ai/video-generator"

SELECTORS: dict[str, str | None] = {
    # ─── Auth state detection ───
    # Logged-in state: user avatar / account menu visible in header
    "logged_in_marker": (
        "[data-cy='user-menu'], "
        "img[alt*='avatar' i], "
        "button[aria-label*='account' i], "
        "button[aria-label*='profile' i], "
        "[data-testid='user-avatar']"
    ),
    # Logged-out state: login/signup CTA visible
    "login_button": (
        "a[href*='/login'], "
        "button:has-text('Log in'), "
        "button:has-text('Sign in'), "
        "a:has-text('Log in')"
    ),

    # ─── Prompt input ───
    # The main text area where the user describes their video
    "prompt_input": (
        "textarea[placeholder*='describe' i], "
        "textarea[placeholder*='prompt' i], "
        "textarea[placeholder*='video' i], "
        "[data-testid='prompt-input'], "
        "textarea"
    ),

    # ─── Aspect ratio selector ───
    # Freepik supports 9:16 ("social_story_9_16") for Shorts/Reels
    "aspect_ratio_trigger": (
        "button[aria-label*='aspect' i], "
        "button:has-text('16:9'), "
        "[data-testid='aspect-ratio']"
    ),
    "aspect_9_16_option": (
        "button:has-text('9:16'), "
        "[data-value='9:16'], "
        "[aria-label*='9:16'], "
        "li:has-text('9:16')"
    ),

    # ─── Generate / Create button ───
    "generate_button": (
        "button:has-text('Generate video'), "
        "button:has-text('Generate'), "
        "button:has-text('Create video'), "
        "button[type='submit']:has-text('Generate')"
    ),

    # ─── Result / download ───
    # After generation completes, a download option appears
    "download_button": (
        "button:has-text('Download'), "
        "a[download], "
        "[aria-label*='download' i], "
        "button[data-testid*='download']"
    ),

    # ─── Error states ───
    "no_credits_marker": (
        "text=/out of credits/i, "
        "text=/크레딧이 부족/i, "
        "text=/upgrade your plan/i, "
        "text=/insufficient credits/i, "
        "[data-testid='no-credits']"
    ),
}
