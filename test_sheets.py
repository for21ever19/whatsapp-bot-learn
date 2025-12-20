import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 1. Настройки
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
JSON_KEYFILE = 'google_sheet.json' 
SHEET_NAME = 'BarberBot Leads'     

print("🔌 Подключаюсь к Google...")

try:
    # 2. Аутентификация
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEYFILE, SCOPE)
    client = gspread.authorize(creds)

    # 3. Открываем таблицу
    sheet = client.open(SHEET_NAME).sheet1 

    # 4. Данные для теста
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    test_row = [today, "Тестовый Йосси", "050-999-9999", "Стрижка", "Завтра утром"]

    # 5. Пишем
    sheet.append_row(test_row)

    print(f"✅ УСПЕХ! Данные добавлены в таблицу '{SHEET_NAME}'")
    print("🚀 Беги проверять таблицу в браузере!")

except Exception as e:
    print(f"❌ ОШИБКА: {e}")
    print("Совет: Проверь, что имя таблицы в коде совпадает с реальным, и что ты дал доступ боту (email из json).")
