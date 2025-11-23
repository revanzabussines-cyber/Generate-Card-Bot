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
# PREMIUM & LIMIT FREE
# =========================

# isi sendiri user id premium, contoh: {123456789}
PREMIUM_USERS = set()

# limit free user: 1 kartu / hari (1 nama)
DAILY_FREE_LIMIT = 1

# (user_id, date_str) -> jumlah kartu yang sudah dipakai
daily_usage = {}

# user_id -> "id" / "en"
user_lang = {}

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
# HELPER UMUM
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


def is_premium(user_id: int) -> bool:
    return user_id in PREMIUM_USERS


def get_today_str() -> str:
    tz = timezone(timedelta(hours=7))  # WIB
    return datetime.now(tz).strftime("%Y-%m-%d")


def get_now_wib_str() -> str:
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz).strftime("%d %b %Y • %H:%M WIB")


def get_lang(user_id: int) -> str:
    return user_lang.get(user_id, "id")  # default Indonesia


def set_lang(user_id: int, lang: str):
    user_lang[user_id] = lang


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

    # center horizontal
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
# UI BUILDER
# =========================

def build_main_keyboard(lang: str) -> InlineKeyboardMarkup:
    if lang == "en":
        gen_label = "🎴 Generate Card"
        batch_label = "📦 Batch Generator"
        lang_label = "🌐 Language"
    else:
        gen_label = "🎴 Generate Card"
        batch_label = "📦 Batch Generator"
        lang_label = "🌐 Language"

    keyboard = [
        [InlineKeyboardButton(gen_label, callback_data="GEN_CARD")],
        [InlineKeyboardButton(batch_label, callback_data="GEN_BATCH")],
        [
            InlineKeyboardButton("👑 Admin", url="https://t.me/VanzzSkyyID"),
            InlineKeyboardButton(lang_label, callback_data="LANG_MENU"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_template_keyboard() -> InlineKeyboardMarkup:
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
    return InlineKeyboardMarkup(keyboard)


# =========================
# HANDLERS
# =========================

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = user.id
    lang = get_lang(uid)
    name = user.first_name or user.username or "User"

    today = get_today_str()
    used = daily_usage.get((uid, today), 0)
    premium = is_premium(uid)

    if premium:
        status_line = "👑 *Status:* Premium user"
        limit_line = "🧾 *Batas harian:* Unlimited\n🎯 *Sisa hari ini:* ∞ kartu"
    else:
        remaining = max(DAILY_FREE_LIMIT - used, 0)
        status_line = "🆓 *Status:* Free user"
        limit_line = (
            f"🧾 *Batas harian:* {DAILY_FREE_LIMIT} kartu\n"
            f"🎯 *Sisa hari ini:* {remaining} kartu"
        )

    time_str = get_now_wib_str()

    if lang == "en":
        text = (
            f"👋 Hello, *{name.upper()}*!\n"
            f"🕒 {time_str}\n\n"
            "*VanzShop ID Card Bot* helps you generate student ID cards automatically.\n\n"
            "✨ Just send *NAME*:\n"
            "• 1 line → 1 card\n"
            "• Up to 10 lines (1 line 1 name, premium only)\n\n"
            f"{status_line}\n{limit_line}\n\n"
            "Upgrade to premium → @VanzzSkyyID\n\n"
            "Choose menu below:"
        )
    else:
        text = (
            f"👋 Halo, *{name.upper()}*!\n"
            f"🕒 {time_str}\n\n"
            "*VanzShop ID Card Bot* bakal bantu kamu bikin ID Card otomatis.\n\n"
            "✨ Cukup kirim *NAMA* aja:\n"
            "• 1 baris → 1 kartu\n"
            "• Bisa kirim sampai 10 baris (1 baris 1 nama, khusus premium)\n\n"
            f"{status_line}\n{limit_line}\n\n"
            "Upgrade ke premium → @VanzzSkyyID\n\n"
            "Sekarang pilih menu di bawah:"
        )

    update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=build_main_keyboard(lang),
    )


def card_cmd(update: Update, context: CallbackContext):
    """Command /card → langsung pilih template."""
    uid = update.effective_user.id
    lang = get_lang(uid)

    if lang == "en":
        text = "Choose card template:"
    else:
        text = "Pilih template kartu yang mau dibuat:"

    update.message.reply_text(
        text,
        reply_markup=build_template_keyboard(),
    )


# ====== Callback tombol menu utama ======

def gen_card_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    uid = query.from_user.id
    lang = get_lang(uid)

    if lang == "en":
        text = "Choose card template:"
    else:
        text = "Pilih template kartu yang mau dibuat:"

    query.message.reply_text(
        text,
        reply_markup=build_template_keyboard(),
    )


def gen_batch_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    uid = query.from_user.id
    lang = get_lang(uid)

    if lang == "en":
        text = (
            "📦 *Batch Generator*\n\n"
            "This feature is not available yet.\n"
            "For now, use *Generate Card*."
        )
    else:
        text = (
            "📦 *Batch Generator*\n\n"
            "Fitur ini belum tersedia.\n"
            "Untuk sementara pakai *Generate Card* dulu ya."
        )

    query.message.reply_text(text, parse_mode="Markdown")


def language_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    keyboard = [
        [
            InlineKeyboardButton("🇮🇩 Bahasa Indonesia", callback_data="SET_LANG_ID"),
            InlineKeyboardButton("🇬🇧 English", callback_data="SET_LANG_EN"),
        ]
    ]
    query.message.reply_text(
        "Pilih bahasa / Choose language:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def set_lang_id(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    set_lang(uid, "id")
    query.answer("Bahasa diganti ke Indonesia")
    # cuma info kecil, nggak ganggu proses card
    query.message.reply_text("✅ Bahasa interface: Indonesia.")


def set_lang_en(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    set_lang(uid, "en")
    query.answer("Language set to English")
    query.message.reply_text("✅ Interface language: English.")


# ====== Template dipilih ======

def template_chosen(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    uid = query.from_user.id
    lang = get_lang(uid)

    data = query.data  # TPL_UK / TPL_IN / TPL_BD / TPL_ID

    tpl_map = {
        "TPL_UK": "UK",
        "TPL_IN": "INDIA",
        "TPL_BD": "BD",
        "TPL_ID": "IDN",
    }

    label_map = {
        "UK": "UK",
        "INDIA": "India",
        "BD": "Bangladesh",
        "IDN": "Indonesia",
    }

    tpl = tpl_map.get(data)
    if not tpl:
        query.message.reply_text("Template tidak dikenal.")
        return

    context.user_data["template"] = tpl

    label = label_map[tpl]

    if lang == "en":
        text = (
            f"✅ Template *{label}* selected.\n\n"
            "Now send *NAMES* (1–10 lines, 1 line 1 name)."
        )
    else:
        text = (
            f"✅ Template *{label}* dipilih.\n\n"
            "Sekarang kirim *nama* (1–10 baris, 1 baris 1 nama)."
        )

    query.message.reply_text(text, parse_mode="Markdown")


# ====== Handle nama (text) ======

def handle_names(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = user.id
    lang = get_lang(uid)

    tpl = context.user_data.get("template")
    if not tpl:
        # kalau user kirim text tapi belum pilih template
        if lang == "en":
            update.message.reply_text("Please choose template first using /card or *Generate Card* button.")
        else:
            update.message.reply_text("Silakan pilih template dulu lewat /card atau tombol *Generate Card*.")
        return

    raw = update.message.text.strip()
    if not raw:
        update.message.reply_text("❌ Input kosong, kirim lagi ya.")
        return

    names = [line.strip() for line in raw.splitlines() if line.strip()]
    if not names:
        update.message.reply_text("❌ Input kosong, kirim lagi ya.")
        return

    # batas 10 baris
    if len(names) > 10:
        names = names[:10]
        update.message.reply_text("⚠ Maksimal 10 baris. Dipakai 10 baris pertama.")

    premium = is_premium(uid)
    today = get_today_str()
    used = daily_usage.get((uid, today), 0)

    # limit free
    if not premium and used >= DAILY_FREE_LIMIT:
        if lang == "en":
            update.message.reply_text(
                "❌ Your free quota for today is already used.\n"
                "Try again tomorrow or upgrade to premium → @VanzzSkyyID"
            )
        else:
            update.message.reply_text(
                "❌ Jatah gratis kamu hari ini sudah dipakai.\n"
                "Coba lagi besok atau upgrade ke premium → @VanzzSkyyID"
            )
        return

    # free user cuma 1 kartu
    if not premium and len(names) > 1:
        names = names[:1]
        if lang == "en":
            update.message.reply_text(
                "⚠ As a *Free user*, you can only generate 1 card per day.\n"
                "Using the first name only.",
                parse_mode="Markdown",
            )
        else:
            update.message.reply_text(
                "⚠ Sebagai *Free user*, kamu cuma bisa generate 1 kartu per hari.\n"
                "Dipakai nama pertama saja.",
                parse_mode="Markdown",
            )

    # info mode aktif
    mode_text = "Premium user" if premium else "Free user"
    if lang == "en":
        update.message.reply_text(
            f"⚙️ Generate card *{mode_text}* activated...",
            parse_mode="Markdown",
        )
    else:
        update.message.reply_text(
            f"⚙️ Generate card *{mode_text}* diaktifkan...",
            parse_mode="Markdown",
        )

    generated = 0

    for name in names:
        raw_name = name.strip()
        upper_name = raw_name.upper()
        title_name = raw_name.title()

        # nama file:
        # UK / INDIA / INDONESIA -> pakai nama kapital
        # BD -> title case
        if tpl in ("UK", "INDIA", "IDN"):
            safe_base = make_safe_filename(upper_name)
        else:
            safe_base = make_safe_filename(title_name)

        out_path = f"{safe_base}.png"

        try:
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

            with open(out_path, "rb") as f:
                doc = InputFile(f, filename=os.path.basename(out_path))
                update.message.reply_document(doc, caption=caption)

            update.message.reply_text(info_text, parse_mode="Markdown")
            generated += 1

        except Exception as e:
            update.message.reply_text(f"❌ Gagal generate untuk '{name}'. Error: {e}")
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    # update limit free
    if not premium and generated > 0:
        daily_usage[(uid, today)] = used + 1

    # selesai 1 kali use → hapus template biar nggak ke-capture terus
    context.user_data.pop("template", None)


def cancel(update: Update, context: CallbackContext):
    context.user_data.clear()
    update.message.reply_text("❌ Proses dibatalkan.")


# =========================
# MAIN
# =========================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable belum di-set di Railway!")

    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # command
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("card", card_cmd))
    dp.add_handler(CommandHandler("cancel", cancel))

    # buttons
    dp.add_handler(CallbackQueryHandler(gen_card_button, pattern="^GEN_CARD$"))
    dp.add_handler(CallbackQueryHandler(gen_batch_button, pattern="^GEN_BATCH$"))
    dp.add_handler(CallbackQueryHandler(language_menu, pattern="^LANG_MENU$"))
    dp.add_handler(CallbackQueryHandler(set_lang_id, pattern="^SET_LANG_ID$"))
    dp.add_handler(CallbackQueryHandler(set_lang_en, pattern="^SET_LANG_EN$"))
    dp.add_handler(CallbackQueryHandler(template_chosen, pattern="^TPL_"))

    # text (nama)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_names))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
