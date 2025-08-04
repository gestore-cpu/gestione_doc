#!/usr/bin/env python3
"""
Test semplice per il sistema di reminder delle visite mediche.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Test import del modulo reminder."""
    try:
        from app.reminder.visite import check_visite_scadenza
        print("✅ Import app.reminder.visite: OK")
        return True
    except ImportError as e:
        print(f"❌ Errore import: {e}")
        return False

def test_scheduler_import():
    """Test import dello scheduler."""
    try:
        from scheduler import avvia_scheduler
        print("✅ Import scheduler: OK")
        return True
    except ImportError as e:
        print(f"❌ Errore import scheduler: {e}")
        return False

def test_models():
    """Test import dei modelli."""
    try:
        from models import LogReminderVisita, VisitaMedicaEffettuata
        print("✅ Import modelli: OK")
        return True
    except ImportError as e:
        print(f"❌ Errore import modelli: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Test semplice sistema reminder")
    print("=" * 40)
    
    success = True
    
    if not test_import():
        success = False
    
    if not test_scheduler_import():
        success = False
    
    if not test_models():
        success = False
    
    if success:
        print("\n✅ TUTTI I TEST SUPERATI!")
        print("🎯 Sistema reminder visite mediche pronto")
    else:
        print("\n❌ ALCUNI TEST FALLITI")
    
    sys.exit(0 if success else 1) 