import os
import logging
import asyncio
import requests
import sqlite3
import re
import json
from datetime import datetime
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

# FORMAT RESPONSE - ATTRACTIVE
def format_response(data, mobile):
    if not data:
        return "❌ No data found for this number!"
    
    # Agar response mein 'response' key hai toh usme se data lo
    if isinstance(data, dict) and 'response' in data:
        actual_data = data['response']
        if isinstance(actual_data, dict):
            data = actual_data
        else:
            data = data
    
    response = f"📱 *┏━━━━━━━━━━━━━━━━━━━━┓*\n"
    response += f"*┃ 📞 NUMBER DETAILS* \n"
    response += f"*┗━━━━━━━━━━━━━━━━━━━━┛*\n\n"
    
    response += f"╭───────────────────╮\n"
    response += f"│ 📱 *Number* │ `{mobile}`\n"
    response += f"╰───────────────────╯\n\n"
    
    # Important fields with emojis
    field_map = {
        'name': '👤 *Name*',
        'fname': '👨 *Father Name*',
        'address': '📍 *Address*',
        'alt': '📞 *Alternate Number*',
        'circle': '📡 *Circle*',
        'id': '🆔 *ID*',
        'email': '📧 *Email*',
        'city': '🏙️ *City*',
        'state': '🏛️ *State*',
        'pincode': '📮 *Pincode*',
        'operator': '📶 *Operator*',
        'carrier': '📶 *Carrier*',
        'type': '📌 *Type*',
        'location': '📍 *Location*'
    }
    
    for key, value in data.items():
        if value and key not in ['mobile', 'number', 'success', 'response']:
            display_key = field_map.get(key, f"📌 *{key.replace('_', ' ').title()}*")
            # Clean address
            if key == 'address' and isinstance(value, str):
                value = value.replace('!', ', ').replace('  ', ' ')
                if len(value) > 50:
                    value = value[:50] + '...'
            response += f"│ {display_key} │ {value}\n"
    
    response += f"\n╭───────────────────╮\n"
    response += f"│ 👨‍💻 *Owner* │ {DEV_TAG}\n"
    response += f"╰───────────────────╯\n"
    
    return response

# COMMANDS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not get_user(user.id):
        create_user(user.id, user.username, user.first_name)
        msg = f"""🌟 *┏━━━━━━━━━━━━━━━━━━━━┓* 🌟
*┃ WELCOME TO* 
*┃ NUMBER INFO BOT* 
*┗━━━━━━━━━━━━━━━━━━━━┛*

╭───────────────────╮
│ 👋 *Hello {user.first_name}!* │
╰───────────────────╯

⭐ *You got 5 FREE credits!*
🔍 *1 credit = 1 search*

💎 *Premium = Unlimited searches*

📱 *Send any mobile number* 
   to get instant info!

━━━━━━━━━━━━━━━━
👨‍💻 {DEV_TAG}"""
    else:
        data = get_user(user.id)
        msg = f"""🌟 *┏━━━━━━━━━━━━━━━━━━━━┓* 🌟
*┃ WELCOME BACK* 
*┃ {user.first_name}* 
*┗━━━━━━━━━━━━━━━━━━━━┛*

╭───────────────────╮
│ ⭐ *Credits:* {data[3]} │
│ 💎 *Premium:* {'✅ Active' if data[4] else '❌ Inactive'} │
│ 🔍 *Searches:* {data[5]} │
╰───────────────────╯

📱 *Send any mobile number* 
   to get instant info!

━━━━━━━━━━━━━━━━
👨‍💻 {DEV_TAG}"""
    
    keyboard = [
        [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ]
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = get_user(user_id)
    if data:
        msg = f"""📊 *┏━━━━━━━━━━━━━━━━━━━━┓*
*┃ YOUR STATISTICS* 
*┗━━━━━━━━━━━━━━━━━━━━┛*

╭───────────────────╮
│ ⭐ *Credits:* {data[3]} │
│ 💎 *Premium:* {'✅ Active' if data[4] else '❌ Inactive'} │
│ 🔍 *Searches:* {data[5]} │
│ 📅 *Joined:* {data[6]} │
╰───────────────────╯

━━━━━━━━━━━━━━━━
👨‍💻 {DEV_TAG}"""
    else:
        msg = "❌ User not found!"
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

async def about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = f"""🤖 *┏━━━━━━━━━━━━━━━━━━━━┓*
*┃ ABOUT BOT* 
*┗━━━━━━━━━━━━━━━━━━━━┛*

╭───────────────────╮
│ 📱 *Number Info Bot* │
│ │
│ ✨ *Features:* │
│ • Mobile number lookup │
│ • Credit system │
│ • Premium users │
│ • Daily free credits │
│ │
│ 📱 *How to use:* │
│ Send any mobile number │
╰───────────────────╯

━━━━━━━━━━━━━━━━
👨‍💻 *Developer:* {DEV_TAG}

*Commands:*
/start - Start bot
/admin - Admin panel"""
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mobile = update.message.text.strip()
    
    if not re.match(r'^\+?\d{10,15}$', mobile):
        await update.message.reply_text("❌ *Invalid number!*\nSend 10-15 digits.\nExample: `9720294892`", parse_mode=ParseMode.MARKDOWN)
        return
    
    user_data = get_user(user_id)
    if not user_data:
        create_user(user_id, update.effective_user.username, update.effective_user.first_name)
        user_data = get_user(user_id)
    
    if not user_data[4] and user_data[3] <= 0:
        await update.message.reply_text(f"""❌ *Insufficient Credits!*

╭───────────────────╮
│ ⭐ *Credits:* {user_data[3]} │
│ 💎 *Upgrade to Premium* │
│   for unlimited searches! │
╰───────────────────╯

Contact admin or wait for daily reset.

━━━━━━━━━━━━━━━━
👨‍💻 {DEV_TAG}""", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Send typing indicator
    await update.message.chat.send_action("typing")
    
    # Fetch data
    data = await fetch_number_info(mobile)
    
    if data:
        # Deduct credit
        if not user_data[4]:
            update_credit(user_id, -1)
        
        # Format response
        response = format_response(data, mobile)
        
        # Add credits info
        credits = user_data[3] - 1 if not user_data[4] else "♾️"
        response += f"\n\n╭───────────────────╮\n"
        response += f"│ ⭐ *Credits:* {credits} │"
        if user_data[4]:
            response += f" (✨ Premium) │"
        response += f"\n╰───────────────────╯\n"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"""❌ *Error fetching data!*

Please try again later.

━━━━━━━━━━━━━━━━
👨‍💻 {DEV_TAG}""", parse_mode=ParseMode.MARKDOWN)

# ADMIN
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ *Access Denied!*")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 All Users", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("➕ Add Credits", callback_data="admin_credits")],
        [InlineKeyboardButton("💎 Premium Management", callback_data="admin_premium")]
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
        if not users:
            await query.edit_message_text("❌ No users found!")
            return
        msg = "👥 *┏━━━━━━━━━━━━━━━━━━━━┓*\n*┃ ALL USERS* \n*┗━━━━━━━━━━━━━━━━━━━━┛*\n\n"
        for u in users[:20]:
            msg += f"╭───────────────────╮\n"
            msg += f"│ 👤 *{u[2]}*\n"
            msg += f"│ ├ ID: `{u[0]}`\n"
            msg += f"│ ├ Credits: {u[3]}\n"
            msg += f"│ ├ Premium: {'✅' if u[4] else '❌'}\n"
            msg += f"│ └ Searches: {u[5]}\n"
            msg += f"╰───────────────────╯\n\n"
        msg += f"━━━━━━━━━━━━━━━━\n*Total:* {len(users)} users\n\n👨‍💻 {DEV_TAG}"
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == "admin_stats":
        users = get_all_users()
        total = len(users)
        premium = sum(1 for u in users if u[4])
        searches = sum(u[5] for u in users)
        credits = sum(u[3] for u in users)
        msg = f"""📊 *┏━━━━━━━━━━━━━━━━━━━━┓*
*┃ BOT STATISTICS* 
*┗━━━━━━━━━━━━━━━━━━━━┛*

╭───────────────────╮
│ 👥 *Users:* {total} │
│ 💎 *Premium:* {premium} │
│ 🔍 *Searches:* {searches} │
│ ⭐ *Credits:* {credits} │
╰───────────────────╯

━━━━━━━━━━━━━━━━
👨‍💻 {DEV_TAG}"""
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == "admin_credits":
        msg = f"""💰 *Add Credits*

Use command:
`/addcredits [user_id] [amount]`

Example:
`/addcredits 123456789 10`

━━━━━━━━━━━━━━━━
👨‍💻 {DEV_TAG}"""
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == "admin_premium":
        msg = f"""💎 *Premium Management*

Use command:
`/premium [user_id] [on/off]`

Example:
`/premium 123456789 on`
`/premium 123456789 off`

━━━━━━━━━━━━━━━━
👨‍💻 {DEV_TAG}"""
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

async def add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Usage: `/addcredits user_id amount`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        user_id, amount = int(args[0]), int(args[1])
        if get_user(user_id):
            update_credit(user_id, amount)
            await update.message.reply_text(f"✅ *Added {amount} credits* to user `{user_id}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ User not found!")
    except:
        await update.message.reply_text("❌ Invalid input!")

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Usage: `/premium user_id on/off`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        user_id, status = int(args[0]), args[1].lower()
        if status == "on":
            set_premium(user_id, 1)
            await update.message.reply_text(f"✅ *Premium enabled* for user `{user_id}`", parse_mode=ParseMode.MARKDOWN)
        elif status == "off":
            set_premium(user_id, 0)
            await update.message.reply_text(f"❌ *Premium disabled* for user `{user_id}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Use 'on' or 'off'")
    except:
        await update.message.reply_text("❌ Invalid input!")

async def reset_credits():
    while True:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET credit = 5 WHERE is_premium = 0")
        conn.commit()
        conn.close()
        logging.info("✅ Daily credits reset")
        await asyncio.sleep(86400)

# MAIN
def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("🤖 Starting Number Info Bot...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addcredits", add_credits))
    app.add_handler(CommandHandler("premium", premium))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(stats_callback, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(about_callback, pattern="^about$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    
    # Daily reset
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(reset_credits())
    
    logging.info("✅ Bot Started Successfully!")
    app.run_polling()

if __name__ == "__main__":
    main()
