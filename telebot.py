import os
import json
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Setup credentials
TOKEN = os.environ.get("TOKEN")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds_json = os.environ.get("GOOGLE_CREDENTIALS")
creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_ID = "1q4w8NAg0M3aLZDTFV5znla3pwKVKJlAAwPwlA7mweDI"  # ganti ini!
ADMIN_ID = 8253266018  # ganti dengan ID Telegram kamu!

users = set()

def get_products():
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet.get_all_records()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users.add(update.effective_user.id)
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
            break

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users.add(update.effective_user.id)
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
    
    berhasil = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=pesan)
            berhasil += 1
        except:
            pass
    
    await update.message.reply_text(f"Broadcast terkirim ke {berhasil} user! ✅")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

print("Bot aktif...")
app.run_polling()
