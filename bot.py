import os
import json
import logging
import asyncio
import aiohttp
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Bot Configuration
BOT_TOKEN = "8691956766:AAGZ58LARMbNdw_JJtUxMWKiuexV3WPTFf4"
API_URL = "https://numtolnfo.suryajasoos-4fe.workers.dev/?mobile={}"
ADMIN_IDS = [5481125164, 9720294892]
DEV_TAG = "@dinamicshai"

# Database Setup
DB_PATH = os.path.join(os.path.dirname(__file__), "user_data.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT, 
                  first_name TEXT, 
                  last_name TEXT,
                  credit INTEGER DEFAULT 5,
                  is_premium INTEGER DEFAULT 0,
                  search_count INTEGER DEFAULT 0,
                  total_searches INTEGER DEFAULT 0,
                  last_search_time TIMESTAMP,
                  joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS search_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  mobile_number TEXT,
                  search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  admin_id INTEGER,
                  action TEXT,
                  target_user_id INTEGER,
                  details TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Database Functions
def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username=None, first_name=None, last_name=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (user_id, username, first_name, last_name, credit) VALUES (?, ?, ?, ?, 5)",
                  (user_id, username, first_name, last_name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_credit(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credit = credit + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def set_premium(user_id, premium_status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_premium = ? WHERE user_id = ?", (premium_status, user_id))
    conn.commit()
    conn.close()

def add_search_history(user_id, mobile):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO search_history (user_id, mobile_number) VALUES (?, ?)", (user_id, mobile))
    c.execute("UPDATE users SET search_count = search_count + 1, total_searches = total_searches + 1, last_search_time = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT search_count, total_searches, credit, is_premium, joined_date, last_search_time FROM users WHERE user_id = ?", (user_id,))
    stats = c.fetchone()
    conn.close()
    return stats

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, last_name, credit, is_premium, total_searches FROM users ORDER BY total_searches DESC")
    users = c.fetchall()
    conn.close()
    return users

# API Function
async def fetch_number_info(mobile):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL.format(mobile), timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                return None
    except Exception as e:
        logging.error(f"API Error: {e}")
        return None

# Bot Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if not get_user(user_id):
        create_user(user_id, user.username, user.first_name, user.last_name)
        welcome_msg = f"""🎉 *Welcome to NumberInfo Bot!* 🎉

👋 Hello {user.first_name}!

✨ *You've received 5 FREE credits* to get started!
🔍 Each search costs 1 credit

📱 *How to use:*
Simply send me any mobile number to get detailed information

💎 *Premium Features:*
• Unlimited searches
• Faster response time
• Priority support

{DEV_TAG}

*Your Credits:* 5 ⭐"""
    else:
        user_data = get_user(user_id)
        welcome_msg = f"""👋 *Welcome back, {user.first_name}!*

📊 *Your Stats:*
┌ Credits: {user_data[3]} ⭐
├ Premium: {'✅ Active' if user_data[4] else '❌ Inactive'}
├ Total Searches: {user_data[6]}
└ Last Search: {user_data[7] or 'Never'}

🔍 *Send any mobile number to search*

{DEV_TAG}"""
    
    keyboard = [
        [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        [InlineKeyboardButton("📞 About", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    stats_data = get_user_stats(user_id)
    
    if stats_data:
        stats_msg = f"""📊 *Your Statistics* 📊

👤 *User:* {query.from_user.first_name}
⭐ *Credits:* {stats_data[2]}
💎 *Premium:* {'✅ Yes' if stats_data[3] else '❌ No'}
🔍 *Today's Searches:* {stats_data[0]}
📈 *Total Searches:* {stats_data[1]}
📅 *Joined:* {stats_data[4]}
🕐 *Last Search:* {stats_data[5] or 'Never'}

{DEV_TAG}"""
    else:
        stats_msg = "⚠️ *User data not found!*"
    
    await query.edit_message_text(stats_msg, parse_mode=ParseMode.MARKDOWN)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    about_msg = f"""🤖 *About NumberInfo Bot*

This bot provides detailed information about any mobile number using our advanced API.

✨ *Features:*
• Mobile number lookup
• User credit system
• Premium features
• Search history
• Admin controls

👨‍💻 *Developer:* {DEV_TAG}
📅 *Version:* 2.0

*Commands:*
/start - Start the bot
/stats - Check your stats
/help - Get help
/credits - Check credits

{DEV_TAG}"""
    
    await query.edit_message_text(about_msg, parse_mode=ParseMode.MARKDOWN)

async def check_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if user_data:
        credit_msg = f"""⭐ *Your Credits* ⭐

💰 *Available Credits:* {user_data[3]}
💎 *Premium Status:* {'✅ Active' if user_data[4] else '❌ Inactive'}

*How to get more credits:*
• Daily free: 5 credits (resets daily)
• Premium users get unlimited searches
• Contact admin for bulk credits

{DEV_TAG}"""
    else:
        credit_msg = "⚠️ *User not found! Please use /start first.*"
    
    await update.message.reply_text(credit_msg, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_msg = f"""🤖 *Help Center* 🤖

📱 *Basic Commands:*
/start - Start the bot
/stats - View your statistics
/credits - Check your credits
/help - Show this help message

🔍 *How to Search:*
Simply send any mobile number in this format:
`9720294892` or `+9720294892`

💎 *Premium Benefits:*
• Unlimited searches
• Priority support
• Advanced features

💰 *Credit System:*
• 1 credit = 1 search
• Daily 5 free credits
• Premium = unlimited

👨‍💻 *Contact Admin:*
Use /admin for support

{DEV_TAG}"""
    
    await update.message.reply_text(help_msg, parse_mode=ParseMode.MARKDOWN)

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mobile = update.message.text.strip()
    
    import re
    if not re.match(r'^\+?\d{10,15}$', mobile):
        await update.message.reply_text("❌ *Invalid mobile number!*\nPlease send a valid 10-15 digit number.\n\nExample: `9720294892`", parse_mode=ParseMode.MARKDOWN)
        return
    
    user_data = get_user(user_id)
    if not user_data:
        create_user(user_id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name)
        user_data = get_user(user_id)
    
    if not user_data[4] and user_data[3] <= 0:
        await update.message.reply_text(
            f"❌ *Insufficient Credits!*\n\n"
            f"⭐ Current credits: {user_data[3]}\n"
            f"💎 *Upgrade to Premium:* Unlimited searches!\n"
            f"Contact admin or wait for daily free credits.\n\n"
            f"{DEV_TAG}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await update.message.chat.send_action(action="typing")
    
    api_data = await fetch_number_info(mobile)
    
    if api_data:
        if not user_data[4]:
            update_credit(user_id, -1)
        
        add_search_history(user_id, mobile)
        
        response = f"""📱 *Mobile Number Information* 📱

*Number:* `{mobile}`

📊 *Details:*
"""
        
        if isinstance(api_data, dict):
            for key, value in api_data.items():
                if value:
                    response += f"┌ *{key.replace('_', ' ').title()}*: {value}\n"
        elif isinstance(api_data, list):
            for item in api_data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if value:
                            response += f"┌ *{key.replace('_', ' ').title()}*: {value}\n"
                else:
                    response += f"┌ {item}\n"
        else:
            response += f"┌ {api_data}\n"
        
        remaining_credits = user_data[3] - 1 if not user_data[4] else "♾️"
        response += f"\n*Credits Left:* {remaining_credits} ⭐"
        if user_data[4]:
            response += " (Premium)"
        
        response += f"\n\n{DEV_TAG}"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(
            f"❌ *Error fetching data!*\n\n"
            f"Please try again later or contact support.\n\n"
            f"{DEV_TAG}",
            parse_mode=ParseMode.MARKDOWN
        )

# Admin Commands
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ *Access Denied!*\nYou are not authorized to use admin commands.", parse_mode=ParseMode.MARKDOWN)
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 All Users", callback_data="admin_users")],
        [InlineKeyboardButton("➕ Add Credits", callback_data="admin_add_credits")],
        [InlineKeyboardButton("💎 Manage Premium", callback_data="admin_premium")],
        [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📝 Admin Logs", callback_data="admin_logs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔐 *Admin Panel* 🔐\n\n"
        f"Welcome to the admin control panel.\n"
        f"Select an option below:\n\n"
        f"{DEV_TAG}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ *Access Denied!*", parse_mode=ParseMode.MARKDOWN)
        return
    
    action = query.data
    
    if action == "admin_users":
        users = get_all_users()
        if users:
            msg = "👥 *All Users* 👥\n\n"
            for i, user in enumerate(users[:20], 1):
                username = f"@{user[1]}" if user[1] else "No username"
                msg += f"{i}. {user[2] or 'Unknown'} {username}\n"
                msg += f"   Credits: {user[4]} | Premium: {'✅' if user[5] else '❌'} | Searches: {user[6]}\n\n"
            msg += f"\n{DEV_TAG}"
            await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
        else:
            await query.edit_message_text("❌ *No users found!*", parse_mode=ParseMode.MARKDOWN)
    
    elif action == "admin_add_credits":
        await query.edit_message_text(
            f"💰 *Add Credits* 💰\n\n"
            f"To add credits to a user, use the command:\n"
            f"`/addcredits [user_id] [amount]`\n\n"
            f"Example: `/addcredits 123456789 10`\n\n"
            f"{DEV_TAG}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif action == "admin_premium":
        await query.edit_message_text(
            f"💎 *Premium Management* 💎\n\n"
            f"To manage premium status, use:\n"
            f"`/premium [user_id] [on/off]`\n\n"
            f"Example: `/premium 123456789 on`\n"
            f"Example: `/premium 123456789 off`\n\n"
            f"{DEV_TAG}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif action == "admin_stats":
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT SUM(total_searches) FROM users")
        total_searches = c.fetchone()[0] or 0
        c.execute("SELECT SUM(credit) FROM users")
        total_credits = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
        premium_users = c.fetchone()[0]
        conn.close()
        
        msg = f"📊 *Bot Statistics* 📊\n\n"
        msg += f"👥 Total Users: {total_users}\n"
        msg += f"💎 Premium Users: {premium_users}\n"
        msg += f"🔍 Total Searches: {total_searches}\n"
        msg += f"⭐ Total Credits: {total_credits}\n\n"
        msg += f"{DEV_TAG}"
        
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    elif action == "admin_logs":
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT 10")
        logs = c.fetchall()
        conn.close()
        
        if logs:
            msg = "📝 *Recent Admin Logs* 📝\n\n"
            for log in logs:
                msg += f"🔹 {log[4]}: Admin {log[1]} → User {log[3]}\n"
                msg += f"   {log[5]}\n\n"
            msg += f"{DEV_TAG}"
            await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
        else:
            await query.edit_message_text("❌ *No logs found!*", parse_mode=ParseMode.MARKDOWN)

async def add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ *Access Denied!*", parse_mode=ParseMode.MARKDOWN)
        return
    
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ *Invalid format!*\n\n"
            "Usage: `/addcredits [user_id] [amount]`\n"
            "Example: `/addcredits 123456789 10`\n\n"
            f"{DEV_TAG}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_user = int(args[0])
        amount = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ *Invalid user ID or amount!*", parse_mode=ParseMode.MARKDOWN)
        return
    
    if get_user(target_user):
        update_credit(target_user, amount)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO admin_logs (admin_id, action, target_user_id, details) VALUES (?, ?, ?, ?)",
                  (user_id, "add_credits", target_user, f"Added {amount} credits"))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ *Credits Added Successfully!*\n\n"
            f"User ID: `{target_user}`\n"
            f"Amount: +{amount} credits\n\n"
            f"{DEV_TAG}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("❌ *User not found!*", parse_mode=ParseMode.MARKDOWN)

async def manage_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ *Access Denied!*", parse_mode=ParseMode.MARKDOWN)
        return
    
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ *Invalid format!*\n\n"
            "Usage: `/premium [user_id] [on/off]`\n"
            "Example: `/premium 123456789 on`\n"
            "Example: `/premium 123456789 off`\n\n"
            f"{DEV_TAG}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_user = int(args[0])
        status = args[1].lower()
    except ValueError:
        await update.message.reply_text("❌ *Invalid user ID!*", parse_mode=ParseMode.MARKDOWN)
        return
    
    if status == "on":
        premium_status = 1
        action_desc = "Enabled premium"
    elif status == "off":
        premium_status = 0
        action_desc = "Disabled premium"
    else:
        await update.message.reply_text("❌ *Invalid status! Use 'on' or 'off'.*", parse_mode=ParseMode.MARKDOWN)
        return
    
    if get_user(target_user):
        set_premium(target_user, premium_status)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO admin_logs (admin_id, action, target_user_id, details) VALUES (?, ?, ?, ?)",
                  (user_id, "manage_premium", target_user, action_desc))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ *Premium Status Updated!*\n\n"
            f"User ID: `{target_user}`\n"
            f"Status: {'✅ Premium' if premium_status else '❌ Normal'}\n\n"
            f"{DEV_TAG}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("❌ *User not found!*", parse_mode=ParseMode.MARKDOWN)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ *Access Denied!*", parse_mode=ParseMode.MARKDOWN)
        return
    
    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text(
            "❌ *Please provide a message to broadcast!*\n\n"
            "Usage: `/broadcast [message]`\n"
            f"{DEV_TAG}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    users = get_all_users()
    sent_count = 0
    
    progress_msg = await update.message.reply_text("📤 *Broadcasting message...*", parse_mode=ParseMode.MARKDOWN)
    
    for user in users:
        try:
            await context.bot.send_message(chat_id=user[0], text=f"📢 *Announcement* 📢\n\n{message}\n\n{DEV_TAG}", parse_mode=ParseMode.MARKDOWN)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"Failed to send to {user[0]}: {e}")
    
    await progress_msg.edit_text(
        f"✅ *Broadcast Complete!*\n\n"
        f"Message sent to: {sent_count} users\n"
        f"Total users: {len(users)}\n\n"
        f"{DEV_TAG}",
        parse_mode=ParseMode.MARKDOWN
    )

async def reset_daily_credits():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credit = 5 WHERE is_premium = 0")
    c.execute("UPDATE users SET search_count = 0")
    conn.commit()
    conn.close()
    logging.info("✅ Daily credits reset completed")

async def daily_credit_reset():
    while True:
        now = datetime.now()
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        sleep_time = (next_reset - now).total_seconds()
        await asyncio.sleep(sleep_time)
        await reset_daily_credits()

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info("🤖 Starting NumberInfo Bot...")
    
    # Create bot application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("credits", check_credits))
    app.add_handler(CommandHandler("help", help_command))
    
    # Admin commands
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addcredits", add_credits))
    app.add_handler(CommandHandler("premium", manage_premium))
    app.add_handler(CommandHandler("broadcast", broadcast))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(about, pattern="^about$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    
    # Start daily credit reset in background
    loop = asyncio.get_event_loop()
    loop.create_task(daily_credit_reset())
    
    logging.info("🚀 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
