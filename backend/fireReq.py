import json
import os
import sys
import requests
import hashlib
from pydantic import BaseModel, Field
from typing import List
import openai
from getToken import receiveToken

#the key is in a sepparate script  under gitignore
FIREWORKS_API_KEY = receiveToken("FW")

# Initialize Fireworks client
client = openai.OpenAI(
    base_url="https://api.fireworks.ai/inference/v1",
    api_key=FIREWORKS_API_KEY,
)

# --- Pydantic Schemas ---
class Question(BaseModel):
    question: str
    choices: List[str] = Field(..., min_items=4, max_items=4)
    correct_answer: int = Field(..., ge=0, le=3)

class QuestionList(BaseModel):
    questions: List[Question]

# --- Core Functions ---
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
        parsed = QuestionList.model_validate_json(content)
        return parsed.questions
    except Exception as e:
        print(f"Failed to get or parse completion: {e}", file=sys.stderr)
        return []

def getMaterials(filename):
    url = f"http://127.0.0.1:5000/get_file_content?file={filename}"
    response = requests.get(url)
    if response.status_code == 200:
        text = response.text
        return text, len(text.split())
    else:
        raise Exception(f"Failed to get file content: {response.status_code} {response.text}")

def split_text_by_word_count(text, max_words=1000):
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]

# --- Main Entry ---
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_text.py <filename>", file=sys.stderr)
        sys.exit(1)

    input_filename = sys.argv[1]

    try:
        text, _ = getMaterials(input_filename)
        parts = split_text_by_word_count(text, max_words=1000)

        all_questions = []
        for part in parts:
            questions = llm(part)
            if questions:
                all_questions.extend([q.model_dump() for q in questions])

        os.makedirs("processed", exist_ok=True)

        # Generate short hash from filename
        hash_digest = hashlib.sha256(input_filename.encode()).hexdigest()[:8]
        output_filename = f"{hash_digest}.json"
        output_path = os.path.join("processed", output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_questions, f, ensure_ascii=False, indent=4)

        # Output filename for Flask route to capture
        print(output_filename)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
