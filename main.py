import logging
import sqlite3
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = "8294731941:AAEE5o_-2Nd6W8u3bqGrwd-D2Y1ilmAlzZc"
ADMIN_ID = 6050668835

logging.basicConfig(level=logging.INFO)

# ================= DATABASE =================

conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    ref INTEGER DEFAULT 0
)""")

c.execute("""CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    status TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS withdraws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    bank TEXT,
    status TEXT
)""")

conn.commit()

# ================= UTILS =================

def get_user(uid):
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return c.fetchone()

def add_user(uid, ref=0):
    c.execute("INSERT OR IGNORE INTO users(user_id,ref) VALUES(?,?)", (uid, ref))
    conn.commit()

def add_balance(uid, amount):
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
    conn.commit()

# ================= UI =================

def user_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Nạp tiền", callback_data="nap")],
        [InlineKeyboardButton("🏧 Rút tiền", callback_data="rut")],
        [InlineKeyboardButton("📊 Số dư", callback_data="sodu")],
        [InlineKeyboardButton("👥 Mời bạn", callback_data="ref")],
        [InlineKeyboardButton("📞 CSKH", callback_data="cskh")]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Duyệt nạp", callback_data="ad_nap")],
        [InlineKeyboardButton("🏧 Duyệt rút", callback_data="ad_rut")]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if args:
        ref = int(args[0])
        add_user(uid, ref)
    else:
        add_user(uid)

    if uid == ADMIN_ID:
        await update.message.reply_text("👑 ADMIN PANEL", reply_markup=admin_menu())
    else:
        await update.message.reply_text("🤖 BOT TÀI CHÍNH - UY TÍN", reply_markup=user_menu())

# ================= CALLBACK =================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        c.execute("SELECT balance, ref FROM users WHERE user_id=?", (uid,))
        bal, ref = c.fetchone()
        await q.message.reply_text(
            f"💰 Số dư: {bal:,} VND\n👥 Đã mời: {ref} người"
        )

    elif data == "ref":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        await q.message.reply_text(f"👥 Link mời:\n{link}")

    elif data == "cskh":
        context.user_data["cskh"] = True
        await q.message.reply_text("Nhập nội dung cần hỗ trợ:")

    elif data == "ad_nap":
        c.execute("SELECT id,user_id,amount FROM deposits WHERE status='pending'")
        rows = c.fetchall()
        if not rows:
            await q.message.reply_text("Không có đơn nạp.")
            return
        for r in rows:
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Duyệt", callback_data=f"nap_ok_{r[0]}"),
                InlineKeyboardButton("❌ Từ chối", callback_data=f"nap_no_{r[0]}")
            ]])
            await q.message.reply_text(
                f"ID:{r[0]}\nUser:{r[1]}\nSố tiền:{r[2]:,}",
                reply_markup=kb
            )

    elif data.startswith("nap_ok_"):
        did = int(data.split("_")[2])
        c.execute("SELECT user_id,amount FROM deposits WHERE id=?", (did,))
        uid2, amt = c.fetchone()

        add_balance(uid2, amt * 2)  # thưởng 100%
        c.execute("UPDATE deposits SET status='done' WHERE id=?", (did,))
        conn.commit()

        await context.bot.send_message(
            uid2,
            f"🎉 Nạp thành công!\n+{amt*2:,} VND (100%)"
        )
        await q.message.reply_text("Đã duyệt nạp.")

    elif data.startswith("nap_no_"):
        did = int(data.split("_")[2])
        c.execute("UPDATE deposits SET status='reject' WHERE id=?", (did,))
        conn.commit()
        await q.message.reply_text("Đã từ chối.")

# ================= TEXT INPUT =================

async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if context.user_data.get("nap"):
        amount = int(text)
        c.execute("INSERT INTO deposits(user_id,amount,status) VALUES(?,?,?)",
                  (uid, amount, "pending"))
        conn.commit()

        await context.bot.send_message(
            ADMIN_ID,
            f"💰 ĐƠN NẠP\nUser:{uid}\nSố tiền:{amount:,}"
        )
        await update.message.reply_text("⏳ Chờ admin duyệt.")
        context.user_data.clear()

    elif context.user_data.get("rut"):
        amount = int(text)
        c.execute("SELECT balance,ref FROM users WHERE user_id=?", (uid,))
        bal, ref = c.fetchone()

        if ref < 10 or bal < 5_000_000 or amount < 5_000_000:
            await update.message.reply_text("❌ Không đủ điều kiện rút.")
            context.user_data.clear()
            return

        context.user_data["rut_amount"] = amount
        context.user_data["bank"] = True
        await update.message.reply_text("Nhập thông tin ngân hàng:")

    elif context.user_data.get("bank"):
        bank = text
        amt = context.user_data["rut_amount"]

        c.execute("INSERT INTO withdraws(user_id,amount,bank,status) VALUES(?,?,?,?)",
                  (uid, amt, bank, "pending"))
        conn.commit()

        await context.bot.send_message(
            ADMIN_ID,
            f"🏧 RÚT TIỀN\nUser:{uid}\nSố:{amt:,}\nBank:{bank}"
        )

        await update.message.reply_text("⏳ Chờ admin duyệt.")
        context.user_data.clear()

    elif context.user_data.get("cskh"):
        await context.bot.send_message(
            ADMIN_ID,
            f"📩 CSKH từ {uid}:\n{text}"
        )
        await update.message.reply_text("Đã gửi CSKH.")
        context.user_data.clear()

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))

print("BOT RUNNING ...")
app.run_polling()
