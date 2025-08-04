# bot.py

import os, json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

USERS_FILE, BLOCKS_FILE, WELCOME_FILE = "users.json", "blocks.json", "welcome.txt"
REPLY_MODE = {}

def load_json(file): return json.load(open(file)) if os.path.exists(file) else {}
def save_json(file, data): json.dump(data, open(file, "w"), indent=2)

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
def block(uid):
    data = load_json(BLOCKS_FILE); data[str(uid)] = True; save_json(BLOCKS_FILE, data)
def unblock(uid):
    data = load_json(BLOCKS_FILE); data.pop(str(uid), None); save_json(BLOCKS_FILE, data)

def get_welcome():
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE) as f: return f.read()
    return "سلام رفیق! 👋\nهر حرف، درد و دل یا پیام مهمی داری، من می‌رسونم به ادمینا 😉"

def keyboard_user():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✉️ ارسال پیام", callback_data="send")]])

def keyboard_admin_reply(uid):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✉️ پاسخ", callback_data=f"reply:{uid}")]])

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
        for aid in ADMINS:
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

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aid = update.effective_user.id
    if aid in REPLY_MODE:
        uid = REPLY_MODE.pop(aid)
        try:
            await context.bot.send_message(uid, update.message.text)
            await update.message.reply_text("✅ پیام شما برای کاربر ارسال شد.")
        except:
            await update.message.reply_text("❌ ارسال ناموفق بود. شاید کاربر بلاک شده یا چت غیرفعاله.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    users = load_json(USERS_FILE)
    msg = "📊 آمار کاربران:\n"
    for uid, u in users.items():
        msg += f"{u['name']} | @{u['username']} | {uid} | {u['start_time']}\n"
    await update.message.reply_text(msg or "هیچ کاربری ثبت نشده.")

async def forall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
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
    if update.effective_user.id not in ADMINS: return
    if context.args:
        uid = int(context.args[0])
        block(uid)
        await update.message.reply_text(f"🚫 کاربر {uid} بلاک شد.")

async def unblock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    if context.args:
        uid = int(context.args[0])
        unblock(uid)
        await update.message.reply_text(f"✅ کاربر {uid} آزاد شد.")

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    if context.args:
        new = int(context.args[0])
        if new not in ADMINS:
            ADMINS.append(new)
            await update.message.reply_text(f"✅ آیدی {new} به ادمین‌ها اضافه شد.")

async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    if context.args:
        rem = int(context.args[0])
        if rem in ADMINS:
            ADMINS.remove(rem)
            await update.message.reply_text(f"✅ آیدی {rem} از لیست ادمین‌ها حذف شد.")

async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    text = " ".join(context.args)
    with open(WELCOME_FILE, "w") as f: f.write(text)
    await update.message.reply_text("✅ پیام خوش‌آمد با موفقیت ذخیره شد.")

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

    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, admin_reply))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, user_message))

    print("🤖 Dr Goshad is online.")
    app.run_polling()

if __name__ == "__main__":
    main()
