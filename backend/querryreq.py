import requests
import re

url = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"




def getMaterials(filename):
    url = f"http://127.0.0.1:5000/get_file_content?file={filename}"
    response = requests.get(url)

    if response.status_code == 200:
        return response.text  # Returns the raw response as a string
    else:
        return f"Error {response.status_code}: {response.text}"  # Returns error details as a string
    
def split_text_preserving_words(text):
    words = text.split()  # Split into words
    num_words = len(words)
    part_size = num_words // 3  # Words per section

    part1 = " ".join(words[:part_size])  # First part
    part2 = " ".join(words[part_size:2*part_size])  # Second part
    part3 = " ".join(words[2*part_size:])  # Third part (handles extra words)

    return part1, part2, part3

def llm(query):
    parameters = {
        "max_new_tokens": 5000,
        "temperature": 0.01,
        "top_k": 50,
        "top_p": 0.95,
        "return_full_text": False
    }

    prompt = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>You are a helpful and smart teacher. You accurately provide an answer to the provided user query.<|eot_id|><|start_header_id|>user<|end_header_id|> Here is the query: ```{query}```.
        Provide a precise and concise answer.<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    prompt = prompt.replace("{query}", query)
    
    payload = {
        "inputs": prompt,
        "parameters": parameters
    }
    
    response = requests.post(url, headers=headers, json=payload)

    # Check if the response is valid
    try:
        response_json = response.json()
    except requests.exceptions.JSONDecodeError:
        return f"Error: Unable to parse JSON response. Response text: {response.text}"

    # Validate response structure
    if isinstance(response_json, list) and len(response_json) > 0 and 'generated_text' in response_json[0]:
        return response_json[0]['generated_text'].strip()
    elif isinstance(response_json, dict) and 'error' in response_json:
        return f"Error: {response_json['error']}"
    else:
        return "Error: Unexpected response format from the API."

query = """Based on the following text, generate multiple-choice questions to test comprehension and critical thinking.
           Each question should have four answer choices, with one correct answer and three plausible distractors.
           Ensure the questions cover key details, main ideas, and inferences from the text.
           Format the output as follows: Question: [MCQ question] a) [Option 1]; b) [Option 2]; c) [Option 3]; d) [Option 4]; Correct Answer: [Correct option letter]
           Generate at least 5 questions with a mix of factual, analytical, and inferential questions and put them in Here is the text:"""

part1, part2, part3 = split_text_preserving_words(getMaterials("111R.pdf"))



print(llm(query + part2))