"""Generate a synthetic grayscale face with smooth (photo-like) shading,
used only to smoke-test the quote-portrait renderer when a real photo
isn't available. Uses radial falloffs instead of flat shapes so tonal
transitions are continuous, like real studio lighting."""

import numpy as np
from PIL import Image, ImageFilter

W, H = 900, 1100
yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

def radial(cx, cy, rx, ry, inner=0.0, outer=255.0, power=2.0):
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    d = np.clip(d, 0, 1)
    return inner + (outer - inner) * (d ** power)

# base: soft vignette background (studio backdrop, lit from upper left) — kept bright
# so it separates cleanly from the subject once auto-contrast stretches the tones.
bg = 222 + 20 * ((xx - W * 0.15) / W) - 14 * (yy / H)
canvas = np.clip(bg, 195, 245)

# shoulders / torso: a clean trapezoid widening from the neck to the frame edges,
# shaded darker on the right (away from the key light) like a real garment.
sy0, sy1 = 760, 1100
half_top, half_bottom = 75, 640
t = np.clip((yy - sy0) / (sy1 - sy0), 0, 1)
half_width = half_top + (half_bottom - half_top) * t
shoulder_mask = (yy > sy0) & (np.abs(xx - W * 0.5) < half_width)
shoulder_tone = 45 + 70 * ((xx - W * 0.5 + half_width) / np.maximum(2 * half_width, 1)) + 20 * t
canvas = np.where(shoulder_mask, shoulder_tone, canvas)

# neck
neck = radial(W * 0.5, 820, 70, 110, inner=95, outer=175, power=1.4)
neck_mask = (np.abs(xx - W * 0.5) < 65) & (yy > 720) & (yy < 900)
canvas = np.where(neck_mask, neck, canvas)

# face base with Rembrandt-style lighting (bright upper-left cheek, shadow lower-right)
face_d = np.sqrt(((xx - W * 0.5) / (W * 0.26)) ** 2 + ((yy - 520) / (H * 0.235)) ** 2)
face_mask = face_d < 1.0
light = 235 - 95 * ((xx - W * 0.30) / (W * 0.55)) - 25 * ((yy - 300) / H)
face_tone = np.clip(light, 90, 235)
face_edge_shadow = 1 - np.clip((1 - face_d) / 0.12, 0, 1)  # jaw/edge falloff
face_tone = face_tone * (1 - 0.55 * face_edge_shadow)
canvas = np.where(face_mask, face_tone, canvas)

# hair mass (dark, soft-edged, textured with subtle noise)
hair_d = np.sqrt(((xx - W * 0.5) / (W * 0.30)) ** 2 + ((yy - 330) / (H * 0.235)) ** 2)
hair_top_mask = (hair_d < 1.05) & (yy < 470)
rng = np.random.default_rng(7)
hair_noise = rng.normal(0, 9, size=canvas.shape)
hair_tone = np.clip(38 + 30 * hair_d + hair_noise, 8, 90)
canvas = np.where(hair_top_mask, hair_tone, canvas)

# eyebrows
for sx in (-1, 1):
    cx = W * 0.5 + sx * 95
    brow = radial(cx, 470, 55, 14, inner=35, outer=140, power=1.3)
    mask = (np.abs(xx - cx) < 58) & (np.abs(yy - 470) < 16)
    canvas = np.where(mask, np.minimum(canvas, brow), canvas)

# eyes (socket shadow + iris + highlight)
for sx in (-1, 1):
    cx = W * 0.5 + sx * 95
    socket = radial(cx, 512, 48, 26, inner=120, outer=210, power=1.5)
    socket_mask = (np.abs(xx - cx) < 50) & (np.abs(yy - 512) < 28)
    canvas = np.where(socket_mask, np.minimum(canvas, socket), canvas)
    iris = radial(cx, 514, 15, 15, inner=15, outer=90, power=1.0)
    iris_mask = ((xx - cx) ** 2 + (yy - 514) ** 2) < 15 ** 2
    canvas = np.where(iris_mask, iris, canvas)
    hi_mask = ((xx - (cx - 5)) ** 2 + (yy - 509) ** 2) < 4 ** 2
    canvas = np.where(hi_mask, 245, canvas)

# nose shading (bridge highlight, side shadow, nostril shadow)
nose_shadow = radial(W * 0.53, 610, 26, 70, inner=140, outer=225, power=1.6)
nose_mask = (xx > W * 0.5) & (xx < W * 0.5 + 55) & (yy > 540) & (yy < 660)
canvas = np.where(nose_mask, np.minimum(canvas, nose_shadow), canvas)
bridge_mask = (np.abs(xx - (W * 0.5 - 8)) < 10) & (yy > 545) & (yy < 630)
canvas = np.where(bridge_mask, np.maximum(canvas, 205), canvas)

# cheekbone shading (soft shadow toward the shadow side)
cheek_shadow = radial(W * 0.5 + 130, 590, 90, 110, inner=110, outer=235, power=1.7)
cheek_mask = (xx > W * 0.55) & (xx < W * 0.78) & (yy > 500) & (yy < 680) & face_mask
canvas = np.where(cheek_mask, np.minimum(canvas, cheek_shadow), canvas)

# mouth
mouth_shadow = radial(W * 0.5, 705, 60, 16, inner=70, outer=170, power=1.4)
mouth_mask = (np.abs(xx - W * 0.5) < 62) & (np.abs(yy - 705) < 18)
canvas = np.where(mouth_mask, np.minimum(canvas, mouth_shadow), canvas)
lip_hi = (np.abs(xx - W * 0.5) < 55) & (np.abs(yy - 697) < 6)
canvas = np.where(lip_hi, np.maximum(canvas, 190), canvas)

# jaw shadow under chin
chin_shadow = radial(W * 0.5, 770, 75, 22, inner=90, outer=200, power=1.5)
chin_mask = (np.abs(xx - W * 0.5) < 78) & (yy > 748) & (yy < 800)
canvas = np.where(chin_mask, np.minimum(canvas, chin_shadow), canvas)

img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), mode="L")
img = img.filter(ImageFilter.GaussianBlur(2.2))
img.save("examples/sample_portrait.png")
print("wrote examples/sample_portrait.png")
