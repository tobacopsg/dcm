# main.py — BOT TELE KIẾM TIỀN FULL: NHIỆM VỤ + REF + GIFTCODE + RÚT + EVENT + BXH
# Python 3.10+ | pip install python-telegram-bot==20.7

import sqlite3, logging, random, string
from datetime import date
from telegram import *
from telegram.ext import *

TOKEN = "8241969129:AAE2amllaL22t0Xb2PwS1GFg2AXtTd9GS3E"
ADMIN_ID = 6050668835

logging.basicConfig(level=logging.INFO)
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

# ===== DB =====
cur.execute("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    ref INTEGER,
    balance INTEGER DEFAULT 0,
    invite_total INTEGER DEFAULT 0,
    invite_today INTEGER DEFAULT 0,
    last_day TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS giftcodes(
    code TEXT PRIMARY KEY,
    value INTEGER,
    used INTEGER DEFAULT 0
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS withdraw(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    time TEXT
)""")

db.commit()

# ===== UTILS =====
def today(): return date.today().isoformat()

def reset_day(uid):
    cur.execute("SELECT last_day FROM users WHERE id=?", (uid,))
    row = cur.fetchone()
    if not row or row[0] != today():
        cur.execute("UPDATE users SET invite_today=0,last_day=? WHERE id=?", (today(), uid))
        db.commit()

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Số dư", callback_data="bal")],
        [InlineKeyboardButton("📌 Nhiệm vụ", callback_data="task")],
        [InlineKeyboardButton("👥 Mời bạn", callback_data="ref")],
        [InlineKeyboardButton("🏆 Đua top", callback_data="top")],
        [InlineKeyboardButton("🎁 Giftcode", callback_data="gift")],
        [InlineKeyboardButton("🏧 Rút tiền", callback_data="wd")]
    ])

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ref = int(context.args[0]) if context.args else None

    cur.execute("SELECT id FROM users WHERE id=?", (u.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users(id,ref,last_day) VALUES(?,?,?)", (u.id, ref, today()))
        if ref and ref != u.id:
            cur.execute("UPDATE users SET balance=balance+50000, invite_total=invite_total+1 WHERE id=?", (ref,))
        db.commit()

    await update.message.reply_text("🤖 BOT TELE KIẾM TIỀN", reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    reset_day(uid)

    if q.data == "bal":
        cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
        await q.edit_message_text(f"💰 Số dư: {cur.fetchone()[0]:,} VND")

    elif q.data == "task":
        await q.edit_message_text(
            "📌 NHIỆM VỤ NGÀY\n"
            "• Nạp tiền: +30%\n"
            "• Mời 3 bạn: +50,000đ\n"
            "• Rút 50k: +15,000đ"
        )

    elif q.data == "ref":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        await q.edit_message_text(f"👥 LINK MỜI BẠN:\n{link}")

    elif q.data == "gift":
        context.user_data["gift"] = True
        await q.edit_message_text("✍️ Gửi giftcode:")

    elif q.data == "wd":
        cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
        bal = cur.fetchone()[0]
        if bal < 50000:
            await q.edit_message_text("❌ Tối thiểu 50k.")
        else:
            cur.execute("UPDATE users SET balance=balance-50000 WHERE id=?", (uid,))
            cur.execute("INSERT INTO withdraw(user_id,amount,time) VALUES(?,?,?)", (uid,50000,today()))
            db.commit()
            await q.edit_message_text("✅ Đã gửi yêu cầu rút 50k.")

    elif q.data == "top":
        cur.execute("SELECT id,invite_total FROM users ORDER BY invite_total DESC LIMIT 10")
        text = "🏆 BXH MỜI BẠN\n\n"
        for i,r in enumerate(cur.fetchall(),1):
            text += f"{i}. {r[0]} - {r[1]} lượt\n"
        await q.edit_message_text(text)

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("gift"):
        code = update.message.text.strip()
        cur.execute("SELECT value,used FROM giftcodes WHERE code=?", (code,))
        row = cur.fetchone()
        if not row:
            await update.message.reply_text("❌ Code sai.")
        elif row[1]:
            await update.message.reply_text("❌ Code đã dùng.")
        else:
            cur.execute("UPDATE giftcodes SET used=1 WHERE code=?", (code,))
            cur.execute("UPDATE users SET balance=balance+? WHERE id=?", (row[0], update.effective_user.id))
            db.commit()
            await update.message.reply_text(f"✅ Nhận {row[0]:,} VND")
        context.user_data["gift"] = False

# ===== ADMIN =====
async def addgift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    val = int(context.args[0])
    code = ''.join(random.choices(string.ascii_uppercase+string.digits,k=10))
    cur.execute("INSERT INTO giftcodes(code,value) VALUES(?,?)",(code,val))
    db.commit()
    await update.message.reply_text(f"🎁 {code} | {val:,}")

async def addbal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    uid = int(context.args[0]); val=int(context.args[1])
    cur.execute("UPDATE users SET balance=balance+? WHERE id=?", (val,uid))
    db.commit()
    await update.message.reply_text("✅ OK")

# ===== RUN =====
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addgift", addgift))
app.add_handler(CommandHandler("addbal", addbal))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

print("BOT RUNNING...")
app.run_polling()
