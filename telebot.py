from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8783768315:AAFix5FfKO27peoZpQQk914_j_AAK3u0gts"
LINK_PRODUK = "https://lynk.id/novansetiadi03"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Halo! 👋 Terima kasih sudah menghubungi.\n\n"
        f"Cek produk digital kami di sini:\n{LINK_PRODUK}\n\n"
        f"Ada yang bisa dibantu?"
    )

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = update.message.text.lower()
    
    if "harga" in pesan or "berapa" in pesan:
        await update.message.reply_text(f"Cek lengkap harga & produk di sini 👇\n{LINK_PRODUK}")
    elif "beli" in pesan or "order" in pesan:
        await update.message.reply_text(f"Yuk langsung order di sini 👇\n{LINK_PRODUK}")
    else:
        await update.message.reply_text(f"Halo! Ada yang bisa dibantu? 😊\nInfo produk: {LINK_PRODUK}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

print("Bot aktif...")
app.run_polling()