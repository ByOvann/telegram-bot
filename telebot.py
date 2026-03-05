import os
import json
import gspread
import sib_api_v3_sdk
from datetime import datetime
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
TWILIO_WA = os.environ.get("TWILIO_WA")
TWILIO_TO = os.environ.get("TWILIO_TO")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds_json = os.environ.get("GOOGLE_CREDENTIALS")
creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_ID = "1q4w8NAg0M3aLZDTFV5znla3pwKVKJlAAwPwlA7mweDI"
ADMIN_ID = 8253266018

# States
ASK_EMAIL = 1
ASK_NAMA, ASK_PRODUK, ASK_KELUHAN, ASK_HP = 2, 3, 4, 5

# ── Google Sheet helpers ──────────────────────────────
def get_products():
    return client.open_by_key(SHEET_ID).sheet1.get_all_records()

def save_user(user_id):
    sheet = client.open_by_key(SHEET_ID).worksheet("users")
    existing = sheet.col_values(1)
    if str(user_id) not in existing:
        sheet.append_row([str(user_id)])

def get_all_users():
    sheet = client.open_by_key(SHEET_ID).worksheet("users")
    users = sheet.col_values(1)
    return [u for u in users if u != "user_id" and u != ""]
def kirim_wa(pesan):
    from twilio.rest import Client
    client_twilio = Client(TWILIO_SID, TWILIO_TOKEN)
    client_twilio.messages.create(
        from_=TWILIO_WA,
        body=pesan,
        to=TWILIO_TO
    )
def save_email(email, nama):
    sheet = client.open_by_key(SHEET_ID).worksheet("emails")
    existing = sheet.col_values(1)
    if email not in existing:
        sheet.append_row([email, nama, datetime.now().strftime("%Y-%m-%d %H:%M")])
        return True
    return False

def get_all_emails():
    sheet = client.open_by_key(SHEET_ID).worksheet("emails")
    return sheet.get_all_records()

def save_bantuan(nama, produk, keluhan, nomor_hp):
    sheet = client.open_by_key(SHEET_ID).worksheet("bantuan")
    sheet.append_row([
        nama, produk, keluhan, nomor_hp,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Pending"
    ])

# ── Brevo email sender ────────────────────────────────
def kirim_email(to_email, to_nama, subject, isi_html):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email, "name": to_nama}],
        sender={"email": "hiuraksasa1927@gmail.com", "name": "TulisanKita"},
        subject=subject,
        html_content=isi_html
    )
    api.send_transac_email(email)

# ── /start ────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    products = get_products()

    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(
            f"{p['nama_produk']} - Rp{int(p['harga']):,}",
            callback_data=f"produk_{p['nama_produk']}"
        )])
    keyboard.append([InlineKeyboardButton("🆘 Bantuan", callback_data="bantuan")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Halo! 👋 Selamat datang di TulisanKita!\nBerikut produk kami:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

# ── Produk button ─────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "bantuan":
        await query.message.reply_text(
            "Halo! 😊 Kami siap membantu.\n\nSilakan ketik *nama lengkap* kamu:",
            parse_mode='Markdown'
        )
        return ASK_NAMA

    products = get_products()
    for p in products:
        if query.data == f"produk_{p['nama_produk']}":
            await query.message.reply_text(
                f"📦 *{p['nama_produk']}*\n"
                f"💰 Harga: Rp{int(p['harga']):,}\n"
                f"📝 {p['deskripsi']}\n\n"
                f"🛒 Order di sini: {p['link']}",
                parse_mode='Markdown'
            )
            await query.message.reply_text(
                "Mau dapat info promo & produk terbaru?\n"
                "Kirim email kamu ya! 📧\n\n"
                "Ketik /skip kalau tidak mau."
            )
            return ASK_EMAIL

# ── Email conversation ────────────────────────────────
async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    nama = update.effective_user.first_name

    if "@" not in email or "." not in email:
        await update.message.reply_text("Format email tidak valid, coba lagi atau ketik /skip")
        return ASK_EMAIL

    baru = save_email(email, nama)
    if baru:
        kirim_email(
            email, nama,
            "Selamat datang! 🎉",
            f"""
            <h2>Halo {nama}! 👋</h2>
            <p>Terima kasih sudah bergabung!</p>
            <p>Kamu akan mendapat info produk & promo terbaru dari kami.</p>
            <p>Cek produk kami: <a href="https://lynk.id/novansetiadi03">Klik di sini</a></p>
            <br><p>Salam,<br>Tim TulisanKita</p>
            """
        )
        await update.message.reply_text("Terima kasih! 🎉 Cek inbox kamu ya! 📧")
    else:
        await update.message.reply_text("Email kamu sudah terdaftar sebelumnya! 😊")

    return ConversationHandler.END

async def skip_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Oke, tidak apa-apa! 😊")
    return ConversationHandler.END

# ── Bantuan conversation ──────────────────────────────
async def ask_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nama'] = update.message.text.strip()
    await update.message.reply_text("Produk apa yang kamu beli? 📦")
    return ASK_PRODUK

async def ask_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['produk'] = update.message.text.strip()
    await update.message.reply_text("Apa pertanyaan atau keluhanmu? 💬")
    return ASK_KELUHAN

async def ask_keluhan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['keluhan'] = update.message.text.strip()
    await update.message.reply_text("Nomor HP kamu berapa? 📱")
    return ASK_HP

async def ask_hp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nomor_hp'] = update.message.text.strip()

    nama = context.user_data['nama']
    produk = context.user_data['produk']
    keluhan = context.user_data['keluhan']
    nomor_hp = context.user_data['nomor_hp']

    save_bantuan(nama, produk, keluhan, nomor_hp)

    # Notif ke Telegram kamu
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🆘 *Permintaan Bantuan Baru!*\n\n"
             f"👤 Nama: {nama}\n"
             f"📦 Produk: {produk}\n"
             f"💬 Keluhan: {keluhan}\n"
             f"📱 HP: {nomor_hp}\n"
             f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        parse_mode='Markdown'
    )
    # Notif ke WhatsApp kamu
    kirim_wa(
        f"🆘 Permintaan Bantuan Baru!\n\n"
        f"👤 Nama: {nama}\n"
        f"📦 Produk: {produk}\n"
        f"💬 Keluhan: {keluhan}\n"
        f"📱 HP: {nomor_hp}\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    await update.message.reply_text(
        "Terima kasih! 🙏\n\n"
        "Permintaan bantuan kamu sudah kami terima.\n"
        "Tim kami akan segera menghubungi kamu! 😊"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Dibatalkan. Ketik /start untuk mulai lagi.")
    return ConversationHandler.END

# ── Auto reply ────────────────────────────────────────
async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    pesan = update.message.text.lower()
    if any(k in pesan for k in ["harga", "produk", "katalog", "beli", "order"]):
        await start(update, context)
    else:
        await update.message.reply_text("Halo! 😊 Ketik /start untuk lihat katalog & bantuan!")

# ── Broadcast & Email blast ───────────────────────────
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Kamu bukan admin!")
        return
    pesan = " ".join(context.args)
    if not pesan:
        await update.message.reply_text("Format: /broadcast pesan kamu")
        return
    users = get_all_users()
    berhasil = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=int(user_id), text=pesan)
            berhasil += 1
        except:
            pass
    await update.message.reply_text(f"Broadcast terkirim ke {berhasil} user! ✅")

async def email_blast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Kamu bukan admin!")
        return
    teks = " ".join(context.args)
    parts = teks.split("|")
    if len(parts) < 2:
        await update.message.reply_text("Format: /emailblast Judul | Isi pesan")
        return
    subject = parts[0].strip()
    isi = parts[1].strip()
    emails = get_all_emails()
    berhasil = 0
    for e in emails:
        try:
            kirim_email(
                e['email'], e['nama'], subject,
                f"<p>{isi}</p><br><a href='https://lynk.id/novansetiadi03'>Cek produk kami</a>"
            )
            berhasil += 1
        except:
            pass
    await update.message.reply_text(f"Email blast terkirim ke {berhasil} subscriber! ✅")

# ── App setup ─────────────────────────────────────────
conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", start),
        CallbackQueryHandler(button_handler)
    ],
    states={
        ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
        ASK_NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_nama)],
        ASK_PRODUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_produk)],
        ASK_KELUHAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_keluhan)],
        ASK_HP: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_hp)],
    },
    fallbacks=[
        CommandHandler("skip", skip_email),
        CommandHandler("cancel", cancel)
    ]
)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(conv_handler)
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("emailblast", email_blast))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

print("Bot aktif...")
app.run_polling()


