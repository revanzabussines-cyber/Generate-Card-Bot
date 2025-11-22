import os
from uuid import uuid4

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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

# Ambil token dari environment (Railway variable: BOT_TOKEN)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Import generator
from generate_id_cards import (
    generate_uk_card,
    generate_india_card,
    generate_bangladesh_card,
)

# =========================
# STATE
# =========================
CHOOSING_TEMPLATE, INPUT_NAMES = range(2)

# =========================
# /start
# =========================

def start(update: Update, context: CallbackContext):
    text = (
        "👋 Selamat datang di *VanzShop ID Card Bot!* \n\n"
        "✨ Model baru: cukup kirim *NAMA* aja.\n"
        "• 1 nama → 1 kartu\n"
        "• Banyak nama (maks 10) → 1 baris = 1 kartu\n\n"
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


# =========================
# /card (sama kayak /start)
# =========================

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


# =========================
# Template dipilih (inline button)
# =========================

def template_chosen(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    tpl_map = {
        "TPL_UK": "UK",
        "TPL_IN": "INDIA",
        "TPL_BD": "BD",
    }

    data = query.data
    tpl = tpl_map.get(data)
    if not tpl:
        query.message.reply_text("Template tidak dikenal.")
        return ConversationHandler.END

    context.user_data["template"] = tpl

    query.message.reply_text(
        "✅ Template *{}* dipilih.\n\n"
        "Sekarang kirim nama yang mau dibuat kartunya.\n"
        "• Bisa 1 nama saja\n"
        "• Bisa banyak nama (maks 10), *1 baris 1 nama*\n\n"
        "Contoh:\n"
        "`Revanza Axcel`\n"
        "`Budi Pratama`\n"
        "`Siti Aisyah`".format(tpl),
        parse_mode="Markdown",
    )

    return INPUT_NAMES


# =========================
# Input nama (single / batch)
# =========================

def handle_names(update: Update, context: CallbackContext):
    tpl = context.user_data.get("template", "UK")
    raw = update.message.text.strip()

    # Split per baris
    names = [line.strip() for line in raw.splitlines() if line.strip()]
    if not names:
        update.message.reply_text("❌ Nama kosong, kirim lagi ya (1–10 nama).")
        return INPUT_NAMES

    if len(names) > 10:
        names = names[:10]
        update.message.reply_text("⚠ Maksimal 10 nama. Dipakai 10 nama pertama.")

    # Generate satu per satu
    for idx, name in enumerate(names, start=1):
        out_path = f"{tpl.lower()}_{idx}_{uuid4().hex}.png"

        try:
            if tpl == "UK":
                generate_uk_card(name, out_path)
            elif tpl == "INDIA":
                generate_india_card(name, out_path)
            else:
                generate_bangladesh_card(name, out_path)

            caption = f"{tpl} • {name}"
            with open(out_path, "rb") as img:
                update.message.reply_photo(img, caption=caption)

        except Exception as e:
            update.message.reply_text(f"❌ Gagal generate untuk '{name}'. Error: {e}")
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    context.user_data.clear()
    return ConversationHandler.END


# =========================
# /cancel
# =========================

def cancel(update: Update, context: CallbackContext):
    context.user_data.clear()
    update.message.reply_text("❌ Proses dibatalkan.")
    return ConversationHandler.END


# =========================
# MAIN
# =========================

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
