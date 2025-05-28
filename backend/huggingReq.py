from huggingface_hub import InferenceClient
import json
import os
import requests
import re

# Initialize the client
client = InferenceClient(
    api_key="" 
)

def try_parse_json_block(text):
    """
    Tries to extract a JSON array from the LLM's output using regex.
    Returns parsed JSON or an empty list.
    """
    try:
        json_block = re.search(r'\[\s*{.*?}\s*]', text, re.DOTALL)
        if json_block:
            return json.loads(json_block.group(0))
    except Exception as e:
        print(f"JSON parsing failed: {e}")
    return []

def llm(text):
    user_prompt = f"""
You are a question generator. Given a source text, generate 10 multiple-choice questions in strict JSON format.

Each question must be an object like:
{{
  "question": "...",
  "choices": ["Option A", "Option B", "Option C", "Option D"]
  "correct answer": "1"
}}

The first option from the choices array must be the correct answer; the other options should be plausible distractors.
Only return a valid array of JSON question objects that can easily be processed. No extra explanation or formatting.

Text:
{text}
"""
    try:
        completion = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[{"role": "user", "content": user_prompt}]
        )
        content = completion.choices[0].message.content
        print("Raw model response:\n", content)

        # Attempt to parse manually
        parsed = try_parse_json_block(content)
        return parsed
    except Exception as e:
        print(f"Failed to get or parse completion: {e}")
        return []

def getMaterials(filename):
    url = f"http://127.0.0.1:5000/get_file_content?file={filename}"
    response = requests.get(url)
    if response.status_code == 200:
        text = response.text
        word_count = len(text.split())
        return text, word_count
    else:
        return f"Error {response.status_code}: {response.text}", 0

def split_text_by_word_count(text, max_words=1000):
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]

# --- Main Execution ---
filename = "103A.pdf"
text, no_words = getMaterials(filename)
parts = split_text_by_word_count(text, max_words=500)

all_questions = []

# To test only one part
questions = llm(parts[9])
if questions:
    all_questions.extend(questions)

# Uncomment to process all parts
# for i, part in enumerate(parts):
#     print(f"Processing part {i + 1}...")
#     questions = llm(part)
#     if questions:
#         all_questions.extend(questions)

os.makedirs("processed", exist_ok=True)
with open("processed/questions.json", "w", encoding="utf-8") as f:
    json.dump(all_questions, f, ensure_ascii=False, indent=4)
