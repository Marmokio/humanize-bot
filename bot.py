import os
import threading
import telebot
from telebot import types
import random
import re
from flask import Flask

# --- 1. ФЕЙКОВЫЙ ВЕБ-СЕРВЕР (Чтобы Render не убивал бота) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    # Render сам подставит нужный порт (обычно 10000)
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. ТВОЙ ТОКЕН ---
TOKEN = '8749974375:AAF2d7iNYo22JZp1de0aMKmGkfdHDR2r0u8'
bot = telebot.TeleBot(TOKEN)

PAID_USERS = set()

REPLACEMENTS = {
    "является": "это", "осуществлять": "делать", "однако": "но",
    "представляет собой": "это", "в настоящее время": "сейчас",
    "функционирование": "работа", "использование": "применение",
    "в связи с тем, что": "потому что", "данный": "этот"
}
HUMAN_PHRASES = ["Честно говоря, ", "Если подумать, ", "Кстати, ", "На самом деле, ", "В принципе, "]

def humanize(text):
    text = re.sub(r'^(В общем|Таким образом|В заключение|Подводя итог),?\s*', '', text, flags=re.MULTILINE | re.IGNORECASE)
    for word, replacement in REPLACEMENTS.items():
        def replace_match(match):
            m = match.group(0)
            return replacement.capitalize() if m[0].isupper() else replacement
        text = re.sub(r'\b' + word + r'\b', replace_match, text, flags=re.IGNORECASE)
    
    sentences = re.split(r'(?<=[.!?])\s+', text)
    new_sentences = []
    for i, sentence in enumerate(sentences):
        if i > 0 and random.random() < 0.3 and len(sentence) > 20:
            sentence = random.choice(HUMAN_PHRASES) + sentence[0].lower() + sentence[1:]
        new_sentences.append(sentence)
    return ' '.join(new_sentences)

def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_help = types.InlineKeyboardButton("📖 Инструкция", callback_data="help")
    btn_status = types.InlineKeyboardButton("👤 Профиль", callback_data="status")
    markup.add(btn_help, btn_status)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    text = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я — ИИ-редактор. Помогаю сделать текст живым и обойти детекторы нейросетей.\n\n"
        "📝 Просто отправь мне текст, и я покажу начало результата."
    )
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu())

@bot.message_handler(commands=['help'])
def help_command(message):
    text = (
        "📖 Как это работает:\n\n"
        "1. Отправь текст, написанный нейросетью.\n"
        "2. Я покажу первые 120 символов.\n"
        "3. Оплати 50 звезд, чтобы получить полный файл.\n"
        "4. После оплаты отправь текст снова, и я пришлю файл."
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['profile'])
def profile_command(message):
    status = "✅ VIP-доступ" if message.chat.id in PAID_USERS else "❌ Бесплатный доступ"
    bot.send_message(message.chat.id, f"Твой статус: {status}")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'):
        return

    bot.send_message(message.chat.id, "⏳ Нейросеть обрабатывает текст...")
    
    if message.chat.id in PAID_USERS:
        result = humanize(message.text)
        filename = f"text_{message.chat.id}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result)
        bot.send_document(message.chat.id, open(filename, "rb"), caption="✅ Готово! Твой уникальный текст.")
        os.remove(filename)
    else:
        preview = humanize(message.text)[:120] + "..."
        prices = [types.LabeledPrice(label="Доступ к тексту", amount=50)]
        try:
            bot.send_invoice(
                message.chat.id,
                title="Очеловеченный текст",
                description=f"Начало: {preview}\n\nОплатите 50 звезд для получения файла.",
                invoice_payload="text_pay",
                provider_token="",
                currency="XTR",
                prices=prices
            )
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "help":
        help_command(call.message)
    elif call.data == "status":
        profile_command(call.message)
    bot.answer_callback_query(call.id)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    PAID_USERS.add(message.chat.id)
    bot.send_message(message.chat.id, "✅ Оплата прошла! Отправь текст снова.")

# --- 3. ЗАПУСК ВСЕГО ВМЕСТЕ ---
if __name__ == '__main__':
    # Запускаем фейковый сайт в отдельном потоке
    threading.Thread(target=run_flask).start()
    print("Веб-сервер запущен. Запускаю бота...")
    # Запускаем бота
    bot.polling(none_stop=True)
