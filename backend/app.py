from flask import Flask, request, jsonify, send_file, make_response
import os
import json
import hashlib
import fitz  # PyMuPDF for PDF text extraction
import re
from collections import Counter
import subprocess
import sys
import random

app = Flask(__name__) # Reverted to standard Flask initialization

RES_FOLDER = "res"
UPLOAD_FOLDER = os.path.join(RES_FOLDER, "uploads")
TEXTS_FOLDER = os.path.join(RES_FOLDER, "texts")
SUBJECTS_FILE = os.path.join(RES_FOLDER, "subjects.json")
LESSONS_FILE = os.path.join(RES_FOLDER, "lessons.json")
FILE_RECORD = os.path.join(RES_FOLDER, "files.json")
LESSONS_RECORD = os.path.join(RES_FOLDER, "lessons")

PROCESSED_FOLDER = "processed" 

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEXTS_FOLDER, exist_ok=True)
os.makedirs(RES_FOLDER, exist_ok=True)
os.makedirs(LESSONS_RECORD, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True) 

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def load_uploaded_files():
    if os.path.exists(FILE_RECORD):
        with open(FILE_RECORD, "r") as f:
            return json.load(f)
    return []

def save_uploaded_files(files):
    with open(FILE_RECORD, "w") as f:
        json.dump(files, f)

def generate_hash(file_path):
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def save_extracted_text(hashcode, filename, main_text, footnotes):
    json_path = os.path.join(TEXTS_FOLDER, f"{os.path.splitext(filename)[0]}.json")
    lesson_data = {
        "file_info": {
            "filename": filename,
            "hashcode": hashcode
        },
        "content": {
            "main_text": main_text,
            "footnotes": footnotes
        }
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(lesson_data, f, indent=4, ensure_ascii=False)

def get_dominant_font_size(pdf_path):
    font_sizes = []
    try:
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc):
                blocks = page.get_text("dict")["blocks"]
                if not blocks:
                    print(f"DEBUG: get_dominant_font_size: Page {page_num + 1} has no text blocks in 'dict' format for {pdf_path}", file=sys.stderr)
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                font_sizes.append(span["size"])
    except Exception as e:
        print(f"ERROR: get_dominant_font_size failed for {pdf_path}: {e}", file=sys.stderr)
        return 10 
    
    if font_sizes:
        most_common_size = Counter(font_sizes).most_common(1)[0][0]
        return most_common_size
    print(f"WARNING: get_dominant_font_size: No font sizes found for {pdf_path}. Defaulting to 10.", file=sys.stderr)
    return 10

def extract_text_by_dynamic_font_size(pdf_path):
    main_text_parts, footnotes_parts = [], []
    
    try:
        doc = fitz.open(pdf_path)
        print(f"DEBUG: Successfully opened PDF file: {pdf_path}", file=sys.stderr)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to open PDF file {pdf_path} in extract_text_by_dynamic_font_size: {e}", file=sys.stderr)
        return "", ""

    try:
        dominant_font_size = get_dominant_font_size(pdf_path)
        footnote_threshold = dominant_font_size * 0.9
    except Exception as e:
        print(f"WARNING: Could not determine dominant font size for {pdf_path}: {e}. Using default threshold.", file=sys.stderr)
        dominant_font_size = 10
        footnote_threshold = 9

    with doc:
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            font_size = span["size"]
                            if text:
                                if font_size < footnote_threshold and font_size < dominant_font_size:
                                    footnotes_parts.append(text)
                                else:
                                    main_text_parts.append(text)
    
    main_text_cleaned = clean_text(" ".join(main_text_parts))
    footnotes_cleaned = clean_text(" ".join(footnotes_parts))

    if not main_text_cleaned.strip() and not footnotes_cleaned.strip():
        print(f"ERROR: Standard text extraction returned NO TEXT for {pdf_path}. This PDF may be image-based and requires OCR, which is currently disabled.", file=sys.stderr)
        raise Exception("No text extracted from PDF via standard method. OCR is disabled.")
    else:
        print(f"INFO: Standard extraction found main text. Total length: {len(main_text_cleaned)}. First 200 chars:\n---START MAIN TEXT---\n{main_text_cleaned[:200].replace('\n', ' ').strip()}...\n---END MAIN TEXT---", file=sys.stderr)
    
    return main_text_cleaned, footnotes_cleaned

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(\.{2,}|,{2,}|-{2,}|\s{2,})', ' ', text)
    text = re.sub(r'\[\d+\]|\(\d+\)', '', text)
    return text.strip()

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
    
    hashcode = generate_hash(file_path)
    
    if file.filename not in load_uploaded_files():
        uploaded_files = load_uploaded_files()
        uploaded_files.append(file.filename)
        save_uploaded_files(uploaded_files)
    
    try:
        main_text, footnotes = extract_text_by_dynamic_font_size(file_path)
        save_extracted_text(hashcode, file.filename, main_text, footnotes)
    except Exception as e:
        return jsonify({'error': f'Error extracting text: {str(e)}'}), 500
    
    return jsonify({
        'message': 'File uploaded successfully',
        'filename': file.filename,
        'hashcode': hashcode,
        'footnotes': footnotes
    }), 200

@app.route('/get_files', methods=['GET'])
def get_files():
    return jsonify({'files': load_uploaded_files()})

@app.route('/get_file', methods=['GET'])
def get_file():
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({'error': 'File name is required'}), 400
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file_name)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    return send_file(file_path, as_attachment=True)

@app.route('/get_file_content', methods=['GET'])
def get_file_content():
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({'error': 'File name is required'}), 400
    json_path = os.path.join(TEXTS_FOLDER, f"{os.path.splitext(file_name)[0]}.json")
    if not os.path.exists(json_path):
        return jsonify({'error': 'Text not found'}), 404
    with open(json_path, "r", encoding="utf-8") as f:
        lesson_data = json.load(f)
    main_text = lesson_data.get("content", {}).get("main_text", "")
    if not main_text:
        return jsonify({'error': 'Main text not found'}), 404
    response = make_response(json.dumps({'main_text': main_text}, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

def load_questions(hash_filename):
    path = os.path.join(PROCESSED_FOLDER, hash_filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_questions_in_lessons(questions, FILE):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

def load_lessons():
    if os.path.exists(LESSONS_FILE):
        with open(LESSONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_lessons(lessons):
    with open(LESSONS_FILE, "w", encoding="utf-8") as f:
        json.dump(lessons, f, indent=2, ensure_ascii=False)

def load_subjects():
    if os.path.exists(SUBJECTS_FILE):
        with open(SUBJECTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_subjects(subjects):
    with open(SUBJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(subjects, f, indent=2, ensure_ascii=False)

@app.route('/get_subjects', methods=['GET'])
def get_subjects():
    return jsonify({'subjects': load_subjects()})

@app.route('/add_subject', methods=['POST'])
def add_subject():
    data = request.get_json()
    subject = data.get("subject")
    if not subject:
        return jsonify({'error': 'Subject name is required'}), 400
    subjects = load_subjects()
    if subject not in subjects:
        subjects.append(subject)
        save_subjects(subjects)
    return jsonify({'message': f'Subject "{subject}" added'}), 200

# Helper function to calculate user difficulty for a single question
def calculate_user_difficulty_score(question):
    num_tries = question.get('number_of_tries', 0)
    num_correct_tries = question.get('number_of_correct_tries', 0)

    if num_tries == 0:
        # If no tries, assume neutral user difficulty (e.g., 0.5 for a 0-1 scale)
        return 0.5 
    
    # Calculate error rate as a proxy for user difficulty (higher error rate = higher difficulty for user)
    error_rate = 1 - (num_correct_tries / num_tries)
    return error_rate

# This is the new function to be called after Lesson 0 completion
@app.route('/finalize_initial_lesson', methods=['POST'])
def finalize_initial_lesson():
    data = request.get_json()
    hash_value = data.get('hash')

    if not hash_value:
        return jsonify({'error': 'Hash value is required'}), 400

    LESSON_DIRECTORY = os.path.join(LESSONS_RECORD, hash_value)
    os.makedirs(LESSON_DIRECTORY, exist_ok=True) # Ensure directory exists

    # Load all questions originally processed
    all_original_questions = load_questions(hash_value + ".json")

    # Load questions specifically from lesson0.json, which have been 'evaluated'
    lesson0_questions_from_file = load_questions_from_lesson_chunk(hash_value, 0)
    
    lesson0_question_texts = {q.get('question') for q in lesson0_questions_from_file if q.get('question')}

    remaining_questions_for_chunks = []
    for q in all_original_questions:
        # Re-initialize stats if they are being processed again for a new path
        q['number_of_tries'] = q.get('number_of_tries', 0)
        q['number_of_correct_tries'] = q.get('number_of_correct_tries', 0)
        q['user_difficulty'] = calculate_user_difficulty_score(q) # Calculate user difficulty here

        # Exclude questions that were part of lesson0.json
        if q.get('question') not in lesson0_question_texts:
            remaining_questions_for_chunks.append(q)

    # --- New Combined Difficulty Sorting Logic ---
    for q in remaining_questions_for_chunks:
        objective_difficulty_percentage = q.get('difficulty_percentage', 50) # 0-100 scale
        user_difficulty_score = q.get('user_difficulty', 0.5) # 0-1 scale (0=easy for user, 1=hard for user)

        # Normalize objective difficulty to a 0-1 scale for consistent weighting
        normalized_objective_difficulty = objective_difficulty_percentage / 100.0

        # Define weights based on objective difficulty categories
        # These weights apply to the *user_difficulty_score* component
        if objective_difficulty_percentage <= 33: # Easy objective
            user_weight = 0.125
        elif 34 <= objective_difficulty_percentage <= 66: # Medium objective
            user_weight = 0.375
        else: # Hard objective
            user_weight = 0.5

        # You need to decide on the overall weighting between objective and user difficulty.
        # Here, I'm proposing a 50/50 split initially.
        # This means:
        # 0.5 * normalized_objective_difficulty (0-1)
        # + 0.5 * (user_difficulty_score * user_weight * 2)  -- *2 to scale user_weight back to a 0-1 contribution
        # Let's adjust this to make more sense:
        # Let's use a "combined_difficulty" score that also ranges from 0-100 (like difficulty_percentage)
        
        # Scale user_difficulty_score (0-1) to influence by its weight
        # A simple way: user_difficulty_score (0-1) * user_weight (e.g., 0.125) gives a tiny value.
        # Let's think about how to combine them to make sense in a 0-100 scale for sorting.
        # A higher combined score means harder.

        # Proposed Combination:
        # User difficulty's influence is based on how "badly" they did on similar questions,
        # but modulated by the *objective* difficulty category.
        # A higher `user_difficulty_score` (error rate) means the question was harder for them.

        # Let's aim for a combined score where objective is the baseline, and user performance
        # shifts it up (if hard for user) or down (if easy for user).
        
        # User difficulty contribution: This should be higher if the user struggled (user_difficulty_score is high)
        # and more so if the question was objectively hard (higher user_weight).
        user_contribution = user_difficulty_score * user_weight * 100 # Scales to 0-50 effectively if user_weight max is 0.5

        # Combined score: Simple weighted average where user_contribution adds to objective.
        # Adjust weight_objective and weight_user as needed.
        weight_objective = 0.5
        weight_user = 0.5 # This 0.5 is for the *overall* user impact, not the internal user_weight.

        # Let's try a different calculation for combined_difficulty_score (0-100)
        # combined_difficulty = (objective_difficulty_percentage * overall_objective_weight) + (user_difficulty_score * user_category_weight * some_scaling_factor_to_reach_100)
        
        # A more intuitive approach:
        # Baseline is objective difficulty.
        # If user_difficulty_score is high (they struggled), increase the effective difficulty.
        # If user_difficulty_score is low (they found it easy), decrease the effective difficulty.
        
        # Let's say user_difficulty_score (0-1, error rate)
        # If user_difficulty_score is 0.5 (average), no change.
        # If user_difficulty_score is 1 (always wrong), max increase.
        # If user_difficulty_score is 0 (always correct), max decrease.

        # `user_influence_factor` ranges from -1 to 1 (easy to hard relative to average performance)
        user_influence_factor = (user_difficulty_score - 0.5) * 2 # -1 to 1

        # Adjust the user_influence_factor by the user_weight (0.125, 0.375, 0.5)
        # This means user struggle on hard questions has a bigger impact on score
        weighted_user_influence = user_influence_factor * user_weight

        # Combine with objective difficulty.
        # We want this combined score to still be somewhat representative of a 0-100 scale.
        # Let's say we allow user performance to shift the objective difficulty by up to +/- 20 points
        # For example, if weighted_user_influence is 0.5, that could be a +10 point shift.
        max_shift = 20 # Max points user performance can shift the objective difficulty

        # Calculate the actual shift
        difficulty_shift = weighted_user_influence * max_shift * 2 # Multiply by 2 because weighted_user_influence is roughly -0.5 to 0.5

        combined_difficulty_score = objective_difficulty_percentage + difficulty_shift

        # Ensure the score stays within reasonable bounds (e.g., 0 to 100)
        combined_difficulty_score = max(0, min(100, combined_difficulty_score))

        q['combined_difficulty_score'] = combined_difficulty_score
        print(f"DEBUG: Question: '{q.get('question', 'N/A')[:50]}...', Obj Difficulty: {objective_difficulty_percentage:.2f}, User Difficulty Score: {user_difficulty_score:.2f}, Combined Difficulty Score: {combined_difficulty_score:.2f}", file=sys.stderr)

    # Sort the remaining questions by the new combined difficulty score
    remaining_questions_for_chunks.sort(key=lambda q: q.get('combined_difficulty_score', 0))

    # Re-chunk the remaining questions starting from lesson1.json
    questions_per_lesson = 15
    total_remaining_questions = len(remaining_questions_for_chunks)
    
    current_lesson_number = 1 # Start numbering from lesson1.json

    # Remove any existing lesson files (lesson1.json, lesson2.json, etc.)
    # to ensure clean re-generation, but preserve lesson0.json
    for f_name in os.listdir(LESSON_DIRECTORY):
        if f_name.startswith('lesson') and f_name.endswith('.json') and f_name != 'lesson0.json':
            os.remove(os.path.join(LESSON_DIRECTORY, f_name))
            print(f"Removed old lesson file: {f_name}", file=sys.stderr)

    full_chunks_remaining = total_remaining_questions // questions_per_lesson

    for i in range(full_chunks_remaining):
        start = i * questions_per_lesson
        end = start + questions_per_lesson
        LESSON_FILE_PATH = os.path.join(LESSON_DIRECTORY, f"lesson{current_lesson_number}.json")
        save_questions_to_lesson_chunk(hash_value, current_lesson_number, remaining_questions_for_chunks[start:end])
        current_lesson_number += 1

    leftover = total_remaining_questions % questions_per_lesson
    if leftover:
        LESSON_FILE_PATH = os.path.join(LESSON_DIRECTORY, f"lesson{current_lesson_number}.json")
        save_questions_to_lesson_chunk(hash_value, current_lesson_number, remaining_questions_for_chunks[-leftover:])

    return jsonify({'message': 'Lessons re-organized successfully after initial test.'}), 200

# Modified make_lesson_path to ONLY create lesson0 initially
def make_lesson_path(hashProcessed):
    LESSON_DIRECTORY = os.path.join(LESSONS_RECORD, hashProcessed)
    os.makedirs(LESSON_DIRECTORY, exist_ok=True)
    
    all_questions = load_questions(hashProcessed + ".json")

    for question in all_questions:
        question['number_of_tries'] = question.get('number_of_tries', 0)
        question['number_of_correct_tries'] = question.get('number_of_correct_tries', 0)
        question['user_difficulty'] = question.get('user_difficulty', 0) # Initialize or keep existing

    # Categorize all questions by difficulty for lesson0 balancing
    easy_questions = []
    medium_questions = []
    hard_questions = []

    for q in all_questions:
        difficulty = q.get('difficulty_percentage', 50)
        if difficulty <= 33:
            easy_questions.append(q)
        elif 34 <= difficulty <= 66:
            medium_questions.append(q)
        else:
            hard_questions.append(q)

    random.shuffle(easy_questions)
    random.shuffle(medium_questions)
    random.shuffle(hard_questions)

    lesson_0_questions = []
    lesson_0_size = 15
    
    target_easy_in_l0 = 5
    target_medium_in_l0 = 5
    target_hard_in_l0 = 5

    # Try to pick target number from each category
    lesson_0_questions.extend(easy_questions[:min(target_easy_in_l0, len(easy_questions))])
    easy_questions = easy_questions[min(target_easy_in_l0, len(easy_questions)):]

    lesson_0_questions.extend(medium_questions[:min(target_medium_in_l0, len(medium_questions))])
    medium_questions = medium_questions[min(target_medium_in_l0, len(medium_questions)):]

    lesson_0_questions.extend(hard_questions[:min(target_hard_in_l0, len(hard_questions))])
    hard_questions = hard_questions[min(target_hard_in_l0, len(hard_questions)):]

    # Fill any remaining slots for Lesson 0
    remaining_pool_for_l0 = easy_questions + medium_questions + hard_questions
    random.shuffle(remaining_pool_for_l0)

    while len(lesson_0_questions) < lesson_0_size and remaining_pool_for_l0:
        lesson_0_questions.append(remaining_pool_for_l0.pop(0))

    # Save Lesson 0
    LESSON_0_FILE_PATH = os.path.join(LESSON_DIRECTORY, "lesson0.json")
    save_questions_in_lessons(lesson_0_questions, LESSON_0_FILE_PATH)

    # Initial generation will only create lesson0.
    # The rest will be handled by finalize_initial_lesson later.


@app.route('/add_lesson', methods=['POST'])
def add_lesson():
    data = request.get_json()
    required_fields = ["lesson_name", "subject", "date", "difficulty", "text"]
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required lesson fields'}), 400

    processed_filename = None

    def is_json_file_empty(json_path):
        if not os.path.exists(json_path):
            return True
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                content = f.read().strip()
                if not content:
                    return True
                data = json.loads(content)
                return not data if isinstance(data, (list, dict)) else False
            except json.JSONDecodeError:
                return True
        return False

    text_identifier = data['text']

    try:
        print(f"[INFO][Flask] Attempting to run fireReq.py for {text_identifier}...", file=sys.stderr)
        result_fire_req = subprocess.run(
            ['python3', 'fireReqObj.py', text_identifier],
            capture_output=True,
            text=True,
            check=True
        )
        processed_filename = result_fire_req.stdout.strip()
        print(f"[INFO][Flask] fireReq.py succeeded with output: {processed_filename}", file=sys.stderr)
        if result_fire_req.stderr:
            print(f"\n[DEBUG][Flask] === Stderr from fireReq.py ===\n{result_fire_req.stderr}\n=======================================\n", file=sys.stderr)

        full_path_fire_req = os.path.join(PROCESSED_FOLDER, processed_filename)
        if is_json_file_empty(full_path_fire_req):
            print(f"[WARNING][Flask] fireReq.py generated an empty or invalid JSON file ({full_path_fire_req}). Deleting and falling back to huggingReq.py", file=sys.stderr)
            if os.path.exists(full_path_fire_req):
                os.remove(full_path_fire_req)

            print(f"[INFO][Flask] Falling back to huggingReq.py for {text_identifier}...", file=sys.stderr)
            result_hugging_req = subprocess.run(
                ['python3', 'huggingReq.py', text_identifier],
                capture_output=True,
                text=True,
                check=True
            )
            processed_filename = result_hugging_req.stdout.strip()
            print(f"[INFO][Flask] huggingReq.py succeeded with output: {processed_filename}", file=sys.stderr)
            if result_hugging_req.stderr:
                print(f"\n[DEBUG][Flask] === Stderr from huggingReq.py ===\n{result_hugging_req.stderr}\n=======================================\n", file=sys.stderr)

            full_path_hugging_req = os.path.join(PROCESSED_FOLDER, processed_filename)
            if is_json_file_empty(full_path_hugging_req):
                print("[ERROR] huggingReq.py also returned empty content.", file=sys.stderr)
                if os.path.exists(full_path_hugging_req):
                    os.remove(full_path_hugging_req)
                return jsonify({'error': 'Both generation methods returned empty content.'}), 500
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] fireReq.py failed: {e.stderr}", file=sys.stderr)
        print("[INFO] Falling back to huggingReq.py...", file=sys.stderr)

        try:
            result_hugging_req = subprocess.run(
                ['python3', 'huggingReq.py', text_identifier],
                capture_output=True,
                text=True,
                check=True
            )
            processed_filename = result_hugging_req.stdout.strip()
            print(f"[INFO] huggingReq.py succeeded with output: {processed_filename}", file=sys.stderr)
            if result_hugging_req.stderr:
                print(f"\n[DEBUG][Flask] === Stderr from huggingReq.py ===\n{result_hugging_req.stderr}\n=======================================\n", file=sys.stderr)

            full_path_hugging_req = os.path.join(PROCESSED_FOLDER, processed_filename)
            if is_json_file_empty(full_path_hugging_req):
                print("[ERROR] huggingReq.py also returned empty content.", file=sys.stderr)
                if os.path.exists(full_path_hugging_req):
                    os.remove(full_path_hugging_req)
                return jsonify({'error': 'Both generation methods returned empty content.'}), 500

        except subprocess.CalledProcessError as e2:
            print(f"[ERROR] huggingReq.py also failed: {e2.stderr}", file=sys.stderr)
            return jsonify({'error': 'Both generation methods failed.'}), 500
    except Exception as e:
        print(f"[CRITICAL ERROR] An unexpected error occurred during subprocess execution: {e}", file=sys.stderr)
        return jsonify({'error': f'Server error during question generation: {str(e)}'}), 500


    if processed_filename and processed_filename.endswith('.json'):
        processed_filename = processed_filename[:-5]

    lessons = load_lessons()
    subject = data['subject']
    subjects = load_subjects()
    if subject not in subjects:
        subjects.append(subject)
        save_subjects(subjects)

    lessons.append({
        'lesson_name': data['lesson_name'],
        'subject': subject,
        'date': data['date'],
        'difficulty': data['difficulty'],
        'text': data['text'],
        'processed filename': processed_filename
    })
    save_lessons(lessons)

    make_lesson_path(processed_filename) # This will now only create lesson0.json initially

    return jsonify({
        'message': f'Lesson \"{data['lesson_name']}\" added successfully under subject \"{subject}\"',
        'lesson': {
            'lesson_name': data['lesson_name'],
            'subject': subject,
            'date': data['date'],
            'difficulty': data['difficulty'],
            'text': data['text'],
            'processed filename': processed_filename
        }
    }), 201


@app.route('/get_lessons', methods=['GET'])
def get_lessons():
    return jsonify({'lessons': load_lessons()}), 200

@app.route('/get_lesson_hash', methods=['GET'])
def get_lesson():
    lesson_name = request.args.get('lesson_name')
    subject = request.args.get('subject')
    if not lesson_name or not subject:
        return jsonify({'error': 'Missing lesson_name or subject parameter'}), 400
    for lesson in load_lessons():
        if lesson['lesson_name'] == lesson_name and lesson['subject'] == subject:
            return jsonify({'lesson hash': lesson['processed filename']}), 200
    return jsonify({'error': 'Lesson not found'}), 404

@app.route('/get_lessons_for_hash')
def get_lessons_for_hash():
    hash_value = request.args.get('hash')
    if not hash_value:
        return jsonify({'error': 'Missing hash'}), 400

    if hash_value.endswith('.json'):
        hash_value = hash_value[:-5]

    lesson_dir = os.path.join(LESSONS_RECORD, hash_value)
    if not os.path.exists(lesson_dir):
        print(f"[DEBUG] Lesson directory not found: {lesson_dir}", file=sys.stderr)
        return jsonify({'lessons': []})

    lesson_files = sorted([
        f for f in os.listdir(lesson_dir) if f.startswith('lesson') and f.endswith('.json')
    ])
    
    lessons_with_percentages = []

    for f in lesson_files:
        try:
            lesson_number = int(f.replace("lesson", "").replace(".json", ""))
            
            lesson_file_path = os.path.join(lesson_dir, f)
            questions_data = []
            if os.path.exists(lesson_file_path):
                with open(lesson_file_path, "r", encoding="utf-8") as lf:
                    questions_data = json.load(lf)

            sum_of_individual_rates = 0.0
            number_of_questions_with_attempts = 0

            for q in questions_data:
                number_of_tries = q.get('number_of_tries', 0)
                number_of_correct_tries = q.get('number_of_correct_tries', 0)

                if number_of_tries > 0:
                    sum_of_individual_rates += (number_of_correct_tries / number_of_tries)
                    number_of_questions_with_attempts += 1
            
            average_percentage = 0.0
            if number_of_questions_with_attempts > 0:
                average_percentage = (sum_of_individual_rates / number_of_questions_with_attempts) * 100
            elif questions_data:
                 average_percentage = 0.0

            lessons_with_percentages.append({
                'lesson_number': lesson_number,
                'percentage': average_percentage
            })
            
        except ValueError:
            print(f"[DEBUG] Could not parse lesson number from file: {f}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"[ERROR] Error processing lesson file {f}: {e}", file=sys.stderr)
            continue

    lessons_with_percentages.sort(key=lambda x: x['lesson_number'])

    return jsonify({'lessons': lessons_with_percentages})


@app.route('/get_lesson_questions', methods=['GET'])
def get_lesson_questions():
    hash_value = request.args.get('hash')
    lesson_number = request.args.get('lesson_number')

    print(f"DEBUG: get_lesson_questions - Received hash: {hash_value}, lesson_number: {lesson_number}", file=sys.stderr)

    if not hash_value or lesson_number is None:
        return jsonify({'error': 'Missing parameters'}), 400

    if hash_value and hash_value.endswith('.json'):
        hash_value = hash_value[:-5]
        print(f"DEBUG: get_lesson_questions - Cleaned hash: {hash_value}", file=sys.stderr)

    lesson_file = os.path.join(LESSONS_RECORD, hash_value, f"lesson{lesson_number}.json")
    print(f"DEBUG: get_lesson_questions - Attempting to open file: {lesson_file}", file=sys.stderr)

    if not os.path.exists(lesson_file):
        print(f"DEBUG: get_lesson_questions - File NOT found: {lesson_file}", file=sys.stderr)
        return jsonify({'error': 'Lesson file not found'}), 404

    with open(lesson_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    return jsonify({'questions': questions})

@app.route('/update_lesson', methods=['POST'])
def update_lesson():
    data = request.get_json()
    lesson_name = data.get('lesson_name')
    subject = data.get('subject')
    date = data.get('date')
    difficulty = data.get('difficulty')
    if not all([lesson_name, subject, date, difficulty]):
        return jsonify({'error': 'Missing required fields'}), 400
    lessons = load_lessons()
    updated = False
    for lesson in lessons:
        if lesson['lesson_name'] == lesson_name and lesson['subject'] == subject:
            lesson['date'] = date
            lesson['difficulty'] = difficulty
            updated = True
            break
    if not updated:
        return jsonify({'error': 'Lesson not found'}), 404
    save_lessons(lessons)
    return jsonify({'message': 'Lesson updated successfully'}), 200

@app.route('/get_processed_file/<hashcode>', methods=['GET'])
def get_processed_file(hashcode):
    filepath = os.path.join(PROCESSED_FOLDER, hashcode + ".json")
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    try:
        with open(filepath, 'r', encoding="utf-8") as file:
            data = json.load(file)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': f'Failed to read file: {str(e)}'}), 500

def load_questions_from_lesson_chunk(hash_value, lesson_number):
    if hash_value.endswith('.json'):
        hash_value = hash_value[:-5]
    lesson_file_path = os.path.join(LESSONS_RECORD, hash_value, f"lesson{lesson_number}.json")
    if os.path.exists(lesson_file_path):
        with open(lesson_file_path, 'r', encoding="utf-8") as f:
            return json.load(f)
    print(f"[ERROR][Flask] Lesson chunk file not found: {lesson_file_path}", file=sys.stderr)
    return []

def save_questions_to_lesson_chunk(hash_value, lesson_number, questions_data):
    if hash_value.endswith('.json'):
        hash_value = hash_value[:-5]
    lesson_file_path = os.path.join(LESSONS_RECORD, hash_value, f"lesson{lesson_number}.json")
    with open(lesson_file_path, 'w', encoding="utf-8") as f:
        json.dump(questions_data, f, indent=4, ensure_ascii=False)
    print(f"[INFO][Flask] Saved updated questions to lesson chunk file: {lesson_file_path}", file=sys.stderr)


@app.route('/update_question_stats', methods=['POST'])
def update_question_stats():
    data = request.get_json()
    if not data:
        print("[ERROR][Flask] /update_question_stats: Request body is empty or not JSON.", file=sys.stderr)
        return jsonify({'error': 'Request body must be JSON'}), 400

    hash_value = data.get('hash')
    lesson_number = data.get('lesson_number')
    question_index = data.get('question_index')
    number_of_tries = data.get('number_of_tries')
    number_of_correct_tries = data.get('number_of_correct_tries')

    if not all([hash_value, lesson_number is not None, question_index is not None,
                number_of_tries is not None, number_of_correct_tries is not None]):
        return jsonify({'error': 'Missing required fields for update'}), 400

    try:
        lesson_questions = load_questions_from_lesson_chunk(hash_value, lesson_number)

        if not lesson_questions:
            return jsonify({'error': 'Lesson chunk file not found or empty'}), 404

        if 0 <= question_index < len(lesson_questions):
            question_to_update = lesson_questions[question_index]
            
            question_to_update['number_of_tries'] = number_of_tries
            question_to_update['number_of_correct_tries'] = number_of_correct_tries
            
            # Recalculate user_difficulty for this specific question when its stats are updated
            question_to_update['user_difficulty'] = calculate_user_difficulty_score(question_to_update)

            save_questions_to_lesson_chunk(hash_value, lesson_number, lesson_questions)
            
            print(f"[INFO][Flask] Updated stats for question {question_index} in lesson {lesson_number} (hash: {hash_value}): Tries={number_of_tries}, Correct={number_of_correct_tries}, User Difficulty Score (Recalc)={question_to_update['user_difficulty']:.2f}", file=sys.stderr)
            return jsonify({'message': 'Question stats updated successfully'}), 200
        else:
            print(f"[ERROR][Flask] /update_question_stats: Invalid question_index: {question_index} for lesson {lesson_number} (hash: {hash_value})", file=sys.stderr)
            return jsonify({'error': 'Invalid question index for this lesson'}), 404

    except Exception as e:
        print(f"[CRITICAL ERROR][Flask] /update_question_stats: Error updating question stats: {e}", file=sys.stderr)
        return jsonify({'error': f'Server error: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)