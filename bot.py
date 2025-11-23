import os
import re
from datetime import datetime, timezone, timedelta

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
# PREMIUM CONFIG
# =========================
# isi sendiri user_id premium, misal: {123456789}
PREMIUM_USERS = set()

# limit free: 1 kartu / hari (1 nama)
daily_usage = {}  # key: (user_id, date_str) -> int


def is_premium(user_id: int) -> bool:
    return user_id in PREMIUM_USERS


# =========================
# PATH DASAR & FILE TEMPLATE / FONT
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_UK = os.path.join(BASE_DIR, "template_uk.png")
TEMPLATE_IN = os.path.join(BASE_DIR, "template_india.png")
TEMPLATE_BD = os.path.join(BASE_DIR, "template_bd.png")
TEMPLATE_ID = os.path.join(BASE_DIR, "template_id.png")  # Indonesia

# UK -> Arial Bold
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

# BANGLADESH -> Verdana
VERDANA_CANDIDATES = [
    os.path.join(BASE_DIR, "verdana.ttf"),
]

# warna biru gelap (mirip teks NAME/ID/BIRTH UK)
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

# INDIA (center horizontal, Y bisa diatur)
INDIA_NAME_Y = 950
INDIA_NAME_SIZE = 46

# INDONESIA (center horizontal juga)
ID_NAME_Y = 540    # atur tinggi nama di kartu Indonesia
ID_NAME_SIZE = 50

# BD
BD_HEADER_POS = (260, 230)
BD_HEADER_SIZE = 32


# =========================
# FUNGSI GENERATE CARD
# =========================

def generate_uk_card(name: str, out_path: str) -> str:
    """Generate kartu UK. Nama: FULL KAPITAL, warna biru gelap, Arial Bold."""
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


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    """Hitung lebar/tinggi teks yang kompatibel dengan Pillow baru."""
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    return w, h


def generate_india_card(name: str, out_path: str) -> str:
    """Generate kartu India. Nama: FULL KAPITAL, warna HITAM, Arial.ttf, auto center."""
    img = Image.open(TEMPLATE_IN).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(ARIAL_REGULAR_CANDIDATES, INDIA_NAME_SIZE)
    text = name.upper()

    # center horizontal pakai textbbox
    text_w, text_h = _measure_text(draw, text, font)
    x = (img.width - text_w) // 2
    y = INDIA_NAME_Y

    for ox, oy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        draw.text((x + ox, y + oy), text, font=font, fill="black")

    img.save(out_path, format="PNG")
    return out_path


def generate_indonesia_card(name: str, out_path: str) -> str:
    """Generate kartu Indonesia. FULL KAPITAL, biru gelap, center."""
    img = Image.open(TEMPLATE_ID).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _load_first_available(ARIAL_ID_CANDIDATES, ID_NAME_SIZE)
    text = name.upper()

    text_w, text_h = _measure_text(draw, text, font)
    x = (img.width - text_w) // 2
    y = ID_NAME_Y

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
# STATE CONVERSATION
# =========================

MAIN_MENU, CHOOSING_TEMPLATE, INPUT_NAMES = range(3)

LANG_ID = "id"
LANG_EN = "en"


# =========================
# HELPER BAHASA & WELCOME
# =========================

def get_lang(context: CallbackContext) -> str:
    return context.user_data.get("lang", LANG_ID)


def set_lang(context: CallbackContext, lang: str):
    context.user_data["lang"] = lang


def get_now_wib() -> str:
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz).strftime("%d/%m/%Y • %H:%M WIB")


def send_welcome_message(update: Update, context: CallbackContext, from_callback=False):
    user = update.effective_user
    lang = get_lang(context)
    username = user.first_name or "User"
    time_str = get_now_wib()

    premium = is_premium(user.id)
    status_text = "Premium user" if premium else "Free user"
    daily_limit = "Unlimited" if premium else "1 kartu per hari"
    sisa = "∞ kartu" if premium else "1 kartu"

    if lang == LANG_EN:
        text = (
            f"👋 Hello, *{username.upper()}!*\n"
            f"🕒 _{time_str}_\n\n"
            "*VanzShop ID Card Bot* will help you create ID Cards automatically.\n\n"
            "✨ Just send *NAME*:\n"
            "• 1 line → 1 card\n"
            "• Up to 10 lines (1 line 1 name, premium only).\n\n"
            f"🆓 *Status:* {status_text}\n"
            f"📌 *Daily limit:* {daily_limit}\n"
            f"🎯 *Remaining today:* {sisa}\n"
            "Upgrade to premium → @VanzzSkyyID\n\n"
            "Now choose menu:"
        )
        gen_btn = "🎴 Generate Card"
        batch_btn = "📦 Batch Generator"
        language_btn = "🌐 Language"
    else:
        text = (
            f"👋 Halo, *{username.upper()}!*\n"
            f"🕒 _{time_str}_\n\n"
            "*VanzShop ID Card Bot* bakal bantu kamu bikin ID Card otomatis.\n\n"
            "✨ Cukup kirim *NAMA* aja:\n"
            "• 1 baris → 1 kartu\n"
            "• Bisa kirim sampai 10 baris (1 baris 1 nama, khusus premium).\n\n"
            f"🆓 *Status:* {status_text}\n"
            f"📌 *Batas harian:* {daily_limit}\n"
            f"🎯 *Sisa jatah hari ini:* {sisa}\n"
            "Upgrade ke premium → @VanzzSkyyID\n\n"
            "Sekarang pilih menu dulu:"
        )
        gen_btn = "🎴 Generate Card"
        batch_btn = "📦 Batch Generator"
        language_btn = "🌐 Language"

    keyboard = [
        [
            InlineKeyboardButton(gen_btn, callback_data="GEN_CARD"),
        ],
        [
            InlineKeyboardButton(batch_btn, callback_data="GEN_BATCH"),
        ],
        [
            InlineKeyboardButton("👑 Admin", url="https://t.me/VanzzSkyyID"),
            InlineKeyboardButton(language_btn, callback_data="LANG_MENU"),
        ],
    ]

    if from_callback and update.callback_query:
        update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# =========================
# HANDLER /start
# =========================

def start(update: Update, context: CallbackContext):
    # default bahasa: Indonesia
    if "lang" not in context.user_data:
        set_lang(context, LANG_ID)

    send_welcome_message(update, context, from_callback=False)
    return MAIN_MENU


# =========================
# MENU BUTTON HANDLERS
# =========================

def gen_card_menu(update: Update, context: CallbackContext):
    """Dipanggil kalau klik 🎴 Generate Card."""
    query = update.callback_query
    query.answer()

    lang = get_lang(context)

    if lang == LANG_EN:
        text = "Choose card template:"
    else:
        text = "Pilih template kartu dulu:"

    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 UK", callback_data="TPL_UK"),
            InlineKeyboardButton("🇮🇳 India", callback_data="TPL_IN"),
            InlineKeyboardButton("🇧🇩 Bangladesh", callback_data="TPL_BD"),
        ],
        [
            InlineKeyboardButton("🇮🇩 Indonesia", callback_data="TPL_ID"),
        ],
    ]

    query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_TEMPLATE


def gen_batch_menu(update: Update, context: CallbackContext):
    """Klik 📦 Batch Generator."""
    query = update.callback_query
    query.answer()

    lang = get_lang(context)
    if lang == LANG_EN:
        text = (
            "📦 *Batch Generator*\n\n"
            "This feature is not available yet in this version.\n"
            "For now, use *Generate Card* menu."
        )
    else:
        text = (
            "📦 *Batch Generator*\n\n"
            "Fitur ini belum tersedia di versi ini.\n"
            "Untuk sementara pakai menu *Generate Card* dulu ya."
        )

    query.message.reply_text(text, parse_mode="Markdown")
    return MAIN_MENU


def language_menu(update: Update, context: CallbackContext):
    """Tombol 🌐 Language diklik."""
    query = update.callback_query
    query.answer()

    keyboard = [
        [
            InlineKeyboardButton("🇮🇩 Bahasa Indonesia", callback_data="LANG_ID"),
            InlineKeyboardButton("🇬🇧 English", callback_data="LANG_EN"),
        ]
    ]

    query.message.reply_text(
        "Pilih bahasa / Choose language:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return MAIN_MENU


def set_lang_id(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    set_lang(context, LANG_ID)
    send_welcome_message(update, context, from_callback=True)
    return MAIN_MENU


def set_lang_en(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    set_lang(context, LANG_EN)
    send_welcome_message(update, context, from_callback=True)
    return MAIN_MENU


# =========================
# TEMPLATE DIPILIH
# =========================

def card_cmd(update: Update, context: CallbackContext):
    """/card langsung ke pilih template (skip menu)."""
    lang = get_lang(context)
    if lang == LANG_EN:
        text = "Choose card template:"
    else:
        text = "Pilih template kartu yang mau dibuat:"

    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 UK", callback_data="TPL_UK"),
            InlineKeyboardButton("🇮🇳 India", callback_data="TPL_IN"),
            InlineKeyboardButton("🇧🇩 Bangladesh", callback_data="TPL_BD"),
        ],
        [
            InlineKeyboardButton("🇮🇩 Indonesia", callback_data="TPL_ID"),
        ],
    ]
    update.message.reply_text(
        text,
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
        "TPL_ID": "IDN",   # Indonesia
    }

    tpl = tpl_map.get(data)
    if not tpl:
        query.message.reply_text("Template tidak dikenal.")
        return ConversationHandler.END

    context.user_data["template"] = tpl

    label = {
        "UK": "UK",
        "INDIA": "India",
        "BD": "Bangladesh",
        "IDN": "Indonesia",
    }[tpl]

    query.message.reply_text(
        f"✅ Template *{label}* dipilih.\n\n"
        "Sekarang kirim *nama* yang mau dibuat kartunya (1–10 baris, 1 baris 1 nama).",
        parse_mode="Markdown",
    )

    return INPUT_NAMES


# =========================
# HANDLE INPUT NAMA
# =========================

def handle_names(update: Update, context: CallbackContext):
    tpl = context.user_data.get("template", "UK")
    raw = update.message.text.strip()
    user = update.effective_user
    lang = get_lang(context)

    # limit harian
    today = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    key = (user.id, today)
    used = daily_usage.get(key, 0)
    premium = is_premium(user.id)

    if not premium and used >= 1:
        if lang == LANG_EN:
            update.message.reply_text(
                "❌ Your free quota for today is already used.\n"
                "Come back tomorrow or upgrade to premium → @VanzzSkyyID"
            )
        else:
            update.message.reply_text(
                "❌ Jatah gratis kamu hari ini sudah dipakai.\n"
                "Coba lagi besok atau upgrade ke premium → @VanzzSkyyID"
            )
        return ConversationHandler.END

    names = [line.strip() for line in raw.splitlines() if line.strip()]
    if not names:
        update.message.reply_text("❌ Input kosong, kirim lagi ya (1–10 baris).")
        return INPUT_NAMES

    if not premium and len(names) > 1:
        # free user: pakai 1 nama pertama saja
        names = names[:1]
        update.message.reply_text(
            "⚠ Free user cuma boleh 1 nama per hari.\n"
            "Dipakai nama pertama saja."
        )

    if len(names) > 10:
        names = names[:10]
        update.message.reply_text("⚠ Maksimal 10 baris. Dipakai 10 baris pertama.")

    # info status generate
    status_text = "Premium user" if premium else "Free user"
    if lang == LANG_EN:
        update.message.reply_text(
            f"⚙️ Generate card *{status_text}* activated...",
            parse_mode="Markdown",
        )
    else:
        update.message.reply_text(
            f"⚙️ Generate card *{status_text}* diaktifkan...",
            parse_mode="Markdown",
        )

    generated = 0

    for name in names:
        raw_name = name.strip()
        upper_name = raw_name.upper()
        title_name = raw_name.title()

        # dasar nama file:
        # UK / INDIA / INDONESIA -> pakai nama kapital
        # BD -> title case
        if tpl in ("UK", "INDIA", "IDN"):
            safe_base = make_safe_filename(upper_name)
        else:
            safe_base = make_safe_filename(title_name)

        out_path = f"{safe_base}.png"

        try:
            # ====== Generate kartu ======
            if tpl == "UK":
                generate_uk_card(upper_name, out_path)

                caption = f"🇬🇧 UK • {upper_name}"
                info_text = (
                    "📘 *Kartu UK (LSE)*\n\n"
                    f"👤 *Nama Lengkap :* {upper_name}\n"
                    "🏫 *Universitas :* The London School of Economics and Political Science (LSE)\n\n"
                    "🪪 *ID (di kartu) :* 1201-0732\n"
                    "🎂 *Tanggal Lahir (di kartu) :* 10/10/2005\n"
                    "📍 *Alamat (di kartu) :* London, UK\n"
                    "🌐 *Domain :* lse.ac.uk\n"
                )

            elif tpl == "INDIA":
                generate_india_card(upper_name, out_path)

                caption = f"🇮🇳 India • {upper_name}"
                info_text = (
                    "📗 *Kartu India (University of Mumbai)*\n\n"
                    f"👤 *Nama Lengkap :* {upper_name}\n"
                    "🏫 *Universitas :* University of Mumbai\n\n"
                    "🎂 *D.O.B (di kartu) :* 15/01/2000\n"
                    "📆 *Validity (di kartu) :* 11/25 - 11/26\n"
                    "🌐 *Domain :* mu.ac.in\n"
                )

            elif tpl == "IDN":
                generate_indonesia_card(upper_name, out_path)

                caption = f"🇮🇩 Indonesia • {upper_name}"
                info_text = (
                    "📙 *Kartu Indonesia (Universitas Islam Indonesia)*\n\n"
                    f"👤 *Nama Lengkap :* {upper_name}\n"
                    "🏫 *Universitas :* Universitas Islam Indonesia\n\n"
                    "🎓 *Program / Class (di kartu) :* Informatika\n"
                    "📞 *Phone (di kartu) :* +6281251575890\n"
                    "🎂 *TTL (di kartu) :* 01 Januari 2005\n"
                    "🌐 *Domain :* pnj.ac.id\n"
                )

            else:  # BD
                generate_bangladesh_card(title_name, out_path)

                caption = f"🇧🇩 Bangladesh • {title_name}"
                info_text = (
                    "📕 *Bangladesh Fee Receipt (Uttara Town College)*\n\n"
                    f"👤 *Nama (header) :* {title_name}\n"
                    "🏫 *College :* Uttara Town College\n"
                    "📆 *Registration Date (di kartu) :* 14.10.25\n"
                    "💰 *Amount (di kartu) :* 18500 BDT\n"
                )

            # ====== Kirim file PNG sebagai document ======
            with open(out_path, "rb") as f:
                doc = InputFile(f, filename=os.path.basename(out_path))
                update.message.reply_document(doc, caption=caption)

            # ====== Kirim format teks biodata ======
            update.message.reply_text(info_text, parse_mode="Markdown")
            generated += 1

        except Exception as e:
            update.message.reply_text(f"❌ Gagal generate untuk '{name}'. Error: {e}")
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    # update usage free
    if not premium and generated > 0:
        daily_usage[key] = used + 1

    context.user_data.clear()
    return ConversationHandler.END


# =========================
# CANCEL
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
            MAIN_MENU: [
                CallbackQueryHandler(gen_card_menu, pattern="^GEN_CARD$"),
                CallbackQueryHandler(gen_batch_menu, pattern="^GEN_BATCH$"),
                CallbackQueryHandler(language_menu, pattern="^LANG_MENU$"),
                CallbackQueryHandler(set_lang_id, pattern="^LANG_ID$"),
                CallbackQueryHandler(set_lang_en, pattern="^LANG_EN$"),
            ],
            CHOOSING_TEMPLATE: [
                CallbackQueryHandler(template_chosen, pattern="^TPL_"),
            ],
            INPUT_NAMES: [
                MessageHandler(Filters.text & ~Filters.command, handle_names),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True,   # hilangin warning CallbackQuery
    )

    dp.add_handler(conv)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
