import os
import re
from uuid import uuid4

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext,
)

from PIL import Image, ImageDraw, ImageFont

# =========================
# CONFIG TOKEN
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")

# =========================
# PATH DASAR & FILE TEMPLATE / FONT
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_UK = os.path.join(BASE_DIR, "template_uk.png")
TEMPLATE_IN = os.path.join(BASE_DIR, "template_india.png")
TEMPLATE_BD = os.path.join(BASE_DIR, "template_bd.png")

ARIAL_BOLD_CANDIDATES = [
    os.path.join(BASE_DIR, "Arial-bold", "Arial-Bold.ttf"),
    os.path.join(BASE_DIR, "Arial-bold", "arial.ttf"),
    os.path.join(BASE_DIR, "verdana.ttf"),
]

VERDANA_CANDIDATES = [
    os.path.join(BASE_DIR, "verdana.ttf"),
]

# warna biru gelap (mirip teks NAME/ID/BIRTH)
DARK_BLUE = (27, 42, 89)


def _load_first_available(candidates, size: int) -> ImageFont.FreeTypeFont:
    """Coba load font dari list path, kalau gagal pakai default Pillow."""
    for path in candidates:
        try:
            if path and os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def make_safe_filename(text: str) -> str:
    """Bikin nama file aman: huruf/angka + underscore."""
    clean = re.sub(r"[^A-Za-z0-9]+", "_", text.strip())
    return clean or "card"


# =========================
# POSISI TEKS DI TEMPLATE
# (kalo mau geser, EDIT DI SINI AJA)
# =========================

# UK
UK_NAME_POS = (250, 325)   # posisi nama
UK_NAME_SIZE = 42

# INDIA
INDIA_NAME_POS = (120, 950)
INDIA_NAME_SIZE = 46

# BD
BD_HEADER_POS = (260, 230)
BD_HEADER_SIZE = 32


# =========================
# FUNGSI GENERATE CARD (DALAM bot.py)
# =========================

def generate_uk_card(name: str, out_path: str) -> str:
    """Generate kartu UK. Nama: FULL KAPITAL, warna biru gelap."""
    img = Image.open(TEMPLATE_UK).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(ARIAL_BOLD_CANDIDATES, UK_NAME_SIZE)

    text = name.upper()
    x, y = UK_NAME_POS

    # sedikit bold (4 layer)
    for ox, oy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((x + ox, y + oy), text, font=font, fill=DARK_BLUE)

    img.save(out_path, format="PNG")
    return out_path


def generate_india_card(name: str, out_path: str) -> str:
    """Generate kartu India. Nama: FULL KAPITAL, warna biru gelap."""
    img = Image.open(TEMPLATE_IN).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(ARIAL_BOLD_CANDIDATES, INDIA_NAME_SIZE)

    text = name.upper()
    x, y = INDIA_NAME_POS

    for ox, oy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((x + ox, y + oy), text, font=font, fill=DARK_BLUE)

    img.save(out_path, format="PNG")
    return out_path


def generate_bangladesh_card(name: str, out_path: str) -> str:
    """Generate fee receipt Bangladesh. Nama Title Case, Verdana, warna hitam."""
    img = Image.open(TEMPLATE_BD).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(VERDANA_CANDIDATES, BD_HEADER_SIZE)

    clean_name = name.title()
    x, y = BD_HEADER_POS

    draw.text((x, y), clean_name, font=font, fill="black")

    img.save(out_path, format="PNG")
    return out_path


# =========================
# TELEGRAM BOT LOGIC
# =========================

CHOOSING_TEMPLATE, INPUT_NAMES = range(2)


def start(update: Update, context: CallbackContext):
    text = (
        "👋 Selamat datang di *VanzShop ID Card Bot!* \n\n"
        "✨ Cukup kirim *NAMA* aja.\n"
        "• 1 baris → 1 kartu\n"
        "• Bisa banyak baris (maks 10), 1 baris 1 nama\n\n"
        "Pilih template dulu:"
    )

    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 UK", callback_data="TPL_UK"),
            InlineKeyboardButton("🇮🇳 India", callback_data="TPL_IN"),
            InlineKeyboardButton("🇧🇩 Bangladesh", callback_data="TPL_BD"),
        ]
    ]

    update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CHOOSING_TEMPLATE


def card_cmd(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 UK", callback_data="TPL_UK"),
            InlineKeyboardButton("🇮🇳 India", callback_data="TPL_IN"),
            InlineKeyboardButton("🇧🇩 Bangladesh", callback_data="TPL_BD"),
        ]
    ]
    update.message.reply_text(
        "Pilih template kartu yang mau dibuat:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_TEMPLATE


def template_chosen(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    data = query.data

    tpl_map = {
        "TPL_UK": "UK",
        "TPL_IN": "INDIA",
        "TPL_BD": "BD",
    }

    tpl = tpl_map.get(data)
    if not tpl:
        query.message.reply_text("Template tidak dikenal.")
        return ConversationHandler.END

    context.user_data["template"] = tpl

    query.message.reply_text(
        f"✅ Template *{tpl}* dipilih.\n\n"
        "Sekarang kirim *nama* yang mau dibuat kartunya (1–10 baris, 1 baris 1 nama).",
        parse_mode="Markdown",
    )

    return INPUT_NAMES


def handle_names(update: Update, context: CallbackContext):
    tpl = context.user_data.get("template", "UK")
    raw = update.message.text.strip()

    names = [line.strip() for line in raw.splitlines() if line.strip()]
    if not names:
        update.message.reply_text("❌ Input kosong, kirim lagi ya (1–10 baris).")
        return INPUT_NAMES

    if len(names) > 10:
        names = names[:10]
        update.message.reply_text("⚠ Maksimal 10 baris. Dipakai 10 baris pertama.")

    for idx, name in enumerate(names, start=1):
        raw_name = name.strip()
        upper_name = raw_name.upper()
        title_name = raw_name.title()

        safe_name = make_safe_filename(raw_name)
        out_path = f"{tpl.lower()}_{safe_name}_{idx}.png"

        try:
            # ====== Generate kartu ======
            if tpl == "UK":
                generate_uk_card(upper_name, out_path)

                caption = f"🇬🇧 UK • {upper_name}"
                info_text = (
                    "📘 *Kartu UK (LSE)*\n\n"
                    f"👤 *Nama Lengkap:* {upper_name}\n"
                    "🏫 *Universitas:* The London School of Economics and Political Science (LSE)\n"
                    "🪪 *ID (di kartu):* 1201-0732\n"
                    "🎂 *Tanggal Lahir (di kartu):* 10/10/2005\n"
                    "📍 *Alamat (di kartu):* London, UK\n"
                )

            elif tpl == "INDIA":
                generate_india_card(upper_name, out_path)

                caption = f"🇮🇳 India • {upper_name}"
                info_text = (
                    "📗 *Kartu India (University of Mumbai)*\n\n"
                    f"👤 *Nama Lengkap:* {upper_name}\n"
                    "🏫 *Universitas:* University of Mumbai\n"
                    "🪪 *ID No (di kartu):* MU23ECE001\n"
                    "📚 *Class (di kartu):* ECE\n"
                    "🎂 *D.O.B (di kartu):* 15/01/2000\n"
                    "📆 *Validity (di kartu):* 11/25 - 11/26\n"
                    "📞 *Mobile (di kartu):* +917546728719\n"
                )

            else:  # BD
                generate_bangladesh_card(title_name, out_path)

                caption = f"🇧🇩 Bangladesh • {title_name}"
                info_text = (
                    "📙 *Bangladesh Fee Receipt (Uttara Town College)*\n\n"
                    f"👤 *Nama (header):* {title_name}\n"
                    "🏫 *College:* Uttara Town College\n"
                    "📆 *Registration Date (di kartu):* 14.10.25\n"
                    "💰 *Amount (di kartu):* 18500 BDT\n"
                )

            # ====== Kirim file PNG sebagai document ======
            with open(out_path, "rb") as f:
                doc = InputFile(f, filename=os.path.basename(out_path))
                update.message.reply_document(doc, caption=caption)

            # ====== Kirim format teks biodata ======
            update.message.reply_text(info_text, parse_mode="Markdown")

        except Exception as e:
            update.message.reply_text(f"❌ Gagal generate untuk '{name}'. Error: {e}")
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    context.user_data.clear()
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    context.user_data.clear()
    update.message.reply_text("❌ Proses dibatalkan.")
    return ConversationHandler.END


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable belum di-set di Railway!")

    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("card", card_cmd),
        ],
        states={
            CHOOSING_TEMPLATE: [
                CallbackQueryHandler(template_chosen, pattern="^TPL_"),
            ],
            INPUT_NAMES: [
                MessageHandler(Filters.text & ~Filters.command, handle_names),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dp.add_handler(conv)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()




