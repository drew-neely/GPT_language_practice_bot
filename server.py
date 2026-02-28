import os
import re
import time
import concurrent.futures

from flask import Flask, request, jsonify, render_template

from openai import OpenAI
from pypinyin import pinyin
from gtts import gTTS

# Load OpenAI API key from file
server_dir = os.path.dirname(__file__)  # directory of server.py
key_file_path = os.path.join(server_dir, "openai_key.txt")
try:
    with open(key_file_path, "r") as file:
        client = OpenAI(api_key=file.read().strip())
except FileNotFoundError:
    print(f"Error: openai_key.txt not found. Make sure it exists and is in the correct directory.")
    exit(1)

OPENAI_MODEL = "gpt-5-mini"

#############################################
#############################################
#############################################

# use pypinyin to get pinyin of chinese text
def get_pinyin(text):
    return ' '.join([py[0] for py in pinyin(text)])

# use openai to translate text
def translate(text):
    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are to translate the users input into english."},
                {"role": "user", "content": text}
            ]
        )
    except Exception as e:
        print(f"Error: {e}")
        return "Error: Translation failed"
    return completion.choices[0].message.content

# use gtts to generate audio from text
def audio(text):
    tts = gTTS(text, lang='zh-TW')
    return tts

system_message = """
    You are a bot designed to help the user practice chinese. They will speak in chinese and you will respond in chinese.
    Your response will be concise and only consist of a response to the users input to simulate a real conversation.
    You should not provide any additional information. You will use only traditional characters. 
    You will limit vocabulary to vocab from the HSK 2 list and up to chapter 15 of the integrated chinese textbook.
"""
system_message = re.sub(r'\s+', ' ', system_message.strip())

feedback_system_message = """
    You are to provide feedback on the users input, not a response to it.
    You should include any corrections in the grammar, or suggest alternative words or phrases if a more natural 
    phrasing exists. Include pinyin for any new vocabulary introduced. Use only traditional 
    characters. Respond only in English. Do not suggest the user is free to respond.
    If there is nothing to critique or the input is in english, you do not need to provide any feedback.
    Be concise but informative.
"""
feedback_system_message = re.sub(r'\s+', ' ', feedback_system_message.strip())

# query openai for next response in conversation
def chat(conversation):
    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=conversation
        )
        response = completion.choices[0].message.content
        return response
    except Exception as e:
        print(f"Error: {e}")
        return "Error: Unable to get response from AI"

def get_next_response(user_input, conversation):
    if conversation == None :
        conversation = [{"role": "system", "content": system_message}]
    conversation.append({"role": "user", "content": user_input})
    response = chat(conversation)
    conversation.append({"role": "system", "content": response})
    return response, conversation

def get_feedback(user_input):
    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": feedback_system_message},
                {"role": "user", "content": user_input}
            ]
        )
    except Exception as e:
        print(f"Error: {e}")
        return "Error: Translation failed"
    return completion.choices[0].message.content

#############################################
#############################################
#############################################

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def process():
    user_input = request.json.get("input", "").strip()
    conversation = request.json.get("conversation", [])
    
    if user_input.lower() in ['p', 'pinyin']:
        if conversation:
            response = get_pinyin(conversation[-1]["content"])
        else :
            response = "No text to get pinyin of"
        audio_file_url = None
        feedback = None
    elif user_input.lower() in ['t', 'translate']:
        if conversation:
            response = translate(conversation[-1]["content"])
        else : 
            response = "No text to translate"
        audio_file_url = None
        feedback = None
    elif user_input.lower() == 'replay':
        if conversation:
            try:
                tts = audio(conversation[-1]["content"])
                tts.save(os.path.join(server_dir, "static/audio.mp3"))
                audio_file_url = f"/static/audio.mp3"
            except Exception as e:
                print(f"Error generating audio: {e}")
                audio_file_url = None
            response = ""
        else :
            response = "No text to replay"
            audio_file_url = None
        feedback = None
    else:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_resp = executor.submit(get_next_response, user_input, conversation)
            future_feed = executor.submit(get_feedback, user_input)

            response, conversation = future_resp.result()
            feedback = future_feed.result()

        try:
            tts = audio(response)
            tts.save(os.path.join(server_dir, "static/audio.mp3"))
            audio_file_url = f"/static/audio.mp3"
        except Exception as e:
            print(f"Error generating audio: {e}")
            audio_file_url = None

    if(audio_file_url):
        audio_file_url += f"?t={time.time()}"

    return jsonify({
        "response": response,
        "audio_url": audio_file_url,
        "feedback": feedback,
        "conversation": conversation
    })



#############################################
#############################################
#############################################

if __name__ == "__main__":
    # make sure static folder exists
    if not os.path.exists("static"):
        os.makedirs("static")
    app.run(debug=True)
