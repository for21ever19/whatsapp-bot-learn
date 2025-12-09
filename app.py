from flask import Flask, request
import requests
import json

app = Flask(__name__)

# --- НАСТРОЙКИ (Вставь свои данные!) ---
ID_INSTANCE = "7105411695" 
API_TOKEN_INSTANCE = "9f729925bb78480cb03371ae60596dc3c9da03f871774a83bd"

# Адрес, куда мы будем отправлять команды на отправку
API_URL = f"https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN_INSTANCE}"

@app.route('/', methods=['GET'])
def home():
    return "Бот работает и готов общаться!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    # Получаем данные от WhatsApp
    data = request.json
    
    # Печатаем красиво, чтобы видеть структуру (для отладки)
    # print(json.dumps(data, indent=2, ensure_ascii=False))

    # ПРОВЕРКА 1: Это вообще входящее сообщение?
    # Грин-АПИ шлет много всего (статусы доставки и т.д.), нам нужны только сообщения.
    if data.get('typeWebhook') != 'incomingMessageReceived':
        return "OK", 200

    # ПРОВЕРКА 2: Это текст? (Может быть картинка или кнопка)
    message_data = data.get('messageData', {})
    text_message_data = message_data.get('textMessageData', {})
    incoming_text = text_message_data.get('textMessage')

    if not incoming_text:
        print("Пришло сообщение без текста (может картинка)")
        return "OK", 200

    # --- ЛОГИКА БОТА ---
    
    # 1. Кто написал?
    sender = data['senderData']['sender'] # Например: "972501234567@c.us"
    chat_id = data['senderData']['chatId']
    name = data['senderData']['senderName']

    print(f"Сообщение от {name}: {incoming_text}")

    # 2. Что ответить? (Простая логика)
    incoming_text = incoming_text.lower() # Превращаем в маленькие буквы
    answer = ""

    if name == 'Папа':
        answer = f"Шалом, {name}! Как дела?"
    else:
        answer = ""

    # 3. Отправляем ответ
    payload = {
        "chatId": chat_id,
        "message": answer
    }
    
    # "Стучимся" в Грин-АПИ
    if answer != "":
        response = requests.post(API_URL, json=payload)
    
    if response.status_code == 200:
        print(f"Ответ отправлен: {answer}")
    else:
        print(f"Ошибка отправки: {response.text}")

    return "OK", 200

if __name__ == '__main__':
    app.run(port=5000)