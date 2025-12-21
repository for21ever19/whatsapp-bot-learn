import os
import logging
import requests
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# --- 1. НАСТРОЙКИ ---
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Магия для Render (восстановление JSON)
if not os.path.exists('google_sheet.json'):
    json_content = os.getenv("GOOGLE_SHEET_JSON_CONTENT")
    if json_content:
        with open('google_sheet.json', 'w') as f:
            f.write(json_content)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buisness2026")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERSION = "v21.0"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- 2. GOOGLE SHEETS ---
try:
    SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('google_sheet.json', SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open('BarberBot Leads').sheet1
    print("✅ CRM подключена!")
except Exception as e:
    print(f"❌ Ошибка CRM: {e}")

# --- 3. СОСТОЯНИЕ ---
user_state = {} 
user_data = {}

# --- 4. ФУНКЦИИ ОТПРАВКИ (HEBREW) ---

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=data)

def send_main_menu(recipient_id):
    """Выбор услуг с ценами"""
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "מעולה! איזה טיפול תרצה?"},
            "action": {
                "buttons": [
                    # WhatsApp ограничивает длину заголовка кнопки 20 символами, пишем коротко
                    {"type": "reply", "reply": {"id": "srv_hair", "title": "✂️ תספורת - 80₪"}},
                    {"type": "reply", "reply": {"id": "srv_beard", "title": "🧔 זקן - 40₪"}},
                    {"type": "reply", "reply": {"id": "srv_combo", "title": "👑 הכל כלול - 100₪"}}
                ]
            }
        }
    }
    requests.post(url, headers=headers, json=data)

def send_location(recipient_id):
    """Отправляет точку на карте"""
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "location",
        "location": {
            "latitude": 32.0783,   # Координаты Дизенгоф 100
            "longitude": 34.7736,
            "name": "King David Cuts",
            "address": "Dizengoff St 100, Tel Aviv-Yafo"
        }
    }
    requests.post(url, headers=headers, json=data)
    
def send_service_selection(recipient_id):
    """Выбор услуг"""
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "💈 *ברוכים הבאים ל-Barbershop!* 💈\nאיך אפשר לעזור לך היום?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "btn_book", "title": "📅 לקבוע תור"}},
                    {"type": "reply", "reply": {"id": "btn_price", "title": "💰 מחיר"}},
                    {"type": "reply", "reply": {"id": "btn_loc", "title": "📍 כתובת"}}
                ]
            }
        }
    }
    requests.post(url, headers=headers, json=data)

def save_lead(phone, data):
    try:
        timestamp = datetime.now().strftime("%d-%m-%Y %H:%M")
        row = [timestamp, data.get('name', ''), phone, data.get('service', ''), data.get('time', '')]
        sheet.append_row(row)
    except Exception as e:
        print(f"Error saving: {e}")

# --- 5. ЛОГИКА ---

@app.route("/", methods=["GET"])
def home():
    return "BarberBot Pro is Live 🇮🇱", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # 1. VERIFY (Проверка токена)
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Forbidden", 403

    # 2. POST (Обработка сообщений)
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
                            
                            # Получаем текст (если это текст)
                            text_body = ""
                            if msg_type == "text":
                                text_body = msg["text"]["body"].lower()

                            # --- 1. ГЛОБАЛЬНЫЙ СБРОС (Emergency Exit) ---
                            # Если клиент хочет начать сначала, неважно где он был
                            reset_words = ["start", "menu", "reset", "התחל", "תפריט", "home"]
                            if text_body in reset_words:
                                user_state[sender] = 'MENU'
                                user_data[sender] = {}
                                send_main_menu(sender)
                                return jsonify({"status": "ok"}), 200

                            # --- 2. ОПРЕДЕЛЯЕМ СОСТОЯНИЕ ---
                            state = user_state.get(sender, 'MENU')

                            # --- ЛОГИКА ГЛАВНОГО МЕНЮ ---
                            if state == 'MENU':
                                if msg_type == "interactive":
                                    # Если нажали кнопку - обрабатываем
                                    btn_id = msg["interactive"]["button_reply"]["id"]
                                    
                                    if btn_id == "btn_price":
                                        send_message(sender, "💵 *המחירון שלנו:*\n\n✂️ תספורת: ₪80\n🧔 זקן: ₪40\n👑 הכל כלול: ₪100")
                                        send_main_menu(sender)
                                    
                                    elif btn_id == "btn_loc":
                                        send_location(sender)
                                        send_main_menu(sender)

                                    elif btn_id == "btn_book":
                                        send_message(sender, "בשמחה! איך קוראים לך? (כתוב את השם)")
                                        user_state[sender] = 'WAIT_NAME'
                                else:
                                    # 🔥 UX FIX: Если прислали ЛЮБОЙ текст (шалом, привет, хочу стричься)
                                    # Мы не ругаем клиента. Мы просто показываем ему меню.
                                    # Это создает ощущение, что бот "понял" приветствие и предложил опции.
                                    send_main_menu(sender)

                            # --- ЛОГИКА ЗАПИСИ (FSM) ---

                            # 2. ЖДЕМ ИМЯ
                            elif state == 'WAIT_NAME':
                                if msg_type == "text":
                                    user_data[sender] = {'name': msg["text"]["body"]}
                                    send_service_selection(sender)
                                    user_state[sender] = 'WAIT_SERVICE'
                                else:
                                    send_message(sender, "בבקשה כתוב את השם שלך כהודעה.")

                            # 3. ЖДЕМ УСЛУГУ
                            elif state == 'WAIT_SERVICE':
                                if msg_type == "interactive":
                                    user_data[sender]['service'] = msg["interactive"]["button_reply"]["title"]
                                    send_message(sender, "באיזה יום ושעה היה נוח לך להגיע? 🗓️\n(לדוגמה: יום שלישי בבוקר או חמישי ב-18:00)")                                    
                                    user_state[sender] = 'WAIT_TIME'
                                else:
                                    send_message(sender, "אנא בחר שירות מהכפתורים 👇")

                            # 4. ЖДЕМ ВРЕМЯ
                            elif state == 'WAIT_TIME':
                                if msg_type == "text":
                                    user_data[sender]['time'] = msg["text"]["body"]
                                    
                                    # Финал
                                    save_lead(sender, user_data[sender])
                                    
                                    summary = (
                                        f"✅ *התור נקבע בהצלחה!*\n\n"
                                        f"👤 שם: {user_data[sender]['name']}\n"
                                        f"✂️ טיפול: {user_data[sender]['service']}\n"
                                        f"🕒 זמן: {user_data[sender]['time']}\n\n"
                                        f"נתראה בקרוב! 👋"
                                    )
                                    send_message(sender, summary)
                                    
                                    user_state[sender] = 'MENU'
                                    user_data[sender] = {}
                                    send_main_menu(sender) # Возвращаем меню для нового круга

        except Exception as e:
            logging.error(f"Error: {e}")

        return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)