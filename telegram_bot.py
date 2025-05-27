# -*- coding: utf-8 -*-
"""Basic structure for the Telegram Payment Bot."""

import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIGURATION (Replace placeholders) ---
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Replace with your Telegram Bot Token
PUSHINPAY_API_TOKEN = "YOUR_PUSHINPAY_API_TOKEN"  # Replace with your PushinPay API Token
PUSHINPAY_API_ENDPOINT = "https://api.pushinpay.com/pix/cashin" # Check the correct endpoint in the documentation
VIDEO_FILE_PATH = "/path/to/your/video.mp4"  # Replace with the actual path to your video file
FINAL_LINK = "YOUR_FINAL_LINK_HERE"  # Replace with the link to send after payment

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
        button_text = f"{plan['name']} - R$ {plan['price']:.2f}".replace('.', ',')
        keyboard.append([InlineKeyboardButton(button_text, callback_data=plan['callback'])])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Send video (using placeholder path)
        # Make sure the bot has permission to read the file
        # You might need to adjust file sending based on size and Telegram limits
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=open(VIDEO_FILE_PATH, 'rb'),  # Use the placeholder path
            caption=INITIAL_TEXT, # Use placeholder text
            reply_markup=reply_markup,
            read_timeout=120, # Increase timeout for potentially large video files
            write_timeout=120
        )
        logger.info(f"Sent video and plan buttons to user {user.id}")
    except FileNotFoundError:
        logger.error(f"Video file not found at {VIDEO_FILE_PATH}. Sending text message instead.")
        await update.message.reply_text(
            f"(Erro: Vídeo não encontrado no caminho '{VIDEO_FILE_PATH}'. Configure o caminho correto.)\n\n{INITIAL_TEXT}",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error sending video/message in start handler: {e}")
        await update.message.reply_text(
            f"Ocorreu um erro ao iniciar. Por favor, tente novamente mais tarde. Detalhes: {e}"
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button presses (plan selection and 'Já paguei')."""
    query = update.callback_query
    await query.answer()  # Answer callback query to stop the loading icon

    user_id = query.from_user.id
    callback_data = query.data
    logger.info(f"User {user_id} clicked button with data: {callback_data}")

    selected_plan = next((plan for plan in PLANS if plan['callback'] == callback_data), None)

    if selected_plan:
        # --- Call PushinPay API to generate Pix --- 
        plan_name = selected_plan['name']
        plan_price = selected_plan['price']
        logger.info(f"User {user_id} selected plan: {plan_name} (R$ {plan_price:.2f})")

        # Prepare data for PushinPay API
        # Check PushinPay documentation for exact required fields and formats
        payload = {
            "value": plan_price,
            # "webhook_url": "YOUR_WEBHOOK_URL_HERE", # Optional: configure if needed for payment confirmation
            # "expires_at": "YYYY-MM-DD HH:MM:SS" # Optional: set expiration if needed
            # Add other required parameters like payer info if necessary
        }
        headers = {
            "Authorization": f"Bearer {PUSHINPAY_API_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            # Make the API call
            response = requests.post(PUSHINPAY_API_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            payment_data = response.json()
            logger.info(f"PushinPay API response for user {user_id}: {payment_data}")

            # --- Extract Pix Code and Expiration --- 
            # Adjust these lines based on the actual structure of the PushinPay API response
            pix_code = payment_data.get('pix_code', 'CODIGO_PIX_NAO_ENCONTRADO') # Example key
            # expires_info = payment_data.get('expires_at', 'N/A') # Example key
            # payment_id = payment_data.get('id', None) # Example key - Store this if needed for checking status

            # Store payment_id or relevant info in context.user_data if needed for 'Já paguei'
            # context.user_data[user_id] = {'payment_id': payment_id, 'plan': plan_name}

            # --- Send Pix Code to User --- 
            message_text = (
                f"Pagamento gerado com sucesso!\n\n"
                f"👉 Plano: {plan_name}\n"
                f"👉 Valor: R$ {plan_price:.2f}\n"
                # f"👉 O código pix expira em: {expires_info}\n\n"
                f"👉 O código pix expira em 10 minutos.\n\n" # Using example text as expiration wasn't explicitly in the provided example
                f"Dê um clique abaixo para copiar o codigo 👇\n\n"
                f"`{pix_code}`\n\n"
                f"Após realizar o pagamento, clique em Já paguei para ter o seu acesso."
            )

            keyboard = [[InlineKeyboardButton("Copiar Código Pix", switch_inline_query=pix_code)],
                        [InlineKeyboardButton("✅ Já paguei ✅", callback_data=f"paid_{callback_data}")]] # Add prefix to distinguish
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode='Markdown')
            logger.info(f"Sent Pix code for plan {plan_name} to user {user_id}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling PushinPay API for user {user_id}: {e}")
            await query.edit_message_text(text=f"❌ Erro ao gerar o pagamento Pix para o plano {plan_name}. Tente novamente mais tarde. Detalhes: {e}")
        except Exception as e:
             logger.error(f"Generic error processing plan selection for user {user_id}: {e}")
             await query.edit_message_text(text=f"❌ Ocorreu um erro inesperado ao processar sua solicitação para o plano {plan_name}. Tente novamente. Detalhes: {e}")

    elif callback_data.startswith("paid_"):
        # --- Handle 'Já paguei' button --- 
        original_plan_callback = callback_data.replace("paid_", "")
        # original_plan = next((plan for plan in PLANS if plan['callback'] == original_plan_callback), None)
        logger.info(f"User {user_id} clicked 'Já paguei' for plan {original_plan_callback}")

        # --- Check Payment Status (Placeholder/Basic Logic) --- 
        # Ideally, you should check the payment status via PushinPay API using a stored payment ID
        # or rely on a webhook notification from PushinPay.
        # This is a simplified version assuming payment is confirmed upon clicking.
        # payment_info = context.user_data.get(user_id)
        # if payment_info and payment_info['plan'] == original_plan['name']:
        #    payment_id_to_check = payment_info['payment_id']
        #    # Add API call here to check status of payment_id_to_check
        #    is_paid = check_pushinpay_status(payment_id_to_check) # Implement this function
        # else:
        #    is_paid = False # Or handle error

        # Placeholder: Assume payment is confirmed for now
        is_paid = True 

        if is_paid:
            logger.info(f"Payment confirmed (simulated) for user {user_id}, plan {original_plan_callback}. Sending final link.")
            await query.edit_message_text(
                text=f"Pagamento confirmado! 🎉\n\nAqui está o seu acesso:\n{FINAL_LINK}" # Use placeholder link
            )
            # Clean up user data if needed
            # if user_id in context.user_data:
            #     del context.user_data[user_id]
        else:
            logger.warning(f"Payment not confirmed (simulated) for user {user_id}, plan {original_plan_callback}.")
            await query.edit_message_text(
                text="Ainda não identificamos o seu pagamento. Por favor, aguarde alguns instantes e tente novamente. Se o problema persistir, entre em contato com o suporte.",
                reply_markup=query.message.reply_markup # Keep the buttons
            )

    else:
        logger.warning(f"Received unknown callback data: {callback_data} from user {user_id}")
        await query.edit_message_text(text="Opção inválida.")


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).read_timeout(30).write_timeout(30).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(CallbackQueryHandler(button_callback))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot polling...")
    application.run_polling()

if __name__ == "__main__":
    main()

