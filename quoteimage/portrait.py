"""Render a quote as text shaped to a portrait photo.

The subject's face is reconstructed out of the quote's own words: the quote
is wrapped into a grid of lines like ordinary paragraph text, then each
character is tinted by the brightness of the photo underneath it. Dark
regions of the photo (shadows, hair, pupils) come out as dark text; bright
regions (skin highlights, background) fade toward the white page. Because
every glyph is drawn undistorted at a normal reading size, the quote stays
fully legible while the aggregate pattern of ink reproduces the portrait.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

DEFAULT_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
]

REPEAT_SEPARATOR = "  ✦  "  # ✦ marks each time the quote loops back to its start


@dataclass
class PortraitConfig:
    width: int = 1400
    cell_size: int = 15
    line_spacing: float = 1.05
    contrast: float = 1.35
    gamma: float = 0.85
    edge_boost: float = 90.0
    white_threshold: int = 248
    mode: str = "grayscale"  # "grayscale" or "dither"
    invert: bool = False
    font_path: str | None = None


def find_default_font() -> str:
    for candidate in DEFAULT_FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(
        "No default monospace font found. Pass --font pointing at a .ttf file."
    )


def load_source_image(image_path: str, width: int) -> Tuple[Image.Image, "np.ndarray"]:
    import numpy as np

    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)  # respect camera orientation
    img = img.convert("L")

    aspect = img.height / img.width
    height = max(1, round(width * aspect))
    img = img.resize((width, height), Image.LANCZOS)
    img = ImageOps.autocontrast(img, cutoff=1)

    return img, np.asarray(img, dtype=np.float64)


def build_darkness_map(pixels: "np.ndarray", config: PortraitConfig) -> "np.ndarray":
    import numpy as np

    brightness = pixels
    if config.contrast != 1.0:
        mid = 127.5
        brightness = (brightness - mid) * config.contrast + mid
        brightness = np.clip(brightness, 0, 255)

    darkness = 255.0 - brightness

    if config.edge_boost > 0:
        edge_img = Image.fromarray(brightness.astype("uint8")).filter(ImageFilter.FIND_EDGES)
        edge = np.asarray(edge_img, dtype=np.float64)
        edge = edge / (edge.max() + 1e-6) * 255.0
        darkness = np.maximum(darkness, edge * (config.edge_boost / 255.0))

    darkness = np.clip(darkness, 0, 255)
    if config.gamma != 1.0:
        darkness = 255.0 * (darkness / 255.0) ** config.gamma

    if config.invert:
        darkness = 255.0 - darkness

    return np.clip(darkness, 0, 255)


def infinite_words(quote: str) -> Iterator[str]:
    words = quote.split()
    if not words:
        raise ValueError("Quote text must contain at least one word.")
    while True:
        yield from words
        yield REPEAT_SEPARATOR.strip()


def wrap_into_lines(
    word_source: Iterator[str], font: ImageFont.FreeTypeFont, max_width: float, num_lines: int
) -> List[List[str]]:
    space_width = font.getlength(" ")
    lines: List[List[str]] = []
    current: List[str] = []
    current_width = 0.0

    for word in word_source:
        word_width = font.getlength(word)
        addition = word_width if not current else space_width + word_width

        if current_width + addition > max_width and current:
            lines.append(current)
            if len(lines) >= num_lines:
                return lines
            current, current_width = [], 0.0
            addition = word_width

        current.append(word)
        current_width += addition

    lines.append(current)
    return lines[:num_lines]


def render_grayscale(
    darkness: "np.ndarray",
    lines: List[List[str]],
    font: ImageFont.FreeTypeFont,
    config: PortraitConfig,
    size: Tuple[int, int],
) -> Image.Image:
    width, height = size
    canvas = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(canvas)
    space_width = font.getlength(" ")
    line_height = int(config.cell_size * config.line_spacing)

    for row, words in enumerate(lines):
        y = row * line_height
        y0, y1 = y, min(y + line_height, height)
        if y0 >= height:
            break
        x = 0.0
        for w_i, word in enumerate(words):
            if w_i > 0:
                x += space_width
            for ch in word:
                ch_width = font.getlength(ch)
                x0, x1 = int(x), min(int(x + ch_width) + 1, width)
                if x1 > x0 and y1 > y0:
                    region = darkness[y0:y1, x0:x1]
                    local_darkness = float(region.mean()) if region.size else 0.0
                else:
                    local_darkness = 0.0

                if local_darkness > (255 - config.white_threshold):
                    gray = int(round(255 - local_darkness))
                    draw.text((x, y), ch, font=font, fill=gray)
                x += ch_width
            if x > width:
                break
    return canvas


def render_dither(
    darkness: "np.ndarray",
    lines: List[List[str]],
    font: ImageFont.FreeTypeFont,
    config: PortraitConfig,
    size: Tuple[int, int],
) -> Image.Image:
    width, height = size
    canvas = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(canvas)
    space_width = font.getlength(" ")
    line_height = int(config.cell_size * config.line_spacing)

    for row, words in enumerate(lines):
        y = row * line_height
        y0, y1 = y, min(y + line_height, height)
        if y0 >= height:
            break
        x = 0.0
        error = 0.0
        for w_i, word in enumerate(words):
            if w_i > 0:
                x += space_width
            for ch in word:
                ch_width = font.getlength(ch)
                x0, x1 = int(x), min(int(x + ch_width) + 1, width)
                if x1 > x0 and y1 > y0:
                    region = darkness[y0:y1, x0:x1]
                    local_darkness = float(region.mean()) if region.size else 0.0
                else:
                    local_darkness = 0.0

                target = local_darkness / 255.0 + error
                if ch != " " and target > 0.5:
                    draw.text((x, y), ch, font=font, fill=0)
                    error = target - 1.0
                else:
                    error = target - 0.0
                x += ch_width
            if x > width:
                break
    return canvas


def generate_portrait(image_path: str, quote: str, output_path: str, config: PortraitConfig) -> Image.Image:
    font_path = config.font_path or find_default_font()
    font = ImageFont.truetype(font_path, size=config.cell_size)

    source_img, pixels = load_source_image(image_path, config.width)
    size = source_img.size
    darkness = build_darkness_map(pixels, config)

    line_height = int(config.cell_size * config.line_spacing)
    num_lines = max(1, size[1] // line_height + 1)

    words = infinite_words(quote)
    lines = wrap_into_lines(words, font, max_width=size[0], num_lines=num_lines)

    renderer = render_dither if config.mode == "dither" else render_grayscale
    canvas = renderer(darkness, lines, font, config, size)

    canvas.save(output_path)
    return canvas


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Shape a quote's text into a black-and-white portrait."
    )
    parser.add_argument("image", help="Path to the source portrait photo.")
    parser.add_argument(
        "quote",
        nargs="?",
        help="Quote text to shape. Omit if using --quote-file.",
    )
    parser.add_argument("-o", "--output", default="quote_portrait.png", help="Output image path.")
    parser.add_argument("--quote-file", help="Read the quote text from a file instead.")
    parser.add_argument("--width", type=int, default=1400, help="Output width in pixels.")
    parser.add_argument("--cell-size", type=int, default=15, help="Font size / row height in pixels.")
    parser.add_argument("--line-spacing", type=float, default=1.05, help="Line height multiplier.")
    parser.add_argument("--contrast", type=float, default=1.35, help="Contrast boost applied to the source photo.")
    parser.add_argument("--gamma", type=float, default=0.85, help="Gamma curve applied to ink darkness (<1 makes midtones darker/bolder).")
    parser.add_argument("--edge-boost", type=float, default=90.0, help="How strongly edges (eyes, nose, jawline) are darkened, 0 to disable.")
    parser.add_argument("--white-threshold", type=int, default=248, help="Brightness above which no glyph is drawn (keeps highlights crisp white).")
    parser.add_argument("--mode", choices=["grayscale", "dither"], default="grayscale", help="'grayscale' shades each glyph by local brightness; 'dither' is pure black/white via error diffusion.")
    parser.add_argument("--invert", action="store_true", help="Invert tone mapping (light subject on dark background).")
    parser.add_argument("--font", dest="font_path", help="Path to a monospace .ttf font.")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)

    if args.quote_file:
        quote = Path(args.quote_file).read_text(encoding="utf-8")
    elif args.quote:
        quote = args.quote
    else:
        print("error: provide a quote as an argument or via --quote-file", file=sys.stderr)
        return 2

    config = PortraitConfig(
        width=args.width,
        cell_size=args.cell_size,
        line_spacing=args.line_spacing,
        contrast=args.contrast,
        gamma=args.gamma,
        edge_boost=args.edge_boost,
        white_threshold=args.white_threshold,
        mode=args.mode,
        invert=args.invert,
        font_path=args.font_path,
    )

    generate_portrait(args.image, quote, args.output, config)
    print(f"Saved {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
