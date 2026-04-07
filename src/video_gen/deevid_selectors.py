"""CSS selectors for deevid.ai UI elements.

Verified against the live site (text-to-video page) on 2026-04-07.

The deevid.ai UI uses Mantine framework. Stable selectors prefer:
  - data-path="prompt" attribute on the textarea (Mantine form binding)
  - form[type=submit] button (the Create button is the form's submit)
  - Visible text content (e.g. "Master V2.0", "720P")

Mantine assigns dynamic IDs (e.g. mantine-lwgu9whbu-target) so we avoid those.

To debug after a UI change:
  python3 -m src.main deevid_login   # opens DevTools-friendly browser
  → Inspect the prompt input area, update keys below.
"""
from __future__ import annotations

# URL paths
TEXT_TO_VIDEO_URL = "https://deevid.ai/text-to-video"

# Selectors verified on the public (logged-out) text-to-video page.
SELECTORS: dict[str, str | None] = {
    # ─── Auth state detection ───
    # When logged in, the avatar/profile menu typically appears in the header.
    # When logged out, "Start For Free" or "Sign in" buttons appear.
    "logged_in_marker": "img[alt*='avatar' i], [data-test='user-menu'], [aria-label*='profile' i]",
    "login_button": "button:has-text('Start For Free'), button:has-text('Log in'), button:has-text('Sign in')",

    # ─── Prompt input ───
    # Mantine form-bound textarea — the data-path attribute is stable.
    "prompt_input": 'textarea[data-path="prompt"]',

    # ─── Model selection (Master V2.0 = Veo 3.1 tier on deevid.ai) ───
    # The default is already Master V2.0 — selection is optional.
    # If we need to change it, click this trigger then a menu opens.
    "model_selector": "div[aria-haspopup='dialog']:has(span:text-is('Master  V2.0'))",
    "model_veo_31_option": None,  # default is fine; leave unset to skip

    # ─── Aspect ratio / duration selector ───
    # Shows "720P | 8s | 16:9" — clicking opens a dialog with options.
    "format_selector": "div[aria-haspopup='dialog']:has(span:text-is('720P'))",
    # Inside the format dialog, the 9:16 option (use :has-text only — text= can't mix with CSS)
    "aspect_9_16_option": "button:has-text('9:16'), [role='option']:has-text('9:16'), div:has-text('9:16'):not(:has(div))",

    # ─── Create / generate button ───
    # The only submit-type button on the page. Text is locale-dependent
    # ("Create" in EN, "생성" in KO) so match by type only.
    "create_button": 'button[type="submit"]',

    # ─── Result / download ───
    # After generation, a download button appears. The exact selector is
    # not yet known — may require login to verify. Best guesses:
    "download_button": "a[download], button:has-text('Download'), [aria-label*='download' i]",

    # ─── Errors ───
    "no_credits_marker": "text=/out of credits/i, text=/insufficient credits/i, text=/not enough credits/i",
}
