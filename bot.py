import os
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

def ask_gpt(prompt):
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer " + OPENAI_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    try:
        data = response.json()
        print("OpenAI raw response:", data)  # Log it for debugging

        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
        elif "error" in data:
            return f"⚠️ OpenAI error: {data['error']['message']}"
        else:
            return "⚠️ Unexpected response from OpenAI."

    except Exception as e:
        print("Error parsing OpenAI response:", str(e))
        return "⚠️ An error occurred while generating the response."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if 'message' in data and 'text' in data['message']:
        chat_id = data['message']['chat']['id']
        user_text = data['message']['text']
        reply = ask_gpt(user_text)

        requests.post(TELEGRAM_API_URL, json={
            'chat_id': chat_id,
            'text': reply
        })
    return {'ok': True}