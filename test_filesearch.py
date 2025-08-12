#!/usr/bin/env python3
"""
Script di test per il File Search AI.
Testa l'upload di documenti e le query con citazioni.
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configurazione
BASE_URL = "http://localhost:5000"
LOGIN_URL = f"{BASE_URL}/login"
UPLOAD_URL = f"{BASE_URL}/ai/fs/upload"
QA_URL = f"{BASE_URL}/ai/fs/qa"

def login(username="admin@example.com", password="admin123"):
    """Effettua il login e ritorna la sessione."""
    session = requests.Session()
    
    # Ottieni il CSRF token
    response = session.get(LOGIN_URL)
    if response.status_code != 200:
        print(f"❌ Errore nell'accesso alla pagina di login: {response.status_code}")
        return None
    
    # Estrai CSRF token (semplificato)
    csrf_token = "test_token"  # In produzione, estrai dal DOM
    
    # Effettua login
    login_data = {
        "email": username,
        "password": password,
        "csrf_token": csrf_token
    }
    
    response = session.post(LOGIN_URL, data=login_data, allow_redirects=False)
    
    if response.status_code in [302, 200]:
        print(f"✅ Login effettuato con successo come {username}")
        return session
    else:
        print(f"❌ Errore nel login: {response.status_code}")
        print(f"Risposta: {response.text}")
        return None

def test_upload_document(session, doc_id):
    """Testa l'upload di un documento nel vector store."""
    print(f"\n📥 Test upload documento {doc_id}...")
    
    try:
        response = session.post(f"{UPLOAD_URL}/{doc_id}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print(f"✅ Upload completato per documento {doc_id}")
                print(f"   OpenAI File ID: {result.get('openai_file_id')}")
                return True
            else:
                print(f"❌ Upload fallito: {result.get('error')}")
                return False
        else:
            print(f"❌ Errore HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante l'upload: {e}")
        return False

def test_qa_query(session, query):
    """Testa una query Q&A con file search."""
    print(f"\n🔍 Test Q&A: '{query}'...")
    
    try:
        data = {"query": query}
        response = session.post(QA_URL, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("answer"):
                print(f"✅ Risposta ricevuta:")
                print(f"   {result['answer']}")
                return True
            else:
                print(f"❌ Risposta vuota: {result}")
                return False
        else:
            print(f"❌ Errore HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante la query: {e}")
        return False

def test_rate_limit(session):
    """Testa il rate limiting."""
    print(f"\n⏱️ Test rate limiting...")
    
    success_count = 0
    for i in range(15):  # Prova 15 chiamate rapide
        try:
            response = session.post(QA_URL, json={"query": f"Test query {i}"})
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                print(f"✅ Rate limit attivato dopo {success_count} chiamate")
                return True
        except:
            pass
    
    print(f"⚠️ Rate limit non attivato dopo {success_count} chiamate")
    return False

def main():
    """Funzione principale di test."""
    print("🤖 Test File Search AI")
    print("=" * 50)
    
    # Login
    session = login()
    if not session:
        print("❌ Impossibile continuare senza login")
        sys.exit(1)
    
    # Test upload documento (usa ID 1 come esempio)
    doc_id = 1
    if test_upload_document(session, doc_id):
        print(f"✅ Upload documento {doc_id} completato")
    else:
        print(f"⚠️ Upload documento {doc_id} fallito, continuo con i test...")
    
    # Test query Q&A
    test_queries = [
        "Qual è il contenuto principale di questo documento?",
        "Ci sono date importanti menzionate?",
        "Quali sono i punti chiave del documento?",
        "C'è qualche riferimento a procedure o processi?"
    ]
    
    for query in test_queries:
        test_qa_query(session, query)
    
    # Test rate limiting
    test_rate_limit(session)
    
    print("\n" + "=" * 50)
    print("✅ Test completati!")

if __name__ == "__main__":
    main()
