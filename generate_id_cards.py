import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# PATH TEMPLATE
# =========================
TEMPLATE_UK = os.path.join(BASE_DIR, "template_uk.png")
TEMPLATE_INDIA = os.path.join(BASE_DIR, "template_india.png")
TEMPLATE_BD = os.path.join(BASE_DIR, "template_bd.png")  # template Bangladesh

# =========================
# PATH FONT
# =========================
# UK & India pakai Arial Bold
ARIAL_BOLD_FONT = os.path.join(BASE_DIR, "Arial-bold.ttf")   # <— font baru lu
ARIAL_REG_FONT = os.path.join(BASE_DIR, "arial.ttf")         # fallback kalau bold nggak ada

# Bangladesh pakai Verdana (kalau nggak ada → fallback ke Arial biasa)
VERDANA_FONT = os.path.join(BASE_DIR, "verdana.ttf")

# =========================
# POSISI & SIZE NAMA
# (Kalau mau geser / gedein, EDIT DI SINI AJA)
# =========================

# 🇬🇧 UK card
UK_NAME_POS = (260, 260)   # (x, y) — geser kanan/kiri/atas/bawah
UK_NAME_SIZE = 42          # gedein/kecilin font

# 🇮🇳 India card
INDIA_NAME_POS = (120, 950)
INDIA_NAME_SIZE = 46

# 🇧🇩 Bangladesh receipt
BD_NAME_POS = (260, 580)   # posisi setelah "Name:"
BD_NAME_SIZE = 32

# =========================
# HELPER
# =========================

def _load_first_available(candidates, size: int) -> ImageFont.FreeTypeFont:
    """
    Coba load font dari list path. Kalau semua gagal → font default.
    """
    for path in candidates:
        if not path:
            continue
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

# =========================
# GENERATOR NAME-ONLY
# =========================

def generate_uk_card(name: str, out_path: str) -> str:
    """
    Generate 1 UK card hanya dengan nama.
    Pakai Arial Bold + fake bold (multi-layer).
    """
    img = Image.open(TEMPLATE_UK).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(
        [ARIAL_BOLD_FONT, ARIAL_REG_FONT],
        UK_NAME_SIZE,
    )

    x, y = UK_NAME_POS

    # Tebal: gambar beberapa kali dengan offset kecil
    offsets = [(0, 0), (1, 0), (0, 1), (1, 1), (1, 2), (2, 1)]
    for ox, oy in offsets:
        draw.text((x + ox, y + oy), name, font=font, fill="black")

    img.save(out_path, format="PNG")
    return out_path


def generate_india_card(name: str, out_path: str) -> str:
    """
    Generate 1 India card hanya dengan nama.
    Pakai Arial Bold + sedikit bold effect.
    """
    img = Image.open(TEMPLATE_INDIA).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(
        [ARIAL_BOLD_FONT, ARIAL_REG_FONT],
        INDIA_NAME_SIZE,
    )

    x, y = INDIA_NAME_POS

    # Bold lebih mild dibanding UK (biar nggak terlalu tebal)
    offsets = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for ox, oy in offsets:
        draw.text((x + ox, y + oy), name, font=font, fill="black")

    img.save(out_path, format="PNG")
    return out_path


def generate_bangladesh_card(name: str, out_path: str) -> str:
    """
    Generate 1 Bangladesh fee receipt hanya dengan nama.
    Font: Verdana (kalau ada), kalau nggak → Arial biasa.
    TANPA bold ekstra, sesuai permintaan.
    """
    img = Image.open(TEMPLATE_BD).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(
        [VERDANA_FONT, ARIAL_REG_FONT, ARIAL_BOLD_FONT],
        BD_NAME_SIZE,
    )

    x, y = BD_NAME_POS
    draw.text((x, y), name, font=font, fill="black")

    img.save(out_path, format="PNG")
    return out_path
