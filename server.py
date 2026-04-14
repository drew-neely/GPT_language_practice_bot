import os

from flask import Flask, request, jsonify, render_template

from chat import process_chat_request
from translate import generate_practice_sentence

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/translate")
def translate_page():
    return render_template("translate.html")

@app.route("/api/chat", methods=["POST"])
def api_chat():
    return jsonify(process_chat_request(request.get_json()))

@app.route("/api/translate/generate", methods=["POST"])
def api_translate_generate():
    result = generate_practice_sentence(request.get_json())
    return jsonify(result)

if __name__ == "__main__":
    # make sure static folder exists
    if not os.path.exists("static"):
        os.makedirs("static")
    app.run(debug=True)
