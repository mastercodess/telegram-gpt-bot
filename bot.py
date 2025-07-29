import os
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Memory/state stores
user_states = {}             # for structured flows
conversation_history = {}    # for GPT memory

def simulate_typing(chat_id):
    requests.post(
        TELEGRAM_API_URL.replace("sendMessage", "sendChatAction"),
        json={"chat_id": chat_id, "action": "typing"}
    )

def send_text(chat_id, text):
    simulate_typing(chat_id)
    requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": text})

def ask_gpt(prompt, chat_id=None):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    history = conversation_history[chat_id]
    history.append({"role": "user", "content": prompt})

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-3.5-turbo",
            "messages": history[-10:]
        }
    )

    try:
        data = response.json()
        print("OpenAI response:", data)

        if "choices" in data:
            reply = data["choices"][0]["message"]["content"].strip()
            history.append({"role": "assistant", "content": reply})
            return reply
        elif "error" in data:
            return f"⚠️ OpenAI error: {data['error']['message']}"
        else:
            return "⚠️ Unexpected response from OpenAI."

    except Exception as e:
        print("Parsing error:", str(e))
        return "⚠️ An error occurred while generating the response."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Incoming Telegram data:", data)

    if 'message' in data and 'text' in data['message']:
        chat_id = data['message']['chat']['id']
        user_text = data['message']['text'].strip()

        # Log interaction to file
        with open("log.txt", "a") as f:
            f.write(f"{chat_id} | USER: {user_text}\n")

        # Handle flow state
        if chat_id not in user_states:
            user_states[chat_id] = {"step": "start"}

        state = user_states[chat_id]

        if state["step"] == "start":
            user_states[chat_id]["step"] = "get_name"
            send_text(chat_id, "Hi there! What’s your name?")
            return {'ok': True}

        elif state["step"] == "get_name":
            user_states[chat_id]["name"] = user_text
            user_states[chat_id]["step"] = "get_email"
            send_text(chat_id, f"Nice to meet you, {user_text.title()}! What’s your email?")
            return {'ok': True}

        elif state["step"] == "get_email":
            user_states[chat_id]["email"] = user_text
            user_states[chat_id]["step"] = "done"
            send_text(chat_id, "Thanks! I’ll remember that. Feel free to ask me anything now.")
            return {'ok': True}

        else:
            # Default to GPT chat
            reply = ask_gpt(user_text, chat_id)
            send_text(chat_id, reply)

            with open("log.txt", "a") as f:
                f.write(f"{chat_id} | BOT: {reply}\n")

            return {'ok': True}

    return {'ok': True}