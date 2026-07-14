"""Generate a synthetic grayscale face, used only to smoke-test portrait.py
when a real photo isn't available."""

from PIL import Image, ImageDraw, ImageFilter

W, H = 900, 1100
img = Image.new("L", (W, H), color=210)
draw = ImageDraw.Draw(img)

# Shoulders
draw.ellipse((150, 850, 750, 1300), fill=70)
# Neck
draw.rectangle((390, 760, 510, 900), fill=180)
# Face
draw.ellipse((220, 260, 680, 800), fill=195)
# Hair
draw.pieslice((200, 150, 700, 620), 180, 360, fill=30)
draw.ellipse((215, 250, 685, 420), fill=30)
# Eyebrows
draw.rectangle((300, 460, 400, 480), fill=40)
draw.rectangle((500, 460, 600, 480), fill=40)
# Eyes
draw.ellipse((310, 500, 390, 540), fill=255)
draw.ellipse((510, 500, 590, 540), fill=255)
draw.ellipse((335, 510, 365, 535), fill=20)
draw.ellipse((535, 510, 565, 535), fill=20)
# Nose shadow
draw.polygon([(450, 540), (420, 650), (480, 650)], fill=160)
# Mouth
draw.ellipse((370, 690, 530, 730), fill=90)
draw.ellipse((385, 695, 515, 715), fill=210)
# Cheek shading
draw.ellipse((230, 560, 340, 680), fill=175)
draw.ellipse((560, 560, 670, 680), fill=175)

img = img.filter(ImageFilter.GaussianBlur(4))
img.save("examples/sample_portrait.png")
print("wrote examples/sample_portrait.png")
