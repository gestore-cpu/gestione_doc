from google.oauth2 import service_account
from googleapiclient.discovery import build

# Percorso alle credenziali
creds = service_account.Credentials.from_service_account_file("credentials.json")

# Inizializza il servizio Google Drive
service = build('drive', 'v3', credentials=creds)

# Richiesta dei primi 5 file
results = service.files().list(pageSize=5, fields="files(id, name)").execute()
items = results.get('files', [])

# Stampa il risultato
if not items:
    print("❌ Nessun file trovato.")
else:
    print("✅ Connessione riuscita. Ecco i file trovati:")
    for item in items:
        print(f"{item['name']} ({item['id']})")
