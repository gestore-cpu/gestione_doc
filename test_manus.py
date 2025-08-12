#!/usr/bin/env python3
"""
Script di test per l'integrazione Manus Core.
Testa le funzionalità principali: sync, webhook, admin routes.
"""

import requests
import json
import hmac
import hashlib
import time
from datetime import datetime

# Configurazione
BASE_URL = "http://localhost:5000"
ADMIN_EMAIL = "admin@example.com"  # Sostituisci con email admin reale
ADMIN_PASSWORD = "password"  # Sostituisci con password reale

def login():
    """Login come admin e ottieni session."""
    session = requests.Session()
    
    # Login
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data)
    
    if response.status_code == 200:
        print("✅ Login admin riuscito")
        return session
    else:
        print(f"❌ Login fallito: {response.status_code}")
        return None

def test_manus_status(session):
    """Test endpoint status Manus."""
    print("\n🔍 Test endpoint status Manus...")
    
    response = session.get(f"{BASE_URL}/admin/manus/status")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Status Manus:")
        print(f"   - Manual links: {data['stats']['manual_links']}")
        print(f"   - Course links: {data['stats']['course_links']}")
        print(f"   - Completions: {data['stats']['completions']}")
        return True
    else:
        print(f"❌ Status fallito: {response.status_code}")
        return False

def test_manus_links(session):
    """Test endpoint links Manus."""
    print("\n🔗 Test endpoint links Manus...")
    
    response = session.get(f"{BASE_URL}/admin/manus/links")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Links Manus:")
        print(f"   - Manuali: {len(data['manuals'])}")
        print(f"   - Corsi: {len(data['courses'])}")
        return True
    else:
        print(f"❌ Links fallito: {response.status_code}")
        return False

def test_sync_manuals(session):
    """Test sync manuale manuali."""
    print("\n📚 Test sync manuale manuali...")
    
    sync_data = {
        "azienda_id": 1,
        "azienda_ref": "mercury"
    }
    
    response = session.post(
        f"{BASE_URL}/admin/manus/sync/manuals",
        json=sync_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Sync manuali: {data['message']}")
        return True
    else:
        print(f"❌ Sync manuali fallito: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_sync_courses(session):
    """Test sync manuale corsi."""
    print("\n🎓 Test sync manuale corsi...")
    
    sync_data = {
        "azienda_id": 1,
        "azienda_ref": "mercury"
    }
    
    response = session.post(
        f"{BASE_URL}/admin/manus/sync/courses",
        json=sync_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Sync corsi: {data['message']}")
        return True
    else:
        print(f"❌ Sync corsi fallito: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_webhook_health():
    """Test health check webhook."""
    print("\n🏥 Test health check webhook...")
    
    response = requests.get(f"{BASE_URL}/webhooks/manus/hooks/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Webhook health: {data['status']}")
        return True
    else:
        print(f"❌ Webhook health fallito: {response.status_code}")
        return False

def test_webhook_signature():
    """Test webhook con firma HMAC."""
    print("\n🔐 Test webhook con firma...")
    
    # Dati di test
    payload = {
        "course_id": "COURSE123",
        "since": "2024-01-01T00:00:00Z"
    }
    
    # Secret di test (usa quello configurato)
    secret = "test_secret"
    
    # Calcola firma HMAC
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "X-Manus-Event": "COURSE_COMPLETED",
        "X-Manus-Signature": signature
    }
    
    response = requests.post(
        f"{BASE_URL}/webhooks/manus/hooks",
        json=payload,
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Webhook con firma: {data['status']}")
        return True
    else:
        print(f"❌ Webhook con firma fallito: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def main():
    """Esegue tutti i test."""
    print("🧪 Test integrazione Manus Core")
    print("=" * 50)
    
    # Login
    session = login()
    if not session:
        print("❌ Impossibile continuare senza login")
        return
    
    # Test
    tests = [
        ("Status Manus", lambda: test_manus_status(session)),
        ("Links Manus", lambda: test_manus_links(session)),
        ("Sync Manuali", lambda: test_sync_manuals(session)),
        ("Sync Corsi", lambda: test_sync_courses(session)),
        ("Webhook Health", lambda: test_webhook_health()),
        ("Webhook Signature", lambda: test_webhook_signature())
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Errore in {test_name}: {e}")
            results.append((test_name, False))
    
    # Riepilogo
    print("\n" + "=" * 50)
    print("📊 RIEPILOGO TEST")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Risultato: {passed}/{len(results)} test passati")
    
    if passed == len(results):
        print("🎉 Tutti i test sono passati!")
    else:
        print("⚠️ Alcuni test sono falliti. Controlla la configurazione.")

if __name__ == "__main__":
    main()
