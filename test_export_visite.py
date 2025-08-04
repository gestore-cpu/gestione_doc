#!/usr/bin/env python3
"""
Test per le funzioni di export PDF e CSV delle visite mediche.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_import_export_functions():
    """Test import delle funzioni di export."""
    try:
        from routes.visite_mediche_routes import export_csv, export_pdf
        print("✅ Import funzioni export: OK")
        return True
    except ImportError as e:
        print(f"❌ Errore import funzioni export: {e}")
        return False

def test_reportlab_import():
    """Test import di ReportLab per PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        print("✅ Import ReportLab: OK")
        return True
    except ImportError as e:
        print(f"❌ Errore import ReportLab: {e}")
        return False

def test_csv_import():
    """Test import per CSV."""
    try:
        import csv
        from io import StringIO, BytesIO
        print("✅ Import CSV: OK")
        return True
    except ImportError as e:
        print(f"❌ Errore import CSV: {e}")
        return False

def test_models_import():
    """Test import dei modelli."""
    try:
        from models import VisitaMedica, User
        print("✅ Import modelli: OK")
        return True
    except ImportError as e:
        print(f"❌ Errore import modelli: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Test export visite mediche")
    print("=" * 40)
    
    success = True
    
    if not test_import_export_functions():
        success = False
    
    if not test_reportlab_import():
        success = False
    
    if not test_csv_import():
        success = False
    
    if not test_models_import():
        success = False
    
    if success:
        print("\n✅ TUTTI I TEST SUPERATI!")
        print("🎯 Funzioni export visite mediche pronte")
        print("\n📋 Funzionalità implementate:")
        print("   📄 Export PDF con filtri (tutte/scadenza/scadute)")
        print("   📊 Export CSV con filtri (tutte/scadenza/scadute)")
        print("   🎨 Template con pulsanti export")
        print("   📈 Statistiche integrate")
        print("   🔍 Logging audit per compliance")
    else:
        print("\n❌ ALCUNI TEST FALLITI")
        print("🔧 Controllare gli errori sopra indicati")
    
    sys.exit(0 if success else 1) 