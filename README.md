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

The quote is set **once, in full** — never repeated. The photo is reduced to
four tonal bands via Otsu thresholding, and each band gets its own
typographic voice, not just a bigger or bolder version of the same one:

| Band | Typeface | Feel |
|---|---|---|
| Faintest highlights | NothingYouCouldDo (script) | a whispered, handwritten touch |
| Soft shading | Instrument Serif Italic | small, delicate |
| Mid-tones | Lora | the readable backbone |
| Deepest shadow (hair, brows, eyes, jaw) | Big Shoulders (bold display) | large, dramatic |

Within a band, every individual word also gets its own small, deterministic
jitter in size and baseline (and a slight tilt for the script band) — so it
reads as hand-set and collaged rather than a mechanically uniform grid,
while staying legible. A solver picks the largest comfortable base size at
which the *entire* quote still fits somewhere on the portrait's shape —
shrinking only as far as genuinely necessary.

A real photo can carry far more fine detail (individual hair strands,
wrinkles) than a short quote has words to trace. Rather than either scatter
a handful of words across hundreds of rows (reads as noise) or blow the type
up to poster size to compensate, the app blurs the tonal map by an amount
tied to the word count before thresholding it — merging fine detail into a
smaller number of coherent regions (a hair mass, glasses, a jaw shadow, a
collar) roughly sized to what the quote can actually cover, then samples
those regions with whole-band voting rather than a single fragile point
sample. A quote is never truncated: if a photo's shape genuinely can't hold
it at a legible size, the remainder wraps as a plain line rather than being
cut off. Very short quotes (a handful of words) inherently can't convey a
detailed likeness — there just isn't enough text — and the status line says
so rather than pretending otherwise.

Controls: output width, contrast, tonal curve, edge emphasis, shading
balance (nudges the tone/background cutoff), and light-text-on-dark-ground
invert — plus a "Download PNG" button.

A longer quote gives the solver more to work with and traces the shape more
fully:

![web app example, long quote](examples/web_example_long.png)

A short quote still spreads across the portrait's most defining regions,
just more sparsely:

![web app example, short quote](examples/web_example.png)

## Command line

A separate, simpler command-line tool (`quoteimage/portrait.py`) is also
included — it tiles the quote repeatedly across the image, shaded by
brightness, rather than the browser app's single-pass/weighted-type
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
