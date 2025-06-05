import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import database
from dotenv import load_dotenv

# Load .env (optional if you want to hide token)
load_dotenv()
TOKEN = "7781487236:AAEeIri2Gy342_GTheWafFEhpX5jVX92DLA"

# States
(
    REGISTER_START,
    REGISTER_EMAIL,
    REGISTER_PASSWORD,
    REGISTER_REFERRAL,
    LOGIN_EMAIL,
    LOGIN_PASSWORD,
    MAIN_MENU,
    VIEW_BALANCE
) = range(8)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [['Register', 'Login']]
    await update.message.reply_text(
        'Welcome! Please choose an option:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return REGISTER_START

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == 'Register':
        await update.message.reply_text('Please enter your email:')
        return REGISTER_EMAIL
    elif choice == 'Login':
        await update.message.reply_text('Please enter your email for login:')
        return LOGIN_EMAIL
    else:
        await update.message.reply_text('Invalid option. Please choose Register or Login.')
        return REGISTER_START

# ----------- Register Flow -----------

async def register_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['email'] = update.message.text
    await update.message.reply_text('Please create a password:')
    return REGISTER_PASSWORD

async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['password'] = update.message.text
    await update.message.reply_text('Please enter a referral code (or type "none" if you dont have one):')
    return REGISTER_REFERRAL

async def register_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    referral_code = update.message.text
    referred_by = None
    if referral_code.lower() != 'none':
        if not database.get_user_by_referral(referral_code):
            await update.message.reply_text('❌ Invalid referral code. Please try again or type "none".')
            return REGISTER_REFERRAL
        referred_by = referral_code

    email = context.user_data['email']
    password = context.user_data['password']
    referral_number, error = database.register_user(email, password, referred_by)
    if referral_number:
        await update.message.reply_text(f'✅ Registration successful!\nYour referral code is: `{referral_number}`\n💰 You received 2 botcoin!', parse_mode="Markdown")
        return ConversationHandler.END
    else:
        await update.message.reply_text(f'❌ Registration failed: {error}. Try a different email.')
        return REGISTER_EMAIL

# ----------- Login Flow -----------

async def login_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['email'] = update.message.text
    await update.message.reply_text('Please enter your password:')
    return LOGIN_PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = context.user_data['email']
    password = update.message.text
    user = database.login_user(email, password)
    if user:
        referral_number = user.get('referral_number', 'N/A')
        bitcoin_balance = user.get('bitcoin_balance', 0)
        
        reply_keyboard = [['View Balance', 'View Referral Code']]
        await update.message.reply_text(
            f"✅ Login successful!\n"
            f"Your referral code is: `{referral_number}`\n"
            f"💰 Current Bitcoin Balance: {bitcoin_balance} botcoin\n\n"
            f"What would you like to do?",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        context.user_data['current_user'] = user
        return MAIN_MENU
    else:
        await update.message.reply_text("❌ Login failed. Invalid credentials.")
        return ConversationHandler.END

# ----------- Main Menu -----------

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    user = context.user_data.get('current_user')
    
    if choice == 'View Balance':
        # Get updated balance from database
        updated_user = database.get_user_by_email(user['email'])
        bitcoin_balance = updated_user.get('bitcoin_balance', 0)
        await update.message.reply_text(f"💰 Your current Bitcoin balance: {bitcoin_balance} botcoin\n\nThank you! Use /start to begin again.")
        return ConversationHandler.END
        
    elif choice == 'View Referral Code':
        referral_code = user.get('referral_number', 'N/A')
        await update.message.reply_text(f"🔗 Your referral code: `{referral_code}`\n\nShare this code with friends to earn rewards!\n\nThank you! Use /start to begin again.", parse_mode="Markdown")
        return ConversationHandler.END
    
    else:
        await update.message.reply_text('Invalid option. Please choose "View Balance" or "View Referral Code".')
        reply_keyboard = [['View Balance', 'View Referral Code']]
        await update.message.reply_text(
            "What would you like to do?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return MAIN_MENU

# ----------- Cancel -----------

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('❌ Operation cancelled.')
    return ConversationHandler.END

# ----------- Main Function -----------

def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REGISTER_START: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_start),
                CommandHandler('start', start)  # Allow /start to restart
            ],
            REGISTER_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_email),
                CommandHandler('start', start)  # Allow /start to restart
            ],
            REGISTER_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_password),
                CommandHandler('start', start)  # Allow /start to restart
            ],
            REGISTER_REFERRAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_referral),
                CommandHandler('start', start)  # Allow /start to restart
            ],
            LOGIN_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, login_email),
                CommandHandler('start', start)  # Allow /start to restart
            ],
            LOGIN_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, login_password),
                CommandHandler('start', start)  # Allow /start to restart
            ],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu),
                CommandHandler('start', start)  # Allow /start to restart
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True  # Allow the conversation to be restarted
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()