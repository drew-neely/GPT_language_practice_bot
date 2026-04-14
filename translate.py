import os
import time
import json

try:
    import anthropic
except ImportError:
    print("Error: 'anthropic' library not found. Please install it using 'pip install anthropic'")
    anthropic = None

from gtts import gTTS

# Load Claude API key from file
server_dir = os.path.dirname(__file__)
key_file_path = os.path.join(server_dir, "claude_key.txt")
client = None
if anthropic:
    try:
        with open(key_file_path, "r") as file:
            claude_api_key = file.read().strip()
            client = anthropic.Anthropic(api_key=claude_api_key)
    except FileNotFoundError:
        print(f"Error: claude_key.txt not found. Make sure it exists and is in the correct directory.")

CLAUDE_MODEL = "claude-haiku-4-5-20251001"

HISTORY_FILE = os.path.join(server_dir, "static", "sentence_history.json")
HISTORY_LENGTH = 10

def read_history():
    """Reads the sentence history from the JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        # Read with utf-8 encoding
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
            return history if isinstance(history, list) else []
    except (json.JSONDecodeError, FileNotFoundError):
        # If file is empty, corrupted, or gone, start fresh
        return []

def write_history(history):
    """Writes the sentence history to the JSON file."""
    # Write with utf-8 encoding and ensure_ascii=False for Chinese characters
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def generate_practice_sentence(config):
    """
    This function uses the Claude API to generate a sentence for translation practice.
    
    Args:
        config (dict): A dictionary containing configuration from the UI.
    """
    if not client:
        return {"error": "Claude client not initialized. Check API key or library installation."}

    vocab_baseline = config.get("vocab_baseline", "beginner HSK 2 level")
    specific_words = config.get("specific_words", "")
    sentence_history = read_history()

    history_list_str = "\n".join([f"- {s}" for s in sentence_history])
    history_prompt_section = f"""- The new sentence MUST be unique and not be the same as or too similar to any of these recently generated sentences:
{history_list_str}""" if sentence_history else ""

    # Construct the prompt for Claude
    prompt = f"""
You are an assistant for a user practicing Chinese listening skills. Your task is to generate a single, simple, and natural-sounding Chinese sentence for them to practice with.

Here are the user's requirements for the sentence:
1.  **Vocabulary Baseline:** The sentence should primarily use vocabulary from the following level: "{vocab_baseline}".
2.  **Specific Words:** If any words are listed here, you MUST include at least one of them in the sentence: "{specific_words}". If this is empty, you don't need to include any specific words.
3.  **Characters:** Use only Traditional Chinese characters.
4.  **Format:** Your response MUST be a JSON object with two keys: "chinese_sentence" and "english_translation". Do not include any other text or explanation outside of the JSON object.
5.  **Variety and Uniqueness:** To ensure the user gets a wide range of practice, please adhere to the following:
    - Avoid common topics like going to the library, eating, or the weather.
    {history_prompt_section}

Example response format:
{{
  "chinese_sentence": "我今天下午想去圖書館看書。",
  "english_translation": "I want to go to the library to read this afternoon."
}}

Now, generate a new sentence based on the user's requirements.
"""

    try:
        # System prompt helps guide Claude to respond in the correct format
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            temperature=1.0,
            system="You are a helpful assistant that provides responses in JSON format.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        ).content[0].text

        # Claude can sometimes wrap the JSON in markdown, so we clean it.
        if message.strip().startswith("```json"):
            message = message.strip()[7:-4].strip()

        data = json.loads(message)
        chinese_sentence = data["chinese_sentence"]
        
        # Update and write history
        sentence_history.append(chinese_sentence)
        write_history(sentence_history[-HISTORY_LENGTH:])

        # Generate audio for the Chinese sentence
        tts = gTTS(text=chinese_sentence, lang='zh-TW')
        audio_filepath = os.path.join(server_dir, "static", "translate_audio.mp3")
        tts.save(audio_filepath)
        data["audio_url"] = f"/static/translate_audio.mp3?t={time.time()}"
        return data

    except Exception as e:
        print(f"Error calling Claude or processing response: {e}")
        return {"error": "Failed to generate sentence from Claude. Check server logs."}