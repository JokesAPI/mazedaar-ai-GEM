import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Conversation memory
conversation_history = {}

def detect_language(text):
    text_lower = text.lower()

    hindi_words = ["hindi", "हिंदी", "हिन्दी", "मजेदार", "चुटकुला", "बताओ", "क्या", "कैसे"]
    telugu_words = ["telugu", "తెలుగు", "చెప్పు", "జోక్", "నవ్వు", "ఏమిటి"]

    for word in hindi_words:
        if word in text_lower or word in text:
            return "Hindi"

    for word in telugu_words:
        if word in text_lower or word in text:
            return "Telugu"

    for char in text:
        if '\u0900' <= char <= '\u097F':
            return "Hindi"
        if '\u0C00' <= char <= '\u0C7F':
            return "Telugu"

    return "English"


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        user_input = data.get("message", "").strip()
        session_id = data.get("session_id", "default")

        if not user_input:
            return jsonify({"error": "Message is empty"}), 400

        language = detect_language(user_input)

        if session_id not in conversation_history:
            conversation_history[session_id] = []

        history = conversation_history[session_id]

        system_prompt = f"""You are Mazedaar AI — a fun, smart, and friendly assistant created for Indian users.

LANGUAGE RULE (MOST IMPORTANT):
- The user's detected language is: {language}
- You MUST reply ONLY in {language}.
- If language is Hindi → reply fully in Hindi (Devanagari script).
- If language is Telugu → reply fully in Telugu script.
- If language is English → reply in English.
- NEVER mix languages unless the user explicitly asks.

JOKE RULE:
- If the user asks for a joke, tell a funny, clean, family-friendly joke.
- Jokes must be in {language} only.
- Keep jokes short (2-4 lines max).

GENERAL RULES:
- Answer any question the user asks clearly and helpfully.
- Be warm, friendly, and engaging.
- Keep responses concise and clear.
- If asked who made you, say "I am Mazedaar AI, your friendly assistant!"
"""

        # Build conversation for Gemini
        full_prompt = system_prompt + "\n\nConversation so far:\n"
        for msg in history[-10:]:
            role = "User" if msg["role"] == "user" else "Bot"
            full_prompt += f"{role}: {msg['content']}\n"
        full_prompt += f"User: {user_input}\nBot:"

        # Call Gemini API
        response = model.generate_content(full_prompt)
        reply = response.text.strip()

        # Save history
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})

        if len(history) > 20:
            conversation_history[session_id] = history[-20:]
        else:
            conversation_history[session_id] = history

        return jsonify({
            "response": reply,
            "language_detected": language
        })

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/clear", methods=["POST"])
def clear_history():
    data = request.get_json()
    session_id = data.get("session_id", "default")
    if session_id in conversation_history:
        del conversation_history[session_id]
    return jsonify({"message": "Conversation cleared."})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Mazedaar AI is running OK"})


if __name__ == "__main__":
    print("Mazedaar AI server starting...")
    print("Running at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
