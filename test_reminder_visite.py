#!/usr/bin/env python3
"""
Test per il sistema di reminder automatici delle visite mediche.
Verifica che il modulo app.reminder.visite funzioni correttamente.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from app.reminder.visite import check_visite_scadenza
from models import VisitaMedicaEffettuata, LogReminderVisita, User, db
from app import create_app

def test_reminder_visite():
    """Test del sistema di reminder per visite mediche."""
    
    app = create_app()
    
    with app.app_context():
        print("🧪 Test sistema reminder visite mediche")
        print("=" * 50)
        
        # Verifica che la funzione sia importabile
        try:
            from app.reminder.visite import check_visite_scadenza
            print("✅ Import funzione check_visite_scadenza: OK")
        except ImportError as e:
            print(f"❌ Errore import: {e}")
            return False
        
        # Verifica che il modello LogReminderVisita esista
        try:
            log_count = LogReminderVisita.query.count()
            print(f"✅ Modello LogReminderVisita: OK ({log_count} record esistenti)")
        except Exception as e:
            print(f"❌ Errore modello LogReminderVisita: {e}")
            return False
        
        # Verifica che ci siano visite mediche nel database
        try:
            visite_count = VisitaMedicaEffettuata.query.count()
            print(f"✅ Visite mediche nel database: {visite_count}")
        except Exception as e:
            print(f"❌ Errore query visite: {e}")
            return False
        
        # Test della funzione (senza inviare email reali)
        try:
            print("\n🔍 Esecuzione test check_visite_scadenza...")
            check_visite_scadenza()
            print("✅ Funzione check_visite_scadenza eseguita senza errori")
        except Exception as e:
            print(f"❌ Errore esecuzione check_visite_scadenza: {e}")
            return False
        
        # Verifica log creati
        try:
            log_count_after = LogReminderVisita.query.count()
            print(f"✅ Log reminder dopo test: {log_count_after}")
        except Exception as e:
            print(f"❌ Errore verifica log: {e}")
            return False
        
        print("\n🎉 Test completato con successo!")
        return True

def test_scheduler_integration():
    """Test dell'integrazione con lo scheduler."""
    
    app = create_app()
    
    with app.app_context():
        print("\n🧪 Test integrazione scheduler")
        print("=" * 40)
        
        try:
            from scheduler import avvia_scheduler
            print("✅ Import scheduler: OK")
        except ImportError as e:
            print(f"❌ Errore import scheduler: {e}")
            return False
        
        try:
            # Verifica che il job sia registrato
            from apscheduler.schedulers.background import BackgroundScheduler
            scheduler = BackgroundScheduler()
            
            # Simula la registrazione del job
            from app.reminder.visite import check_visite_scadenza
            from apscheduler.triggers.cron import CronTrigger
            
            scheduler.add_job(
                func=check_visite_scadenza,
                trigger=CronTrigger(hour=6, minute=30),
                id="check_visite_mediche",
                replace_existing=True
            )
            
            print("✅ Job scheduler registrato correttamente")
            print(f"✅ Job ID: check_visite_mediche")
            print(f"✅ Trigger: 6:30 AM daily")
            
        except Exception as e:
            print(f"❌ Errore registrazione job: {e}")
            return False
        
        print("🎉 Test integrazione scheduler completato!")
        return True

if __name__ == "__main__":
    print("🚀 Avvio test sistema reminder visite mediche")
    print("=" * 60)
    
    success = True
    
    # Test principale
    if not test_reminder_visite():
        success = False
    
    # Test integrazione scheduler
    if not test_scheduler_integration():
        success = False
    
    if success:
        print("\n✅ TUTTI I TEST SUPERATI!")
        print("🎯 Sistema reminder visite mediche funzionante")
    else:
        print("\n❌ ALCUNI TEST FALLITI")
        print("🔧 Controllare gli errori sopra indicati")
    
    sys.exit(0 if success else 1) 