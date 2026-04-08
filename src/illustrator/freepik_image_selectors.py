"""CSS selectors for freepik.com/pikaso AI image generator UI.

Verified against live DOM on 2026-04-08 with Premium+ account.
40 image models available, data-cy pattern: `ai-model-item-<slug>`.

To debug after a UI change:
  python3 -m src.main freepik_login   # opens headed browser
  → Open DevTools, inspect elements and update keys below.
"""
from __future__ import annotations

# URL for the AI image generator (Pikaso suite)
FREEPIK_IMAGE_URL = "https://www.freepik.com/pikaso/ai-image-generator"

# Mapping human-readable name → data-cy slug (full All models list).
# Only the "unlimited" models on Premium+ are listed here; add others as needed.
IMAGE_MODEL_DATA_CY: dict[str, str] = {
    # ─── Premium+ 무제한 이미지 모델 ───
    "Google Nano Banana Pro": "ai-model-item-imagen-nano-banana-2",   # 1K/2K ⭐
    "Google Nano Banana 2": "ai-model-item-imagen-nano-banana-2-flash",  # ⭐
    "Google Nano Banana": "ai-model-item-imagen-nano-banana",         # base ⭐
    "Seedream 5 Lite": "ai-model-item-seedream-5-lite",               # ⭐
    "Recraft V4": "ai-model-item-recraft-v4",                         # ⭐
    "Grok": "ai-model-item-grok",                                     # ⭐
    "GPT Image 1.5": "ai-model-item-gpt-1-5-high",                    # high quality ⭐
    "GPT Image 1.5 Medium": "ai-model-item-gpt-1-5-medium",           # ⭐
    "Flux.2 Max": "ai-model-item-flux-2-max",                         # ⭐
    "Flux.2 Pro": "ai-model-item-flux-2",                             # ⭐

    # ─── 크레딧 소모 (참고용) ───
    "Auto": "ai-model-item-auto",
    "Cinematic": "ai-model-item-cinematic",
    "Flux.2 Flex": "ai-model-item-flux-2-flex",
    "Flux.2 Klein": "ai-model-item-flux-2-klein",
    "Flux.1 Kontext Max": "ai-model-item-flux-kontext-high",
    "Flux.1 Kontext Pro": "ai-model-item-flux-kontext",
    "Mystic 2.5": "ai-model-item-mystic-2-5",
    "Flux.1": "ai-model-item-flux-dev",
    "Ideogram": "ai-model-item-ideogram",
    "Google Imagen 3": "ai-model-item-imagen3",
    "Google Imagen 4 Fast": "ai-model-item-imagen4-fast",
    "Google Imagen 4": "ai-model-item-imagen4",
    "Google Imagen 4 Ultra": "ai-model-item-imagen4-ultra",
    "GPT": "ai-model-item-gpt-medium",
    "GPT 1 - HQ": "ai-model-item-gpt-high",
    "Seedream 4": "ai-model-item-seedream-4",
    "Seedream 4 4K": "ai-model-item-seedream-4-4k",
    "Seedream 4.5": "ai-model-item-seedream-4-5",
    "Runway": "ai-model-item-runway-gen4",
}

IMAGE_SELECTORS: dict[str, str | None] = {
    # ─── Login state ───
    "user_avatar": "[data-cy='user-avatar']",

    # ─── Prompt input (contenteditable, not textarea) ───
    "prompt_input": (
        "[data-cy='image-prompt-input'], "
        "[contenteditable='true']"
    ),
    "clear_prompt_button": "[data-cy='clear-prompt-button']",

    # ─── Model selection ───
    "model_selector_trigger": "[data-cy='tti-mode-selector-v3-trigger']",
    "all_models_button": "[data-cy='ai-model-selector-show-all-button']",
    "model_modal_backdrop": "div.fixed.inset-0.backdrop-blur-lg",

    # ─── Aspect ratio ───
    "aspect_ratio_trigger": "[data-cy='image-aspect-ratio-input']",
    "aspect_9_16_option": "button:has-text('9:16')",

    # ─── Number of images ───
    "number_of_images_input": "[data-cy='image-number-of-images-input']",
    "decrease_number_images_button": "[data-cy='decrease-number-images-button']",
    "increase_number_images_button": "[data-cy='increase-number-images-button']",

    # ─── Generate ───
    "generate_button": "[data-cy='generate-button']",
    "no_credits_marker": "[data-cy='generate-button']:has-text('Upgrade')",
}
