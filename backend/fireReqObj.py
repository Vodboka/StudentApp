import json
import os
import sys
import requests
import hashlib
import random  # Import random module
from collections import defaultdict # Import defaultdict for tracking indices
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

# Temporary schema for parsing LLM output BEFORE randomization
# We expect the LLM to still put the conceptual correct answer at index 0 initially
class ParsedQuestion(BaseModel):
    question: str
    choices: List[str] = Field(..., min_items=4, max_items=4)
    # The LLM will put the correct answer at index 0 based on prompt,
    # but we'll re-randomize this later.
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

class FinalQuestionList(BaseModel):
    questions: List[Question]

# --- Core Functions ---
def llm(text):
    # Updated user_prompt to request difficulty_percentage and removed the
    # "first option is correct" constraint from the LLM.
    user_prompt = f"""
You are a question generator. Given a source text, generate 10 multiple-choice questions in strict JSON format.
Each question must be an object like:
{{
  "question": "...",
  "choices": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": 0,
  "difficulty_percentage": 50
}}
For `correct_answer`, initially place the conceptually correct answer at index 0 in the 'choices' array.
For `difficulty_percentage`, assign a percentage (0-100) indicating the objective difficulty of the question based on the text. 0 is very easy, 100 is very hard.

Only return a valid JSON object with a "questions" key containing an array of question objects. No extra explanation or formatting.
Text:
{text}
"""
    try:
        completion = client.chat.completions.create(
            model="accounts/fireworks/models/llama-v3p1-8b-instruct",
            messages=[{"role": "user", "content": user_prompt}],
            # Use ParsedQuestionList schema for validation of initial LLM output
            response_format={"type": "json_object", "schema": ParsedQuestionList.model_json_schema()},
            max_tokens=2048,
            temperature=0.1, # Keep temperature low for structured output
            top_p=1,
            presence_penalty=0,
            frequency_penalty=0
        )
        content = completion.choices[0].message.content
        parsed = ParsedQuestionList.model_validate_json(content)
        return parsed.questions
    except Exception as e:
        print(f"Failed to get or parse completion: {e}", file=sys.stderr)
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

    # Create a list of available indices, initially 0, 1, 2, 3 repeated for enough questions
    # This ensures we always have options, though the constraint might reduce them.
    all_possible_indices = [0, 1, 2, 3] * ((len(questions) // 4) + 1)
    random.shuffle(all_possible_indices)

    for i, pq in enumerate(questions):
        original_correct_text = pq.choices[0] # Assume LLM put correct answer at index 0

        # Create a list of valid indices for this specific question
        # An index is valid if its count is less than max_count_per_index
        valid_indices = [
            idx for idx in range(4) if index_counts[idx] < max_count_per_index
        ]

        if not valid_indices:
            # Fallback if all indices are capped. This should ideally not happen
            # if total questions are not excessively large compared to max_count_per_index * 4.
            # If it does, it means we can't satisfy the constraint perfectly for the remaining questions.
            # For simplicity, if no valid indices are left, we'll pick one that has the minimum count.
            # A more robust solution might reshuffle previously assigned indices.
            min_val = min(index_counts.values())
            valid_indices = [idx for idx, count in index_counts.items() if count == min_val]
            print(f"Warning: Exhausted valid indices for question {i+1}. Re-using min-count index: {valid_indices}", file=sys.stderr)


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

        all_parsed_questions = []
        for part in parts:
            parsed_questions = llm(part) # LLM returns ParsedQuestion objects
            if parsed_questions:
                all_parsed_questions.extend(parsed_questions)

        # Randomize correct answer indices after all questions are generated
        final_questions_for_output = randomize_correct_answer_indices(all_parsed_questions)

        os.makedirs("processed", exist_ok=True)

        # Generate short hash from filename
        hash_digest = hashlib.sha256(input_filename.encode()).hexdigest()[:8]
        output_filename = f"{hash_digest}.json"
        output_path = os.path.join("processed", output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            # Dump the final list of Question objects
            json.dump([q.model_dump() for q in final_questions_for_output], f, ensure_ascii=False, indent=4)

        # Output filename for Flask route to capture
        print(output_filename)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)