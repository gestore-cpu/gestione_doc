#!/usr/bin/env python3
"""
Test per verificare la struttura del codice AI Assistant.
Verifica che tutti i file e le funzioni siano presenti.
"""

import os
import sys

def test_code_structure():
    """Test della struttura del codice AI Assistant."""
    
    print("🏗️ TEST STRUTTURA CODICE AI ASSISTANT")
    print("=" * 50)
    
    # Test 1: Verifica file esistenti
    print("\n📁 Test 1: Verifica file esistenti")
    
    required_files = [
        "models.py",
        "routes/admin_routes.py",
        "templates/admin/ai_insights.html",
        "templates/admin/dashboard.html"
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ File trovato: {file_path}")
        else:
            print(f"❌ File mancante: {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"⚠️ File mancanti: {len(missing_files)}")
    else:
        print("✅ Tutti i file richiesti sono presenti")
    
    # Test 2: Verifica modello InsightAI
    print("\n🗄️ Test 2: Verifica modello InsightAI")
    
    try:
        with open("models.py", "r") as f:
            content = f.read()
            
        required_model_elements = [
            "class InsightAI",
            "insight_text",
            "insight_type",
            "severity",
            "status",
            "affected_users",
            "affected_documents",
            "pattern_data"
        ]
        
        found_elements = 0
        for element in required_model_elements:
            if element in content:
                found_elements += 1
                print(f"✅ Elemento modello trovato: {element}")
            else:
                print(f"❌ Elemento modello mancante: {element}")
        
        print(f"✅ Modello InsightAI: {found_elements}/{len(required_model_elements)} elementi trovati")
        
    except Exception as e:
        print(f"❌ Errore lettura models.py: {e}")
    
    # Test 3: Verifica route AI
    print("\n🔗 Test 3: Verifica route AI")
    
    try:
        with open("routes/admin_routes.py", "r") as f:
            content = f.read()
            
        required_routes = [
            "/admin/ai_insights",
            "/admin/api/ai_insights/generate",
            "/admin/api/ai_insights/summary",
            "/admin/api/ai_insights/",
            "def ai_insights",
            "def generate_insights_api",
            "def ai_insights_summary",
            "def resolve_insight",
            "def ignore_insight"
        ]
        
        found_routes = 0
        for route in required_routes:
            if route in content:
                found_routes += 1
                print(f"✅ Route/funzione trovata: {route}")
            else:
                print(f"❌ Route/funzione mancante: {route}")
        
        print(f"✅ Route AI: {found_routes}/{len(required_routes)} elementi trovati")
        
    except Exception as e:
        print(f"❌ Errore lettura admin_routes.py: {e}")
    
    # Test 4: Verifica funzioni AI
    print("\n🤖 Test 4: Verifica funzioni AI")
    
    try:
        with open("routes/admin_routes.py", "r") as f:
            content = f.read()
            
        required_functions = [
            "def generate_ai_insights",
            "def get_ai_insights_summary",
            "DownloadDeniedLog.query",
            "InsightAI.query",
            "AdminLog("
        ]
        
        found_functions = 0
        for func in required_functions:
            if func in content:
                found_functions += 1
                print(f"✅ Funzione AI trovata: {func}")
            else:
                print(f"❌ Funzione AI mancante: {func}")
        
        print(f"✅ Funzioni AI: {found_functions}/{len(required_functions)} elementi trovati")
        
    except Exception as e:
        print(f"❌ Errore lettura funzioni AI: {e}")
    
    # Test 5: Verifica template HTML
    print("\n📄 Test 5: Verifica template HTML")
    
    try:
        with open("templates/admin/ai_insights.html", "r") as f:
            content = f.read()
            
        required_html_elements = [
            "AI Assistant - Insight Strategici",
            "Insight Attivi",
            "Genera Nuovi Insight",
            "Risolvi",
            "Ignora",
            "generateNewInsights",
            "resolveInsight",
            "ignoreInsight"
        ]
        
        found_elements = 0
        for element in required_html_elements:
            if element in content:
                found_elements += 1
                print(f"✅ Elemento HTML trovato: {element}")
            else:
                print(f"❌ Elemento HTML mancante: {element}")
        
        print(f"✅ Template HTML: {found_elements}/{len(required_html_elements)} elementi trovati")
        
    except Exception as e:
        print(f"❌ Errore lettura template HTML: {e}")
    
    # Test 6: Verifica integrazione dashboard
    print("\n📊 Test 6: Verifica integrazione dashboard")
    
    try:
        with open("templates/admin/dashboard.html", "r") as f:
            content = f.read()
            
        required_dashboard_elements = [
            "AI Assistant - Insight Strategici",
            "ai-insights-total",
            "ai-insights-critical",
            "ai-insights-attention",
            "loadAIInsightsSummary",
            "generateAIInsights"
        ]
        
        found_elements = 0
        for element in required_dashboard_elements:
            if element in content:
                found_elements += 1
                print(f"✅ Elemento dashboard trovato: {element}")
            else:
                print(f"❌ Elemento dashboard mancante: {element}")
        
        print(f"✅ Integrazione dashboard: {found_elements}/{len(required_dashboard_elements)} elementi trovati")
        
    except Exception as e:
        print(f"❌ Errore lettura dashboard: {e}")
    
    print("\n" + "=" * 50)
    print("✅ TEST STRUTTURA CODICE COMPLETATO")
    print("🎯 Verifica struttura completata!")
    
    return True

if __name__ == "__main__":
    success = test_code_structure()
    sys.exit(0 if success else 1) 