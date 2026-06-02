"""Generate synthetic sound effects as MP3 files for data/sfx/.

Uses Python wave module for WAV generation, then converts to MP3
via subprocess (lame) if available, or keeps WAV with .mp3 extension
for basic compatibility.
"""
import math
import os
import struct
import subprocess
import sys
import wave
from pathlib import Path

SFX_DIR = Path(__file__).parent.parent / "data" / "sfx"
SAMPLE_RATE = 44100


def sine_wave(freq: float, duration: float, volume: float = 0.8) -> list[int]:
    """Generate sine wave samples."""
    n = int(SAMPLE_RATE * duration)
    return [
        int(volume * 32767 * math.sin(2 * math.pi * freq * t / SAMPLE_RATE))
        for t in range(n)
    ]


def fade(samples: list[int], fade_in: float = 0.02, fade_out: float = 0.05) -> list[int]:
    """Apply fade in/out to samples."""
    result = list(samples)
    fi = int(SAMPLE_RATE * fade_in)
    fo = int(SAMPLE_RATE * fade_out)
    for i in range(min(fi, len(result))):
        result[i] = int(result[i] * i / fi)
    for i in range(min(fo, len(result))):
        idx = len(result) - 1 - i
        result[idx] = int(result[idx] * i / fo)
    return result


def mix(samples_list: list[list[int]]) -> list[int]:
    """Mix multiple sample lists together."""
    max_len = max(len(s) for s in samples_list)
    result = [0] * max_len
    for samples in samples_list:
        for i, s in enumerate(samples):
            result[i] = max(-32767, min(32767, result[i] + s))
    return result


def silence(duration: float) -> list[int]:
    return [0] * int(SAMPLE_RATE * duration)


def noise_burst(duration: float, volume: float = 0.3) -> list[int]:
    """Generate white noise burst."""
    import random
    n = int(SAMPLE_RATE * duration)
    return [int(random.uniform(-1, 1) * volume * 32767) for _ in range(n)]


def chirp(freq_start: float, freq_end: float, duration: float, volume: float = 0.7) -> list[int]:
    """Frequency sweep."""
    n = int(SAMPLE_RATE * duration)
    result = []
    for t in range(n):
        progress = t / n
        freq = freq_start + (freq_end - freq_start) * progress
        result.append(int(volume * 32767 * math.sin(2 * math.pi * freq * t / SAMPLE_RATE)))
    return result


def write_wav(path: Path, samples: list[int]) -> None:
    """Write samples as WAV file."""
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        data = struct.pack(f"<{len(samples)}h", *samples)
        f.writeframes(data)


def wav_to_mp3(wav_path: Path, mp3_path: Path) -> bool:
    """Convert WAV to MP3 using lame if available."""
    try:
        subprocess.run(
            ["lame", "--quiet", "-b", "128", str(wav_path), str(mp3_path)],
            check=True, capture_output=True, timeout=10,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def generate_all():
    SFX_DIR.mkdir(parents=True, exist_ok=True)

    effects = {
        # Surprise
        "surprise_ding": lambda: fade(
            mix([sine_wave(1200, 0.15, 0.8), sine_wave(1800, 0.15, 0.4)])
            + silence(0.05)
            + mix([sine_wave(1500, 0.2, 0.6), sine_wave(2200, 0.2, 0.3)]),
            fade_out=0.1
        ),
        "surprise_boom": lambda: fade(
            mix([
                sine_wave(80, 0.8, 0.9),
                sine_wave(120, 0.6, 0.7),
                noise_burst(0.15, 0.5),
            ]),
            fade_in=0.01, fade_out=0.4
        ),
        "surprise_huh": lambda: fade(
            chirp(300, 800, 0.3, 0.7) + silence(0.1) + chirp(600, 1200, 0.15, 0.5),
            fade_out=0.1
        ),

        # Laugh
        "laugh_haha": lambda: fade(
            mix([
                sine_wave(400, 0.12, 0.5) + silence(0.08) +
                sine_wave(450, 0.12, 0.5) + silence(0.08) +
                sine_wave(500, 0.12, 0.5),
                chirp(200, 600, 0.6, 0.3),
            ]),
            fade_out=0.15
        ),
        "laugh_kkk": lambda: fade(
            sine_wave(600, 0.08, 0.4) + silence(0.04) +
            sine_wave(650, 0.08, 0.4) + silence(0.04) +
            sine_wave(700, 0.08, 0.4) + silence(0.04) +
            sine_wave(750, 0.08, 0.3),
            fade_out=0.08
        ),
        "laugh_burst": lambda: fade(
            mix([
                noise_burst(0.8, 0.3),
                sine_wave(350, 0.1, 0.5) + silence(0.05) +
                sine_wave(400, 0.1, 0.5) + silence(0.05) +
                sine_wave(500, 0.15, 0.6) + silence(0.05) +
                sine_wave(450, 0.1, 0.4),
            ]),
            fade_out=0.2
        ),

        # Touching
        "touching_bell": lambda: fade(
            mix([
                sine_wave(523, 1.5, 0.5),  # C5
                sine_wave(659, 1.5, 0.3),  # E5
                sine_wave(784, 1.5, 0.2),  # G5
            ]),
            fade_in=0.01, fade_out=0.8
        ),
        "touching_warm": lambda: fade(
            mix([
                sine_wave(262, 1.0, 0.4),  # C4
                sine_wave(330, 1.0, 0.3),  # E4
                sine_wave(392, 0.8, 0.2),  # G4
                sine_wave(523, 0.6, 0.15),  # C5
            ]),
            fade_in=0.1, fade_out=0.5
        ),

        # Emphasis
        "emphasis_drumroll": lambda: fade(
            mix([
                # Rapid low hits
                sum([sine_wave(100, 0.03, 0.6) + silence(0.02) for _ in range(20)], []),
                noise_burst(1.0, 0.2),
            ]),
            fade_in=0.05, fade_out=0.2
        ),
        "emphasis_tada": lambda: fade(
            mix([
                sine_wave(523, 0.15, 0.7) + silence(0.05) +  # C5
                sine_wave(659, 0.15, 0.7) + silence(0.05) +  # E5
                sine_wave(784, 0.4, 0.8),  # G5
                sine_wave(392, 0.15, 0.4) + silence(0.05) +  # G4
                sine_wave(494, 0.15, 0.4) + silence(0.05) +  # B4
                sine_wave(587, 0.4, 0.5),  # D5
            ]),
            fade_out=0.15
        ),
        "emphasis_reveal": lambda: fade(
            chirp(800, 2000, 0.3, 0.6) +
            mix([sine_wave(2000, 0.4, 0.5), sine_wave(3000, 0.4, 0.3)]),
            fade_in=0.02, fade_out=0.2
        ),

        # UI
        "ui_transition": lambda: fade(
            chirp(400, 1200, 0.25, 0.5) + chirp(1200, 600, 0.15, 0.3),
            fade_out=0.1
        ),
        "ui_click": lambda: fade(
            mix([
                sine_wave(1000, 0.05, 0.7),
                sine_wave(2000, 0.03, 0.4),
                noise_burst(0.02, 0.3),
            ]),
            fade_out=0.03
        ),
    }

    has_lame = subprocess.run(
        ["which", "lame"], capture_output=True
    ).returncode == 0

    for name, gen_fn in effects.items():
        samples = gen_fn()
        wav_path = SFX_DIR / f"{name}.wav"
        mp3_path = SFX_DIR / f"{name}.mp3"

        write_wav(wav_path, samples)

        if has_lame:
            if wav_to_mp3(wav_path, mp3_path):
                wav_path.unlink()
                print(f"  ✓ {name}.mp3 ({mp3_path.stat().st_size // 1024} KB)")
                continue

        # No lame: rename wav to mp3 (works for most players/Remotion)
        wav_path.rename(mp3_path)
        print(f"  ✓ {name}.mp3 (WAV, {mp3_path.stat().st_size // 1024} KB)")

    print(f"\n완료: {len(effects)}개 효과음 → {SFX_DIR}")


if __name__ == "__main__":
    generate_all()
