"""CSS selectors for freepik.com/pikaso AI video generator UI.

Verified against live DOM on 2026-04-08. Freepik uses Vue with dynamic class
names, so data-cy attributes are preferred over class-based selectors.

Stable data-cy attributes identified:
  - [data-cy="generate-button"]           → Generate / Upgrade button
  - [data-cy="video-aspect-ratio-option"] → aspect ratio trigger
  - [data-cy="ai-model-item-<name>"]      → each model in the "All models" modal
  - [data-cy="user-avatar"]               → logged-in detection

The `All models` modal pattern (ai-model-item-<slug>) lets us pick any of
41 models by stable slug regardless of the visible display text.

To debug after a UI change:
  python3 -m src.main freepik_login   # opens headed browser
  → Open DevTools, inspect elements and update keys below.
"""
from __future__ import annotations

# URL for the AI video generator (Pikaso suite, not the landing page)
FREEPIK_VIDEO_URL = "https://www.freepik.com/pikaso/ai-video-generator"

# Mapping from human-readable model name → data-cy slug
# Verified 2026-04-08 with Premium+ account (41 models available).
# "무제한" models on Premium+ are marked with a comment.
MODEL_DATA_CY: dict[str, str] = {
    # ─── Premium+ 무제한 영상 모델 ───
    "Kling 2.5": "ai-model-item-kling-25",                        # 720p-1080p, 5-10s  ⭐ unlimited
    "MiniMax Hailuo 2.3 Fast": "ai-model-item-minimax-video-2_3-fast",  # 768p-1080p, 6-10s  ⭐ unlimited
    "Wan 2.2": "ai-model-item-wan-2-2",                           # 480p-720p, 5-10s   ⭐ unlimited

    # ─── 크레딧 소모 영상 모델 (폴백/고급) ───
    "Auto": "ai-model-item-auto-mode",
    "Seedance 2.0": "ai-model-item-bytedance-seedance-pro-2.0",
    "Seedance 2.0 Fast": "ai-model-item-bytedance-seedance-fast-2.0",
    "Seedance 1.5 Pro": "ai-model-item-bytedance-seedance-pro-1.5",
    "Seedance 1.0 Pro": "ai-model-item-bytedance-seedance-pro",
    "Seedance 1.0 Fast": "ai-model-item-bytedance-seedance-fast",
    "Seedance 1.0 Lite": "ai-model-item-bytedance-seedance-lite",
    "Kling 3.0": "ai-model-item-kling-30",
    "Kling 3.0 Omni": "ai-model-item-kling-omni3",
    "Kling 3.0 Motion Control": "ai-model-item-kling-motion-control-30",
    "Kling 2.6": "ai-model-item-kling-26",
    "Kling 2.6 Motion Control": "ai-model-item-kling-motion-control",
    "Kling O1": "ai-model-item-kling-omni1",
    "Kling 2.1": "ai-model-item-kling-21",
    "Kling 2.1 Master": "ai-model-item-kling-21-master",
    "Google Veo 3.1": "ai-model-item-google-veo3_1",
    "Google Veo 3.1 Fast": "ai-model-item-google-veo3_1-fast",
    "Google Veo 3": "ai-model-item-google-veo3",
    "Google Veo 3 Fast": "ai-model-item-google-veo3-fast",
    "Google Veo 2": "ai-model-item-google-veo2",
    "Grok": "ai-model-item-grok-default",
    "Runway Gen-4.5": "ai-model-item-runway-gen45",
    "Runway Gen 4": "ai-model-item-runway-std",
    "Runway Act Two": "ai-model-item-runway-act-two",
    "MiniMax Hailuo 2.3": "ai-model-item-minimax-video-2_3",
    "MiniMax Hailuo 02": "ai-model-item-minimax-video-02",
    "MiniMax Live Illustrations": "ai-model-item-minimax-video-01-live2d",
    "OpenAI Sora 2 Pro": "ai-model-item-openai-sora2-pro",
    "OpenAI Sora 2": "ai-model-item-openai-sora2-standard",
    "PixVerse 5.5": "ai-model-item-pixverse-5-5",
    "Wan 2.6": "ai-model-item-wan-2-6",
    "Wan 2.5": "ai-model-item-wan-2-5",
    "Wan 2.2 Animate Move": "ai-model-item-wan-2-2-animate",
    "LTX 2 Fast": "ai-model-item-ltx-ltx2-fast",
    "LTX 2 Pro": "ai-model-item-ltx-ltx2-pro",
    "Veed Fabric 1.0": "ai-model-item-veed-fabric-1.0",
    "Veed Fabric 1.0 Fast": "ai-model-item-veed-fabric-1.0-fast",
    "Omni Human 1.5": "ai-model-item-bytedance-omnihuman-lipsync",
}

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

    # ─── Model selection ───
    # The model button shows the currently selected model's display name.
    # Its text can be "Auto", "Seedance 1.0 Lite", "Kling 2.5", etc.
    # We use a union of common prefixes to find it regardless of state.
    "model_dropdown_trigger": (
        "button:has-text('Auto'):not(:has-text('All')), "
        "button:has-text('Seedance'):not(:has-text('Add')):not(:has-text('Use')), "
        "button:has-text('Kling'):not(:has-text('Add')):not(:has-text('Use')), "
        "button:has-text('Wan'):not(:has-text('Add')):not(:has-text('Use')), "
        "button:has-text('MiniMax'):not(:has-text('Add')):not(:has-text('Use')), "
        "button:has-text('Veo'):not(:has-text('Add')):not(:has-text('Use')), "
        "button:has-text('Runway'):not(:has-text('Add')):not(:has-text('Use')), "
        "button:has-text('Sora'):not(:has-text('Add')):not(:has-text('Use'))"
    ),
    # After clicking model dropdown, an "All models" button opens the full modal
    "all_models_button": "button:has-text('All models')",
    # The full-screen modal backdrop — used to detect open/close state
    "model_modal_backdrop": "div.fixed.inset-0.backdrop-blur-lg",

    # ─── Start image / End image upload (image-to-video) ───
    # Kling 2.5 supports Start / End frame inputs. Playwright uploads files
    # directly via `input.set_input_files()` on the first image file input.
    "start_image_trigger": "[data-cy='video-start-frame-input']",
    "end_image_trigger": "[data-cy='video-end-frame-input']",
    # File inputs below the start-frame UI — image/* accept
    "image_file_inputs": "input[type='file'][accept*='image']",
}
