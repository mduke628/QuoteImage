# QuoteImage

Turns a portrait photo + a quote into a black-and-white typographic portrait.

## Browser app

`web/index.html` is a self-contained, no-install web app — everything (image
processing, text layout, rendering) runs client-side in JavaScript on a
`<canvas>`, so your photo never leaves the browser. Just open the file in
Chrome:

```bash
open web/index.html          # macOS
xdg-open web/index.html      # Linux
# or just double-click the file / drag it into a Chrome tab
```

Upload a photo, paste a quote, and it renders live.

It's a genuine **calligram**: the letters themselves bend to trace the
actual contour lines of the photo — the hairline, a jaw's edge, a glasses
rim, a collar — rather than being poured into a grid of straight rows. The
photo is traced with marching squares at four tonal thresholds (an Otsu
split, plus three finer bands into the shadows), producing a set of contour
strokes tagged by how dark the tone they trace is. Each tone gets its own
typographic voice, not just a bigger or bolder version of the same one:

| Tone | Typeface | Feel |
|---|---|---|
| Faintest highlights | NothingYouCouldDo (script) | a whispered, handwritten touch |
| Soft shading | Instrument Serif Italic | small, delicate |
| Mid-tones | Lora | the readable backbone |
| Deepest shadow (hair, brows, eyes, jaw) | Big Shoulders (bold display) | large, dramatic |

The quote is walked character-by-character along every contour stroke, each
glyph rotated to the path's local tangent so it leans into the curve it's
tracing. A short quote can't fill hundreds of strokes on its own, so — like
a real word-artist repeating a phrase to fill a shape — it cycles
indefinitely (separated by ✦) until every contour the photo offers has been
traced. A solver picks the type size that keeps most of those contours long
enough to carry legible letters: too large and only the longest strokes
(an outline, a shoulder) can hold any text, leaving the interior detail
(eyes, brow, glasses) bare; too small and it stops reading as letters at
all. The image is recognizable purely from the *arrangement* of the
strokes — the quote is never truncated to make that work; if a photo's
strokes genuinely can't carry even one full pass of it, the remainder wraps
as a plain line rather than being cut off.

Controls: output width, contrast, tonal curve, edge emphasis, shading
balance (nudges the tone/background cutoff), and light-text-on-dark-ground
invert — plus a "Download PNG" button.

A longer quote reads clearly in full on its first pass around the shape:

![web app example, long quote](examples/web_example_long.png)

A short quote just cycles more times to trace the same contours:

![web app example, short quote](examples/web_example.png)

## Command line

A separate, simpler command-line tool (`quoteimage/portrait.py`) is also
included — it tiles the quote repeatedly across a row/column grid, shaded
by brightness, rather than the browser app's contour-tracing calligram
approach above.

![CLI example](examples/cli_example.png)

## Setup

```bash
pip install -r requirements.txt
```

Needs a monospace TrueType font on the system (DejaVu Sans Mono, Liberation
Mono, or FreeMono are auto-detected); pass `--font /path/to/font.ttf` if
none of those are installed.

## Usage

```bash
python3 -m quoteimage.portrait photo.jpg "Your quote here." -o portrait.png
```

Or read a long quote (with attribution) from a file:

```bash
python3 -m quoteimage.portrait photo.jpg --quote-file quote.txt -o portrait.png
```

### Key options

| Flag | Default | Effect |
|---|---|---|
| `--width` | 1400 | Output width in pixels (height follows the photo's aspect ratio). |
| `--cell-size` | 15 | Font size / row height. Smaller = more detail, finer text. |
| `--contrast` | 1.35 | Contrast boost on the source photo before mapping to ink. |
| `--gamma` | 0.85 | <1 darkens midtones (bolder, more visible text); >1 lightens them. |
| `--edge-boost` | 90 | How strongly edges (eyes, nose, jaw outline) are darkened for recognizability. Set to `0` to disable. |
| `--white-threshold` | 248 | Brightness above which no glyph is drawn, keeping highlights crisp white. |
| `--mode` | `grayscale` | `grayscale` shades each glyph by local brightness (best likeness). `dither` uses error diffusion for a pure black/white (no gray) result. |
| `--invert` | off | Light subject on a dark/black background instead of dark-on-white. |

Run `python3 -m quoteimage.portrait --help` for the full list.

## How it works

1. The photo is loaded, auto-contrasted, and converted to grayscale.
2. An edge map (Pillow's `FIND_EDGES`) is blended in so facial contours stay
   crisp even in flatter-toned areas.
3. The quote is split into words and repeated indefinitely (looping quotes
   are separated with `✦`), then greedily word-wrapped into text lines that
   fill the image, just like a paragraph.
4. For every glyph, the script samples the average brightness of the photo
   pixels directly beneath it and uses that to pick the glyph's gray level
   (or, in `--mode dither`, whether to draw it at all, via 1-D error
   diffusion along each line).
5. The result is saved as a flattened grayscale PNG.

## Tuning tips

- **Faces looking muddy/unrecognizable:** raise `--edge-boost` and/or lower
  `--gamma` (e.g. `0.7`) to punch up contrast.
- **Text hard to read:** raise `--cell-size` (bigger glyphs) or lower
  `--contrast`/raise `--white-threshold` so fewer glyphs render at heavy ink.
- **Want a poster-style pure black/white look:** use `--mode dither`.
- For best results use a well-lit, front-facing portrait with a plain
  background and good separation between the subject and background
  brightness.

## Try it without a real photo

`examples/make_sample_portrait.py` draws a synthetic face you can use to
sanity-check the pipeline:

```bash
python3 examples/make_sample_portrait.py
python3 -m quoteimage.portrait examples/sample_portrait.png \
  "The only way to do great work is to love what you do." \
  -o examples/cli_example.png
```
