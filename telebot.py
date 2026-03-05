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
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds_json = os.environ.get("GOOGLE_CREDENTIALS")
creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_ID = "1q4w8NAg0M3aLZDTFV5znla3pwKVKJlAAwPwlA7mweDI"
ADMIN_ID = 8253266018
ASK_EMAIL = 1

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

# ── Brevo email sender ────────────────────────────────
def kirim_email(to_email, to_nama, subject, isi_html):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email, "name": to_nama}],
        sender={"email": "emailkamu@gmail.com", "name": "Toko Digital Kamu"},
        subject=subject,
        html_content=isi_html
    )
    api.send_transac_email(email)

# ── Telegram handlers ─────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    products = get_products()
    
    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(
            f"{p['nama_produk']} - Rp{int(p['harga']):,}",
            callback_data=p['nama_produk']
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Halo! 👋 Selamat datang!\nBerikut produk kami:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    products = get_products()
    for p in products:
        if p['nama_produk'] == query.data:
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

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    nama = update.effective_user.first_name
    
    if "@" not in email or "." not in email:
        await update.message.reply_text("Format email tidak valid, coba lagi atau ketik /skip")
        return ASK_EMAIL
    
    baru = save_email(email, nama)
    
    if baru:
        # Kirim welcome email
        kirim_email(
            email, nama,
            "Selamat datang! 🎉",
            f"""
            <h2>Halo {nama}! 👋</h2>
            <p>Terima kasih sudah bergabung!</p>
            <p>Kamu akan mendapat info produk & promo terbaru dari kami.</p>
            <p>Cek produk kami di sini: <a href="https://lynk.id/novansetiadi03">Klik di sini</a></p>
            <br>
            <p>Salam,<br>Tim Toko Digital</p>
            """
        )
        await update.message.reply_text(
            "Terima kasih! 🎉 Email kamu sudah terdaftar.\n"
            "Cek inbox kamu ya, ada pesan dari kami! 📧"
        )
    else:
        await update.message.reply_text("Email kamu sudah terdaftar sebelumnya! 😊")
    
    return ConversationHandler.END

async def skip_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Oke, tidak apa-apa! 😊")
    return ConversationHandler.END

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    pesan = update.message.text.lower()
    
    if any(k in pesan for k in ["harga", "produk", "katalog", "beli", "order"]):
        await start(update, context)
    else:
        await update.message.reply_text("Halo! 😊 Ketik /start untuk lihat katalog produk kami!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Kamu bukan admin!")
        return
    
    pesan = " ".join(context.args)
    if not pesan:
        await update.message.reply_text("Format: /broadcast pesan kamu disini")
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
    
    if len(context.args) < 2:
        await update.message.reply_text("Format: /emailblast Judul | Isi pesan kamu")
        return
    
    teks = " ".join(context.args)
    parts = teks.split("|")
    subject = parts[0].strip()
    isi = parts[1].strip() if len(parts) > 1 else teks
    
    emails = get_all_emails()
    berhasil = 0
    for e in emails:
        try:
            kirim_email(
                e['email'], e['nama'],
                subject,
                f"<p>{isi}</p><br><a href='https://lynk.id/novansetiadi03'>Cek produk kami</a>"
            )
            berhasil += 1
        except:
            pass
    
    await update.message.reply_text(f"Email blast terkirim ke {berhasil} subscriber! ✅")

# ── App setup ─────────────────────────────────────────
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(button_handler)],
    states={ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)]},
    fallbacks=[CommandHandler("skip", skip_email)]
)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("emailblast", email_blast))
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

print("Bot aktif...")
app.run_polling()
