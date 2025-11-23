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

# =========================
# PREMIUM & LIMIT HARIAN
# =========================

DAILY_LIMIT_FREE = 1  # free user: 1 kartu / hari

# isi sendiri ID user premium, contoh: {123456789, 987654321}
PREMIUM_USER_IDS = set()

# penyimpan pemakaian harian (di RAM saja)
# key: (user_id, 'YYYY-MM-DD') -> jumlah kartu yang sudah dibuat
user_daily_usage = {}


def get_today_str() -> str:
    tz = timezone(timedelta(hours=7))  # WIB
    return datetime.now(tz).strftime("%Y-%m-%d")


def is_premium(user_id: int) -> bool:
    return user_id in PREMIUM_USER_IDS


# =========================
# TOOLING FONT & FILENAME
# =========================

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


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    """Hitung lebar/tinggi teks yang kompatibel dengan Pillow baru."""
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    return w, h


# =========================
# POSISI TEKS DI TEMPLATE
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
    """Generate kartu Indonesia (Universitas Islam Indonesia style). FULL KAPITAL, biru gelap, center."""
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
# TELEGRAM BOT LOGIC
# =========================

MAIN_MENU, CHOOSING_TEMPLATE, INPUT_NAMES = range(3)


def build_template_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇬🇧 UK", callback_data="TPL_UK"),
                InlineKeyboardButton("🇮🇳 India", callback_data="TPL_IN"),
            ],
            [
                InlineKeyboardButton("🇧🇩 Bangladesh", callback_data="TPL_BD"),
                InlineKeyboardButton("🇮🇩 Indonesia", callback_data="TPL_ID"),
            ],
        ]
    )


def start(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = user.id
    name = user.first_name or user.username or "User"

    tz = timezone(timedelta(hours=7))  # WIB
    now = datetime.now(tz)
    time_str = now.strftime("%d %b %Y • %H:%M WIB")

    today_key = (uid, get_today_str())
    used = user_daily_usage.get(today_key, 0)

    if is_premium(uid):
        status_line = "👑 *Status:* Premium user"
        limit_lines = (
            "🧾 *Batas harian:* Unlimited\n"
            "🚀 Bebas kirim sampai 10 baris (1 baris 1 nama)."
        )
    else:
        remaining = max(DAILY_LIMIT_FREE - used, 0)
        status_line = "🆓 *Status:* Free user"
        limit_lines = (
            f"📌 *Batas harian:* {DAILY_LIMIT_FREE} kartu per hari.\n"
            f"🎯 *Sisa jatah hari ini:* {remaining} kartu."
        )

    text = (
        f"👋 Halo, *{name.upper()}*!\n"
        f"🕒 {time_str}\n\n"
        "*VanzShop ID Card Bot* bakal bantu kamu bikin ID Card otomatis.\n\n"
        "✨ Cukup kirim *NAMA* aja:\n"
        "• 1 baris → 1 kartu\n"
        "• Bisa kirim sampai 10 baris (1 baris 1 nama, khusus premium).\n\n"
        f"{status_line}\n"
        f"{limit_lines}\n"
        "Upgrade ke premium → @VanzzSkyyID\n\n"
        "Sekarang pilih mode dulu:"
    )

    keyboard = [
        [
            InlineKeyboardButton("🎴 Generate Card", callback_data="GEN_CARD"),
            InlineKeyboardButton("📦 Batch Generator", callback_data="GEN_BATCH"),
        ],
        [
            InlineKeyboardButton("👑 Admin", url="https://t.me/VanzzSkyyID"),
            InlineKeyboardButton("🌐 Language", callback_data="LANG_MENU"),
        ],
    ]

    update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return MAIN_MENU


def card_cmd(update: Update, context: CallbackContext):
    # shortcut lama: langsung pilih template
    update.message.reply_text(
        "Pilih template kartu yang mau dibuat:",
        reply_markup=build_template_keyboard(),
    )
    return CHOOSING_TEMPLATE


# ========= MAIN MENU CALLBACKS =========

def gen_card_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    query.message.reply_text(
        "Pilih template kartu yang mau dibuat:",
        reply_markup=build_template_keyboard(),
    )

    return CHOOSING_TEMPLATE


def gen_batch_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.message.reply_text(
        "📦 Mode *Batch Generator* belum tersedia di versi ini.\n"
        "Untuk sekarang, pakai *Generate Card* dulu ya. 😊",
        parse_mode="Markdown",
    )
    return MAIN_MENU


def language_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    kb = [
        [
            InlineKeyboardButton("🇮🇩 Indonesia", callback_data="LANG_ID"),
            InlineKeyboardButton("🇬🇧 English", callback_data="LANG_EN"),
        ]
    ]
    query.message.reply_text(
        "Pilih bahasa / Choose language:",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return MAIN_MENU


def set_lang_id(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer("Bahasa diset ke Indonesia")
    context.user_data["lang"] = "id"
    query.message.reply_text("✅ Bahasa kamu sekarang: Indonesia.")
    return MAIN_MENU


def set_lang_en(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer("Language set to English")
    context.user_data["lang"] = "en"
    query.message.reply_text("✅ Your language is now: English. (UI still mainly Indonesian 😉)")
    return MAIN_MENU


# ========= TEMPLATE SELECTION =========

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


# ========= HANDLE NAMA =========

def handle_names(update: Update, context: CallbackContext):
    tpl = context.user_data.get("template", "UK")
    raw = update.message.text.strip()
    user = update.effective_user
    uid = user.id

    # cek limit harian
    premium = is_premium(uid)
    today_key = (uid, get_today_str())
    used = user_daily_usage.get(today_key, 0)

    if not premium:
        remaining = DAILY_LIMIT_FREE - used
        if remaining <= 0:
            update.message.reply_text(
                "❌ Jatah kartu *free* kamu untuk hari ini sudah habis.\n"
                "Upgrade ke premium biar bisa unlimited → @VanzzSkyyID",
                parse_mode="Markdown",
            )
            return ConversationHandler.END

    names = [line.strip() for line in raw.splitlines() if line.strip()]
    if not names:
        update.message.reply_text("❌ Input kosong, kirim lagi ya (1–10 baris).")
        return INPUT_NAMES

    if len(names) > 10:
        names = names[:10]
        update.message.reply_text("⚠ Maksimal 10 baris. Dipakai 10 baris pertama.")

    # apply limit free user
    if not premium:
        remaining = DAILY_LIMIT_FREE - used
        if len(names) > remaining:
            names = names[:remaining]
            update.message.reply_text(
                f"⚠ Free user cuma bisa {DAILY_LIMIT_FREE} kartu per hari.\n"
                f"Dipakai *{remaining}* nama pertama dulu ya.",
                parse_mode="Markdown",
            )

    # Info mode aktif
    if premium:
        update.message.reply_text("⚙️ Generate card *Premium user* diaktifkan.", parse_mode="Markdown")
    else:
        update.message.reply_text("⚙️ Generate card *Free user* diaktifkan.", parse_mode="Markdown")

    processed_count = 0

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

            processed_count += 1

        except Exception as e:
            update.message.reply_text(f"❌ Gagal generate untuk '{name}'. Error: {e}")
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    # update pemakaian harian untuk free user
    if not premium and processed_count > 0:
        user_daily_usage[today_key] = used + processed_count

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
    )

    dp.add_handler(conv)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
