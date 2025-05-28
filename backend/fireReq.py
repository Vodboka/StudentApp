import json
import os
import requests
from pydantic import BaseModel, Field
from typing import List
import openai  

# Set your Fireworks API key
FIREWORKS_API_KEY = "my_API_Key"  

# Initialize the Fireworks client
client = openai.OpenAI(
    base_url="https://api.fireworks.ai/inference/v1",
    api_key=FIREWORKS_API_KEY,
)

# Define the Pydantic schema for a single question
class Question(BaseModel):
    question: str
    choices: List[str] = Field(..., min_items=4, max_items=4)
    correct_answer: int = Field(..., ge=0, le=3)

# Define the Pydantic schema for the list of questions
class QuestionList(BaseModel):
    questions: List[Question]

def llm(text):
    user_prompt = f"""
You are a question generator. Given a source text, generate 10 multiple-choice questions in strict JSON format.

Each question must be an object like:
{{
  "question": "...",
  "choices": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": 0
}}

The first option from the choices array must be the correct answer; the other options should be plausible distractors.
Only return a valid JSON object with a "questions" key containing an array of question objects. No extra explanation or formatting.

Text:
{text}
"""

    try:
        completion = client.chat.completions.create(
            model="accounts/fireworks/models/llama-v3p1-8b-instruct",
            messages=[{"role": "user", "content": user_prompt}],
            response_format={"type": "json_object", "schema": QuestionList.model_json_schema()},
            max_tokens=2048,
            temperature=0.1,
            top_p=1,
            presence_penalty=0,
            frequency_penalty=0
        )
        content = completion.choices[0].message.content
        print("Raw model response:\n", content)

        # Parse the JSON response into the QuestionList schema
        parsed = QuestionList.model_validate_json(content)
        return parsed.questions
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
    all_questions.extend([q.model_dump() for q in questions])

# Uncomment to process all parts
# for i, part in enumerate(parts):
#     print(f"Processing part {i + 1}...")
#     questions = llm(part)
#     if questions:
#         all_questions.extend([q.model_dump() for q in questions])

os.makedirs("processed", exist_ok=True)
with open("processed/questions.json", "w", encoding="utf-8") as f:
    json.dump(all_questions, f, ensure_ascii=False, indent=4)
