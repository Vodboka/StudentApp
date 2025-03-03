from flask import Flask, request, jsonify
import os
import pytesseract
from pdf2image import convert_from_path

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the uploads folder exists
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

uploaded_files = []  # Stores file names
extracted_texts = {}  # Stores extracted text for each file


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        print("No file in request")
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        print("File has no name")
        return jsonify({'error': 'No selected file'}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    print(f"Saving file to: {file_path}")

    try:
        file.save(file_path)  # Save file
    except Exception as e:
        print(f"File save error: {str(e)}")
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

    uploaded_files.append(file.filename)  # Store filename in list

    # Convert PDF to Images
    try:
        images = convert_from_path(file_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img) + "\n"

        extracted_texts[file.filename] = text.strip()
        print("Text extracted successfully!")
    except Exception as e:
        print(f"OCR error: {str(e)}")
        return jsonify({'error': f'Error extracting text: {str(e)}'}), 500

    return jsonify({'message': 'File uploaded successfully', 'files': uploaded_files}), 200


@app.route('/get_files', methods=['GET'])
def get_files():
    """Returns a list of uploaded file names."""
    return jsonify({'files': uploaded_files})


@app.route('/get_text', methods=['GET'])
def get_text():
    """Returns extracted text for a specific file."""
    file_name = request.args.get('file')

    if not file_name:
        return jsonify({'error': 'File name is required'}), 400

    if file_name not in extracted_texts:
        return jsonify({'error': 'File not found or text not extracted'}), 404

    return jsonify({'extracted_text': extracted_texts[file_name]})

@app.route('/get_file_content', methods=['GET'])
def get_file_content():
    file_name = request.args.get('file')
    if file_name in extracted_texts:
        return jsonify({'text': extracted_texts[file_name]})
    return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
