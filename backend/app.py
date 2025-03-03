from flask import Flask, request, jsonify, send_file
import os
import json
from pdfminer.high_level import extract_text

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
FILE_RECORD = "files.json"  # Stores filenames persistently
TEXT_RECORD = "text.json"  # Stores extracted text persistently

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Load stored filenames
def load_uploaded_files():
    if os.path.exists(FILE_RECORD):
        with open(FILE_RECORD, "r") as f:
            return json.load(f)
    return []

# Load extracted text
def load_extracted_texts():
    if os.path.exists(TEXT_RECORD):
        with open(TEXT_RECORD, "r") as f:
            return json.load(f)
    return {}

# Save filenames persistently
def save_uploaded_files(files):
    with open(FILE_RECORD, "w") as f:
        json.dump(files, f)

# Save extracted text persistently
def save_extracted_texts(texts):
    with open(TEXT_RECORD, "w") as f:
        json.dump(texts, f)

# Load previous state
uploaded_files = load_uploaded_files()
extracted_texts = load_extracted_texts()


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

    if file.filename not in uploaded_files:
        uploaded_files.append(file.filename)
        save_uploaded_files(uploaded_files)  # Save persistently

    # Extract text using pdfminer.six
    try:
        extracted_text = extract_text(file_path).strip()
        extracted_texts[file.filename] = extracted_text
        save_extracted_texts(extracted_texts)  # Save persistently
    except Exception as e:
        return jsonify({'error': f'Error extracting text: {str(e)}'}), 500

    return jsonify({'message': 'File uploaded successfully', 'files': uploaded_files}), 200


@app.route('/get_files', methods=['GET'])
def get_files():
    """Returns a list of uploaded file names."""
    return jsonify({'files': uploaded_files})


@app.route('/get_file', methods=['GET'])
def get_file():
    """Returns the uploaded PDF file for a specific filename."""
    file_name = request.args.get('file')

    if not file_name:
        return jsonify({'error': 'File name is required'}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file_name)

    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    return send_file(file_path, as_attachment=True)


@app.route('/get_file_content', methods=['GET'])
def get_file_content():
    """Returns extracted text from the uploaded PDF."""
    file_name = request.args.get('file')

    if not file_name:
        return jsonify({'error': 'File name is required'}), 400

    if file_name not in extracted_texts:
        return jsonify({'error': 'Text not found'}), 404

    return jsonify({'text': extracted_texts[file_name]})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
