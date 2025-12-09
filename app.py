from flask import Flask, request
import requests
import json

app = Flask(__name__)

# --- НАСТРОЙКИ ---
ID_INSTANCE = "7105411695"
API_TOKEN_INSTANCE = "9f729925bb78480cb03371ae60596dc3c9da03f871774a83bd"

# Базовый адрес (без уточнения sendMessage или sendButtons)
BASE_URL = f"https://api.green-api.com/waInstance{ID_INSTANCE}"

@app.route('/', methods=['GET'])
def home():
    return "Бот работает!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    
    # 1. Проверяем, что это входящее сообщение
    if data.get('typeWebhook') != 'incomingMessageReceived':
        return "OK", 200

    # 2. Получаем данные отправителя
    sender_data = data.get('senderData', {})
    chat_id = sender_data.get('chatId')
    name = sender_data.get('senderName')
    
    # 3. ФИЛЬТР: Работаем только если пишет Папа
    if name != 'Папа':
        print(f"Пишет {name}, но мы отвечаем только Папе.")
        return "OK", 200

    # 4. Разбираем сообщение
    message_data = data.get('messageData', {})
    
    # СЦЕНАРИЙ А: Пришел ТЕКСТ -> Шлем Меню
    if message_data.get('typeMessage') == 'textMessage':
        incoming_text = message_data['textMessageData']['textMessage'].lower()
        print(f"Папа написал текст: {incoming_text}")
        send_menu(chat_id, name)

    # СЦЕНАРИЙ Б: Нажата КНОПКА -> Реагируем
    elif message_data.get('typeMessage') == 'buttonsResponseMessage':
        button_id = message_data['buttonsResponseMessageData']['selectedButtonId']
        print(f"Папа нажал кнопку: {button_id}")

        if button_id == 'price':
            send_text(chat_id, "💰 Стрижка: 100 shek\nБорода: 50 shek")
        elif button_id == 'location':
            send_text(chat_id, "📍 Мы находимся: Tel Aviv, Dizengoff 100")
        elif button_id == 'support':
            send_text(chat_id, "Перевожу на человека... 👤")

    return "OK", 200


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (Вынесены наружу) ---

def send_menu(chat_id, user_name):
    # Тут формируем правильный URL для кнопок
    url = f"{BASE_URL}/sendButtons/{API_TOKEN_INSTANCE}"
    
    payload = {
        "chatId": chat_id,
        "message": f"Шалом, {user_name}! Выберите действие:",
        "buttons": [
            {"buttonId": "price", "buttonText": "Прайс 💰"},
            {"buttonId": "location", "buttonText": "Адрес 📍"},
            {"buttonId": "support", "buttonText": "Позвать человека"}
        ]
    }
    # Отправляем
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка отправки меню: {e}")

def send_text(chat_id, text):
    # Тут URL для обычного текста
    url = f"{BASE_URL}/sendMessage/{API_TOKEN_INSTANCE}"
    payload = {
        "chatId": chat_id,
        "message": text
    }
    requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(port=5000)