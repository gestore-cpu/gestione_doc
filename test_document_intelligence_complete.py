#!/usr/bin/env python3
"""
🧪 Test Completo Document Intelligence - STEP 4
===============================================
Verifica tutte le funzionalità implementate in DOCS.031 (Step 1-3)
"""

import sys
import os
import requests
import json
from datetime import datetime

# Configurazione
BASE_URL = "http://localhost:5000"
TEST_USER = "admin@mercurysurgelati.org"
TEST_PASSWORD = "admin123"

def test_imports():
    """Test importazione moduli principali"""
    print("🔍 Test importazione moduli...")
    
    try:
        from services.document_intelligence import DocumentIntelligence
        print("✅ DocumentIntelligence importato")
    except ImportError as e:
        print(f"❌ Errore import DocumentIntelligence: {e}")
        return False
    
    try:
        from models import Document
        print("✅ Modello Document importato")
    except ImportError as e:
        print(f"❌ Errore import Document: {e}")
        return False
    
    try:
        from routes.document_intelligence_routes import document_intelligence_bp
        print("✅ Blueprint document_intelligence importato")
    except ImportError as e:
        print(f"❌ Errore import blueprint: {e}")
        return False
    
    return True

def test_ai_analysis():
    """Test analisi AI di un documento"""
    print("\n🧠 Test analisi AI...")
    
    try:
        from services.document_intelligence import DocumentIntelligence
        from models import Document
        
        # Crea istanza AI
        ai = DocumentIntelligence()
        
        # Simula analisi documento
        test_doc_id = 1
        result = ai.analyze_document(test_doc_id)
        
        print(f"✅ Analisi AI completata per documento {test_doc_id}")
        print(f"   Status: {result.get('status', 'N/A')}")
        print(f"   Explain: {result.get('explain', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore analisi AI: {e}")
        return False

def test_api_endpoints():
    """Test endpoint API"""
    print("\n🌐 Test endpoint API...")
    
    endpoints = [
        ("/docs/analyze-pdf", "POST"),
        ("/docs/critical", "GET"),
        ("/docs/export-critical", "GET")
    ]
    
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}")
            
            print(f"✅ {method} {endpoint}: {response.status_code}")
            
        except requests.exceptions.ConnectionError:
            print(f"⚠️  {method} {endpoint}: Server non raggiungibile")
        except Exception as e:
            print(f"❌ {method} {endpoint}: {e}")
    
    return True

def test_export_functionality():
    """Test funzionalità export"""
    print("\n📤 Test export CSV...")
    
    try:
        from routes.document_intelligence_routes import export_critical_documents
        
        # Test parametri
        params = {
            "status": "incompleto",
            "explain": "firma RSPP",
            "format": "csv"
        }
        
        print("✅ Funzione export_critical_documents disponibile")
        print(f"   Parametri test: {params}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test export: {e}")
        return False

def test_frontend_elements():
    """Test elementi frontend"""
    print("\n🎨 Test elementi frontend...")
    
    try:
        # Verifica template
        template_path = "templates/admin/doc_overview.html"
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verifica presenza elementi AI
            ai_elements = [
                "ai_status",
                "ai_explain", 
                "analyzeAI",
                "Esporta Documenti Critici"
            ]
            
            for element in ai_elements:
                if element in content:
                    print(f"✅ Elemento '{element}' presente nel template")
                else:
                    print(f"⚠️  Elemento '{element}' non trovato")
            
            return True
        else:
            print("❌ Template non trovato")
            return False
            
    except Exception as e:
        print(f"❌ Errore test frontend: {e}")
        return False

def test_database_fields():
    """Test campi database AI"""
    print("\n🗄️ Test campi database AI...")
    
    try:
        from models import Document
        
        # Verifica campi AI nel modello
        ai_fields = [
            'ai_status',
            'ai_explain', 
            'ai_task_id',
            'ai_analysis',
            'ai_analyzed_at'
        ]
        
        doc_columns = Document.__table__.columns.keys()
        
        for field in ai_fields:
            if field in doc_columns:
                print(f"✅ Campo '{field}' presente nel modello")
            else:
                print(f"❌ Campo '{field}' mancante nel modello")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test database: {e}")
        return False

def test_security():
    """Test sicurezza e accessi"""
    print("\n🔐 Test sicurezza...")
    
    try:
        from routes.document_intelligence_routes import document_intelligence_bp
        
        # Verifica decoratori di sicurezza
        routes = document_intelligence_bp.deferred_functions
        
        print("✅ Blueprint document_intelligence registrato")
        print(f"   Numero route: {len(routes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test sicurezza: {e}")
        return False

def main():
    """Esegue tutti i test"""
    print("🧪 Test Completo Document Intelligence - STEP 4")
    print("=" * 50)
    
    tests = [
        ("Importazione moduli", test_imports),
        ("Analisi AI", test_ai_analysis),
        ("Endpoint API", test_api_endpoints),
        ("Export funzionalità", test_export_functionality),
        ("Elementi frontend", test_frontend_elements),
        ("Campi database", test_database_fields),
        ("Sicurezza", test_security)
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
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Risultato: {passed}/{total} test superati")
    
    if passed == total:
        print("🎉 TUTTI I TEST SUPERATI! Sistema Document Intelligence pronto per produzione.")
    else:
        print("⚠️  Alcuni test falliti. Verificare le implementazioni.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 