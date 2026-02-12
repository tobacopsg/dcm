# -*- coding: utf-8 -*-
# FULL TELEGRAM BOT - FINAL VERSION

import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = "8294731941:AAEE5o_-2Nd6W8u3bqGrwd-D2Y1ilmAlzZc"
ADMIN_ID = 6050668835

# ================= DATABASE =================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    total_deposit INTEGER DEFAULT 0,
    invite_count INTEGER DEFAULT 0,
    inviter INTEGER DEFAULT 0,
    created_at TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS transactions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,
    amount INTEGER,
    note TEXT,
    created_at TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS deposits(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    status TEXT,
    created_at TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS withdrawals(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    bank TEXT,
    status TEXT,
    created_at TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS bank(
    id INTEGER PRIMARY KEY,
    bank TEXT,
    stk TEXT,
    name TEXT
)""")

conn.commit()

# ================= HELPERS =================

def get_user(uid):
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return cur.fetchone()

def create_user(uid, inviter=0):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)",
                (uid,0,0,0,inviter,datetime.now().isoformat()))
    conn.commit()

def add_balance(uid, amt, note=""):
    cur.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
    cur.execute("INSERT INTO transactions(user_id,type,amount,note,created_at) VALUES (?,?,?,?,?)",
                (uid,"+",amt,note,datetime.now().isoformat()))
    conn.commit()

def sub_balance(uid, amt, note=""):
    cur.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (amt, uid))
    cur.execute("INSERT INTO transactions(user_id,type,amount,note,created_at) VALUES (?,?,?,?,?)",
                (uid,"-",amt,note,datetime.now().isoformat()))
    conn.commit()

# ================= MENUS =================

def user_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Nạp tiền", callback_data="deposit"),
         InlineKeyboardButton("💸 Rút tiền", callback_data="withdraw")],
        [InlineKeyboardButton("📊 Số dư", callback_data="balance"),
         InlineKeyboardButton("🤝 Mời bạn", callback_data="invite")],
        [InlineKeyboardButton("☎️ CSKH", callback_data="support")]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏦 Cài ngân hàng", callback_data="set_bank")],
        [InlineKeyboardButton("📥 Duyệt nạp", callback_data="admin_dep"),
         InlineKeyboardButton("📤 Duyệt rút", callback_data="admin_wd")]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args
    inviter = int(args[0]) if args else 0

    create_user(uid, inviter)

    if uid == ADMIN_ID:
        await update.message.reply_text("👑 ADMIN PANEL", reply_markup=admin_menu())
    else:
        await update.message.reply_text("🤖 OKVIP BOT KM VIP", reply_markup=user_menu())

# ================= CALLBACK =================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    # -------- USER --------

    if data == "balance":
        u = get_user(uid)
        cur.execute("SELECT type,amount,note FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,))
        logs = cur.fetchall()
        log_text = "\n".join([f"{'+' if i[0]=='+' else '-'}{i[1]:,} VND - {i[2]}" for i in logs])
        await q.message.edit_text(
            f"💰 Số dư: {u[1]:,} VND\n"
            f"📥 Tổng nạp: {u[2]:,} VND\n"
            f"🤝 Đã mời: {u[3]} bạn\n\n"
            f"📜 Lịch sử giao dịch:\n{log_text or 'Chưa có'}",
            reply_markup=user_menu()
        )

    elif data == "invite":
        await q.message.edit_text(
            f"🤝 LINK MỜI CỦA BẠN:\nhttps://t.me/{context.bot.username}?start={uid}\n\n"
            f"🎁 Thưởng: 149.000 VND / 1 bạn hợp lệ\n"
            f"📌 Điều kiện: Bạn bè nạp ≥ 99.000 VND",
            reply_markup=user_menu()
        )

    elif data == "deposit":
        cur.execute("SELECT bank,stk,name FROM bank WHERE id=1")
        b = cur.fetchone()
        if not b:
            await q.message.edit_text("❌ Hệ thống chưa cấu hình ngân hàng.", reply_markup=user_menu())
            return
        bank, stk, name = b
        context.user_data["wait_dep"] = True
        await q.message.edit_text(
            f"🏦 {bank}\n🏧 STK: {stk}\n👤 {name}\n\n"
            f"📌 Nội dung CK: NAP {uid}\n\n"
            f"Nhập số tiền muốn nạp (VND):"
        )

    elif data == "withdraw":
        u = get_user(uid)
        if u[3] <= 10 or u[1] < 5_000_000:
            await q.message.edit_text(
                "❌ Điều kiện rút tiền:\n"
                "- Mời trên 10 bạn\n"
                "- Số dư ≥ 5.000.000 VND",
                reply_markup=user_menu()
            )
            return
        context.user_data["wait_wd_amt"] = True
        await q.message.edit_text("💸 Nhập số tiền muốn rút (VND):")

    elif data == "support":
        context.user_data["wait_support"] = True
        await q.message.edit_text("Nhập nội dung cần hỗ trợ:")

    # -------- ADMIN --------

    elif data == "set_bank":
        context.user_data["set_bank"] = True
        await q.message.edit_text("Nhập: BANK|STK|NAME")

    elif data == "admin_dep":
        cur.execute("SELECT id,user_id,amount FROM deposits WHERE status='pending'")
        rows = cur.fetchall()
        if not rows:
            await q.message.edit_text("Không có yêu cầu nạp chờ duyệt.", reply_markup=admin_menu())
            return
        for d in rows:
            await context.bot.send_message(
                ADMIN_ID,
                f"📥 DUYỆT NẠP\nUser: {d[1]}\nTiền: {d[2]:,} VND",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ DUYỆT", callback_data=f"dep_ok_{d[0]}"),
                    InlineKeyboardButton("❌ TỪ CHỐI", callback_data=f"dep_no_{d[0]}")
                ]])
            )

    elif data.startswith("dep_ok"):
        did = int(data.split("_")[2])
        cur.execute("SELECT user_id,amount FROM deposits WHERE id=?", (did,))
        uid2, amt = cur.fetchone()

        add_balance(uid2, amt*2, "Nạp + thưởng 100%")
        cur.execute("UPDATE users SET total_deposit=total_deposit+? WHERE user_id=?", (amt, uid2))

        cur.execute("SELECT inviter FROM users WHERE user_id=?", (uid2,))
        inv = cur.fetchone()[0]
        if inv != 0 and amt >= 99_000:
            cur.execute("UPDATE users SET invite_count=invite_count+1 WHERE user_id=?", (inv,))
            add_balance(inv, 149_000, "Thưởng mời bạn")

        cur.execute("UPDATE deposits SET status='done' WHERE id=?", (did,))
        conn.commit()

        await context.bot.send_message(
            uid2,
            f"🎉 Nạp thành công!\n💰 {amt:,} VND\n🎁 Thưởng 100%\n👉 Tổng nhận: {amt*2:,} VND",
            reply_markup=user_menu()
        )
        await q.message.edit_text("✅ Đã duyệt nạp")

    elif data == "admin_wd":
        cur.execute("SELECT id,user_id,amount,bank FROM withdrawals WHERE status='pending'")
        rows = cur.fetchall()
        if not rows:
            await q.message.edit_text("Không có yêu cầu rút chờ duyệt.", reply_markup=admin_menu())
            return
        for w in rows:
            await context.bot.send_message(
                ADMIN_ID,
                f"💸 DUYỆT RÚT\nUser: {w[1]}\nTiền: {w[2]:,} VND\nNgân hàng: {w[3]}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ DUYỆT", callback_data=f"wd_ok_{w[0]}"),
                    InlineKeyboardButton("❌ TỪ CHỐI", callback_data=f"wd_no_{w[0]}")
                ]])
            )

    elif data.startswith("wd_ok"):
        wid = int(data.split("_")[2])
        cur.execute("SELECT user_id,amount FROM withdrawals WHERE id=?", (wid,))
        uid2, amt = cur.fetchone()
        cur.execute("UPDATE withdrawals SET status='done' WHERE id=?", (wid,))
        conn.commit()
        await context.bot.send_message(uid2, f"🎉 Rút thành công {amt:,} VND", reply_markup=user_menu())
        await q.message.edit_text("✅ Đã duyệt rút")

    elif data.startswith("wd_no"):
        wid = int(data.split("_")[2])
        cur.execute("SELECT user_id,amount FROM withdrawals WHERE id=?", (wid,))
        uid2, amt = cur.fetchone()
        add_balance(uid2, amt, "Hoàn tiền rút bị từ chối")
        cur.execute("UPDATE withdrawals SET status='deny' WHERE id=?", (wid,))
        conn.commit()
        await context.bot.send_message(uid2, f"❌ Rút {amt:,} VND bị từ chối → đã hoàn tiền", reply_markup=user_menu())
        await q.message.edit_text("❌ Đã từ chối rút & hoàn tiền")

    elif data.startswith("reply_"):
        uid2 = int(data.split("_")[1])
        context.user_data["reply_uid"] = uid2
        await q.message.edit_text(f"Nhập nội dung phản hồi cho user {uid2}:")

# ================= TEXT =================

async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.strip()

    if context.user_data.get("set_bank"):
        b, s, n = txt.split("|")
        cur.execute("DELETE FROM bank")
        cur.execute("INSERT INTO bank VALUES (1,?,?,?)", (b, s, n))
        conn.commit()
        await update.message.reply_text("✅ Đã cập nhật ngân hàng", reply_markup=admin_menu())
        context.user_data.clear()

    elif context.user_data.get("wait_dep"):
        amt = int(txt)
        cur.execute("INSERT INTO deposits(user_id,amount,status,created_at) VALUES (?,?,?,?)",
                    (uid, amt, "pending", datetime.now().isoformat()))
        conn.commit()
        await update.message.reply_text("⏳ Đã gửi yêu cầu nạp – chờ admin duyệt", reply_markup=user_menu())
        context.user_data.clear()

    elif context.user_data.get("wait_wd_amt"):
        amt = int(txt)
        context.user_data["wd_amt"] = amt
        context.user_data["wait_wd_amt"] = False
        context.user_data["wait_wd_bank"] = True
        await update.message.reply_text("🏦 Nhập thông tin ngân hàng nhận tiền:")

    elif context.user_data.get("wait_wd_bank"):
        context.user_data["wd_bank"] = txt
        amt = context.user_data["wd_amt"]
        await update.message.reply_text(
            f"🔎 XÁC NHẬN THÔNG TIN RÚT\n\n"
            f"💰 Số tiền: {amt:,} VND\n"
            f"🏦 Ngân hàng: {txt}\n\n"
            f"Vui lòng xác nhận:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ XÁC NHẬN", callback_data="wd_confirm"),
                InlineKeyboardButton("❌ HỦY", callback_data="wd_cancel")
            ]])
        )

    elif context.user_data.get("wait_support"):
        await context.bot.send_message(
            ADMIN_ID,
            f"📩 CSKH từ {uid}:\n{txt}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💬 REPLY", callback_data=f"reply_{uid}")
            ]])
        )
        await update.message.reply_text("✅ Đã gửi CSKH", reply_markup=user_menu())
        context.user_data.clear()

    elif context.user_data.get("reply_uid"):
        uid2 = context.user_data["reply_uid"]
        await context.bot.send_message(uid2, f"💬 CSKH phản hồi:\n{txt}", reply_markup=user_menu())
        await update.message.reply_text("✅ Đã gửi phản hồi", reply_markup=admin_menu())
        context.user_data.clear()

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))

print("BOT RUNNING...")
app.run_polling()
