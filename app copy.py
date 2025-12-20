import os
from pathlib import Path
import logging
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- 🔧 ЖЕЛЕЗНЫЙ ЗАГРУЗЧИК НАСТРОЕК ---

# 1. Пытаемся найти .env прямо рядом с app.py
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# 2. Читаем переменные
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# 3. 🚨 ЗАПАСНОЙ ПАРАШЮТ (Если .env не сработал)
if not VERIFY_TOKEN:
    print("⚠️ ВНИМАНИЕ: .env не прочитался! Использую резервные настройки.")
    VERIFY_TOKEN = "buisness2026"
    # Сюда вставь токен, если он тоже теряется
    # WHATSAPP_TOKEN = "твой_длинный_токен..." 

print(f"✅ Настройки загружены. Токен верификации: {VERIFY_TOKEN}")

# ----------------------------------------

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VERSION = "v21.0"

# --- ФУНКЦИИ ОТПРАВКИ (ТВОЙ ИНСТРУМЕНТАРИЙ) ---

def send_message(recipient_id, text):
    """Отправляет текстовое сообщение"""
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(url, headers=headers, json=data)
    return response

def send_reply_button(recipient_id, text, buttons):
    """
    Отправляет кнопки.
    buttons = [{"id": "btn1", "title": "Button 1"}]
    """
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Формируем структуру кнопок для Meta
    action_buttons = []
    for btn in buttons:
        action_buttons.append({
            "type": "reply",
            "reply": {
                "id": btn["id"],
                "title": btn["title"]
            }
        })

    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {"buttons": action_buttons}
        }
    }
    requests.post(url, headers=headers, json=data)

# --- СЕРВЕРНАЯ ЧАСТЬ ---

@app.route("/", methods=["GET"])
def home():
    return "BarberBot Meta Server is Running! 🚀", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # === 1. ВЕРИФИКАЦИЯ ===
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        # 👇 ДОБАВЬ ЭТИ ДВЕ СТРОКИ ДЛЯ ОТЛАДКИ 👇
        print(f"Meta прислала токен: '{token}'")
        print(f"Сервер ждет токен:   '{VERIFY_TOKEN}'")

        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                logging.info("WEBHOOK_VERIFIED")
                return challenge, 200
            else:
                return "Forbidden", 403
            

    # === 2. ОБРАБОТКА СООБЩЕНИЙ (КЛИЕНТ ПИШЕТ НАМ) ===
    if request.method == "POST":
        data = request.json
        # Логируем входящий JSON (полезно для отладки)
        # logging.info(f"Received: {data}")

        try:
            # Проверяем структуру JSON от Meta
            if data.get("object") == "whatsapp_business_account":
                for entry in data.get("entry", []):
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        
                        # Если есть сообщение
                        if "messages" in value:
                            message = value["messages"][0]
                            sender_id = message["from"] # Номер телефона клиента
                            
                            # --- ЛОГИКА БОТА ---
                            
                            # 1. Если пришел ТЕКСТ
                            if message["type"] == "text":
                                text_body = message["text"]["body"].lower()
                                print(f"📩 Текст от {sender_id}: {text_body}")

                                if text_body in ["hi", "hello", "привет", "шалом", "start"]:
                                    # Отправляем меню кнопками
                                    btns = [
                                        {"id": "btn_price", "title": "💰 Прайс"},
                                        {"id": "btn_address", "title": "📍 Адрес"}
                                    ]
                                    send_reply_button(sender_id, "Шалом! Выберите действие:", btns)
                                else:
                                    # Эхо-ответ
                                    send_message(sender_id, f"Вы написали: {text_body}")

                            # 2. Если нажали КНОПКУ
                            elif message["type"] == "interactive":
                                btn_id = message["interactive"]["button_reply"]["id"]
                                print(f"🔘 Кнопка от {sender_id}: {btn_id}")

                                if btn_id == "btn_price":
                                    send_message(sender_id, "Стрижка: 80 ILS\nБорода: 40 ILS")
                                elif btn_id == "btn_address":
                                    send_message(sender_id, "Мы на Дизенгоф 100, Тель-Авив.")

        except Exception as e:
            logging.error(f"Error: {e}")

        return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)