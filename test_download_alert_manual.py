#!/usr/bin/env python3
"""
Script di test manuale per il sistema Download Alert
Testa direttamente il service senza HTTP requests
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from models import db, DownloadLog, User, Document, DownloadAlert
from services.download_alert_service import run_download_detection
from app import app
import random

def test_detection_service():
    """Testa direttamente il service di detection"""
    print("🔍 Testando service di detection...")
    
    # Pulisci alert esistenti di test
    DownloadAlert.query.filter(DownloadAlert.details.contains({"test": True})).delete()
    db.session.commit()
    
    # Esegui detection
    try:
        alerts = run_download_detection(datetime.utcnow())
        print(f"✅ Detection completato: {len(alerts)} alert creati")
        
        # Mostra risultati
        for alert in alerts:
            print(f"\n📊 Alert {alert.id}:")
            print(f"   Regola: {alert.rule}")
            print(f"   Severità: {alert.severity.value}")
            print(f"   Stato: {alert.status.value}")
            print(f"   IP: {alert.ip_address}")
            print(f"   Finestra: {alert.window_from.strftime('%H:%M')} - {alert.window_to.strftime('%H:%M')}")
            
            if alert.details:
                print(f"   Dettagli: {alert.details}")
        
        return alerts
        
    except Exception as e:
        print(f"❌ Errore durante detection: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_dashboard_data():
    """Testa i dati per la dashboard"""
    print("\n📊 Testando dati dashboard...")
    
    try:
        # Statistiche
        new_24h = DownloadAlert.query.filter(
            DownloadAlert.status == DownloadAlert.status.NEW,
            DownloadAlert.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        critical_24h = DownloadAlert.query.filter(
            DownloadAlert.severity == DownloadAlert.severity.CRITICAL,
            DownloadAlert.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        total = DownloadAlert.query.count()
        
        print(f"📈 Statistiche:")
        print(f"   Nuovi (24h): {new_24h}")
        print(f"   Critici (24h): {critical_24h}")
        print(f"   Totali: {total}")
        
    except Exception as e:
        print(f"❌ Errore durante test dashboard: {str(e)}")

def test_scheduler_job():
    """Testa che il job scheduler sia registrato"""
    print("\n⏰ Testando job scheduler...")
    
    try:
        from scheduler_config import scheduler
        
        # Controlla se il job è registrato
        jobs = scheduler.get_jobs()
        download_job = None
        
        for job in jobs:
            if 'detect_suspicious_downloads' in str(job.func):
                download_job = job
                break
        
        if download_job:
            print(f"✅ Job scheduler trovato:")
            print(f"   ID: {download_job.id}")
            print(f"   Trigger: {download_job.trigger}")
            print(f"   Prossima esecuzione: {download_job.next_run_time}")
        else:
            print("⚠️  Job scheduler non trovato")
            
    except Exception as e:
        print(f"❌ Errore durante test scheduler: {str(e)}")

def main():
    """Funzione principale"""
    print("🧪 TEST MANUALE SISTEMA DOWNLOAD ALERT")
    print("="*50)
    
    with app.app_context():
        try:
            # Testa scheduler
            test_scheduler_job()
            
            # Testa detection
            alerts = test_detection_service()
            
            # Testa dashboard
            test_dashboard_data()
            
            print("\n" + "="*50)
            print("✅ TEST COMPLETATO!")
            print("="*50)
            
            if alerts:
                print(f"🎯 Alert rilevati: {len(alerts)}")
                for alert in alerts:
                    print(f"   • {alert.rule}: {alert.severity.value}")
            else:
                print("⚠️  Nessun alert rilevato")
            
            print("\n📋 Prossimi passi:")
            print("1. 🔍 Controlla /admin/download-alerts")
            print("2. 📧 Verifica email per alert critici")
            print("3. 🔧 Testa azioni admin")
            print("4. ⏰ Aspetta 10 minuti per prossima esecuzione scheduler")
            
        except Exception as e:
            print(f"❌ Errore durante il test: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
