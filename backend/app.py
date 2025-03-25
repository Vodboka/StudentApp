from flask import Flask, request, jsonify, send_file
import os
import json
import hashlib
import fitz  # PyMuPDF for PDF text extraction
import re
from collections import Counter  # To find most common font size

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

# Save extracted text into a JSON file
def save_extracted_text(hashcode, filename, main_text, footnotes):
    """Saves extracted text and footnotes in a structured JSON format."""
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

# Determine the dominant font size in the document
def get_dominant_font_size(pdf_path):
    """Finds the most common font size in the document to use as a baseline."""
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
    return 10  # Fallback value if no text is found

# Extract main text and footnotes using a dynamic font size threshold
def extract_text_by_dynamic_font_size(pdf_path):
    """Extracts text from a PDF, separating main text and footnotes using dynamic font size."""
    main_text, footnotes = [], []

    dominant_font_size = get_dominant_font_size(pdf_path)
    footnote_threshold = dominant_font_size * 0.9  # Footnotes usually smaller than this

    with fitz.open(pdf_path) as doc:
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            font_size = span["size"]

                            # Identify footnotes: usually smaller font
                            if font_size < footnote_threshold:
                                footnotes.append(text)
                            else:
                                main_text.append(text)

    # Clean text properly
    main_text_cleaned = clean_text(" ".join(main_text))
    footnotes_cleaned = clean_text(" ".join(footnotes))

    return main_text_cleaned, footnotes_cleaned

def clean_text(text):
    """Cleans text by removing extra spaces and unwanted characters."""
    text = re.sub(r'\s+', ' ', text)  # Remove extra spaces
    text = re.sub(r'(\.{2,}|,{2,}|-{2,}|\s{2,})', ' ', text)  # Remove repeated symbols
    text = re.sub(r'\[\d+\]|\(\d+\)', '', text)  # Remove footnote reference numbers
    return text.strip()

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

    # Extract and clean text, separating main text and footnotes
    try:
        main_text, footnotes = extract_text_by_dynamic_font_size(file_path)
        save_extracted_text(hashcode, file.filename, main_text, footnotes)  # Save persistently
    except Exception as e:
        return jsonify({'error': f'Error extracting text: {str(e)}'}), 500

    return jsonify({
        'message': 'File uploaded successfully',
        'filename': file.filename,
        'hashcode': hashcode,
        'footnotes': footnotes  # Properly extracted footnotes
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

    json_path = os.path.join(TEXTS_FOLDER, f"{os.path.splitext(file_name)[0]}.json")
    if not os.path.exists(json_path):
        return jsonify({'error': 'Text not found'}), 404

    with open(json_path, "r") as f:
        lesson_data = json.load(f)

    # Extract only the main_text from the content part
    main_text = lesson_data.get("content", {}).get("main_text", "")

    if not main_text:
        return jsonify({'error': 'Main text not found'}), 404

    return jsonify({'main_text': main_text})


# Run Flask App
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
