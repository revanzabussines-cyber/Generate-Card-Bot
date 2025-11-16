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
    CallbackQueryHandler
)

# =====================================
# KONFIGURASI DASAR
# =====================================

BOT_TOKEN = os.getenv("BOT_TOKEN")  # ambil dari environment variable

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN tidak ditemukan. Set env BOT_TOKEN di Render dulu.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_UK = os.path.join(BASE_DIR, "template_uk.png")
TEMPLATE_INDIA = os.path.join(BASE_DIR, "template_india.png")

# UK text settings
TEXT_X_UK = 240
TEXT_Y_UK = 320
FONT_SIZE_UK = 46

# INDIA text settings (center)
FONT_SIZE_INDIA = 42
TEXT_Y_INDIA = 675   # Posisi tepat di bawah foto
TEXT_COLOR_INDIA = (0, 0, 0)

# Font path
FONT_PATH = os.path.join(BASE_DIR, "arialbd.ttf")



# =====================================
# HELPER
# =====================================

def safe_filename(name: str):
    name = name.upper().strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Z0-9_]", "", name)
    return (name or "IDCARD") + ".png"


def generate_card(name: str, template_path: str):
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    text = name.strip().upper()

    # Load fonts
    try:
        font_uk = ImageFont.truetype(FONT_PATH, FONT_SIZE_UK)
        font_india = ImageFont.truetype(FONT_PATH, FONT_SIZE_INDIA)
    except:
        font_uk = ImageFont.load_default()
        font_india = ImageFont.load_default()

    # ========================
    # TEMPLATE UK
    # ========================
    if "uk" in template_path.lower():
        bbox = draw.textbbox((0, 0), text, font=font_uk)
        h = bbox[3] - bbox[1]
        x = TEXT_X_UK
        y = TEXT_Y_UK - h // 2

        draw.text((x, y), text, font=font_uk, fill=(28, 26, 126))

    # ========================
    # TEMPLATE INDIA (CENTER)
    # ========================
    else:
        bbox = draw.textbbox((0, 0), text, font=font_india)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        x = (img.width // 2) - (w // 2)
        y = TEXT_Y_INDIA

        draw.text((x, y), text, font=font_india, fill=TEXT_COLOR_INDIA)

    # Save output
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
        "Bot ini membantu kamu membuat **ID Card otomatis**, cepat, rapi, dan gratis.\n\n"
        "📌 *Template yang tersedia:*\n"
        "• 🇬🇧 Student Card UK (LSE)\n"
        "• 🇮🇳 Student Card India\n"
        "• 🧾 Batch Generate (hingga 10 nama sekaligus)\n\n"
        "💬 **Dibuat oleh:** *VanzShop.id*\n"
        "👤 **Owner:** @VanzzSkyyID\n"
        "🔧 Butuh bot custom? Hubungi owner.\n\n"
        "Gunakan:\n"
        "• `/card` → Buat 1 kartu\n"
        "• `/batch` → Buat banyak kartu\n"
    )
    update.message.reply_text(welcome_text, parse_mode="Markdown")


# ================= SINGLE MODE ================
def card(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 Card UK", callback_data="single_uk"),
            InlineKeyboardButton("🇮🇳 Card INDIA", callback_data="single_india")
        ]
    ]
    update.message.reply_text("Pilih template kartu:", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= BATCH MODE ================
def batch(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 Batch UK", callback_data="batch_uk"),
            InlineKeyboardButton("🇮🇳 Batch INDIA", callback_data="batch_india")
        ]
    ]
    update.message.reply_text("Pilih template batch:", reply_markup=InlineKeyboardMarkup(keyboard))


# =================================================
# HANDLE TOMBOL INLINE
# =================================================

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

    if data == "single_uk":
        context.user_data["mode"] = "single"
        context.user_data["template"] = TEMPLATE_UK
        query.edit_message_text("Kirim 1 nama untuk kartu 🇬🇧 UK:")
        return

    if data == "single_india":
        context.user_data["mode"] = "single"
        context.user_data["template"] = TEMPLATE_INDIA
        query.edit_message_text("Kirim 1 nama untuk kartu 🇮🇳 India:")
        return

    if data == "batch_uk":
        context.user_data["mode"] = "batch"
        context.user_data["template"] = TEMPLATE_UK
        query.edit_message_text("Kirim daftar nama (max 10), 1 per baris:")
        return

    if data == "batch_india":
        context.user_data["mode"] = "batch"
        context.user_data["template"] = TEMPLATE_INDIA
        query.edit_message_text("Kirim daftar nama (max 10), 1 per baris:")
        return


# =====================================
# HANDLE INPUT USER
# =====================================

def handle_text(update: Update, context: CallbackContext):
    mode = context.user_data.get("mode")
    msg = update.message.text

    if mode == "single":
        update.message.reply_text("⏳ Membuat kartu...")
        template = context.user_data["template"]

        img = generate_card(msg, template)

        update.message.reply_document(
            document=img,
            caption=f"🎉 Kartu selesai dibuat untuk *{msg.upper()}*",
            parse_mode="Markdown"
        )

        context.user_data["mode"] = None
        return

    if mode == "batch":
        names = [n.strip() for n in msg.splitlines() if n.strip()]
        names = names[:10]
        template = context.user_data["template"]

        update.message.reply_text(f"⏳ Membuat {len(names)} kartu...")

        for name in names:
            img = generate_card(name, template)
            update.message.reply_document(
                document=img,
                caption=f"✨ {name.upper()}",
                parse_mode="Markdown"
            )

        update.message.reply_text("🎉 Batch selesai!")
        context.user_data["mode"] = None
        return

    update.message.reply_text("Gunakan /card atau /batch untuk mulai.")


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

    print("🤖 Bot ID Card berjalan di CMD gratis...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()

