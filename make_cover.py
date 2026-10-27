"""Builds the Workshop cover of Battle Details (768x768, in the style of the Coalition Demands and Quartermaster
covers): the musketeers of cover_full.png at the top, the title in the game's Cormorant Garamond and the main features
below. Writes cover.png, the square preview.
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = "E:/SteamLibrary/steamapps/common/Europa Universalis V/game/"
FONTS = GAME + "loading_screen/fonts/CormorantGaramond/"
SIZE = 768
ART_H = 540
GOLD = (232, 196, 120)
TEXT = (226, 222, 210)
FEATURES = "Dice Rolls  ·  Flanks  ·  Losses  ·  Battle Journal"


def gradient(top, bottom):
    im = Image.new("RGB", (SIZE, SIZE))
    d = ImageDraw.Draw(im)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        d.line([(0, y), (SIZE, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return im


def main():
    cover = gradient((40, 30, 24), (20, 15, 12))

    # the picture to the cover's width, from its top (the faces), faded into the background at its bottom; it is a
    # screenshot: the mouse pointer on it painted over with the background either side, and the window's edge cut off
    full = Image.open(os.path.join(HERE, "cover_full.png")).convert("RGB")
    px = full.load()
    x0, x1, y0, y1 = 415, 436, 7, 38
    for y in range(y0, y1):
        a, b = px[x0, y], px[x1, y]
        for x in range(x0 + 1, x1):
            px[x, y] = tuple(round(a[i] + (b[i] - a[i]) * (x - x0) / (x1 - x0)) for i in range(3))
    patch = (x0 - 2, y0 - 2, x1 + 2, y1 + 2)
    full.paste(full.crop(patch).filter(ImageFilter.GaussianBlur(2)), patch[:2])
    full = full.crop((4, 0, full.width, full.height))
    art = full.resize((SIZE, round(full.height * SIZE / full.width)), Image.LANCZOS).crop((0, 0, SIZE, ART_H))
    fade = Image.new("L", art.size, 255)
    d = ImageDraw.Draw(fade)
    for y in range(ART_H - 190, ART_H):
        d.line([(0, y), (SIZE, y)], fill=round(255 * (ART_H - y) / 190))
    cover.paste(art, (0, 0), fade)

    d = ImageDraw.Draw(cover)
    title = ImageFont.truetype(FONTS + "CormorantGaramond-SemiBold.ttf", 108)
    sub = ImageFont.truetype(FONTS + "CormorantGaramond-Medium.ttf", 30)
    t = "Battle Details"
    w = d.textlength(t, font=title)
    d.text(((SIZE - w) / 2 + 3, 528 + 3), t, font=title, fill=(10, 8, 6))
    d.text(((SIZE - w) / 2, 528), t, font=title, fill=GOLD)
    d.line([(150, 666), (SIZE - 150, 666)], fill=GOLD, width=2)
    w = d.textlength(FEATURES, font=sub)
    assert w < SIZE - 40, w
    d.text(((SIZE - w) / 2, 682), FEATURES, font=sub, fill=TEXT)

    cover.save(os.path.join(HERE, "cover.png"))
    print("cover.png", cover.size)


if __name__ == "__main__":
    main()
