import requests

# API URL to the Meta-Llama model endpoint
API_URL = "https://router.huggingface.co/hf-inference/models/meta-llama/Llama-3.1-8B-Instruct/v1/chat/completions"


headers = {
    "Authorization": "Bearer hf_my_real_token",
}

def query(payload):
    """
    Send the request to the Hugging Face API and return the response.
    """
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

def llm(text):
    """
    Function to generate multiple-choice questions based on the provided text using Llama 3.1.
    """
    # Prepare the prompt for generating MCQs from the provided text
    prompt = f"""Based on the following text, generate multiple-choice questions to test comprehension and critical thinking.
                Each question should have four answer choices, with one correct answer and three plausible distractors.
                Ensure the questions cover key details, main ideas, and inferences from the text.
                Format the output as follows: 
                Question: [MCQ question] 
                a) [Option 1]; 
                b) [Option 2]; 
                c) [Option 3]; 
                d) [Option 4]; 
                Correct Answer: [Correct option letter]
                Generate 10 questions that test the facts presented in the text:
                {text}. """  # a paragraph has between 50-100 words, making MCQ for 1000 words

    # Prepare the payload for the API call
    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "model": "meta-llama/Llama-3.1-8B-Instruct"
    }

    # Query the API and get the response
    response = query(payload)
    
    # Extract and return the generated content from the response
    return response["choices"][0]["message"]["content"]

def getMaterials(filename):
    """
    Function to get the content of a file (could be a PDF, text file, etc.) from a local or remote source.
    Also returns the number of words in the text.
    """
    url = f"http://127.0.0.1:5000/get_file_content?file={filename}"
    response = requests.get(url)

    if response.status_code == 200:
        text = response.text
        word_count = len(text.split())
        return text, word_count  # Return both text and word count
    else:
        return f"Error {response.status_code}: {response.text}", 0  # Error message and word count = 0

def split_text_by_word_count(text, max_words=1000):
    """
    Splits a given text into chunks, each containing up to `max_words` words.
    Returns a list of text parts.
    """
    words = text.split()
    parts = []

    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        parts.append(chunk)

    return parts


text, no_words = getMaterials("DCI1.pdf")


parts = split_text_by_word_count(text, max_words=1000)

questions = []

for i, part in enumerate(parts):
    #questions.append(llm(part))
    print(part)
print(questions)
