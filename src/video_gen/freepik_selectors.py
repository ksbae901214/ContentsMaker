"""CSS selectors for freepik.com/pikaso AI video generator UI.

Verified against live DOM on 2026-04-07. Freepik uses Vue with dynamic class
names, so text-based selectors and data-cy attributes are preferred.

To debug after a UI change:
  python3 -m src.main freepik_login   # opens headed browser
  → Open DevTools, inspect elements and update keys below.
"""
from __future__ import annotations

# URL for the AI video generator (Pikaso suite, not the landing page)
FREEPIK_VIDEO_URL = "https://www.freepik.com/pikaso/ai-video-generator"

SELECTORS: dict[str, str | None] = {
    # ─── Auth state detection ───
    # Logged-in: user initial avatar button visible (e.g. 'P' button in header)
    "logged_in_marker": (
        "[data-cy='user-menu'], "
        "img[alt*='avatar' i], "
        "button[aria-label*='account' i], "
        "button[aria-label*='profile' i]"
    ),
    # Logged-out: login CTA visible
    "login_button": (
        "a[href*='/login'], "
        "button:has-text('Log in'), "
        "button:has-text('Sign in'), "
        "a:has-text('Log in')"
    ),

    # ─── Prompt input ───
    # Confirmed: a contenteditable div (NOT a textarea) with this placeholder.
    # Use click() + type() — page.fill() doesn't work on contenteditable.
    "prompt_input": "[contenteditable=true]",

    # ─── Aspect ratio selector ───
    # The aspect ratio button shows the currently selected ratio (e.g. '9:16').
    # data-cy is stable across UI refreshes.
    "aspect_ratio_trigger": "[data-cy='video-aspect-ratio-option']",
    "aspect_9_16_option": "button:has-text('9:16')",

    # ─── Generate / Create button ───
    # Confirmed: data-cy="generate-button". Becomes disabled when no prompt.
    # Changes to "Upgrade" text when subscription credits are exhausted.
    "generate_button": "[data-cy='generate-button']",

    # ─── Result / download ───
    # After generation, a new video[src] appears in the DOM (CDN URL).
    # We detect by polling _get_video_urls() for a new URL.
    "download_button": (
        "button:has-text('Download'), "
        "a[download], "
        "[aria-label*='download' i]"
    ),

    # ─── Error states ───
    # Credits exhausted: the generate button text changes to "Upgrade".
    # We detect this by checking the button's inner text after clicking.
    "no_credits_marker": (
        "[data-cy='generate-button']:has-text('Upgrade')"
    ),
}
