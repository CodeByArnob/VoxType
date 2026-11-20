"""
Generates high-resolution icon assets for VoxType.
Features a modern microphone and audio waveform symbol without text.
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw


def create_voxtype_icon(size: int = 512) -> Image.Image:
    # High-res RGBA image
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = size * 0.06
    r = size * 0.22

    # Draw rounded squircle background with dark tech gradient
    bg_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg_img)

    # Base squircle
    bg_draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=int(r),
        fill=(14, 18, 27, 255),
        outline=(59, 130, 246, 120),
        width=int(size * 0.015),
    )

    # Subtle inner glow
    for i in range(int(size * 0.04)):
        alpha = int(35 * (1.0 - i / (size * 0.04)))
        bg_draw.rounded_rectangle(
            [pad + i, pad + i, size - pad - i, size - pad - i],
            radius=int(max(1, r - i)),
            outline=(99, 102, 241, alpha),
            width=1,
        )

    img = Image.alpha_composite(img, bg_img)
    draw = ImageDraw.Draw(img)

    # Geometry for Microphone and Waveform
    cx, cy = size * 0.5, size * 0.44

    # Waveform vertical bars flanking the sides
    bar_color = (96, 165, 250, 220)
    bar_width = int(size * 0.024)
    bar_radius = int(bar_width // 2)

    left_bars_h = [0.12, 0.20, 0.32, 0.18]
    right_bars_h = [0.18, 0.32, 0.20, 0.12]

    # Left bars
    spacing = size * 0.05
    for i, h in enumerate(reversed(left_bars_h)):
        bx = cx - size * 0.22 - (i * spacing)
        bh = size * h
        draw.rounded_rectangle(
            [bx - bar_width // 2, cy - bh // 2, bx + bar_width // 2, cy + bh // 2],
            radius=bar_radius,
            fill=bar_color,
        )

    # Right bars
    for i, h in enumerate(right_bars_h):
        bx = cx + size * 0.22 + (i * spacing)
        bh = size * h
        draw.rounded_rectangle(
            [bx - bar_width // 2, cy - bh // 2, bx + bar_width // 2, cy + bh // 2],
            radius=bar_radius,
            fill=bar_color,
        )

    # Central Microphone Capsule
    mic_w = size * 0.16
    mic_h = size * 0.30
    mic_radius = int(mic_w // 2)
    mic_top = cy - mic_h // 2
    mic_bottom = cy + mic_h // 2

    # Gradient fill for capsule (Cyan to Indigo)
    draw.rounded_rectangle(
        [cx - mic_w // 2, mic_top, cx + mic_w // 2, mic_bottom],
        radius=mic_radius,
        fill=(56, 189, 248, 255),
        outline=(255, 255, 255, 230),
        width=int(size * 0.012),
    )

    # Microphone Cradle (U-shaped arc)
    cradle_r = size * 0.14
    cradle_top = cy - size * 0.04
    cradle_bottom = cy + size * 0.20
    cradle_width = int(size * 0.026)

    # Draw arc
    draw.arc(
        [cx - cradle_r, cradle_top, cx + cradle_r, cradle_bottom],
        start=0,
        end=180,
        fill=(241, 245, 249, 255),
        width=cradle_width,
    )

    # Stem and Base Stand
    stem_top = cradle_bottom - (cradle_bottom - cradle_top) * 0.08
    stem_bottom = stem_top + size * 0.12
    draw.line(
        [(cx, stem_top), (cx, stem_bottom)],
        fill=(241, 245, 249, 255),
        width=cradle_width,
    )

    base_w = size * 0.24
    draw.rounded_rectangle(
        [cx - base_w // 2, stem_bottom, cx + base_w // 2, stem_bottom + cradle_width],
        radius=int(cradle_width // 2),
        fill=(241, 245, 249, 255),
    )

    return img


def generate_assets():
    assets_dir = Path("assets")
    assets_dir.mkdir(parents=True, exist_ok=True)

    icon_512 = create_voxtype_icon(512)
    icon_512.save(assets_dir / "icon.png")

    # Generate ICO with multi-size layers
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon_512.save(assets_dir / "icon.ico", format="ICO", sizes=sizes)

    # Also save to voxtype/resources for packaging
    res_dir = Path("voxtype/resources")
    res_dir.mkdir(parents=True, exist_ok=True)
    icon_512.save(res_dir / "icon.png")
    icon_512.save(res_dir / "icon.ico", format="ICO", sizes=sizes)

    print(f"Generated icons in {assets_dir} and {res_dir}")


if __name__ == "__main__":
    generate_assets()
