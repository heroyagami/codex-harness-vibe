from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


# The Remotion scene is 1080x1440, while auto-motion's parallax transitions
# need 200px of overscan on every edge for camera movement.
WIDTH, HEIGHT = 1480, 1840


def make_background(path: Path, *, light: bool) -> None:
    random.seed(20260821 + int(light))
    top = (244, 240, 232) if light else (10, 14, 22)
    bottom = (222, 232, 234) if light else (16, 28, 42)
    image = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = image.load()
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        wave = math.sin(ratio * math.pi * 3) * 0.025
        for x in range(WIDTH):
            diagonal = (x / WIDTH - 0.5) * 0.06
            amount = min(1.0, max(0.0, ratio + wave + diagonal))
            noise = random.randint(-2, 2)
            pixels[x, y] = tuple(
                max(0, min(255, round(a + (b - a) * amount) + noise))
                for a, b in zip(top, bottom)
            )
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    accent = (35, 150, 160, 25) if light else (46, 180, 190, 22)
    for cx, cy, radius in ((120, 180, 430), (950, 570, 520), (410, 1320, 500)):
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=accent)
    overlay = overlay.filter(ImageFilter.GaussianBlur(120))
    Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB").save(path, quality=95)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=Path, required=True)
    args = parser.parse_args()
    resources = args.vendor.resolve() / "resources"
    backgrounds = resources / "backgrounds"
    backgrounds.mkdir(parents=True, exist_ok=True)
    make_background(backgrounds / "darkbg.png", light=False)
    make_background(backgrounds / "lightbg.png", light=True)
    for asset in resources.iterdir():
        if asset.is_file() and ("猫学长" in asset.name or "avatar" in asset.name.lower()):
            asset.unlink()
    print("Neutral backgrounds installed; upstream avatar removed.")


if __name__ == "__main__":
    main()
