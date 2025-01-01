import re
import os
import threading

from openai import OpenAI
from pypinyin import pinyin
from gtts import gTTS
import tempfile

# Load OpenAI API key from file
try:
    with open("openai_key.txt", "r") as file:
        client = OpenAI(api_key=file.read().strip())
except FileNotFoundError:
    print(f"Error: openai_key.txt not found. Make sure it exists and is in the correct directory.")
    exit(1)

# translate text using openai
def translate(text):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are to translate the users input into english."},
                {"role": "user", "content": text}
            ]
        )
    except Exception as e:
        print(f"Error: {e}")
        return "Error: Translation failed"
    return completion.choices[0].message.content

def audio(text):
    tts = gTTS(text, lang='zh-TW')
    return tts

def _play_audio(tts, speed):
    with tempfile.NamedTemporaryFile(delete=True) as file:
        tts.save(file.name)
        os.system(f'ffplay -nodisp -autoexit -af "volume=0.3" -af "atempo={speed}" "{file.name}" > /dev/null 2>&1')

def play_audio(tts, speed=1):
    threading.Thread(target=_play_audio, args=(tts,speed)).start()

# Main function to carry out chat
def chat(system_message):

    conversation = [{"role": "system", "content": system_message}]
    print("ChatGPT Terminal. Type 'exit' to end the conversation.")
    
    last_output = ""
    last_audio = None
    hide_text = False
    while True:
        user_input = input(">").strip()
        if user_input.lower() in ['quit', 'q', 'exit', 'exit()']: # exit the conversation
            print("Goodbye!")
            break
        elif user_input.lower() in ['p', 'pinyin']: # print pinyin of last output
            if(last_output):
                print(' '.join([py[0] for py in pinyin(last_output)]))
        elif user_input.lower() in ['t', 'translate']: # translate last output
            if(last_output):
                print(translate(last_output))
        elif user_input.lower() in ['a', 'audio']: # play audio of last output
            if last_audio :
                play_audio(last_audio, speed=0.75)
        elif user_input.lower() in ['h', 'hide']: # toggle hide text
            hide_text = not hide_text
            if hide_text:
                print("Text will be hidden")
            else:
                print("Text will be shown")
        elif user_input.lower() in ['r', 'repeat']: # repeat text and audio of last output
            if(last_output):
                print(last_output)
            if last_audio :
                play_audio(last_audio, speed=0.75)
        else :                                      # continue conversation
            conversation.append({"role": "user", "content": user_input})
            try:
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=conversation
                )
            except Exception as e:
                print(f"Error: {e}")
                break
            response = completion.choices[0].message.content
            tts = audio(response)
            if not hide_text:
                print(response)
            play_audio(tts)
            last_output = response
            last_audio = tts
            conversation.append({"role": "system", "content": response})

        

if __name__ == "__main__":
    
    system_message = """
        You are a bot designed to help the user practice chinese. They will speak in chinese and you will respond in chinese.
        Your response will be concise and only consist of a response to the users input to simulate a real conversation.
        You should not provide any additional information. You will use only traditional characters. 
        You will limit vocabulary to vocab from the HSK 2 list and up to chapter 15 of the integrated chinese textbook.
    """.strip()
    system_message = re.sub(r'\s+', ' ', system_message)

    chat(system_message)