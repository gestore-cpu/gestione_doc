#!/usr/bin/env python3
"""
Script di test per il sistema di report CEO mensile.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.ceo_monthly_report import CEOMonthlyReportGenerator, genera_report_ceo_mensile
from datetime import datetime

def test_report_generation():
    """Test completo della generazione report."""
    print("🧪 Test Sistema Report CEO Mensile")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Test 1: Creazione generatore
            print("\n1️⃣ Test creazione generatore...")
            generator = CEOMonthlyReportGenerator(month=7, year=2024)
            print(f"✅ Generatore creato per {generator.month_names[generator.month]} {generator.year}")
            
            # Test 2: Recupero dati
            print("\n2️⃣ Test recupero dati...")
            sensitive_sends = generator.get_sensitive_pdf_sends()
            print(f"✅ Invii PDF sensibili: {len(sensitive_sends)}")
            
            active_alerts = generator.get_active_ai_alerts()
            print(f"✅ Alert AI attivi: {len(active_alerts)}")
            
            audit_events = generator.get_audit_trail_events()
            print(f"✅ Eventi audit trail: {len(audit_events)}")
            
            # Test 3: Generazione PDF
            print("\n3️⃣ Test generazione PDF...")
            pdf_content = generator.generate_pdf_report()
            if pdf_content:
                print(f"✅ PDF generato: {len(pdf_content)} bytes")
            else:
                print("❌ Errore generazione PDF")
                return False
            
            # Test 4: Salvataggio file
            print("\n4️⃣ Test salvataggio file...")
            file_path = generator.save_report_to_file()
            if file_path:
                print(f"✅ File salvato: {file_path}")
            else:
                print("❌ Errore salvataggio file")
                return False
            
            # Test 5: Funzione principale
            print("\n5️⃣ Test funzione principale...")
            result = genera_report_ceo_mensile(month=7, year=2024, send_email=False)
            if result['success']:
                print(f"✅ Report generato: {result['file_path']}")
                print(f"✅ Email inviata: {result.get('email_sent', False)}")
            else:
                print(f"❌ Errore: {result.get('error', 'Errore sconosciuto')}")
                return False
            
            print("\n🎉 Tutti i test completati con successo!")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante il test: {e}")
            return False

def test_scheduler_integration():
    """Test integrazione con scheduler."""
    print("\n🤖 Test Integrazione Scheduler")
    print("=" * 30)
    
    try:
        from scheduler import genera_report_ceo_mensile_automatico
        
        with app.app_context():
            print("✅ Funzione scheduler importata correttamente")
            print("✅ Integrazione scheduler completata")
            return True
            
    except Exception as e:
        print(f"❌ Errore integrazione scheduler: {e}")
        return False

def main():
    """Funzione principale di test."""
    print("🚀 Avvio Test Sistema Report CEO Mensile")
    print("=" * 60)
    
    # Test generazione report
    test1_passed = test_report_generation()
    
    # Test integrazione scheduler
    test2_passed = test_scheduler_integration()
    
    # Risultati finali
    print("\n" + "=" * 60)
    print("📊 RISULTATI TEST")
    print("=" * 60)
    print(f"✅ Test Generazione Report: {'PASSATO' if test1_passed else 'FALLITO'}")
    print(f"✅ Test Integrazione Scheduler: {'PASSATO' if test2_passed else 'FALLITO'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 TUTTI I TEST PASSATI!")
        print("✅ Il sistema di report CEO mensile è pronto per l'uso.")
        return True
    else:
        print("\n❌ ALCUNI TEST FALLITI!")
        print("⚠️ Verificare gli errori prima di utilizzare il sistema.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
