import requests

url = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.3-70B-Instruct"
token = ""



def getMaterials(filename):
    url = "http://127.0.0.1:5000/get_file_content?file=" + filename
    response = requests.get(url)

    print(response.status_code)  # HTTP status code (e.g., 200)
    print(response.json())

getMaterials("103A.pdf")