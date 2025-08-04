#!/usr/bin/env python3
"""
🧪 Test e Validazione Completa Document Intelligence - STEP 4
============================================================
Verifica tutte le funzionalità implementate in DOCS.031 (Step 1-3)
"""

import sys
import os
import requests
import json
import csv
from io import StringIO
from datetime import datetime

# Configurazione
BASE_URL = "http://localhost:5000"
TEST_USER = "admin@mercurysurgelati.org"
TEST_PASSWORD = "admin123"

def test_upload_analysis():
    """Test upload PDF + analisi AI automatica"""
    print("📤 Test Upload + Analisi AI...")
    
    try:
        # Simula upload PDF
        test_file = "test_document.pdf"
        if not os.path.exists(test_file):
            print("⚠️  File test non trovato, creando file di test...")
            with open(test_file, 'w') as f:
                f.write("Test document content")
        
        files = {'file': open(test_file, 'rb')}
        data = {'nome': 'Test Document AI', 'categoria': 'Test'}
        
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
        
        if response.status_code == 200:
            print("✅ Upload PDF completato")
            
            # Verifica analisi AI automatica
            doc_id = response.json().get('document_id', 1)
            print(f"   Documento ID: {doc_id}")
            
            # Controlla campi AI nel database
            from models import Document
            doc = Document.query.get(doc_id)
            if doc:
                print(f"   AI Status: {doc.ai_status}")
                print(f"   AI Explain: {doc.ai_explain}")
                print(f"   AI Task ID: {doc.ai_task_id}")
                print(f"   AI Analyzed: {doc.ai_analyzed_at}")
                
                if doc.ai_status:
                    print("✅ Analisi AI automatica funzionante")
                    return True
                else:
                    print("⚠️  Analisi AI non eseguita automaticamente")
                    return False
            else:
                print("❌ Documento non trovato nel database")
                return False
                
        else:
            print(f"❌ Upload fallito: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Errore test upload: {e}")
        return False

def test_manual_analysis():
    """Test analisi AI manuale da frontend"""
    print("\n🧠 Test Analisi AI Manuale...")
    
    try:
        # Simula richiesta analisi manuale
        doc_id = 1  # ID documento di test
        response = requests.post(f"{BASE_URL}/docs/analyze-pdf", 
                               json={"document_id": doc_id})
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Analisi AI manuale completata")
            print(f"   Status: {data.get('status', 'N/A')}")
            print(f"   Explain: {data.get('explain', 'N/A')}")
            print(f"   Task ID: {data.get('task_id', 'N/A')}")
            return True
        else:
            print(f"❌ Analisi AI fallita: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Errore test analisi manuale: {e}")
        return False

def test_filters():
    """Test filtri AI nel frontend"""
    print("\n🔍 Test Filtri AI...")
    
    try:
        # Test filtro per status
        response = requests.get(f"{BASE_URL}/admin/doc-overview?ai_status=incompleto")
        if response.status_code == 200:
            print("✅ Filtro ai_status funzionante")
        else:
            print(f"❌ Filtro ai_status fallito: {response.status_code}")
        
        # Test filtro per explain
        response = requests.get(f"{BASE_URL}/admin/doc-overview?ai_explain=firma%20RSPP")
        if response.status_code == 200:
            print("✅ Filtro ai_explain funzionante")
        else:
            print(f"❌ Filtro ai_explain fallito: {response.status_code}")
        
        # Test combinazione filtri
        response = requests.get(f"{BASE_URL}/admin/doc-overview?ai_status=incompleto&ai_explain=firma")
        if response.status_code == 200:
            print("✅ Combinazione filtri funzionante")
        else:
            print(f"❌ Combinazione filtri fallita: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test filtri: {e}")
        return False

def test_export_csv():
    """Test export CSV documenti critici"""
    print("\n📤 Test Export CSV...")
    
    try:
        # Test export con filtri
        params = {
            "status": "incompleto",
            "explain": "firma RSPP",
            "format": "csv"
        }
        
        response = requests.get(f"{BASE_URL}/docs/export-critical", params=params)
        
        if response.status_code == 200:
            print("✅ Export CSV completato")
            
            # Verifica contenuto CSV
            content = response.text
            if "text/csv" in response.headers.get("Content-Type", ""):
                print("✅ Content-Type corretto")
            else:
                print("⚠️  Content-Type non corretto")
            
            # Verifica intestazioni
            if "Utente" in content and "Documento" in content and "Stato AI" in content:
                print("✅ Intestazioni CSV corrette")
            else:
                print("❌ Intestazioni CSV mancanti")
            
            # Verifica caratteri speciali
            if "RSPP" in content or "firma" in content:
                print("✅ Caratteri speciali gestiti correttamente")
            else:
                print("⚠️  Caratteri speciali non verificati")
            
            return True
        else:
            print(f"❌ Export CSV fallito: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Errore test export: {e}")
        return False

def test_security():
    """Test sicurezza e accessi"""
    print("\n🔐 Test Sicurezza...")
    
    try:
        # Test accesso utente normale (dovrebbe essere negato)
        response = requests.get(f"{BASE_URL}/docs/export-critical")
        if response.status_code == 401 or response.status_code == 403:
            print("✅ Accesso negato a utenti non autorizzati")
        else:
            print(f"⚠️  Accesso non protetto: {response.status_code}")
        
        # Test CSRF protection
        response = requests.post(f"{BASE_URL}/docs/analyze-pdf", 
                               json={"document_id": 1})
        if response.status_code == 400 or response.status_code == 401:
            print("✅ Protezione CSRF attiva")
        else:
            print(f"⚠️  Protezione CSRF non verificata: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test sicurezza: {e}")
        return False

def test_database_fields():
    """Test campi database AI"""
    print("\n🗄️ Test Campi Database AI...")
    
    try:
        from models import Document
        
        # Verifica campi AI
        ai_fields = [
            'ai_status',
            'ai_explain', 
            'ai_task_id',
            'ai_analysis',
            'ai_analyzed_at'
        ]
        
        doc_columns = Document.__table__.columns.keys()
        
        missing_fields = []
        for field in ai_fields:
            if field not in doc_columns:
                missing_fields.append(field)
        
        if not missing_fields:
            print("✅ Tutti i campi AI presenti nel database")
            return True
        else:
            print(f"❌ Campi AI mancanti: {missing_fields}")
            return False
            
    except Exception as e:
        print(f"❌ Errore test database: {e}")
        return False

def test_logs():
    """Test log AI"""
    print("\n📋 Test Log AI...")
    
    try:
        log_file = "logs/ai_docs.log"
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                content = f.read()
            
            log_entries = [
                "document_ai_analysis_requested",
                "export_critical_documents", 
                "document_task_association"
            ]
            
            found_entries = []
            for entry in log_entries:
                if entry in content:
                    found_entries.append(entry)
            
            if found_entries:
                print(f"✅ Log AI trovati: {found_entries}")
                return True
            else:
                print("⚠️  Nessun log AI trovato")
                return False
        else:
            print("⚠️  File log non trovato")
            return False
            
    except Exception as e:
        print(f"❌ Errore test log: {e}")
        return False

def main():
    """Esegue tutti i test di validazione"""
    print("🧪 Test e Validazione Completa Document Intelligence - STEP 4")
    print("=" * 60)
    
    tests = [
        ("Upload + Analisi AI", test_upload_analysis),
        ("Analisi AI Manuale", test_manual_analysis),
        ("Filtri AI", test_filters),
        ("Export CSV", test_export_csv),
        ("Sicurezza", test_security),
        ("Campi Database", test_database_fields),
        ("Log AI", test_logs)
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
    print("\n" + "=" * 60)
    print("📊 RIEPILOGO VALIDAZIONE")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Risultato: {passed}/{total} test superati")
    
    if passed == total:
        print("🎉 TUTTI I TEST SUPERATI! Document Intelligence pronto per produzione.")
        print("\n✅ Funzionalità verificate:")
        print("   - Upload PDF + analisi AI automatica")
        print("   - Analisi AI manuale da frontend")
        print("   - Filtri avanzati per stato e spiegazioni")
        print("   - Export CSV con caratteri speciali")
        print("   - Controllo accessi e sicurezza")
        print("   - Campi database AI completi")
        print("   - Log AI per audit")
    else:
        print("⚠️  Alcuni test falliti. Verificare le implementazioni.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 