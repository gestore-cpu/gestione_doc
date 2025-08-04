from google.cloud import storage

# Percorso del file JSON delle credenziali
key_path = "/var/www/gestione_doc/gcp_credentials.json"

# Inizializza il client GCS
client = storage.Client.from_service_account_json(key_path)

# Elenca tutti i bucket accessibili
print("BUCKET DISPONIBILI:")
for bucket in client.list_buckets():
    print("-", bucket.name)
