from PIL import Image, ImageDraw, ImageFont
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ================================
# 1. CARI FILE TEMPLATE
# ================================
def get_template():
    for f in os.listdir(BASE_DIR):
        low = f.lower()
        if low.startswith("template") and low.endswith((".png", ".jpg", ".jpeg")):
            print("✔ Template ditemukan:", f)
            return os.path.join(BASE_DIR, f)
    print("❌ Template tidak ditemukan.")
    return None

# ================================
# 2. LOAD NAMES.TXT
# ================================
def load_names():
    file_path = os.path.join(BASE_DIR, "names.txt")
    if not os.path.exists(file_path):
        print("❌ names.txt TIDAK ditemukan!")
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        names = [x.strip() for x in f.readlines() if x.strip()]

    if not names:
        print("❌ names.txt kosong!")
        return None

    print("✔", len(names), "nama dimuat dari names.txt")
    return names

# ================================
# POSISI TEKS (SAMAIN CANVA)
# ================================
# center kira-kira: X=390, Y=340 dari data Canva
TEXT_X = 390
TEXT_Y = 333

# ================================
# GENERATE ID CARD
# ================================
def generate(template_img, name, idx):
    img = template_img.copy()
    draw = ImageDraw.Draw(img)

    # FONT BOLD (ARIAL BOLD) + SIZE PAS
    try:
        font = ImageFont.truetype("arialbd.ttf", 49)
    except:
        font = ImageFont.load_default()

    # NAMA UPPERCASE
    text = name.strip().upper()

    # HITUNG SIZE TEKS
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    # POSISI TENGAH DI TITIK YANG KITA SET
    x = TEXT_X - w // 2
    y = TEXT_Y - h // 2

    # WARNA BIRU SAMA SEPERTI NAME/ID/BIRTH (kurang lebih #1C1A7E)
    color = (28, 26, 126)

    draw.text((x, y), text, font=font, fill=color)

    # BUAT NAMA FILE AMAN
    safe = "".join(c for c in text if c.isalnum())
    if not safe:
        safe = f"user{idx}"

    output_dir = os.path.join(BASE_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)

    out_file = os.path.join(output_dir, f"idcard_{idx}_{safe}.png")
    img.save(out_file)

    print("✔ Saved:", out_file)

# ================================
# MAIN PROGRAM
# ================================
def main():
    template_path = get_template()
    if not template_path:
        return

    names = load_names()
    if not names:
        return

    template_img = Image.open(template_path)

    for i, name in enumerate(names, 1):
        generate(template_img, name, i)

    print("\n🔥 Semua ID Card berhasil dibuat! Cek folder output.")

if __name__ == "__main__":
    main()
