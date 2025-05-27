# -*- coding: utf-8 -*-
"""Basic structure for the Telegram Payment Bot, adapted for Render deployment."""

import logging
import requests
import json
import os # Import os module to access environment variables
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIGURATION (Read from Environment Variables or use defaults/placeholders) ---
TELEGRAM_BOT_TOKEN = os.environ.get("8051340678:AAGodiGyqjoAdYWYmDX9y8u_WsLQJnFEcBg")
PUSHINPAY_API_TOKEN = os.environ.get("31014|qWDjQVC0rw67nV87BO8LQjMFppkFZ6B0kGeKeV7pd2707f3b")
PUSHINPAY_API_ENDPOINT = os.environ.get("PUSHINPAY_API_ENDPOINT", "https://api.pushinpay.com/pix/cashin") # Default endpoint
VIDEO_FILE_PATH = os.environ.get("VIDEO_FILE_PATH", "/path/to/your/video.mp4") # Default placeholder path
FINAL_LINK = os.environ.get("FINAL_LINK", "https://descubratudo.site/vipsim2/") # Default placeholder link

# --- Check if essential tokens are set ---
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN set for bot. Set the environment variable.")
if not PUSHINPAY_API_TOKEN:
    raise ValueError("No PUSHINPAY_API_TOKEN set. Set the environment variable.")

# Initial text message (Lorem Ipsum placeholder)
INITIAL_TEXT = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. 
Escolha seu plano abaixo:
"""

# Plan details (Name, Price, Callback Data)
PLANS = [
    {"name": "💞SEMANAL💞", "price": 11.99, "callback": "plan_semanal"},
    {"name": "🧨MENSAL + FLAGRAS🧨", "price": 15.99, "callback": "plan_mensal"},
    {"name": "🌈ALUNAS BRUTAIS🌈", "price": 29.99, "callback": "plan_brutais"},
    {"name": "💣ETERNO💣", "price": 49.90, "callback": "plan_eterno"},
]

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the initial message with video and plan buttons when /start is issued."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")

    keyboard = []
    for plan in PLANS:
       button_text = f"{plan['name']} - R$ {plan['price']:.2f}".replace(".", ",")
        keyboard.append([InlineKeyboardButton(button_text, callback_data=plan["callback"])])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Check if video file exists before trying to open it
        if os.path.exists(VIDEO_FILE_PATH):
             await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=open(VIDEO_FILE_PATH, "rb"),
                caption=INITIAL_TEXT,
                reply_markup=reply_markup,
                read_timeout=120,
                write_timeout=120
            )
             logger.info(f"Sent video and plan buttons to user {user.id}")
        else:
            logger.warning(f"Video file not found at {VIDEO_FILE_PATH}. Sending text message only.")
            await update.message.reply_text(
                f"(Vídeo não configurado ou não encontrado.)\n\n{INITIAL_TEXT}",
                reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Error sending video/message in start handler: {e}")
        # Avoid sending detailed error messages to the user in production
        await update.message.reply_text(
            f"Ocorreu um erro ao iniciar. Por favor, tente novamente mais tarde."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button presses (plan selection and 'Já paguei')."""
    query = update.callback_query
    await query.answer()  # Answer callback query to stop the loading icon

    user_id = query.from_user.id
    callback_data = query.data
    logger.info(f"User {user_id} clicked button with data: {callback_data}")

    selected_plan = next((plan for plan in PLANS if plan["callback"] == callback_data), None)

    if selected_plan:
        # --- Call PushinPay API to generate Pix --- 
        plan_name = selected_plan["name"]
        plan_price = selected_plan["price"]
        logger.info(f"User {user_id} selected plan: {plan_name} (R$ {plan_price:.2f})")

        payload = {
            "value": plan_price,
            # Add other required parameters based on PushinPay docs
        }
        headers = {
            "Authorization": f"Bearer {PUSHINPAY_API_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(PUSHINPAY_API_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            payment_data = response.json()
            logger.info(f"PushinPay API response for user {user_id}: {payment_data}")

            pix_code = payment_data.get("pix_code", "CODIGO_PIX_NAO_ENCONTRADO")

            message_text = (
                f"Pagamento gerado com sucesso!\n\n"
                f"👉 Plano: {plan_name}\n"
                f"👉 Valor: R$ {plan_price:.2f}\n"
                f"👉 O código pix expira em 10 minutos.\n\n"
                f"Dê um clique abaixo para copiar o codigo 👇\n\n"
                f"`{pix_code}`\n\n"
                f"Após realizar o pagamento, clique em Já paguei para ter o seu acesso."
            )

            keyboard = [[InlineKeyboardButton("Copiar Código Pix", switch_inline_query=pix_code)],
                        [InlineKeyboardButton("✅ Já paguei ✅", callback_data=f"paid_{callback_data}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode="Markdown")
            logger.info(f"Sent Pix code for plan {plan_name} to user {user_id}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling PushinPay API for user {user_id}: {e}")
            await query.edit_message_text(text=f"❌ Erro ao gerar o pagamento Pix para o plano {plan_name}. Tente novamente mais tarde.")
        except Exception as e:
             logger.error(f"Generic error processing plan selection for user {user_id}: {e}")
             await query.edit_message_text(text=f"❌ Ocorreu um erro inesperado ao processar sua solicitação para o plano {plan_name}. Tente novamente.")

    elif callback_data.startswith("paid_"):
        original_plan_callback = callback_data.replace("paid_", "")
        logger.info(f"User {user_id} clicked 'Já paguei' for plan {original_plan_callback}")

        # --- Check Payment Status (Placeholder/Basic Logic) --- 
        # IMPLEMENT REAL PAYMENT CHECK HERE (API Call or Webhook)
        is_paid = True # Placeholder

        if is_paid:
            logger.info(f"Payment confirmed (simulated) for user {user_id}, plan {original_plan_callback}. Sending final link.")
            await query.edit_message_text(
                text=f"Pagamento confirmado! 🎉\n\nAqui está o seu acesso:\n{FINAL_LINK}"
            )
        else:
            logger.warning(f"Payment not confirmed (simulated) for user {user_id}, plan {original_plan_callback}.")
            await query.edit_message_text(
                text="Ainda não identificamos o seu pagamento. Por favor, aguarde alguns instantes e tente novamente.",
                reply_markup=query.message.reply_markup
            )

    else:
        logger.warning(f"Received unknown callback data: {callback_data} from user {user_id}")
        await query.edit_message_text(text="Opção inválida.")


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).read_timeout(30).write_timeout(30).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    logger.info("Starting bot polling...")
    application.run_polling()

if __name__ == "__main__":
    main()

