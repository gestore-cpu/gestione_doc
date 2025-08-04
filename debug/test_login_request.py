import requests

url = "http://127.0.0.1:5001/auth/login"

try:
    response = requests.get(url)
    print(f"✅ STATUS: {response.status_code}")
    print("==== HEADERS ====")
    print(response.headers)
    print("==== HTML (first 500 chars) ====")
    print(response.text[:500])
except Exception as e:
    print(f"❌ Errore durante la richiesta a {url}:\n{e}") 