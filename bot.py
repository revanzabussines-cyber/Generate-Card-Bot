import os
import io
import re
from PIL import Image, ImageDraw, ImageFont

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
)

# =====================================
# KONFIGURASI DASAR
# =====================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN tidak ditemukan. Set env BOT_TOKEN di Render / Railway!")

BOT_TOKEN = BOT_TOKEN.strip()

TOKEN_PATTERN = re.compile(r"^\d+:[A-Za-z0-9_-]{30,}$")
if not TOKEN_PATTERN.match(BOT_TOKEN):
    raise ValueError("❌ Format BOT_TOKEN salah. Cek lagi token di dashboard.")

print("BOT_TOKEN OK | len =", len(BOT_TOKEN))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_UK = os.path.join(BASE_DIR, "template_uk.png")
TEMPLATE_INDIA = os.path.join(BASE_DIR, "template_india.png")

FONT_PATH = os.path.join(BASE_DIR, "arial.ttf")

CHANNEL_URL = "https://t.me/VanzDisscusion"
GROUP_URL = "https://t.me/VANZSHOPGROUP"

# CONFIG POSISI TEKS UK
TEXT_X_UK = 250
TEXT_Y_UK = 325   # TURUN 30px dari sebelumnya
FONT_SIZE_UK = 25

# INDIA
FONT_SIZE_INDIA = 42
TEXT_Y_INDIA = 675
TEXT_COLOR_INDIA = (0, 0, 0)


# =====================================
# HELPER
# =====================================

def safe_filename(name: str) -> str:
    name = name.upper().strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Z0-9_]", "", name)
    return (name or "IDCARD") + ".png"


def generate_card(name: str, template_path: str) -> io.BytesIO:
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    text = name.strip().upper()

    try:
        font_uk = ImageFont.truetype(FONT_PATH, FONT_SIZE_UK)
        font_india = ImageFont.truetype(FONT_PATH, FONT_SIZE_INDIA)
    except Exception:
        font_uk = ImageFont.load_default()
        font_india = ImageFont.load_default()

    # ==========================
    # TEMPLATE UK (PERBAIKAN)
    # ==========================
    if "uk" in template_path.lower():

        bbox = draw.textbbox((0, 0), text, font=font_uk)
        h = bbox[3] - bbox[1]

        offset_y = 10   # turun dikit biar pas 👍

        x = TEXT_X_UK
        y = (TEXT_Y_UK - h // 2) + offset_y

        draw.text(
            (x, y),
            text,
            font=font_uk,
            fill=(28, 26, 126),
            stroke_width=2,
            stroke_fill=(10, 8, 80),
        )

    # ==========================
    # TEMPLATE INDIA
    # ==========================
    else:
        bbox = draw.textbbox((0, 0), text, font=font_india)
        w = bbox[2] - bbox[0]
        x = (img.width // 2) - (w // 2)
        y = TEXT_Y_INDIA
        draw.text((x, y), text, font=font_india, fill=TEXT_COLOR_INDIA)

    output = io.BytesIO()
    output.name = safe_filename(text)
    img.save(output, "PNG")
    output.seek(0)
    return output


# =====================================
# HANDLERS
# =====================================

def start(update: Update, context: CallbackContext):
    welcome_text = (
        "👋 **Selamat datang di VanzShop ID Card Bot!**\n\n"
        "Bikin ID Card otomatis dengan cepat.\n\n"
        "Pilih menu di bawah atau pakai perintah:\n"
        "• `/card` → Pilih template & buat 1 kartu\n"
        "• `/batch` → Buat banyak kartu sekaligus"
    )

    keyboard = [
        [InlineKeyboardButton("🇬🇧 Generate Card UK", callback_data="single_uk")],
        [InlineKeyboardButton("🇮🇳 Generate Card India", callback_data="single_india")],
        [
            InlineKeyboardButton("📦 Batch Card UK", callback_data="batch_uk"),
            InlineKeyboardButton("📦 Batch Card India", callback_data="batch_india"),
        ],
        [
            InlineKeyboardButton("📢 Channel", url=CHANNEL_URL),
            InlineKeyboardButton("👥 Group", url=GROUP_URL),
        ],
    ]

    update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def card(update: Update, context: CallbackContext):
    keyboard = [[
        InlineKeyboardButton("🇬🇧 UK", callback_data="single_uk"),
        InlineKeyboardButton("🇮🇳 India", callback_data="single_india"),
    ]]
    update.message.reply_text(
        "Pilih template kartu:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def batch(update: Update, context: CallbackContext):
    keyboard = [[
        InlineKeyboardButton("🇬🇧 UK Batch", callback_data="batch_uk"),
        InlineKeyboardButton("🇮🇳 India Batch", callback_data="batch_india"),
    ]]
    update.message.reply_text(
        "Pilih template batch:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def button_handler(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    data = q.data

    if data.startswith("single"):
        context.user_data["mode"] = "single"
    else:
        context.user_data["mode"] = "batch"

    if "uk" in data:
        context.user_data["template"] = TEMPLATE_UK
    else:
        context.user_data["template"] = TEMPLATE_INDIA

    if context.user_data["mode"] == "single":
        q.edit_message_text("Kirim 1 nama untuk dibuatkan kartu.")
    else:
        q.edit_message_text("Kirim daftar nama (max 10), 1 baris 1 nama.")


def handle_text(update: Update, context: CallbackContext):
    mode = context.user_data.get("mode")
    msg = update.message.text

    if mode == "single":
        update.message.reply_text("⏳ Membuat kartu...")
        img = generate_card(msg, context.user_data["template"])
        update.message.reply_document(img, caption=f"Done: {msg.upper()}")
        context.user_data["mode"] = None
        return

    if mode == "batch":
        names = [n.strip() for n in msg.splitlines() if n.strip()][:10]
        update.message.reply_text(f"⏳ Membuat {len(names)} kartu...")
        for name in names:
            img = generate_card(name, context.user_data["template"])
            update.message.reply_document(img, caption=name.upper())
        update.message.reply_text("🎉 Batch selesai!")
        context.user_data["mode"] = None
        return

    update.message.reply_text("Gunakan /start, /card, atau /batch untuk mulai.")


# =====================================
# MAIN
# =====================================

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("card", card))
    dp.add_handler(CommandHandler("batch", batch))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    print("BOT ONLINE 🚀")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()








