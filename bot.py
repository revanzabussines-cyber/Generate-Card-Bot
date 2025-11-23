import os
import re
from datetime import datetime, date

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

try:
    # Biar waktu pakai WIB
    from zoneinfo import ZoneInfo
    WIB = ZoneInfo("Asia/Jakarta")

    def now_wib():
        return datetime.now(WIB)
except Exception:
    def now_wib():
        return datetime.now()


# =========================
# CONFIG TOKEN & PREMIUM
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")

# user premium (unlimited generate)
PREMIUM_USERS = {7321522905}

# limit free
MAX_FREE_PER_DAY = 1
daily_usage = {}  # user_id -> {"date": "YYYY-MM-DD", "count": int}


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

# BANGLADESH -> Verdana
VERDANA_CANDIDATES = [
    os.path.join(BASE_DIR, "verdana.ttf"),
]

# warna biru gelap baru (#1E2365)
DARK_BLUE = (30, 35, 101)


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
INDIA_NAME_Y = 1000
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
# HELPER QUOTA & LANGUAGE
# =========================

def get_usage_record(user_id: int):
    today = date.today().isoformat()
    rec = daily_usage.get(user_id)
    if not rec or rec["date"] != today:
        rec = {"date": today, "count": 0}
        daily_usage[user_id] = rec
    return rec


def get_remaining_quota(user_id: int, is_premium: bool):
    if is_premium:
        return None
    rec = get_usage_record(user_id)
    return max(0, MAX_FREE_PER_DAY - rec["count"])


def get_lang(context: CallbackContext) -> str:
    return context.user_data.get("lang", "id")


def build_start_text(user, lang: str, is_premium: bool, remaining):
    name = user.first_name or "User"
    now_str = now_wib().strftime("%d-%m-%Y %H:%M")

    if lang == "en":
        status_line = "🔓 *Status:* Premium user" if is_premium else "🆓 *Status:* Free user"
        if is_premium:
            limit_lines = (
                "♾ *Daily limit:* Unlimited.\n"
                "✅ You can generate as many cards as you want today."
            )
        else:
            limit_lines = (
                f"📌 *Daily limit:* {MAX_FREE_PER_DAY} card per day.\n"
                f"🎯 *Remaining today:* {remaining} card."
            )

        text = (
            f"👋 Hello, *{name.upper()}*!\n"
            f"⏰ *Time:* {now_str}\n\n"
            "*VanzShop ID Card Bot* will help you generate ID Cards automatically.\n\n"
            "✨ Just send the *NAME*:\n"
            "• 1 line → 1 card\n"
            "• You can send up to 10 lines (1 line = 1 name, for premium users).\n\n"
            f"{status_line}\n{limit_lines}\n\n"
            "Now choose what you want to do:"
        )
    else:
        status_line = "🔓 *Status:* Premium user" if is_premium else "🆓 *Status:* Free user"
        if is_premium:
            limit_lines = (
                "♾ *Batas harian:* Unlimited.\n"
                "✅ Kamu bisa generate kartu sepuasnya hari ini."
            )
        else:
            limit_lines = (
                f"📌 *Batas harian:* {MAX_FREE_PER_DAY} kartu per hari.\n"
                f"🎯 *Sisa jatah hari ini:* {remaining} kartu."
            )

        text = (
            f"👋 Halo, *{name.upper()}*!\n"
            f"⏰ *Waktu sekarang:* {now_str}\n\n"
            "*VanzShop ID Card Bot* bakal bantu kamu bikin ID Card otomatis.\n\n"
            "✨ Cukup kirim *NAMA* aja:\n"
            "• 1 baris → 1 kartu\n"
            "• Bisa kirim sampai 10 baris (1 baris 1 nama, khusus premium).\n\n"
            f"{status_line}\n{limit_lines}\n\n"
            "Sekarang pilih yang mau kamu lakukan:"
        )

    return text


def build_action_keyboard(lang: str):
    if lang == "en":
        btn_generate = "📇 Generate card"
        btn_batch = "📦 Batch generator"
        btn_admin = "👑 Admin"
        btn_lang = "🌐 Language"
    else:
        btn_generate = "📇 Generate card"
        btn_batch = "📦 Generator batch"
        btn_admin = "👑 Admin"
        btn_lang = "🌐 Language"

    keyboard = [
        [
            InlineKeyboardButton(btn_generate, callback_data="ACT_SINGLE"),
            InlineKeyboardButton(btn_batch, callback_data="ACT_BATCH"),
        ],
        [
            InlineKeyboardButton(btn_admin, callback_data="BTN_ADMIN"),
            InlineKeyboardButton(btn_lang, callback_data="BTN_LANG"),
        ],
    ]
    return keyboard


def build_template_keyboard(lang: str):
    # label negara sama aja di dua bahasa
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
    return keyboard


# =========================
# HANDLER TELEGRAM
# =========================

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    lang = get_lang(context)
    is_premium = user.id in PREMIUM_USERS
    remaining = get_remaining_quota(user.id, is_premium)

    text = build_start_text(user, lang, is_premium, remaining)
    keyboard = build_action_keyboard(lang)

    update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    context.user_data["step"] = "choose_action"
    context.user_data["template"] = None
    context.user_data["mode"] = None


def action_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    user = query.from_user
    lang = get_lang(context)
    is_premium = user.id in PREMIUM_USERS

    # agar notifikasi loading di HP ilang
    query.answer()

    if data == "ACT_SINGLE" or data == "ACT_BATCH":
        # ACT_BATCH sekarang diperlakukan sama, bedanya cuma teks
        context.user_data["mode"] = "batch" if data == "ACT_BATCH" else "single"
        context.user_data["step"] = "choose_template"

        if lang == "en":
            mode_text = "single card" if data == "ACT_SINGLE" else "batch (multi-line) mode"
            text = (
                f"✅ *Generate {mode_text} activated.*\n\n"
                "Now choose the ID Card template you want to use:"
            )
        else:
            mode_text = "1 kartu" if data == "ACT_SINGLE" else "batch (banyak nama)"
            text = (
                f"✅ *Generate {mode_text} diaktifkan.*\n\n"
                "Sekarang pilih template ID Card yang mau dipakai:"
            )

        keyboard = build_template_keyboard(lang)
        query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data == "BTN_ADMIN":
        if lang == "en":
            text = (
                "👑 *Admin / Owner:*\n"
                "@VanzzSkyyID\n\n"
                "📢 *Info Channel:* VanzINFO"
            )
        else:
            text = (
                "👑 *Admin / Owner:*\n"
                "@VanzzSkyyID\n\n"
                "📢 *Channel Info:* VanzINFO"
            )
        query.message.reply_text(text, parse_mode="Markdown")

    elif data == "BTN_LANG":
        # ganti bahasa, tapi gak ganggu step proses (kecuali di menu awal)
        old_lang = lang
        new_lang = "en" if old_lang == "id" else "id"
        context.user_data["lang"] = new_lang
        is_premium = user.id in PREMIUM_USERS
        remaining = get_remaining_quota(user.id, is_premium)

        # kalau lagi di menu utama, rebuild teks + keyboard
        if context.user_data.get("step") == "choose_action":
            text = build_start_text(user, new_lang, is_premium, remaining)
            keyboard = build_action_keyboard(new_lang)
            query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            # lagi di tengah flow, cukup kasih notif
            if new_lang == "en":
                query.message.reply_text("🌐 Language switched to *English*.", parse_mode="Markdown")
            else:
                query.message.reply_text("🌐 Bahasa diganti ke *Indonesia*.", parse_mode="Markdown")


def template_chosen(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    lang = get_lang(context)

    query.answer()

    tpl_map = {
        "TPL_UK": "UK",
        "TPL_IN": "INDIA",
        "TPL_BD": "BD",
        "TPL_ID": "IDN",
    }

    tpl = tpl_map.get(data)
    if not tpl:
        query.message.reply_text("Template tidak dikenal.")
        return

    context.user_data["template"] = tpl
    context.user_data["step"] = "input_names"

    label = {
        "UK": "UK (LSE)",
        "INDIA": "India (University of Mumbai)",
        "BD": "Bangladesh (Uttara Town College)",
        "IDN": "Indonesia (Universitas Islam Indonesia)",
    }[tpl]

    if lang == "en":
        text = (
            f"✅ *Template {label} selected.*\n\n"
            "Now send the *name(s)* you want to put on the card.\n"
            "• 1–10 lines.\n"
            "• 1 line = 1 card."
        )
    else:
        text = (
            f"✅ *Template {label} dipilih.*\n\n"
            "Sekarang kirim *nama* yang mau dibuat kartunya.\n"
            "• 1–10 baris.\n"
            "• 1 baris = 1 kartu."
        )

    query.message.reply_text(text, parse_mode="Markdown")


def handle_names(update: Update, context: CallbackContext):
    user = update.effective_user
    lang = get_lang(context)
    tpl = context.user_data.get("template")
    step = context.user_data.get("step")

    # kalau bukan lagi fase input nama, cuekin aja / kasih info pendek
    if step != "input_names" or not tpl:
        return

    is_premium = user.id in PREMIUM_USERS
    rec = get_usage_record(user.id)
    remaining = get_remaining_quota(user.id, is_premium)

    raw = update.message.text.strip()
    names = [line.strip() for line in raw.splitlines() if line.strip()]

    if not names:
        if lang == "en":
            update.message.reply_text("❌ Input is empty, please send 1–10 names.")
        else:
            update.message.reply_text("❌ Input kosong, kirim 1–10 nama ya.")
        return

    if len(names) > 10:
        names = names[:10]
        if lang == "en":
            update.message.reply_text("⚠ Maximum 10 lines. Using the first 10 lines.")
        else:
            update.message.reply_text("⚠ Maksimal 10 baris. Dipakai 10 baris pertama.")

    # cek quota free
    if not is_premium:
        if remaining <= 0:
            if lang == "en":
                update.message.reply_text(
                    "❌ Your free quota for today is already used.\n"
                    "Upgrade to premium → @VanzzSkyyID 😉"
                )
            else:
                update.message.reply_text(
                    "❌ Jatah free kamu hari ini sudah habis.\n"
                    "Upgrade ke premium → @VanzzSkyyID 😉"
                )
            return

        if len(names) > remaining:
            names = names[:remaining]
            if lang == "en":
                update.message.reply_text(
                    f"⚠ Free user can only generate {remaining} more card(s) today.\n"
                    f"Using the first {remaining} line(s)."
                )
            else:
                update.message.reply_text(
                    f"⚠ Free user cuma bisa generate {remaining} kartu lagi hari ini.\n"
                    f"Dipakai {remaining} baris pertama."
                )

    # info mode saat generate
    if is_premium:
        if lang == "en":
            status_text = "🔓 *Premium mode active.* Generating your card(s)..."
        else:
            status_text = "🔓 *Premium user diaktifkan.* Sedang generate kartu..."
    else:
        if lang == "en":
            status_text = (
                "🆓 *Free mode active.*\n"
                f"Daily limit: {MAX_FREE_PER_DAY} card.\n"
                f"Remaining before this request: {remaining} card."
            )
        else:
            status_text = (
                "🆓 *Generate card free user diaktifkan.*\n"
                f"Batas harian: {MAX_FREE_PER_DAY} kartu.\n"
                f"Sisa sebelum request ini: {remaining} kartu."
            )

    update.message.reply_text(status_text, parse_mode="Markdown")

    generated = 0

    for name in names:
        raw_name = name.strip()
        upper_name = raw_name.upper()
        title_name = raw_name.title()

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

    if not is_premium and generated > 0:
        rec["count"] += generated

    # setelah selesai, balik ke menu awal
    context.user_data["step"] = "choose_action"
    context.user_data["template"] = None
    context.user_data["mode"] = None

    # opsi: kirim menu lagi biar user enak
    is_premium = user.id in PREMIUM_USERS
    remaining = get_remaining_quota(user.id, is_premium)
    text = build_start_text(user, lang, is_premium, remaining)
    keyboard = build_action_keyboard(lang)
    update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable belum di-set di Railway!")

    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # command
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("card", start))  # alias

    # inline buttons
    dp.add_handler(CallbackQueryHandler(action_buttons, pattern="^(ACT_|BTN_)"))
    dp.add_handler(CallbackQueryHandler(template_chosen, pattern="^TPL_"))

    # text input (nama)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_names))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()

