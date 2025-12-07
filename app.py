from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Bot is alive!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Получено сообщение:", data)
    return "OK", 200

if __name__ == '__main__':
    app.run(port=5000)