import os
import logging
import asyncio
import requests
import sqlite3
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from concurrent.futures import ThreadPoolExecutor

# CONFIG
BOT_TOKEN = "8691956766:AAGZ58LARMbNdw_JJtUxMWKiuexV3WPTFf4"
API_URL = "https://numtolnfo.suryajasoos-4fe.workers.dev/?mobile={}"
ADMIN_IDS = [5481125164, 9720294892]
DEV_TAG = "@dinamicshai"
DB_PATH = "user_data.db"

# DATABASE
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, 
                  credit INTEGER DEFAULT 5, is_premium INTEGER DEFAULT 0, 
                  total_searches INTEGER DEFAULT 0, joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (user_id, username, first_name, credit) VALUES (?, ?, ?, 5)",
                  (user_id, username, first_name))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def update_credit(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credit = credit + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def set_premium(user_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_premium = ? WHERE user_id = ?", (status, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, credit, is_premium, total_searches FROM users")
    users = c.fetchall()
    conn.close()
    return users

# API
def fetch_number_info_sync(mobile):
    try:
        response = requests.get(API_URL.format(mobile), timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

async def fetch_number_info(mobile):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, fetch_number_info_sync, mobile)

# COMMANDS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not get_user(user.id):
        create_user(user.id, user.username, user.first_name)
        msg = f"🎉 Welcome {user.first_name}!\n⭐ You got 5 free credits!\nSend any number to search.\n\n{DEV_TAG}"
    else:
        data = get_user(user.id)
        msg = f"👋 Welcome back {user.first_name}!\n⭐ Credits: {data[3]}\n💎 Premium: {'✅' if data[4] else '❌'}\n🔍 Total Searches: {data[5]}\n\nSend any number to search.\n\n{DEV_TAG}"
    
    keyboard = [[InlineKeyboardButton("📊 Stats", callback_data="stats")]]
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = get_user(user_id)
    if data:
        msg = f"📊 Your Stats:\n⭐ Credits: {data[3]}\n💎 Premium: {'✅' if data[4] else '❌'}\n🔍 Searches: {data[5]}\n📅 Joined: {data[6]}\n\n{DEV_TAG}"
    else:
        msg = "❌ User not found!"
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mobile = update.message.text.strip()
    
    if not re.match(r'^\+?\d{10,15}$', mobile):
        await update.message.reply_text("❌ Invalid number! Send 10-15 digits.\nExample: `9720294892`", parse_mode=ParseMode.MARKDOWN)
        return
    
    user_data = get_user(user_id)
    if not user_data:
        create_user(user_id, update.effective_user.username, update.effective_user.first_name)
        user_data = get_user(user_id)
    
    if not user_data[4] and user_data[3] <= 0:
        await update.message.reply_text(f"❌ No credits!\n⭐ Credits: {user_data[3]}\nContact admin for more.\n\n{DEV_TAG}", parse_mode=ParseMode.MARKDOWN)
        return
    
    await update.message.chat.send_action("typing")
    data = await fetch_number_info(mobile)
    
    if data:
        if not user_data[4]:
            update_credit(user_id, -1)
        
        response = f"📱 *Number Info*\n*Number:* `{mobile}`\n\n"
        if isinstance(data, dict):
            for k, v in data.items():
                if v:
                    response += f"┌ *{k.replace('_', ' ').title()}*: {v}\n"
        else:
            response += f"┌ {data}\n"
        
        credits = user_data[3] - 1 if not user_data[4] else "♾️"
        response += f"\n⭐ Credits: {credits}\n\n{DEV_TAG}"
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ API Error! Try again.\n\n{DEV_TAG}", parse_mode=ParseMode.MARKDOWN)

# ADMIN
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access Denied!")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")]
    ]
    await update.message.reply_text("🔐 *Admin Panel*", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("❌ Access Denied!")
        return
    
    if query.data == "admin_users":
        users = get_all_users()
        msg = "👥 *Users*\n\n"
        for u in users[:10]:
            msg += f"• {u[2]} (@{u[1] or 'no username'})\n  Credits: {u[3]} | Premium: {'✅' if u[4] else '❌'} | Searches: {u[5]}\n\n"
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
    elif query.data == "admin_stats":
        users = get_all_users()
        total = len(users)
        premium = sum(1 for u in users if u[4])
        searches = sum(u[5] for u in users)
        await query.edit_message_text(f"📊 *Bot Stats*\n👥 Users: {total}\n💎 Premium: {premium}\n🔍 Searches: {searches}\n\n{DEV_TAG}", parse_mode=ParseMode.MARKDOWN)

async def add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: `/addcredits user_id amount`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        user_id, amount = int(args[0]), int(args[1])
        if get_user(user_id):
            update_credit(user_id, amount)
            await update.message.reply_text(f"✅ Added {amount} credits to user {user_id}")
        else:
            await update.message.reply_text("❌ User not found!")
    except:
        await update.message.reply_text("❌ Invalid input!")

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: `/premium user_id on/off`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        user_id, status = int(args[0]), args[1].lower()
        if status == "on":
            set_premium(user_id, 1)
            await update.message.reply_text(f"✅ Premium enabled for {user_id}")
        elif status == "off":
            set_premium(user_id, 0)
            await update.message.reply_text(f"❌ Premium disabled for {user_id}")
        else:
            await update.message.reply_text("❌ Use 'on' or 'off'")
    except:
        await update.message.reply_text("❌ Invalid input!")

async def reset_credits():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credit = 5 WHERE is_premium = 0")
    conn.commit()
    conn.close()
    logging.info("✅ Daily credits reset")

async def daily_reset():
    while True:
        now = datetime.now()
        next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        await asyncio.sleep((next_day - now).total_seconds())
        await reset_credits()

# MAIN
def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("🤖 Starting Bot...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addcredits", add_credits))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CallbackQueryHandler(stats_callback, pattern="stats"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="admin_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    
    asyncio.create_task(daily_reset())
    
    logging.info("✅ Bot Started Successfully!")
    app.run_polling()

if __name__ == "__main__":
    main()
