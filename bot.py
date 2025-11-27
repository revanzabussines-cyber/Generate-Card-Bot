# =========================
# PATH DASAR & FILE TEMPLATE / FONT
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_UK = os.path.join(BASE_DIR, "template_uk.png")
TEMPLATE_IN = os.path.join(BASE_DIR, "template_india.png")
TEMPLATE_BD = os.path.join(BASE_DIR, "template_bd.png")
TEMPLATE_ID = os.path.join(BASE_DIR, "template_id.png")  # Indonesia

# UK & ID -> Arial Bold
ARIAL_BOLD_CANDIDATES = [
    os.path.join(BASE_DIR, "Arial-bold", "Arial-bold.ttf"),
    os.path.join(BASE_DIR, "Arial-bold", "Arial-Bold.ttf"),
    os.path.join(BASE_DIR, "Arial-bold.ttf"),
]

# INDIA -> Arial biasa (arial.ttf), fallback ke Arial Bold / default
ARIAL_REGULAR_CANDIDATES = [
    os.path.join(BASE_DIR, "arial.ttf"),
] + ARIAL_BOLD_CANDIDATES

# INDONESIA -> pakai Arial Bold juga
ARIAL_ID_CANDIDATES = ARIAL_BOLD_CANDIDATES

# BANGLADESH -> Verdana (diperluas untuk mencakup berbagai lokasi)
VERDANA_CANDIDATES = [
    os.path.join(BASE_DIR, "verdana.ttf"),
    os.path.join(BASE_DIR, "Verdana.ttf"),
    os.path.join(BASE_DIR, "fonts", "verdana.ttf"),
    os.path.join(BASE_DIR, "fonts", "Verdana.ttf"),
    "/usr/share/fonts/truetype/msttcorefonts/verdana.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Verdana.ttf",
    "C:\\Windows\\Fonts\\verdana.ttf",
    "C:\\Windows\\Fonts\\Verdana.ttf",
]

# warna biru gelap baru (#1E2365)
DARK_BLUE = (30, 35, 101)


def _load_first_available(candidates, size: int) -> ImageFont.FreeTypeFont:
    """Coba load font dari list path, kalau gagal pakai default Pillow."""
    for path in candidates:
        try:
            if path and os.path.exists(path):
                font = ImageFont.truetype(path, size)
                print(f"✅ Font berhasil dimuat: {path}")
                return font
        except Exception as e:
            print(f"⚠️ Gagal load font {path}: {e}")
            continue
    
    print("⚠️ Semua font kandidat gagal, menggunakan default font")
    return ImageFont.load_default()


# =========================
# POSISI TEKS DI TEMPLATE
# =========================

# UK
UK_NAME_POS = (250, 325)
UK_NAME_SIZE = 42

# INDIA (center horizontal, Y bisa diatur)
INDIA_NAME_Y = 665
INDIA_NAME_SIZE = 43

# INDONESIA (center horizontal, bisa geser kanan/kiri pakai offset)
ID_NAME_Y = 320
ID_NAME_X_OFFSET = 200
ID_NAME_SIZE = 50

# BANGLADESH - PENTING: Pastikan posisi dan ukuran sesuai template
BD_HEADER_POS = (145, 427)
BD_HEADER_SIZE = 28  # Ukuran font Verdana


def generate_bangladesh_card(name: str, out_path: str) -> str:
    """
    Generate fee receipt Bangladesh. 
    Nama Title Case, Verdana font, warna hitam.
    """
    img = Image.open(TEMPLATE_BD).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Load font Verdana dengan pengecekan
    font = _load_first_available(VERDANA_CANDIDATES, BD_HEADER_SIZE)
    
    # Verifikasi apakah font benar-benar Verdana atau default
    try:
        font_name = font.getname()[0] if hasattr(font, 'getname') else "Unknown"
        print(f"Font yang digunakan untuk BD: {font_name}")
    except:
        pass

    # Format nama: Title Case
    clean_name = name.title()
    x, y = BD_HEADER_POS

    # Tulis teks tanpa bold overlay (Verdana biasanya tidak perlu bold manual)
    draw.text((x, y), clean_name, font=font, fill="black")

    img.save(out_path, format="PNG")
    return out_path
