from google.cloud import storage

# Percorso del file locale che vuoi caricare
local_file_path = "esempio.pdf"  # Cambia questo se vuoi caricare un altro file

# Percorso del file JSON delle credenziali
credentials_path = "/var/www/gestione_doc/gcp_credentials.json"

# Nome del bucket e "percorso" di destinazione nel bucket
bucket_name = "mio-bucket-di-test"
destination_blob_name = "documenti/test/esempio.pdf"  # GCS non ha vere cartelle, ma usa i nomi come prefissi

# Inizializza il client
client = storage.Client.from_service_account_json(credentials_path)
bucket = client.bucket(bucket_name)
blob = bucket.blob(destination_blob_name)

# Carica il file
blob.upload_from_filename(local_file_path)

print(f"✅ File caricato su gs://{bucket_name}/{destination_blob_name}")
