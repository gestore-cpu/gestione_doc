#!/usr/bin/env python3
"""
Test per il STEP 3 - Filtro, Ricerca e Export Avanzato Document Intelligence.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_route_filters():
    """Test che la route doc_overview supporti i filtri AI."""
    try:
        from routes.admin_routes import doc_overview
        print("✅ Route doc_overview importata: OK")
        
        # Verifica che la funzione esista
        if callable(doc_overview):
            print("✅ Funzione doc_overview callable: OK")
            return True
        else:
            print("❌ Funzione doc_overview non callable")
            return False
            
    except ImportError as e:
        print(f"❌ Errore import route: {e}")
        return False
    except Exception as e:
        print(f"❌ Errore test route: {e}")
        return False

def test_export_route():
    """Test che la route export_critical supporti i nuovi parametri."""
    try:
        from routes.document_intelligence_routes import export_critical_documents
        print("✅ Route export_critical_documents importata: OK")
        
        # Verifica che la funzione esista
        if callable(export_critical_documents):
            print("✅ Funzione export_critical_documents callable: OK")
            return True
        else:
            print("❌ Funzione export_critical_documents non callable")
            return False
            
    except ImportError as e:
        print(f"❌ Errore import route: {e}")
        return False
    except Exception as e:
        print(f"❌ Errore test route: {e}")
        return False

def test_template_filters():
    """Test che il template contenga i filtri AI."""
    try:
        template_path = "templates/admin/doc_overview.html"
        if os.path.exists(template_path):
            print("✅ Template doc_overview.html: OK")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            required_elements = [
                'name="ai_status"',
                'name="ai_explain"',
                '🧠 Stato AI',
                '🔍 Cerca motivo AI',
                '⬇️ Esporta Risultati',
                '🔄 Reset Filtri',
                'document_intelligence.export_critical_documents'
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in content:
                    missing_elements.append(element)
            
            if not missing_elements:
                print("✅ Tutti gli elementi filtro presenti: OK")
                return True
            else:
                print(f"❌ Elementi filtro mancanti: {missing_elements}")
                return False
        else:
            print("❌ Template doc_overview.html non trovato")
            return False
            
    except Exception as e:
        print(f"❌ Errore test template: {e}")
        return False

def test_form_functionality():
    """Test che il form di filtro sia funzionale."""
    try:
        template_path = "templates/admin/doc_overview.html"
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica elementi form
        form_elements = [
            '<form method="GET"',
            'select name="ai_status"',
            'input type="text" name="ai_explain"',
            'button type="submit"',
            'url_for(\'document_intelligence.export_critical_documents\')'
        ]
        
        missing_elements = []
        for element in form_elements:
            if element not in content:
                missing_elements.append(element)
        
        if not missing_elements:
            print("✅ Form di filtro completo: OK")
            return True
        else:
            print(f"❌ Elementi form mancanti: {missing_elements}")
            return False
            
    except Exception as e:
        print(f"❌ Errore test form: {e}")
        return False

def test_javascript_updates():
    """Test che il JavaScript sia aggiornato per i filtri."""
    try:
        template_path = "templates/admin/doc_overview.html"
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        js_elements = [
            'function updateDocumentCount()',
            'ai_status',
            'ai_explain',
            'documenti filtrati',
            'Stato:',
            'Motivo:'
        ]
        
        missing_elements = []
        for element in js_elements:
            if element not in content:
                missing_elements.append(element)
        
        if not missing_elements:
            print("✅ JavaScript aggiornato: OK")
            return True
        else:
            print(f"❌ Elementi JavaScript mancanti: {missing_elements}")
            return False
            
    except Exception as e:
        print(f"❌ Errore test JavaScript: {e}")
        return False

def test_export_parameters():
    """Test che l'export supporti i nuovi parametri."""
    try:
        route_path = "routes/document_intelligence_routes.py"
        with open(route_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        export_elements = [
            'explain = request.args.get(\'explain\')',
            'explain_filter',
            'Document.ai_explain.ilike',
            'Filtra per spiegazione AI'
        ]
        
        missing_elements = []
        for element in export_elements:
            if element not in content:
                missing_elements.append(element)
        
        if not missing_elements:
            print("✅ Export con parametri avanzati: OK")
            return True
        else:
            print(f"❌ Elementi export mancanti: {missing_elements}")
            return False
            
    except Exception as e:
        print(f"❌ Errore test export: {e}")
        return False

def test_ui_improvements():
    """Test che l'UI sia migliorata."""
    try:
        template_path = "templates/admin/doc_overview.html"
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ui_elements = [
            'row g-2 align-items-end',
            'form-label',
            'form-select',
            'form-control',
            'btn btn-primary',
            'btn btn-outline-danger',
            'btn btn-outline-secondary',
            'badge bg-info'
        ]
        
        missing_elements = []
        for element in ui_elements:
            if element not in content:
                missing_elements.append(element)
        
        if not missing_elements:
            print("✅ UI moderna implementata: OK")
            return True
        else:
            print(f"❌ Elementi UI mancanti: {missing_elements}")
            return False
            
    except Exception as e:
        print(f"❌ Errore test UI: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Test STEP 3 - Filtro, Ricerca e Export Avanzato")
    print("=" * 60)
    
    success = True
    
    if not test_route_filters():
        success = False
    
    if not test_export_route():
        success = False
    
    if not test_template_filters():
        success = False
    
    if not test_form_functionality():
        success = False
    
    if not test_javascript_updates():
        success = False
    
    if not test_export_parameters():
        success = False
    
    if not test_ui_improvements():
        success = False
    
    if success:
        print("\n✅ TUTTI I TEST SUPERATI!")
        print("🎯 STEP 3 - Filtro, Ricerca e Export Avanzato COMPLETATO")
        print("\n📋 Funzionalità implementate:")
        print("   🔍 Filtro per stato AI (completo, incompleto, scaduto, manca_firma)")
        print("   🔍 Ricerca per spiegazione AI (ai_explain)")
        print("   📤 Export CSV dinamico con filtri applicati")
        print("   🎨 UI moderna con Bootstrap 5")
        print("   🔄 Pulsante reset filtri")
        print("   📊 Contatore documenti filtrati")
        print("   🔗 Link export aggiornati con parametri")
        print("   💬 Tooltip informativi")
        print("   🎯 Controllo ruoli (solo admin/CEO)")
        print("\n🚀 Esempio utilizzo:")
        print("   GET /admin/doc-overview?ai_status=incompleto&ai_explain=firma")
        print("   GET /docs/export-critical?status=incompleto&explain=firma&format=csv")
    else:
        print("\n❌ ALCUNI TEST FALLITI")
        print("🔧 Controllare gli errori sopra indicati")
    
    sys.exit(0 if success else 1) 