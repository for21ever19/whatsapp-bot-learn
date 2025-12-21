import os
import logging
import requests
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# --- 1. НАСТРОЙКИ И БЕЗОПАСНОСТЬ ---
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


# 🛠 МАГИЯ ДЛЯ RENDER: Восстанавливаем json-файл из переменной
if not os.path.exists('google_sheet.json'):
    # Если файла нет (мы на сервере), создаем его из переменной окружения
    json_content = os.getenv("GOOGLE_SHEET_JSON_CONTENT")
    if json_content:
        with open('google_sheet.json', 'w') as f:
            f.write(json_content)
        print("✅ Файл google_sheet.json восстановлен из переменной!")
    else:
        print("⚠️ ВНИМАНИЕ: Нет файла google_sheet.json и нет переменной!")

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buisness2026")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERSION = "v21.0"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- 2. ПОДКЛЮЧЕНИЕ GOOGLE SHEETS ---
try:
    SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('google_sheet.json', SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open('BarberBot Leads').sheet1 # <--- ПРОВЕРЬ ИМЯ ТАБЛИЦЫ!
    print("✅ Google Sheets подключен успешно!")
except Exception as e:
    print(f"❌ Ошибка Google Sheets: {e}")

# --- 3. ПАМЯТЬ БОТА (ВРЕМЕННАЯ) ---
# user_state хранит этап диалога: 'MENU', 'WAIT_NAME', 'WAIT_SERVICE', 'WAIT_TIME'
user_state = {} 
# user_data хранит ответы: {'phone': {'name': 'Yossi', 'service': 'Hair'}}
user_data = {}

# --- 4. ФУНКЦИИ ОТПРАВКИ ---

def send_message(recipient_id, text):
    """Отправляет простой текст"""
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=data)

def send_menu_buttons(recipient_id):
    """Отправляет главное меню"""
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "💈 Добро пожаловать в BarberBot! Чем помочь?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "btn_book", "title": "✂️ Записаться"}},
                    {"type": "reply", "reply": {"id": "btn_price", "title": "💰 Прайс"}},
                    {"type": "reply", "reply": {"id": "btn_loc", "title": "📍 Где мы?"}}
                ]
            }
        }
    }
    requests.post(url, headers=headers, json=data)

def send_service_selection(recipient_id):
    """Отправляет выбор услуг (списком или кнопками)"""
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    
    # Для простоты используем кнопки (максимум 3)
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Какая услуга вас интересует?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "srv_hair", "title": "Стрижка"}},
                    {"type": "reply", "reply": {"id": "srv_beard", "title": "Борода"}},
                    {"type": "reply", "reply": {"id": "srv_combo", "title": "Комплекс"}}
                ]
            }
        }
    }
    requests.post(url, headers=headers, json=data)

def save_lead_to_sheet(phone, data):
    """Записывает лид в таблицу"""
    try:
        timestamp = datetime.now().strftime("%d-%m-%Y %H:%M")
        row = [
            timestamp,              # Дата заявки
            data.get('name', ''),   # Имя
            phone,                  # Телефон
            data.get('service', ''),# Услуга
            data.get('time', '')    # Желаемое время
        ]
        sheet.append_row(row)
        print(f"📝 Заявка сохранена: {row}")
    except Exception as e:
        print(f"❌ Ошибка записи в таблицу: {e}")

# --- 5. ОБРАБОТЧИК СООБЩЕНИЙ ---

@app.route("/", methods=["GET"])
def home():
    return "BarberBot Brain is Active! 🧠", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # 1. Verify
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Forbidden", 403

    # 2. Handle Messages
    if request.method == "POST":
        data = request.json
        try:
            if data.get("object") == "whatsapp_business_account":
                for entry in data.get("entry", []):
                    for change in entry.get("changes", []):
                        val = change.get("value", {})
                        
                        if "messages" in val:
                            msg = val["messages"][0]
                            sender = msg["from"]
                            msg_type = msg["type"]
                            
                            # Получаем текущее состояние пользователя (или MENU если нет)
                            state = user_state.get(sender, 'MENU')
                            
                            # --- ЛОГИКА "СБРОСА" ---
                            # Если клиент пишет "старт" или "меню" — сбрасываем всё
                            text_body = ""
                            if msg_type == "text":
                                text_body = msg["text"]["body"].lower()
                            
                            if text_body in ["start", "menu", "старт", "меню", "привет"]:
                                user_state[sender] = 'MENU'
                                user_data[sender] = {}
                                send_menu_buttons(sender)
                                return jsonify({"status": "ok"}), 200

                            # --- КОНЕЧНЫЙ АВТОМАТ (FSM) ---
                            
                            if state == 'MENU':
                                # Обработка кнопок главного меню
                                if msg_type == "interactive":
                                    btn_id = msg["interactive"]["button_reply"]["id"]
                                    
                                    if btn_id == "btn_price":
                                        send_message(sender, "💵 Стрижка: 80₪\n🧔 Борода: 40₪\n🔥 Комплекс: 100₪")
                                        send_menu_buttons(sender) # Возвращаем меню
                                        
                                    elif btn_id == "btn_loc":
                                        send_message(sender, "📍 Мы находимся: Dizengoff 100, Tel Aviv")
                                        send_menu_buttons(sender)
                                        
                                    elif btn_id == "btn_book":
                                        send_message(sender, "Отлично! Как к вам обращаться? (Напишите имя)")
                                        user_state[sender] = 'WAIT_NAME' # Переходим на след. шаг

                            elif state == 'WAIT_NAME':
                                if msg_type == "text":
                                    name = msg["text"]["body"]
                                    user_data[sender] = {'name': name} # Запомнили имя
                                    
                                    send_service_selection(sender) # Спрашиваем услугу
                                    user_state[sender] = 'WAIT_SERVICE'
                                else:
                                    send_message(sender, "Пожалуйста, напишите ваше имя текстом.")

                            elif state == 'WAIT_SERVICE':
                                if msg_type == "interactive":
                                    srv_id = msg["interactive"]["button_reply"]["title"] # Берем текст кнопки
                                    user_data[sender]['service'] = srv_id # Запомнили услугу
                                    
                                    send_message(sender, "На когда вы хотите записаться? (Например: 'Завтра в 18:00')")
                                    user_state[sender] = 'WAIT_TIME'
                                else:
                                    send_message(sender, "Пожалуйста, выберите услугу, нажав на кнопку.")

                            elif state == 'WAIT_TIME':
                                if msg_type == "text":
                                    time_slot = msg["text"]["body"]
                                    user_data[sender]['time'] = time_slot # Запомнили время
                                    
                                    # ФИНАЛ: Сохраняем и подтверждаем
                                    save_lead_to_sheet(sender, user_data[sender])
                                    
                                    final_text = (
                                        f"✅ Заявка принята!\n"
                                        f"👤 {user_data[sender]['name']}\n"
                                        f"✂️ {user_data[sender]['service']}\n"
                                        f"🕒 {time_slot}\n\n"
                                        f"Мастер скоро свяжется для подтверждения."
                                    )
                                    send_message(sender, final_text)
                                    
                                    # Сброс в начало
                                    user_state[sender] = 'MENU'
                                    user_data[sender] = {}

        except Exception as e:
            logging.error(f"Error: {e}")

        return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)