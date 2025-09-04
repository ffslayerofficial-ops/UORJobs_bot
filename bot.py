import os
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
    ConversationHandler,
)
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# Import our custom modules
import database as db
import jobs
import ai_parser
import payments

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Conversation Handler States for Daily Alerts ---
GETTING_KEYWORD, GETTING_LOCATION, GETTING_SALARY = range(3)


# --- Standard Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    user = update.effective_user
    db.add_user(user.id)
    welcome_message = (
        f"👋 **Welcome to UOR Job Bot, {user.first_name}!**\n\n"
        "I'm your intelligent career assistant. Just tell me what you're looking for!\n\n"
        "**Example:** `find me remote software engineer jobs`\n\n"
        "**Top Features:**\n"
        "🧠 **Smart Search:** I understand natural language.\n"
        "📅 **Daily Alerts:** Get custom job alerts every morning with `/daily`.\n"
        "💎 **Lifetime Premium:** Unlock unlimited features with `/premium`.\n\n"
        "Type /help to see all commands."
    )
    await update.message.reply_markdown(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the /help command is issued."""
    help_text = (
        "**Here's how I can help you:**\n\n"
        "**Job Searching**\n"
        "To search for a job, just send me a message with what you want. For example:\n"
        "- `data science internships in bangalore`\n"
        "- `work from home python developer jobs`\n\n"
        "**Commands**\n"
        "/start - Welcome message\n"
        "/daily - Set up a conversational daily job alert\n"
        "/stop - Unsubscribe from daily job alerts\n"
        "/premium - Upgrade to a Lifetime Premium account\n"
        "/help - Shows this message"
    )
    await update.message.reply_markdown(help_text)

# --- Daily Alert Conversation Functions ---

async def daily_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation for setting a daily alert."""
    await update.message.reply_text(
        "Of course! I can set up a daily job alert for you.\n\n"
        "What kind of job or skill are you looking for? (e.g., 'Software Engineer' or 'Python')"
    )
    return GETTING_KEYWORD

async def get_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the job keyword and asks for the location."""
    user_keyword = update.message.text
    context.user_data['daily_keyword'] = user_keyword
    await update.message.reply_text(
        f"Great, '{user_keyword}'. Now, where should I look for this job?\n\n"
        "You can give me a city name or simply say 'remote'."
    )
    return GETTING_LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for the minimum salary."""
    user_location = update.message.text
    context.user_data['daily_location'] = user_location
    await update.message.reply_text(
        f"Okay, I'll search in '{user_location}'.\n\n"
        "What is the minimum annual salary (in ₹) you're looking for? (e.g., 800000).\n\n"
        "Type **0** if you don't want to filter by salary.",
        parse_mode='Markdown'
    )
    return GETTING_SALARY

async def get_salary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores salary, saves everything to DB, and ends conversation."""
    try:
        min_salary = int(update.message.text.replace(',', ''))
    except ValueError:
        await update.message.reply_text("That doesn't look like a valid number. Please enter the salary again (e.g., 500000).")
        return GETTING_SALARY

    keyword = context.user_data['daily_keyword']
    location = context.user_data['daily_location']
    user_id = update.effective_user.id

    db.subscribe_user(user_id, keyword, location, min_salary)
    salary_text = f"with a minimum salary of ₹{min_salary:,}" if min_salary > 0 else "with no salary preference"
    
    await update.message.reply_text(
        "Perfect! Your alert is all set up. I will search for "
        f"<b>{keyword}</b> jobs in <b>{location}</b> {salary_text}.\n\n"
        "You can change this anytime by running /daily again.",
        parse_mode='HTML'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def stop_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    context.user_data.clear()
    await update.message.reply_text("Okay, I've cancelled the setup.")
    return ConversationHandler.END


# --- Premium & Payment Functions ---

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain premium features and provide a payment button for Lifetime access."""
    premium_message = (
        "<b>Go Premium for LIFE!</b>\n\n"
        "For a one-time payment, unlock the best features forever.\n\n"
        "💎 **Premium Plan (Lifetime):**\n"
        "  - Unlimited intelligent job searches\n"
        "  - Up to 5 daily alerts with salary filters\n"
        "  - Job Match Score™ to see job relevance\n"
        "  - Early access to exclusive listings (coming soon)\n\n"
        "<b>Special Offer:</b> Just <b>₹79</b> for Lifetime Access!\n\n"
        "Click below to get instant premium access forever."
    )
    keyboard = [[InlineKeyboardButton("Pay ₹79 for Lifetime Access", callback_data='start_payment')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(premium_message, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline button callbacks for payments."""
    query = update.callback_query
    await query.answer()

    if query.data == 'start_payment':
        user_id = query.from_user.id
        await query.message.reply_text("Generating your secure payment link...")
        payment_url = payments.create_payment_link(user_id)
        
        if payment_url:
            keyboard = [[InlineKeyboardButton("Click Here to Pay Securely", url=payment_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "Your payment link is ready. You will be upgraded automatically after payment.",
                reply_markup=reply_markup
            )
        else:
            await query.message.reply_text("Sorry, we couldn't create a payment link. Please try again later.")


# --- Core Bot Logic ---

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unsubscribe user from all daily alerts."""
    user_id = update.effective_user.id
    db.unsubscribe_user(user_id)
    await update.message.reply_text("You have been unsubscribed from all daily job alerts.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all non-command text messages for intelligent job searching."""
    user_id = update.effective_user.id
    user_query = update.message.text
    
    db.add_user(user_id)
    user_data = db.get_user(user_id)

    if user_data.get("premium_status", "free") == "free":
        today = datetime.now().date().isoformat()
        if user_data.get("last_search_date") == today and user_data.get("searches_today", 0) >= 3:
            await update.message.reply_text(
                "You have reached your daily search limit. Upgrade to /premium for unlimited searches."
            )
            return
        db.update_search_count(user_id)
        
    await update.message.reply_text("🧠 Understanding your request...")

    try:
        parsed_data = ai_parser.parse_query_with_ai(user_query)
        keywords = parsed_data.get("keywords", user_query)
        location = parsed_data.get("location", "any")

        await update.message.reply_text(f"🔍 Searching for '{keywords}' jobs in '{location}'...")
        job_listings = await jobs.fetch_jobs(keywords, location)

        if not job_listings:
            await update.message.reply_text("No jobs found for your search criteria.")
            return

        for job in job_listings:
            analysis = ai_parser.get_job_match_score(user_query, job.get('description', ''))
            score = analysis.get('score', 'N/A')
            reason = analysis.get('reason', '')

            message = (
                f"<b>Job Title:</b> {job['title']}\n"
                f"<b>Company:</b> {job['company']}\n"
                f"<b>Location:</b> {job['location']}\n"
                f"<b>✨ Match Score™: {score}/100</b>\n"
                f"<i>Reason: {reason}</i>"
            )
            if job.get('salary'):
                message += f"\n<b>Salary:</b> {job['salary']}"

            keyboard = [[InlineKeyboardButton("Apply Now", url=job['link'])]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_html(message, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in intelligent search: {e}")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")

async def send_daily_jobs(application: Application):
    """Fetches and sends daily job alerts to all subscribed users."""
    subscribed_users = db.get_subscribed_users()
    logger.info(f"Running daily job alert for {len(subscribed_users)} users.")

    for user in subscribed_users:
        user_id, keyword, location, min_salary = user
        try:
            job_listings = await jobs.fetch_jobs(keyword, location)
            if job_listings:
                await application.bot.send_message(user_id, f"☀️ Good morning! Here are your daily job alerts for '{keyword}':")
                for job in job_listings:
                    message = (
                        f"<b>Job Title:</b> {job['title']}\n"
                        f"<b>Company:</b> {job['company']}\n"
                        f"<b>Location:</b> {job['location']}\n"
                    )
                    if job.get('salary'):
                        message += f"<b>Salary:</b> {job['salary']}\n"
                    
                    keyboard = [[InlineKeyboardButton("Apply Now", url=job['link'])]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await application.bot.send_message(user_id, message, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to send daily jobs to {user_id}: {e}")


# --- Main Bot Setup and Execution ---

async def main() -> None:
    """Start the bot and all its components."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
        
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("daily", daily_start)],
        states={
            GETTING_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_keyword)],
            GETTING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
            GETTING_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_salary)],
        },
        fallbacks=[CommandHandler("stop", stop_conversation)],
    )

    # Add all handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("premium", premium))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Initialize database
    db.init_db()

    # Schedule daily job alerts
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(send_daily_jobs, 'cron', hour=9, minute=0, args=[application])
    scheduler.start()

    try:
        logger.info("Bot is starting...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await application.updater.stop()
        await application.stop()
        scheduler.shutdown()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    asyncio.run(main())