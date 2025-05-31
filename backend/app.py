from flask import Flask, request, jsonify, send_file, make_response
import os
import json
import hashlib
import fitz  # PyMuPDF for PDF text extraction
import re
from collections import Counter
import subprocess
import fireReq

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
os.makedirs(PROCESSED_FOLDER, exist_ok=True) # Ensure processed folder exists

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
    # This call to make_lesson_path with a hardcoded hash might be for testing.
    # In a real application, this should be triggered by a lesson creation event.
    make_lesson_path("43c64af6")
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
    try:
        result = subprocess.run(
            ['python3', 'fireReq.py', data['text']],
            capture_output=True,
            text=True,
            check=True
        )
        processed_filename = result.stdout.strip()
        # CRITICAL FIX: Ensure processed_filename does not contain .json extension
        # This makes sure that the hash stored and passed around is clean.
        if processed_filename.endswith('.json'):
            processed_filename = processed_filename[:-5] # Remove '.json'

    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Script error: {e.stderr}'}), 500
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
        'processed filename': processed_filename # Store just the hash here
    })
    save_lessons(lessons)
    make_lesson_path(processed_filename) # Pass just the hash
    return jsonify({
        'message': f'Lesson "{data["lesson_name"]}" added successfully under subject "{subject}"',
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
