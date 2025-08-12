#!/usr/bin/env python3
"""
Script di test per i 4 endpoint AI
"""

import requests
import json
import os

# Configurazione
BASE_URL = "https://docs.mercurysurgelati.org"
SESSION_COOKIE = "INSERISCI_COOKIE_SESSIONE"  # Sostituisci con cookie valido

def get_session():
    """Crea una sessione con cookie di autenticazione"""
    session = requests.Session()
    
    if SESSION_COOKIE != "INSERISCI_COOKIE_SESSIONE":
        session.headers.update({
            'Cookie': SESSION_COOKIE
        })
    
    session.headers.update({
        'Content-Type': 'application/json',
        'User-Agent': 'Test AI Endpoints'
    })
    
    return session

def test_summarize(session):
    """Test endpoint /ai/summarize/{doc_id}"""
    print("\n🔍 Test /ai/summarize/123")
    print("="*50)
    
    url = f"{BASE_URL}/ai/summarize/123"
    data = {
        "text": "Questo è un verbale di audit ISO 9001 per l'azienda Mercury Surgelati. L'audit è stato condotto il 15/07/2025 e ha verificato la conformità ai requisiti della norma ISO 9001:2015. Sono state identificate alcune non conformità minori che dovranno essere corrette entro 30 giorni.",
        "max_words": 50
    }
    
    try:
        response = session.post(url, json=data, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Successo!")
            print(f"Riassunto: {result.get('summary', 'N/A')}")
        else:
            print(f"❌ Errore: {response.text}")
            
    except Exception as e:
        print(f"❌ Errore: {str(e)}")

def test_tag(session):
    """Test endpoint /ai/tag/{doc_id}"""
    print("\n🏷️  Test /ai/tag/123")
    print("="*50)
    
    url = f"{BASE_URL}/ai/tag/123"
    data = {
        "text": "Fattura n. 445 del 12/07/2025, fornitore X SRL, importo €1.250,00, scadenza 30/09/2025. Documento riservato per il reparto amministrazione."
    }
    
    try:
        response = session.post(url, json=data, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Successo!")
            print(f"Tipologia: {result.get('tipologia', 'N/A')}")
            print(f"Sensibilità: {result.get('sensibilita', 'N/A')}")
            print(f"Azienda: {result.get('azienda', 'N/A')}")
            print(f"Reparto: {result.get('reparto', 'N/A')}")
            print(f"Scadenze: {result.get('scadenze', [])}")
        else:
            print(f"❌ Errore: {response.text}")
            
    except Exception as e:
        print(f"❌ Errore: {str(e)}")

def test_extract(session):
    """Test endpoint /ai/extract/{doc_id}"""
    print("\n📋 Test /ai/extract/123")
    print("="*50)
    
    url = f"{BASE_URL}/ai/extract/123"
    schema = {
        "type": "object",
        "properties": {
            "fornitore": {"type": "string"},
            "importo": {"type": "number"},
            "data_fattura": {"type": "string", "format": "date"},
            "numero_fattura": {"type": "string"}
        },
        "required": ["fornitore", "importo"]
    }
    
    data = {
        "text": "Fattura n. 445 del 12/07/2025, fornitore X SRL, importo €1.250,00, scadenza 30/09/2025.",
        "schema": schema
    }
    
    try:
        response = session.post(url, json=data, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Successo!")
            print(f"Fornitore: {result.get('fornitore', 'N/A')}")
            print(f"Importo: {result.get('importo', 'N/A')}")
            print(f"Data: {result.get('data_fattura', 'N/A')}")
            print(f"Numero: {result.get('numero_fattura', 'N/A')}")
        else:
            print(f"❌ Errore: {response.text}")
            
    except Exception as e:
        print(f"❌ Errore: {str(e)}")

def test_qa(session):
    """Test endpoint /ai/qa"""
    print("\n❓ Test /ai/qa")
    print("="*50)
    
    url = f"{BASE_URL}/ai/qa"
    data = {
        "doc_id": 123,
        "query": "Qual è la data di scadenza?",
        "text": "Fattura 445 scade il 30/09/2025."
    }
    
    try:
        response = session.post(url, json=data, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Successo!")
            print(f"Risposta: {result.get('answer', 'N/A')}")
        else:
            print(f"❌ Errore: {response.text}")
            
    except Exception as e:
        print(f"❌ Errore: {str(e)}")

def main():
    """Funzione principale"""
    print("🧪 TEST ENDPOINT AI")
    print("="*60)
    print(f"📍 URL Base: {BASE_URL}")
    print(f"⏰ Timestamp: {os.popen('date').read().strip()}")
    print("="*60)
    
    # Verifica configurazione
    if SESSION_COOKIE == "INSERISCI_COOKIE_SESSIONE":
        print("\n❌ ERRORE: Devi configurare SESSION_COOKIE!")
        print("📝 Istruzioni:")
        print("1. Accedi a https://docs.mercurysurgelati.org")
        print("2. Apri DevTools (F12) → Network")
        print("3. Fai una richiesta → Copia il cookie 'session'")
        print("4. Sostituisci SESSION_COOKIE con il valore copiato")
        return
    
    # Crea sessione
    session = get_session()
    
    # Test di connessione
    print("\n🔗 Test connessione...")
    try:
        response = session.get(BASE_URL, timeout=10)
        if response.status_code == 200:
            print("✅ Connessione OK")
        else:
            print(f"⚠️  Connessione: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Errore connessione: {str(e)}")
        return
    
    # Esegui test
    test_summarize(session)
    test_tag(session)
    test_extract(session)
    test_qa(session)
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETATO!")
    print("="*60)
    print("📋 Risultati:")
    print("• Se tutti i test sono OK: sistema AI funzionante")
    print("• Se errori 429: rate limiting attivo")
    print("• Se errori 401/403: problemi di autenticazione")
    print("• Se errori 500: problemi server/OpenAI")

if __name__ == "__main__":
    main()
