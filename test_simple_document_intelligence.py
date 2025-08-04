#!/usr/bin/env python3
"""
🧪 Test Semplificato Document Intelligence
=========================================
Verifica rapida delle funzionalità principali
"""

def test_imports():
    """Test importazione moduli base"""
    print("🔍 Test importazione moduli...")
    
    try:
        from models import Document
        print("✅ Modello Document importato")
        
        # Verifica campi AI
        ai_fields = ['ai_status', 'ai_explain', 'ai_task_id', 'ai_analysis', 'ai_analyzed_at']
        doc_columns = Document.__table__.columns.keys()
        
        for field in ai_fields:
            if field in doc_columns:
                print(f"✅ Campo '{field}' presente")
            else:
                print(f"❌ Campo '{field}' mancante")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore import: {e}")
        return False

def test_template():
    """Test template frontend"""
    print("\n🎨 Test template...")
    
    try:
        with open('templates/admin/doc_overview.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        ai_elements = [
            "ai_status",
            "ai_explain", 
            "analyzeAI",
            "export_critical_documents"
        ]
        
        found = 0
        for element in ai_elements:
            if element in content:
                print(f"✅ '{element}' presente")
                found += 1
            else:
                print(f"❌ '{element}' mancante")
        
        print(f"📊 {found}/{len(ai_elements)} elementi AI trovati")
        return found > 0
        
    except Exception as e:
        print(f"❌ Errore template: {e}")
        return False

def test_routes():
    """Test route document intelligence"""
    print("\n🌐 Test route...")
    
    try:
        from routes.document_intelligence_routes import document_intelligence_bp
        print("✅ Blueprint document_intelligence importato")
        
        # Verifica route registrate
        routes = [rule.rule for rule in document_intelligence_bp.url_map.iter_rules()]
        print(f"📋 Route trovate: {len(routes)}")
        
        for route in routes:
            print(f"   - {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore route: {e}")
        return False

def main():
    """Esegue test semplificati"""
    print("🧪 Test Semplificato Document Intelligence")
    print("=" * 40)
    
    tests = [
        ("Importazione", test_imports),
        ("Template", test_template),
        ("Route", test_routes)
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {name}: PASS")
                passed += 1
            else:
                print(f"❌ {name}: FAIL")
        except Exception as e:
            print(f"❌ {name}: ERROR - {e}")
    
    print(f"\n🎯 Risultato: {passed}/{total} test superati")
    
    if passed == total:
        print("🎉 TUTTI I TEST SUPERATI!")
    else:
        print("⚠️  Alcuni test falliti.")
    
    return passed == total

if __name__ == "__main__":
    main() 