import logging
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = "8294731941:AAEE5o_-2Nd6W8u3bqGrwd-D2Y1ilmAlzZc"
ADMIN_ID = 6050668835

logging.basicConfig(level=logging.INFO)

# ===== DATABASE =====

conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    ref INTEGER DEFAULT 0
)""")

c.execute("""CREATE TABLE IF NOT EXISTS deposits(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    status TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS withdraws(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    bank TEXT,
    status TEXT
)""")

conn.commit()

# ===== UTILS =====

def add_user(uid, ref=0):
    c.execute("INSERT OR IGNORE INTO users VALUES(?,?,?)", (uid,0,ref))
    conn.commit()

def add_balance(uid, amount):
    c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, uid))
    conn.commit()

# ===== MENU =====

def user_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Nạp tiền", callback_data="nap")],
        [InlineKeyboardButton("🏧 Rút tiền", callback_data="rut")],
        [InlineKeyboardButton("📊 Số dư", callback_data="sodu")],
        [InlineKeyboardButton("👥 Mời bạn", callback_data="ref")]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Duyệt nạp", callback_data="ad_nap")],
        [InlineKeyboardButton("🏧 Duyệt rút", callback_data="ad_rut")]
    ])

# ===== START =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if args:
        add_user(uid, int(args[0]))
    else:
        add_user(uid)

    if uid == ADMIN_ID:
        await update.message.reply_text("👑 ADMIN PANEL", reply_markup=admin_menu())
    else:
        await update.message.reply_text("🤖 BOT TÀI CHÍNH", reply_markup=user_menu())

# ===== CALLBACK =====

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if data == "nap":
        context.user_data["nap"] = True
        await q.message.reply_text("Nhập số tiền cần nạp (VND):")

    elif data == "rut":
        context.user_data["rut"] = True
        await q.message.reply_text("Nhập số tiền muốn rút (VND):")

    elif data == "sodu":
        c.execute("SELECT balance,ref FROM users WHERE user_id=?", (uid,))
        bal, ref = c.fetchone()
        await q.message.reply_text(f"💰 Số dư: {bal:,} VND\n👥 Đã mời: {ref} người")

    elif data == "ref":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        await q.message.reply_text(f"👥 Link mời:\n{link}")

# ===== TEXT =====

async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if context.user_data.get("nap"):
        amount = int(text)
        c.execute("INSERT INTO deposits(user_id,amount,status) VALUES(?,?,?)",
                  (uid, amount, "pending"))
        conn.commit()

        await context.bot.send_message(ADMIN_ID, f"💰 ĐƠN NẠP\nUser:{uid}\nSố:{amount:,}")
        await update.message.reply_text("⏳ Chờ admin duyệt.")
        context.user_data.clear()

    elif context.user_data.get("rut"):
        amount = int(text)
        c.execute("SELECT balance,ref FROM users WHERE user_id=?", (uid,))
        bal, ref = c.fetchone()

        if ref < 10 or bal < 5_000_000:
            await update.message.reply_text("❌ Không đủ điều kiện rút.")
            context.user_data.clear()
            return

        context.user_data["bank"] = amount
        await update.message.reply_text("Nhập thông tin ngân hàng:")

    elif context.user_data.get("bank"):
        amount = context.user_data["bank"]
        bank = text

        c.execute("INSERT INTO withdraws(user_id,amount,bank,status) VALUES(?,?,?,?)",
                  (uid, amount, bank, "pending"))
        conn.commit()

        await context.bot.send_message(
            ADMIN_ID, f"🏧 RÚT TIỀN\nUser:{uid}\nSố:{amount:,}\nBank:{bank}"
        )

        await update.message.reply_text("⏳ Chờ admin duyệt.")
        context.user_data.clear()

# ===== RUN =====

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))

print("BOT RUNNING")
app.run_polling()

