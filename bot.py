import os, json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
USERS_FILE, BLOCKS_FILE, ADMINS_FILE, WELCOME_FILE = "users.json", "blocks.json", "admins.json", "welcome.txt"
REPLY_MODE = {}

# ------------------ فایل‌های ذخیره‌سازی ------------------
def load_json(file): return json.load(open(file)) if os.path.exists(file) else {}
def save_json(file, data): json.dump(data, open(file, "w"), indent=2)

# ------------------ کاربران ------------------
def save_user(user):
    users = load_json(USERS_FILE)
    if str(user.id) not in users:
        users[str(user.id)] = {
            "name": user.full_name,
            "username": user.username,
            "start_time": datetime.now().isoformat()
        }
        save_json(USERS_FILE, users)

def is_blocked(uid): return str(uid) in load_json(BLOCKS_FILE)
def block(uid): data = load_json(BLOCKS_FILE); data[str(uid)] = True; save_json(BLOCKS_FILE, data)
def unblock(uid): data = load_json(BLOCKS_FILE); data.pop(str(uid), None); save_json(BLOCKS_FILE, data)

# ------------------ ادمین‌ها ------------------
def get_admins(): return list(map(int, load_json(ADMINS_FILE).keys()))
def is_admin(uid): return uid in get_admins()
def add_admin(user_id, name, username):
    data = load_json(ADMINS_FILE)
    data[str(user_id)] = {"name": name, "username": username}
    save_json(ADMINS_FILE, data)

def remove_admin(user_id):
    data = load_json(ADMINS_FILE)
    data.pop(str(user_id), None)
    save_json(ADMINS_FILE, data)

# ------------------ پیام خوش‌آمد و دکمه‌ها ------------------
def get_welcome():
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE) as f: return f.read()
    return "سلام رفیق! 👋\nهر حرف، درد و دل یا پیام مهمی داری، من می‌رسونم به ادمینا 😉"

def keyboard_user():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✉️ ارسال پیام", callback_data="send")]])

def keyboard_admin_reply(uid):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✉️ پاسخ", callback_data=f"reply:{uid}")]])

# ------------------ تعامل کاربر ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    await update.message.reply_text(get_welcome(), reply_markup=keyboard_user())

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "send":
        await query.message.reply_text("خب منتظرم! هرچی می‌خوای بنویس تا بفرستم 🚀")
        context.user_data["awaiting_message"] = True
    elif query.data.startswith("reply:"):
        uid = int(query.data.split(":")[1])
        REPLY_MODE[query.from_user.id] = uid
        await query.message.reply_text("📝 پیام خود را بنویس تا به کاربر ارسال شود:")

async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blocked(user.id):
        await update.message.reply_text("🚫 متاسفم! شما اجازه ارسال پیام نداری.")
        return
    if context.user_data.get("awaiting_message"):
        msg = update.message.text or "<بدون متن>"
        for aid in get_admins():
            await context.bot.send_message(
                aid,
                f"📩 پیام جدید از {user.full_name} (@{user.username} | {user.id}):\n\n{msg}",
                reply_markup=keyboard_admin_reply(user.id)
            )
        await update.message.reply_text(
            "✅ پیامت رسید! به گوش ادمین‌ها رسوندم.\nاگه بازم حرفی داشتی، دکمه پایین رو بزن!",
            reply_markup=keyboard_user()
        )
        context.user_data["awaiting_message"] = False

# ------------------ پاسخ ادمین ------------------
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aid = update.effective_user.id
    if aid in REPLY_MODE:
        uid = REPLY_MODE.pop(aid)
        try:
            await context.bot.send_message(uid, update.message.text)
            await update.message.reply_text("✅ پیام شما برای کاربر ارسال شد.")
        except:
            await update.message.reply_text("❌ ارسال ناموفق بود. شاید کاربر بلاک شده یا چت غیرفعاله.")

# ------------------ دستورات مدیریتی ------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    users = load_json(USERS_FILE)
    msg = "📊 آمار کاربران:\n"
    for uid, u in users.items():
        msg += f"{u['name']} | @{u['username']} | {uid} | {u['start_time']}\n"
    await update.message.reply_text(msg or "هیچ کاربری ثبت نشده.")

async def forall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    text = update.message.reply_to_message.text
    users = load_json(USERS_FILE)
    count = 0
    for uid in users:
        try:
            await context.bot.send_message(int(uid), text)
            count += 1
        except: pass
    await update.message.reply_text(f"📤 پیام برای {count} نفر ارسال شد.")

async def block_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if context.args:
        uid = int(context.args[0])
        block(uid)
        await update.message.reply_text(f"🚫 کاربر {uid} بلاک شد.")

async def unblock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if context.args:
        uid = int(context.args[0])
        unblock(uid)
        await update.message.reply_text(f"✅ کاربر {uid} آزاد شد.")

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if context.args:
        new_id = int(context.args[0])
        user = await context.bot.get_chat(new_id)
        add_admin(new_id, user.full_name, user.username)
        await update.message.reply_text(f"✅ آیدی {new_id} به ادمین‌ها اضافه شد.")

async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if context.args:
        rem = int(context.args[0])
        remove_admin(rem)
        await update.message.reply_text(f"✅ آیدی {rem} از لیست ادمین‌ها حذف شد.")

async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    text = " ".join(context.args)
    with open(WELCOME_FILE, "w") as f: f.write(text)
    await update.message.reply_text("✅ پیام خوش‌آمد با موفقیت ذخیره شد.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    msg = """📋 دستورات مدیریتی (فقط برای ادمین):

/stats — نمایش آمار کاربران
/forall (ریپلای) — ارسال پیام همگانی
/block <user_id> — بلاک کردن کاربر
/unblock <user_id> — آزاد کردن کاربر
/addadmin <user_id> — اضافه کردن ادمین
/removeadmin <user_id> — حذف ادمین
/setwelcome <متن> — تنظیم پیام خوش‌آمد

✉️ برای پاسخ به پیام کاربر از دکمه «پاسخ» زیر پیام استفاده کنید.
"""
    await update.message.reply_text(msg)

# ------------------ اجرای اصلی ------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("forall", forall))
    app.add_handler(CommandHandler("block", block_cmd))
    app.add_handler(CommandHandler("unblock", unblock_cmd))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CommandHandler("setwelcome", setwelcome))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, admin_reply))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, user_message))
    print("🤖 Dr Goshad is online.")
    app.run_polling()

if __name__ == "__main__":
    main()
