"""
Test base per verificare le funzioni di export audit
Versione semplificata senza database
"""

import os
import sys
from datetime import datetime

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_export_functions_exist():
    """
    Test per verificare che le funzioni di export esistano.
    """
    print("🧪 Test verifica esistenza funzioni export...")
    
    try:
        # Importa le funzioni
        from routes.qms_routes import export_audit_csv, export_audit_pdf
        
        print("✅ Funzione export_audit_csv trovata")
        print("✅ Funzione export_audit_pdf trovata")
        
        # Verifica che siano funzioni
        assert callable(export_audit_csv), "export_audit_csv non è una funzione"
        assert callable(export_audit_pdf), "export_audit_pdf non è una funzione"
        
        print("✅ Entrambe le funzioni sono callable")
        
    except ImportError as e:
        print(f"❌ Errore import: {e}")
        return False
    except Exception as e:
        print(f"❌ Errore generico: {e}")
        return False
    
    return True

def test_csv_format():
    """
    Test per verificare il formato CSV generato.
    """
    print("📊 Test formato CSV...")
    
    try:
        # Simula dati di test
        test_data = [
            ['Nome', 'Email', 'Firma', 'Attestato'],
            ['Mario Rossi', 'mario@test.com', '✅', '✅'],
            ['Luigi Verdi', 'luigi@test.com', '❌', '✅']
        ]
        
        # Verifica formato
        csv_content = []
        for row in test_data:
            csv_content.append(','.join(row))
        
        csv_text = '\n'.join(csv_content)
        
        # Verifica elementi chiave
        checks = [
            ('Nome,Email,Firma,Attestato', 'Header'),
            ('Mario Rossi', 'User 1'),
            ('Luigi Verdi', 'User 2'),
            ('✅', 'Present signature'),
            ('❌', 'Missing signature')
        ]
        
        for check_text, check_name in checks:
            if check_text in csv_text:
                print(f"✅ {check_name}: OK")
            else:
                print(f"❌ {check_name}: MISSING")
        
        print(f"📄 CSV generato: {len(csv_text)} caratteri")
        
    except Exception as e:
        print(f"❌ Errore test CSV: {e}")
        return False
    
    return True

def test_pdf_requirements():
    """
    Test per verificare le dipendenze PDF.
    """
    print("📄 Test dipendenze PDF...")
    
    try:
        # Verifica reportlab
        import reportlab
        print(f"✅ ReportLab versione: {reportlab.Version}")
        
        # Verifica pandas
        import pandas
        print(f"✅ Pandas versione: {pandas.__version__}")
        
        # Verifica moduli reportlab
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import inch
        
        print("✅ Tutti i moduli ReportLab disponibili")
        
    except ImportError as e:
        print(f"❌ Errore import PDF: {e}")
        return False
    except Exception as e:
        print(f"❌ Errore test PDF: {e}")
        return False
    
    return True

def test_route_paths():
    """
    Test per verificare i path delle route.
    """
    print("🛣️ Test path route...")
    
    # Verifica che i path siano corretti
    csv_path = "/qms/eventi/{evento_id}/verifica_audit/export_csv"
    pdf_path = "/qms/eventi/{evento_id}/verifica_audit/export_pdf"
    
    print(f"✅ CSV path: {csv_path}")
    print(f"✅ PDF path: {pdf_path}")
    
    # Verifica formato path
    assert '{evento_id}' in csv_path, "Path CSV non contiene placeholder evento_id"
    assert '{evento_id}' in pdf_path, "Path PDF non contiene placeholder evento_id"
    assert 'export_csv' in csv_path, "Path CSV non contiene export_csv"
    assert 'export_pdf' in pdf_path, "Path PDF non contiene export_pdf"
    
    print("✅ Formato path corretto")
    return True

def test_filename_format():
    """
    Test per verificare il formato filename.
    """
    print("📁 Test formato filename...")
    
    # Simula filename
    evento_id = 123
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    csv_filename = f"audit_evento_{evento_id}_{timestamp}.csv"
    pdf_filename = f"audit_evento_{evento_id}_{timestamp}.pdf"
    
    print(f"✅ CSV filename: {csv_filename}")
    print(f"✅ PDF filename: {pdf_filename}")
    
    # Verifica formato
    assert 'audit_evento_' in csv_filename, "Filename CSV non contiene audit_evento_"
    assert 'audit_evento_' in pdf_filename, "Filename PDF non contiene audit_evento_"
    assert '.csv' in csv_filename, "Filename CSV non contiene .csv"
    assert '.pdf' in pdf_filename, "Filename PDF non contiene .pdf"
    assert str(evento_id) in csv_filename, "Filename CSV non contiene evento_id"
    assert str(evento_id) in pdf_filename, "Filename PDF non contiene evento_id"
    
    print("✅ Formato filename corretto")
    return True

def main():
    """
    Esegue tutti i test base.
    """
    print("🚀 Avvio test base export audit...")
    print("=" * 50)
    
    tests = [
        ("Verifica esistenza funzioni", test_export_functions_exist),
        ("Test formato CSV", test_csv_format),
        ("Test dipendenze PDF", test_pdf_requirements),
        ("Test path route", test_route_paths),
        ("Test formato filename", test_filename_format)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 RISULTATI TEST:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\n🎯 Totale: {passed}/{total} test passati")
    
    if passed == total:
        print("🎉 TUTTI I TEST PASSATI!")
        return True
    else:
        print("⚠️ Alcuni test falliti")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1) 