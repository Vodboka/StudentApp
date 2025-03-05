from flask import Flask, request, jsonify, send_file
import os
import json
import hashlib
from pdfminer.high_level import extract_text

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
TEXTS_FOLDER = "texts"  # Directory to store JSON files
FILE_RECORD = "files.json"  # Stores uploaded filenames persistently

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEXTS_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Load stored filenames
def load_uploaded_files():
    if os.path.exists(FILE_RECORD):
        with open(FILE_RECORD, "r") as f:
            return json.load(f)
    return []

# Save filenames persistently
def save_uploaded_files(files):
    with open(FILE_RECORD, "w") as f:
        json.dump(files, f)

# Generate a unique hashcode based on file content
def generate_hash(file_path):
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()

# Save extracted text into a JSON file with hashcode as the filename
def save_extracted_text(hashcode, filename, text):
    json_path = os.path.join(TEXTS_FOLDER, f"{filename}.json")
    lesson_data = {
        "filename": filename,
        "text": text,
        "hashcode": hashcode
    }
    with open(json_path, "w") as f:
        json.dump(lesson_data, f, indent=4)

# Load extracted text from a specific JSON file
def load_extracted_text(hashcode):
    json_path = os.path.join(TEXTS_FOLDER, f"{hashcode}.json")
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            return json.load(f)
    return None

# Upload endpoint
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)

    try:
        file.save(file_path)  # Save file
    except Exception as e:
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

    hashcode = generate_hash(file_path)

    if file.filename not in load_uploaded_files():
        uploaded_files = load_uploaded_files()
        uploaded_files.append(file.filename)
        save_uploaded_files(uploaded_files)  # Save persistently

    # Extract text using pdfminer.six
    try:
        extracted_text = extract_text(file_path).strip()
        save_extracted_text(hashcode, file.filename, extracted_text)  # Save persistently
    except Exception as e:
        return jsonify({'error': f'Error extracting text: {str(e)}'}), 500

    return jsonify({
        'message': 'File uploaded successfully',
        'filename': file.filename,
        'hashcode': hashcode
    }), 200

# Get list of uploaded files
@app.route('/get_files', methods=['GET'])
def get_files():
    return jsonify({'files': load_uploaded_files()})

# Get a specific file
@app.route('/get_file', methods=['GET'])
def get_file():
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({'error': 'File name is required'}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file_name)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    return send_file(file_path, as_attachment=True)

# Get extracted text by file name
@app.route('/get_file_content', methods=['GET'])
def get_file_content():
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({'error': 'File name is required'}), 400

    lesson_data = load_extracted_text(file_name)
    if not lesson_data:
        return jsonify({'error': 'Text not found'}), 404

    return jsonify(lesson_data)

# Get all stored lessons
@app.route('/get_lessons', methods=['GET'])
def get_lessons():
    """Returns a list of all stored lesson JSON files."""
    lesson_files = [f for f in os.listdir(TEXTS_FOLDER) if f.endswith(".json")]
    return jsonify({'lessons': lesson_files})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
