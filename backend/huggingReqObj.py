import json
import os
import sys
import requests
import hashlib
import re
import random  # Import random module
from collections import defaultdict # Import defaultdict for tracking indices
from huggingface_hub import InferenceClient
from getToken import receiveToken
from pydantic import BaseModel, Field, ValidationError
from typing import List

# --- Pydantic Schemas ---

# Temporary schema for parsing LLM output BEFORE randomization
# We expect the LLM to still put the conceptual correct answer at index 0 initially
class ParsedQuestion(BaseModel):
    question: str
    choices: List[str] = Field(..., min_items=4, max_items=4)
    # The LLM will be prompted to put the correct answer at index 0.
    # This field will store that initial index (which should be 0).
    correct_answer: int = Field(..., ge=0, le=3)
    difficulty_percentage: int = Field(..., ge=0, le=100) # Added difficulty

class ParsedQuestionList(BaseModel):
    questions: List[ParsedQuestion]

# Final schema for the output JSON after randomization
class Question(BaseModel):
    question: str
    choices: List[str] = Field(..., min_items=4, max_items=4)
    correct_answer: int = Field(..., ge=0, le=3)
    difficulty_percentage: int = Field(..., ge=0, le=100) # Added difficulty

class FinalQuestionList(BaseModel): # Renamed to avoid conflict if QuestionList is used elsewhere
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
def try_parse_json_block(text) -> List[dict]:
    """
    Attempts to extract and parse a JSON array of question objects or a JSON object
    containing a 'questions' key. Returns a list of parsed question dictionaries.
    """
    json_str = ""
    try:
        # Regex to find either a JSON object with "questions" key or a direct JSON array
        match = re.search(r'(\{.*?"questions"\s*:\s*\[.*?\]\s*\})|(\[\s*{.*?}\s*\])', text, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            json_str = text # Fallback to entire text if no specific block found

        if not json_str.strip():
            print("[DEBUG] JSON string for parsing is empty after extraction. Returning empty list.", file=sys.stderr)
            return []

        parsed_data = json.loads(json_str)

        if isinstance(parsed_data, dict) and "questions" in parsed_data and isinstance(parsed_data["questions"], list):
            # If it's an object with a 'questions' key, return the list under that key
            return parsed_data["questions"]
        elif isinstance(parsed_data, list):
            # If it's a direct list of questions, return it
            return parsed_data
        else:
            print(f"[WARNING] Parsed JSON is not a list or an object with 'questions' key. Actual type: {type(parsed_data)}", file=sys.stderr)
            return []

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSONDecodeError in try_parse_json_block: {e}. Problematic string: {json_str[:200]}...", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[ERROR] General error in try_parse_json_block: {e}", file=sys.stderr)
        return []

# --- LLM Function ---
def llm(text) -> List[ParsedQuestion]:
    """
    Calls the Hugging Face LLM to generate questions and parses the raw text output
    into ParsedQuestion objects.
    """
    user_prompt = f"""
You are a question generator. Given a source text, generate 10 multiple-choice questions in strict JSON format.

Each question must be an object like:
{{
  "question": "...",
  "choices": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": 0,
  "difficulty_percentage": 50
}}

Initially, place the conceptually correct answer at index 0 in the 'choices' array. The `correct_answer` field should reflect this initial index (0).
For `difficulty_percentage`, assign a percentage (0-100) indicating the objective difficulty of the question based on the text. 0 is very easy, 100 is very hard.

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
        )
        content = completion.choices[0].message.content
        print(f"[DEBUG] Raw LLM content (from huggingReq.py):\n{content}", file=sys.stderr)

        # Parse raw content into a list of dictionaries
        question_dicts = try_parse_json_block(content)

        # Validate each dictionary against the ParsedQuestion schema
        parsed_questions = []
        for q_dict in question_dicts:
            try:
                parsed_questions.append(ParsedQuestion.model_validate(q_dict))
            except ValidationError as e:
                print(f"[ERROR] Pydantic validation error for a question dictionary: {e}", file=sys.stderr)
                print(f"[ERROR] Invalid question dict: {q_dict}", file=sys.stderr)
                # Skip this invalid question and continue with others
            except Exception as e:
                print(f"[ERROR] Unexpected error validating question dict: {e}", file=sys.sys.stderr)
                print(f"[ERROR] Problematic dict: {q_dict}", file=sys.stderr)

        if not parsed_questions:
            print(f"[DEBUG] No valid ParsedQuestion objects created from raw content. Raw content was:\n{content}", file=sys.stderr)

        return parsed_questions
    except Exception as e:
        print(f"[ERROR] Failed to get completion from LLM in huggingReq.py: {e}", file=sys.stderr)
        return []

def randomize_correct_answer_indices(questions: List[ParsedQuestion]) -> List[Question]:
    """
    Randomizes the correct_answer index (0-3) for each question,
    ensuring no more than 4 questions have the same correct_answer index.
    The original correct answer text (which was at index 0 from LLM) is moved to the new random index.
    """
    final_questions = []
    # Tracks how many times each index (0, 1, 2, 3) has been assigned as correct
    index_counts = defaultdict(int)
    max_count_per_index = 4 # Constraint: no more than 4 questions with the same index

    for i, pq in enumerate(questions):
        # Ensure choices list has at least 4 elements before proceeding
        if len(pq.choices) < 4:
            print(f"Warning: Question {i+1} has less than 4 choices. Skipping randomization for this question.", file=sys.stderr)
            # If choices are insufficient, just use the original question as is,
            # or handle as an error. For now, we'll just append it with original values.
            final_questions.append(
                Question(
                    question=pq.question,
                    choices=pq.choices,
                    correct_answer=pq.correct_answer, # This would still be 0 as per ParsedQuestion
                    difficulty_percentage=pq.difficulty_percentage
                )
            )
            continue # Move to the next question

        original_correct_text = pq.choices[0] # Assume LLM put correct answer at index 0

        # Create a list of valid indices for this specific question
        # An index is valid if its count is less than max_count_per_index
        valid_indices = [
            idx for idx in range(4) if index_counts[idx] < max_count_per_index
        ]

        if not valid_indices:
            # Fallback if all indices are capped. This means we cannot satisfy the constraint.
            # In this scenario, pick the index with the minimum current count to minimize deviation.
            min_val = min(index_counts.values())
            valid_indices = [idx for idx, count in index_counts.items() if count == min_val]
            # If still no valid indices (e.g., all counts are equal and maxed out, which shouldn't happen with 4 options and max_count_per_index=4)
            if not valid_indices:
                valid_indices = [0] # Default to 0 if all else fails
            print(f"Warning: Exhausted valid indices for question {i+1}. Re-using min-count index: {valid_indices[0]}", file=sys.stderr)


        new_correct_index = random.choice(valid_indices)

        # Update choices list:
        # 1. Store the choice at new_correct_index (which is now a distractor)
        # 2. Place the original_correct_text at new_correct_index
        # 3. Place the stored distractor at original_correct_index (which was 0)
        new_choices = list(pq.choices) # Create a mutable copy
        if new_correct_index != 0:
            distractor_at_new_index = new_choices[new_correct_index]
            new_choices[new_correct_index] = original_correct_text
            new_choices[0] = distractor_at_new_index
        # If new_correct_index is 0, no swap is needed as it's already there

        index_counts[new_correct_index] += 1

        final_questions.append(
            Question(
                question=pq.question,
                choices=new_choices,
                correct_answer=new_correct_index,
                difficulty_percentage=pq.difficulty_percentage
            )
        )
    return final_questions


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
        all_parsed_questions: List[ParsedQuestion] = [] # List to hold ParsedQuestion objects

        for part in parts:
            # llm now returns ParsedQuestion objects directly
            parsed_questions_from_llm = llm(part)
            if parsed_questions_from_llm:
                all_parsed_questions.extend(parsed_questions_from_llm)
            else:
                print(f"[DEBUG] llm(part) returned no ParsedQuestion objects for a text part. Part (first 100 chars): {part[:100]}...", file=sys.stderr)

        # Randomize correct answer indices after all questions are generated and parsed
        final_questions_for_output = randomize_correct_answer_indices(all_parsed_questions)

        os.makedirs("processed", exist_ok=True)
        hash_digest = hashlib.sha256(input_filename.encode()).hexdigest()[:8]
        output_filename = f"{hash_digest}.json"
        output_path = os.path.join("processed", output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            if not final_questions_for_output: # Check the final list
                print(f"[WARNING] No questions generated in total for {output_path}. Writing empty array to file.", file=sys.stderr)
            # Dump the final list of Question objects
            json.dump([q.model_dump() for q in final_questions_for_output], f, ensure_ascii=False, indent=4)

        print(output_filename)

    except Exception as e:
        print(f"[CRITICAL ERROR] Main script execution failed: {e}", file=sys.stderr)
        sys.exit(1)