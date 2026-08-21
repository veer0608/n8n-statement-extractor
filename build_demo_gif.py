"""
Build demo.gif - an animated explainer for the listing.

Tells the real story: rows extract and reconcile one by one, then the model's
salary-row mistake gets caught and flagged. Styled to match thumbnail.png.
Deterministic (PIL frames), no screen recording needed.
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 540
BG = (10, 18, 32)
PANEL = (16, 29, 48)
PANEL_LINE = (34, 55, 79)
INK = (234, 240, 247)
MUTE = (150, 170, 192)
GREEN = (86, 214, 160)
AMBER = (255, 154, 82)
BLUE = (74, 163, 255)
ROW_LINE = (23, 37, 56)
FLAG_BG = (36, 26, 18)

F = "C:/Windows/Fonts/arial.ttf"
FB = "C:/Windows/Fonts/arialbd.ttf"
FM = "C:/Windows/Fonts/consola.ttf"
title = ImageFont.truetype(FB, 30)
kick = ImageFont.truetype(FB, 15)
hd = ImageFont.truetype(FB, 15)
rowf = ImageFont.truetype(F, 17)
amt = ImageFont.truetype(FM, 17)
small = ImageFont.truetype(F, 14)
big = ImageFont.truetype(FB, 34)
med = ImageFont.truetype(FB, 19)

# date, description, amount-string, status: 'ok' | 'flag'
ROWS = [
    ("02 Jun", "NEFT IN  Orion Logistics", "826,820.00", "ok"),
    ("05 Jun", "RTGS  Harbourside Supplies LLP", "728,574.50", "ok"),
    ("12 Jun", "Card reversal  merchant dispute", "754,484.50", "ok"),
    ("14 Jun", "Salary disbursement  batch 1", "541,684.50", "flag"),
    ("22 Jun", "NEFT IN  Kestrel Industries", "634,877.25", "ok"),
    ("30 Jun", "IMPS IN  Settlement adjustment", "518,312.00", "ok"),
]

MX, TOP = 60, 150
RW, RH = 840, 46


def base():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.ellipse([W - 360, -220, W + 120, 180], fill=(18, 44, 68))
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # kicker + title
    d.ellipse([MX, 44, MX + 11, 55], fill=AMBER)
    d.text((MX + 22, 42), "n8n WORKFLOW  ·  PDF EXTRACTION", font=kick, fill=BLUE)
    d.text((MX, 74), "Statement PDF  ", font=title, fill=INK)
    w1 = d.textlength("Statement PDF  ", font=title)
    d.text((MX + w1, 74), "\u2192 ", font=title, fill=BLUE)
    w2 = w1 + d.textlength("\u2192 ", font=title)
    d.text((MX + w2, 74), "Reconciled Rows", font=title, fill=GREEN)
    # table header
    d.text((MX, TOP - 26), "DATE", font=hd, fill=MUTE)
    d.text((MX + 90, TOP - 26), "DESCRIPTION", font=hd, fill=MUTE)
    d.text((MX + 560, TOP - 26), "BALANCE", font=hd, fill=MUTE)
    d.text((MX + 770, TOP - 26), "CHECK", font=hd, fill=MUTE)
    d.line([MX, TOP - 4, MX + RW, TOP - 4], fill=PANEL_LINE, width=1)
    return img, d


def mark(d, cx, cy, kind):
    r = 13
    if kind == "ok":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(20, 52, 42), outline=GREEN)
        d.line([cx - 6, cy, cx - 2, cy + 5], fill=GREEN, width=3)
        d.line([cx - 2, cy + 5, cx + 6, cy - 5], fill=GREEN, width=3)
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=FLAG_BG, outline=AMBER)
        d.line([cx, cy - 6, cx, cy + 2], fill=AMBER, width=3)
        d.ellipse([cx - 2, cy + 5, cx + 2, cy + 9], fill=AMBER)


def draw_rows(d, revealed, flag_on):
    for i in range(revealed):
        date, desc, bal, status = ROWS[i]
        y = TOP + i * RH
        is_flag = status == "flag" and flag_on
        if is_flag:
            d.rounded_rectangle([MX - 8, y + 3, MX + RW + 8, y + RH - 5], radius=7, fill=FLAG_BG)
        d.text((MX, y + 12), date, font=rowf, fill=MUTE)
        d.text((MX + 90, y + 12), desc, font=rowf, fill=INK if not is_flag else AMBER)
        d.text((MX + 560, y + 12), bal, font=amt, fill=INK)
        cx, cy = MX + 792, y + RH // 2
        if status == "flag" and not flag_on:
            d.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], outline=PANEL_LINE)
        else:
            mark(d, cx, cy, status if not is_flag else "flag")
        if is_flag:
            d.text((MX + 90, y + 30), "", font=small)
        if i < revealed - 1:
            d.line([MX, y + RH, MX + RW, y + RH], fill=ROW_LINE, width=1)


def flag_caption(d):
    y = TOP + 4 * RH + 6
    d.text((MX + 90, y), "balance mismatch: expected 967,284.50, got 541,684.50  \u2192  sent to review",
           font=small, fill=AMBER)


def summary_overlay(img):
    ov = Image.new("RGBA", (W, H), (10, 18, 32, 205))
    d = ImageDraw.Draw(ov)
    cx = W // 2
    d.text((cx, 150), "15 reconciled   ·   1 flagged", font=big, fill=INK, anchor="mm")
    d.rounded_rectangle([cx - 250, 200, cx - 10, 250], radius=10, fill=(20, 52, 42))
    d.text((cx - 130, 225), "15  verified", font=med, fill=GREEN, anchor="mm")
    d.rounded_rectangle([cx + 10, 200, cx + 250, 250], radius=10, fill=FLAG_BG)
    d.text((cx + 130, 225), "1  caught", font=med, fill=AMBER, anchor="mm")
    d.text((cx, 300), "The model mislabelled a row. The arithmetic caught it", font=med, fill=INK, anchor="mm")
    d.text((cx, 332), "before it reached the books.", font=med, fill=INK, anchor="mm")
    d.text((cx, 392), "Every row: reconciled, flagged, or marked unverified.", font=rowf, fill=MUTE, anchor="mm")
    d.text((cx, 418), "Nothing wrong ever passes as right.", font=rowf, fill=MUTE, anchor="mm")
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


frames, durations = [], []


def add(img, ms):
    frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=128))
    durations.append(ms)


# intro
img, d = base()
add(img, 700)
# reveal rows one by one (salary shown neutral first)
for r in range(1, len(ROWS) + 1):
    img, d = base()
    draw_rows(d, r, flag_on=False)
    add(img, 360)
# flag the salary row
img, d = base()
draw_rows(d, len(ROWS), flag_on=True)
flag_caption(d)
add(img, 1500)
# summary
img, d = base()
draw_rows(d, len(ROWS), flag_on=True)
add(summary_overlay(img), 2600)

frames[0].save("demo.gif", save_all=True, append_images=frames[1:],
               duration=durations, loop=0, optimize=True, disposal=2)
import os
print("wrote demo.gif  %d frames  %.1f KB" % (len(frames), os.path.getsize("demo.gif") / 1024))
