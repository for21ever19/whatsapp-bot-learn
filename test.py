import requests
import json

# --- ТВОИ ДАННЫЕ META ---
# Токен я вставил твой, но лучше храни его в переменной
ACCESS_TOKEN = "EAAnd0wQ6J3kBQN9qZCDVoBeDh3CIIT0T2fpEJGs6xYAw86eD2OL61eYeVtrgZBZAT3LecPzGcDzHpoZCdFk8MCbA3tPidKlREiMIh9GpcdtpTouUZA1NZAOEOjFPZASPvKr2ZBY1linNgZCoeFDH7zRP8gvE50BpZBrKuDYZAmaZBz2Fn35qSJwlGdfbAYszLI6EXhZAKj0nPNMmFpTJpTgSrCVRlyvzFiCYnZBZCwkjlvCHV3PzGXtkItswZApKppbzJpj5CsiAi7lsvrLAMCM43SdPC3lgoFbt"

# 👇 ВСТАВЬ СЮДА PHONE NUMBER ID (не путай с Token!)
PHONE_NUMBER_ID = "950774071448018" 

# 👇 ВСТАВЬ СЮДА СВОЙ НОМЕР (куда отправлять)
# Пример: "972501234567"
RECIPIENT_NUMBER = "972539364695" 

# Адрес API Facebook
URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Тело сообщения с КНОПКАМИ (Interactive Message)
payload = {
    "messaging_product": "whatsapp",
    "to": RECIPIENT_NUMBER,
    "type": "interactive",
    "interactive": {
        "type": "button",
        "body": {
            "text": "🔥 Шалом! Это тест официальных кнопок Meta!"
        },
        "action": {
            "buttons": [
                {
                    "type": "reply",
                    "reply": {
                        "id": "btn_price",
                        "title": "💰 Прайс"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "btn_address",
                        "title": "📍 Адрес"
                    }
                }
            ]
        }
    }
}

print("Отправляю запрос в Meta...")

try:
    response = requests.post(URL, headers=headers, json=payload)
    print(f"Статус код: {response.status_code}")
    print(f"Ответ: {response.text}")
except Exception as e:
    print(f"Ошибка: {e}")