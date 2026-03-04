import requests

API_BASE_URL = "http://127.0.0.1:8000/api"
url = f"{API_BASE_URL}/pumps/find_suitable/"
params = {
    "required_flow": 200,
    "required_head": 500
}

response = requests.get(url, params=params)
print(f"Статус: {response.status_code}")
print(f"Ответ: {response.text}")