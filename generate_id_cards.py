import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# TEMPLATE PATH
# =========================
TEMPLATE_UK = os.path.join(BASE_DIR, "template_uk.png")
TEMPLATE_IN = os.path.join(BASE_DIR, "template_india.png")
TEMPLATE_BD = os.path.join(BASE_DIR, "template_bd.png")

# =========================
# FONT CANDIDATES
# =========================
# UK & INDIA: coba cari Arial-bold di beberapa kemungkinan nama file
ARIAL_BOLD_CANDIDATES = [
    os.path.join(BASE_DIR, "Arial-bold", "Arial-bold.ttf"),
    os.path.join(BASE_DIR, "Arial-bold", "Arial-Bold.ttf"),
    os.path.join(BASE_DIR, "Arial-bold.ttf"),
]

# BANGLADESH: verdana.ttf (sesuai permintaan)
VERDANA_CANDIDATES = [
    os.path.join(BASE_DIR, "verdana.ttf"),
]


def _load_first_available(candidates, size: int) -> ImageFont.FreeTypeFont:
    """
    Coba load font dari list path. Kalau semua gagal, pakai default Pillow
    (biar bot tetap jalan dan nggak 'cannot open resource').
    """
    for path in candidates:
        try:
            if path and os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            continue
    # fallback aman
    return ImageFont.load_default()


# =========================
# POSISI / SIZE TEKS
# (Kalau mau geser, EDIT DI SINI AJA)
# =========================

# UK
UK_NAME_POS = (260, 260)
UK_NAME_SIZE = 42

# INDIA
INDIA_NAME_POS = (120, 950)
INDIA_NAME_SIZE = 46

# BD (header miring atas)
BD_HEADER_POS = (260, 230)
BD_HEADER_SIZE = 32


# =========================
# GENERATE UK
# =========================

def generate_uk_card(name: str, out_path: str) -> str:
    img = Image.open(TEMPLATE_UK).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(ARIAL_BOLD_CANDIDATES, UK_NAME_SIZE)

    # NAMA FULL KAPITAL
    text = name.upper()
    x, y = UK_NAME_POS

    for ox, oy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((x + ox, y + oy), text, font=font, fill="black")

    img.save(out_path, format="PNG")
    return out_path


# =========================
# GENERATE INDIA
# =========================

def generate_india_card(name: str, out_path: str) -> str:
    img = Image.open(TEMPLATE_IN).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(ARIAL_BOLD_CANDIDATES, INDIA_NAME_SIZE)

    # NAMA FULL KAPITAL
    text = name.upper()
    x, y = INDIA_NAME_POS

    for ox, oy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((x + ox, y + oy), text, font=font, fill="black")

    img.save(out_path, format="PNG")
    return out_path



# =========================
# GENERATE BANGLADESH
# =========================

def generate_bangladesh_card(name: str, out_path: str) -> str:
    """
    Generate Bangladesh fee receipt — header miring cuma pakai NAMA.
    Font khusus: verdana.ttf (kalau ada), fallback ke default kalau nggak ketemu.
    """
    img = Image.open(TEMPLATE_BD).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(VERDANA_CANDIDATES, BD_HEADER_SIZE)

    clean_name = name.title()
    x, y = BD_HEADER_POS

    draw.text((x, y), clean_name, font=font, fill="black")

    img.save(out_path, format="PNG")
    return out_path
