from flask import Flask, request, jsonify, send_file, make_response
import os
import json
import hashlib
import fitz  # PyMuPDF for PDF text extraction
import re
from collections import Counter
import subprocess
import fireReq
import sys

app = Flask(__name__)

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
    with open(json_path, "w") as f:
        json.dump(lesson_data, f, indent=4, ensure_ascii=False)

def get_dominant_font_size(pdf_path):
    font_sizes = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            font_sizes.append(span["size"])
    if font_sizes:
        most_common_size = Counter(font_sizes).most_common(1)[0][0]
        return most_common_size
    return 10

def extract_text_by_dynamic_font_size(pdf_path):
    main_text, footnotes = [], []
    dominant_font_size = get_dominant_font_size(pdf_path)
    footnote_threshold = dominant_font_size * 0.9
    with fitz.open(pdf_path) as doc:
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            font_size = span["size"]
                            if font_size < footnote_threshold:
                                footnotes.append(text)
                            else:
                                main_text.append(text)
    main_text_cleaned = clean_text(" ".join(main_text))
    footnotes_cleaned = clean_text(" ".join(footnotes))
    return main_text_cleaned, footnotes_cleaned

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(\.{2,}|,{2,}|-{2,}|\s{2,})', ' ', text)
    text = re.sub(r'\[\d+\]|\(\d+\)', '', text)
    return text.strip()

def extract_text_with_ocr_fallback(pdf_path):
    """
    Attempts standard text extraction first. If no main text is found,
    falls back to OCR for text extraction.
    """
    print(f"INFO: Attempting standard text extraction for {pdf_path}...", file=sys.stderr)
    main_text, footnotes = extract_text_by_dynamic_font_size(pdf_path)

    if not main_text.strip():
        print(f"WARNING: No main text found via standard extraction for {pdf_path}. Falling back to OCR...", file=sys.stderr)
        ocr_text_parts = []
        try:
            with fitz.open(pdf_path) as doc:
                for page_num, page in enumerate(doc):
                    print(f"DEBUG: Performing OCR on page {page_num + 1} of {pdf_path}...", file=sys.stderr)
                    
                    # Attempt to get textpage with OCR flag
                    try:
                        textpage = page.get_textpage(flags=4) # Flag 4 enables OCR
                        page_ocr_text = textpage.extractText()
                        
                        if page_ocr_text.strip():
                            ocr_text_parts.append(page_ocr_text)
                            print(f"DEBUG: OCR successfully extracted text from page {page_num + 1}.", file=sys.stderr)
                        else:
                            print(f"WARNING: OCR found no text on page {page_num + 1} of {pdf_path} (extracted text was empty).", file=sys.stderr)
                    except Exception as ocr_page_e:
                        print(f"ERROR: PyMuPDF OCR failed on page {page_num + 1}: {ocr_page_e}", file=sys.stderr)
                        # If OCR fails on a page, it might still work on others, so don't re-raise immediately
            
            # If OCR found text, use it as main_text. Footnotes cannot be reliably separated.
            if ocr_text_parts:
                main_text = clean_text(" ".join(ocr_text_parts))
                footnotes = "" # OCR doesn't differentiate footnotes by font size
                print(f"INFO: Successfully extracted text from {pdf_path} using OCR.", file=sys.stderr)
            else:
                print(f"ERROR: OCR fallback also found no text for {pdf_path}. This indicates a very challenging PDF or a deeper OCR issue.", file=sys.stderr)
                raise Exception("No text extracted from PDF, even with OCR fallback.")

        except Exception as e:
            print(f"CRITICAL ERROR: OCR text extraction failed for {pdf_path}: {e}", file=sys.stderr)
            raise Exception(f"OCR text extraction failed: {e}")
    else:
        print(f"INFO: Standard text extraction successful for {pdf_path}.", file=sys.stderr)

    return main_text, footnotes

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
        # Call the new fallback function here
        main_text, footnotes = extract_text_with_ocr_fallback(file_path)
        save_extracted_text(hashcode, file.filename, main_text, footnotes)
    except Exception as e:
        return jsonify({'error': f'Error extracting text: {str(e)}'}), 500
    
    return jsonify({
        'message': 'File uploaded successfully',
        'filename': file.filename,
        'hashcode': hashcode,
        'footnotes': footnotes # Note: footnotes will be empty if OCR was used
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
    # This function expects hash_filename to include the .json extension
    path = os.path.join(PROCESSED_FOLDER, hash_filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_questions_in_lessons(questions, FILE):
    with open(FILE, "w") as f:
        json.dump(questions, f, indent=2)

def load_lessons():
    if os.path.exists(LESSONS_FILE):
        with open(LESSONS_FILE, "r") as f:
            return json.load(f)
    return []

def save_lessons(lessons):
    with open(LESSONS_FILE, "w") as f:
        json.dump(lessons, f, indent=2)

def load_subjects():
    if os.path.exists(SUBJECTS_FILE):
        with open(SUBJECTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_subjects(subjects):
    with open(SUBJECTS_FILE, "w") as f:
        json.dump(subjects, f, indent=2)

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

def make_lesson_path(hashProcessed):
    # hashProcessed should already be just the hash (no .json) from add_lesson
    LESSON_DIRECTORY = os.path.join(LESSONS_RECORD, hashProcessed)
    os.makedirs(LESSON_DIRECTORY, exist_ok=True)
    
    # load_questions expects the filename with .json, so append it here
    questions = load_questions(hashProcessed + ".json")

    # Add tracking fields to each question
    for question in questions:
        question['number_of_tries'] = 0
        question['number_of_correct_tries'] = 0

    total_questions = len(questions)
    full_chunks = total_questions // 15

    for i in range(full_chunks):
        start = i * 15
        end = start + 15
        LESSON_FILE = os.path.join(LESSON_DIRECTORY, f"lesson{i}.json")
        save_questions_in_lessons(questions[start:end], LESSON_FILE)

    # Handle leftover questions
    leftover = total_questions % 15
    if leftover:
        LESSON_FILE = os.path.join(LESSON_DIRECTORY, f"lesson{full_chunks}.json")
        save_questions_in_lessons(questions[-leftover:], LESSON_FILE)



@app.route('/add_lesson', methods=['POST'])
def add_lesson():
    data = request.get_json()
    required_fields = ["lesson_name", "subject", "date", "difficulty", "text"]
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required lesson fields'}), 400

    processed_filename = None

    def is_json_file_empty(json_path):
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    return not data  # True if [] or {}
                except json.JSONDecodeError:
                    return True
        return True

    # Run fireReq
    try:
        result = subprocess.run(
            ['python3', 'fireReq.py', data['text']],
            capture_output=True,
            text=True,
            check=True
        )
        processed_filename = result.stdout.strip()
        print(f"[INFO] fireReq.py succeeded with output: {processed_filename}")

        # Check if the output file is empty
        full_path = os.path.join("processed", f"{processed_filename}")
        if is_json_file_empty(full_path):
            print("[WARNING] fireReq.py output was empty. Deleting and falling back to huggingReq.py")
            os.remove(full_path)

            # Try huggingReq
            result = subprocess.run(
                ['python3', 'huggingReq.py', data['text']],
                capture_output=True,
                text=True,
                check=True
            )
            processed_filename = result.stdout.strip()
            print(f"[INFO] huggingReq.py succeeded with output: {processed_filename}")

            full_path = os.path.join("processed", f"{processed_filename}")
            if is_json_file_empty(full_path):
                print("[ERROR] huggingReq.py also returned empty content.")
                os.remove(full_path)
                return jsonify({'error': 'Both generation methods returned empty content.'}), 500

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] fireReq.py failed: {e.stderr}")
        print("[INFO] Falling back to huggingReq.py...")

        try:
            result = subprocess.run(
                ['python3', 'huggingReq.py', data['text']],
                capture_output=True,
                text=True,
                check=True
            )
            processed_filename = result.stdout.strip()
            print(f"[INFO] huggingReq.py succeeded with output: {processed_filename}")

            full_path = os.path.join("processed", f"{processed_filename}")
            if is_json_file_empty(full_path):
                print("[ERROR] huggingReq.py also returned empty content.")
                os.remove(full_path)
                return jsonify({'error': 'Both generation methods returned empty content.'}), 500

        except subprocess.CalledProcessError as e2:
            print(f"[ERROR] huggingReq.py also failed: {e2.stderr}")
            return jsonify({'error': 'Both generation methods failed.'}), 500

    # Clean .json extension
    if processed_filename.endswith('.json'):
        processed_filename = processed_filename[:-5]

    # Save lesson metadata
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

    make_lesson_path(processed_filename)

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
            # This returns the processed filename as stored, which should now be just the hash
            return jsonify({'lesson hash': lesson['processed filename']}), 200
    return jsonify({'error': 'Lesson not found'}), 404

@app.route('/get_lessons_for_hash')
def get_lessons_for_hash():
    hash_value = request.args.get('hash')
    if not hash_value:
        return jsonify({'error': 'Missing hash'}), 400

    # Ensure hash_value does not end with .json when used for directory name
    # This acts as a safeguard, though the frontend should now send a clean hash
    if hash_value.endswith('.json'):
        hash_value = hash_value[:-5] # Remove '.json'

    lesson_dir = os.path.join(LESSONS_RECORD, hash_value)
    if not os.path.exists(lesson_dir):
        # Log if directory not found for debugging
        print(f"DEBUG: Lesson directory not found: {lesson_dir}")
        return jsonify({'lessons': []})

    lesson_files = sorted([
        f for f in os.listdir(lesson_dir) if f.startswith('lesson') and f.endswith('.json')
    ])
    

    lesson_numbers = []
    for f in lesson_files:
        try:
            number = int(f.replace("lesson", "").replace(".json", ""))
            lesson_numbers.append(number)
        except ValueError:
            # Log if file name parsing fails
            print(f"DEBUG: Could not parse lesson number from file: {f}")
            continue

    return jsonify({'lessons': lesson_numbers})

@app.route('/get_lesson_questions', methods=['GET'])
def get_lesson_questions():
    hash_value = request.args.get('hash')
    lesson_number = request.args.get('lesson_number')

    print(f"DEBUG: get_lesson_questions - Received hash: {hash_value}, lesson_number: {lesson_number}")

    if not hash_value or lesson_number is None:
        return jsonify({'error': 'Missing parameters'}), 400

    # IMPORTANT: Ensure hash_value does not contain .json extension here if it's coming from frontend
    # (Though the add_lesson fix should prevent this, it's good to be defensive)
    if hash_value and hash_value.endswith('.json'):
        hash_value = hash_value[:-5]
        print(f"DEBUG: get_lesson_questions - Cleaned hash: {hash_value}")

    lesson_file = os.path.join(LESSONS_RECORD, hash_value, f"lesson{lesson_number}.json")
    print(f"DEBUG: get_lesson_questions - Attempting to open file: {lesson_file}")

    if not os.path.exists(lesson_file):
        print(f"DEBUG: get_lesson_questions - File NOT found: {lesson_file}")
        return jsonify({'error': 'Lesson file not found'}), 404

    with open(lesson_file, "r") as f:
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
    # This endpoint expects just the hashcode, so it will append .json to find the file
    filepath = os.path.join(PROCESSED_FOLDER, hashcode + ".json")
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': f'Failed to read file: {str(e)}'}), 500

def load_questions_from_lesson_chunk(hash_value, lesson_number):
    """
    Loads questions from a specific lesson chunk file (e.g., res/lessons/{hash}/lessonX.json).
    """
    # Ensure hash_value does not have .json extension
    if hash_value.endswith('.json'):
        hash_value = hash_value[:-5]

    lesson_file_path = os.path.join(LESSONS_RECORD, hash_value, f"lesson{lesson_number}.json")
    if os.path.exists(lesson_file_path):
        with open(lesson_file_path, 'r', encoding="utf-8") as f:
            return json.load(f)
    print(f"[ERROR][Flask] Lesson chunk file not found: {lesson_file_path}", file=sys.stderr)
    return []

def save_questions_to_lesson_chunk(hash_value, lesson_number, questions_data):
    """
    Saves the updated list of questions back to a specific lesson chunk file.
    """
    # Ensure hash_value does not have .json extension
    if hash_value.endswith('.json'):
        hash_value = hash_value[:-5]

    lesson_file_path = os.path.join(LESSONS_RECORD, hash_value, f"lesson{lesson_number}.json")
    with open(lesson_file_path, 'w', encoding="utf-8") as f:
        json.dump(questions_data, f, indent=4, ensure_ascii=False)
    print(f"[INFO][Flask] Saved updated questions to lesson chunk file: {lesson_file_path}", file=sys.stderr)


# <<<< MODIFY this existing route in your Flask app >>>>
@app.route('/update_question_stats', methods=['POST'])
def update_question_stats():
    """
    Receives updated stats (number_of_tries, number_of_correct_tries) for a specific question
    and persists them to the relevant lesson chunk JSON file.
    """
    data = request.get_json()
    if not data:
        print("[ERROR][Flask] /update_question_stats: Request body is empty or not JSON.", file=sys.stderr)
        return jsonify({'error': 'Request body must be JSON'}), 400

    hash_value = data.get('hash')
    lesson_number = data.get('lesson_number')
    question_index = data.get('question_index')
    number_of_tries = data.get('number_of_tries')
    number_of_correct_tries = data.get('number_of_correct_tries')

    # Basic validation for required fields
    if not all([hash_value, lesson_number is not None, question_index is not None,
                number_of_tries is not None, number_of_correct_tries is not None]):
        print(f"[ERROR][Flask] /update_question_stats: Missing required fields. Received: {data}", file=sys.stderr)
        return jsonify({'error': 'Missing required fields for update'}), 400

    try:
        # Load the questions from the specific lesson chunk file
        lesson_questions = load_questions_from_lesson_chunk(hash_value, lesson_number)

        if not lesson_questions:
            # This means the lesson chunk file itself was not found or was empty
            return jsonify({'error': 'Lesson chunk file not found or empty'}), 404

        # Check if the question_index is valid within this specific lesson's questions
        if 0 <= question_index < len(lesson_questions):
            question_to_update = lesson_questions[question_index]
            
            # Update the stats for the specific question
            question_to_update['number_of_tries'] = number_of_tries
            question_to_update['number_of_correct_tries'] = number_of_correct_tries
            
            # Save the entire updated list of questions back to this specific lesson file
            save_questions_to_lesson_chunk(hash_value, lesson_number, lesson_questions)
            
            print(f"[INFO][Flask] Updated stats for question {question_index} in lesson {lesson_number} (hash: {hash_value}): Tries={number_of_tries}, Correct={number_of_correct_tries}", file=sys.stderr)
            return jsonify({'message': 'Question stats updated successfully'}), 200
        else:
            print(f"[ERROR][Flask] /update_question_stats: Invalid question_index: {question_index} for lesson {lesson_number} (hash: {hash_value})", file=sys.stderr)
            return jsonify({'error': 'Invalid question index for this lesson'}), 404

    except Exception as e:
        print(f"[CRITICAL ERROR][Flask] /update_question_stats: Error updating question stats: {e}", file=sys.stderr)
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
