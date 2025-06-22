import json
import os
import requests
import sys
import hashlib
import re
from huggingface_hub import InferenceClient
from getToken import receiveToken
from pydantic import BaseModel, Field, ValidationError
from typing import List

# --- Pydantic Schemas ---pip 
class Question(BaseModel):
    question: str
    choices: List[str] = Field(..., min_items=4, max_items=4)
    correct_answer: int = Field(..., ge=0, le=3)

class QuestionList(BaseModel):
    questions: List[Question]

# --- Initialize Hugging Face client ---
client = None
try:
    hf_token = receiveToken("HF")
    if not hf_token:
        print("[CRITICAL ERROR] Hugging Face API token is empty or invalid. Please check getToken.py. Exiting.", file=sys.stderr)
        sys.exit(1)
    client = InferenceClient(api_key=hf_token)
except Exception as e:
    print(f"[CRITICAL ERROR] Failed to initialize Hugging Face client: {e}. Ensure API key is correct and network is stable. Exiting.", file=sys.stderr)
    sys.exit(1)

# --- JSON Parsing Helper ---
def try_parse_json_block(text):
    json_str = ""
    try:
        match = re.search(r'(\{.*?"questions"\s*:\s*\[.*?\]\s*\})|(\[\s*{.*?}\s*\])', text, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            json_str = text

        if not json_str.strip():
            print("[DEBUG] JSON string for parsing is empty after extraction. Returning empty list.", file=sys.stderr)
            return []

        parsed_data = json.loads(json_str)

        if isinstance(parsed_data, dict) and "questions" in parsed_data:
            validated_list = QuestionList.model_validate(parsed_data).questions
        elif isinstance(parsed_data, list):
            validated_list = [Question.model_validate(q) for q in parsed_data]
        else:
            print(f"[WARNING] Parsed JSON is not a list or an object with 'questions' key. Actual type: {type(parsed_data)}", file=sys.stderr)
            return []
        
        for q in validated_list:
            q.correct_answer = 0

        print(f"[DEBUG] Successfully parsed and validated {len(validated_list)} questions.", file=sys.stderr)
        return [q.model_dump() for q in validated_list]

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSONDecodeError in try_parse_json_block: {e}. Problematic string: {json_str[:200]}...", file=sys.stderr)
        return []
    except ValidationError as e:
        print(f"[ERROR] Pydantic validation error in try_parse_json_block: {e}", file=sys.stderr)
        print(f"[ERROR] Validation failed for: {json_str[:500]}...", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[ERROR] General error in try_parse_json_block: {e}", file=sys.stderr)
        return []

# --- LLM Function ---
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
        if client is None:
            print("[ERROR] Hugging Face InferenceClient is not initialized. Cannot make LLM call.", file=sys.stderr)
            return []

        completion = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=2048,
            temperature=0.1,
            # Removed timeout parameter as it's causing the error
        )
        content = completion.choices[0].message.content
        print(f"[DEBUG] Raw LLM content (from huggingReq.py):\n{content}", file=sys.stderr)
        
        questions = try_parse_json_block(content)
        if not questions:
            print(f"[DEBUG] No questions parsed by try_parse_json_block. Raw content was:\n{content}", file=sys.stderr)
        
        return questions
    except Exception as e: # Catch any other exceptions now that timeout is gone
        print(f"[ERROR] Failed to get completion from LLM in huggingReq.py: {e}", file=sys.stderr)
        return []

# --- getMaterials Function ---
def getMaterials(filename):
    url = f"http://127.0.0.1:5000/get_file_content?file={filename}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        text = response.text
        return text, len(text.split())
    except requests.exceptions.Timeout:
        raise Exception(f"Failed to get file content (timeout): Request timed out after 30 seconds for {url}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get file content (request error) from {url}: {e}")

# --- split_text_by_word_count Function ---
def split_text_by_word_count(text, max_words=1000):
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]

# --- Main Entry Point ---
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python huggingReq.py <filename>", file=sys.stderr)
        sys.exit(1)

    input_filename = sys.argv[1]

    try:
        text, _ = getMaterials(input_filename)
        if not text.strip():
            print(f"[CRITICAL ERROR] Retrieved empty text content for filename: '{input_filename}'. Cannot generate questions. Exiting.", file=sys.stderr)
            sys.exit(1)

        parts = split_text_by_word_count(text, max_words=1000)
        all_questions = []

        for part in parts:
            questions = llm(part)
            if questions:
                all_questions.extend(questions)
            else:
                print(f"[DEBUG] llm(part) returned no questions for a text part. Part (first 100 chars): {part[:100]}...", file=sys.stderr)

        os.makedirs("processed", exist_ok=True)
        hash_digest = hashlib.sha256(input_filename.encode()).hexdigest()[:8]
        output_filename = f"{hash_digest}.json"
        output_path = os.path.join("processed", output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            if not all_questions:
                print(f"[WARNING] No questions generated in total for {output_path}. Writing empty array to file.", file=sys.stderr)
            json.dump(all_questions, f, ensure_ascii=False, indent=4)

        print(output_filename)

    except Exception as e:
        print(f"[CRITICAL ERROR] Main script execution failed: {e}", file=sys.stderr)
        sys.exit(1)