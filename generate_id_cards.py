import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# TEMPLATE PATH
TEMPLATE_UK = os.path.join(BASE_DIR, "template_uk.png")
TEMPLATE_IN = os.path.join(BASE_DIR, "template_india.png")
TEMPLATE_BD = os.path.join(BASE_DIR, "template_bd.png")

# FONT
ARIAL_BOLD = os.path.join(BASE_DIR, "Arial-bold", "Arial-Bold.ttf")
VERDANA = os.path.join(BASE_DIR, "verdana.ttf")

def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()


# ==========================
# UK CARD GENERATOR
# ==========================

def generate_uk_card(name: str, out_path: str):

    img = Image.open(TEMPLATE_UK).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font_big = _load_font(ARIAL_BOLD, 40)
    font_mid = _load_font(ARIAL_BOLD, 38)

    draw.text((190, 180), name, fill="black", font=font_big)
    draw.text((240, 255), "1201-0732", fill="black", font=font_mid)
    draw.text((240, 330), "10/10/2005", fill="black", font=font_mid)
    draw.text((260, 405), "LONDON, UK", fill="black", font=font_mid)

    img.save(out_path, format="PNG")
    return out_path


# ==========================
# INDIA CARD GENERATOR
# ==========================

def generate_india_card(name: str, out_path: str):

    img = Image.open(TEMPLATE_IN).convert("RGBA")
    draw = ImageDraw.Draw(img)

    font_big = _load_font(ARIAL_BOLD, 42)
    font_sml = _load_font(ARIAL_BOLD, 34)

    draw.text((350, 310), name, fill="black", font=font_big)
    draw.text((350, 390), "ECE", fill="black", font=font_sml)
    draw.text((720, 390), "MU23ECE001", fill="black", font=font_sml)
    draw.text((350, 460), "15/01/2000", fill="black", font=font_sml)
    draw.text((720, 460), "11/25 - 11/26", fill="black", font=font_sml)
    draw.text((350, 530), "+917546728719", fill="black", font=font_sml)

    img.save(out_path, format="PNG")
    return out_path


# =========================
