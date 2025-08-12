#!/usr/bin/env python3
"""
Script di test per il monitoraggio AI post-migrazione.
Verifica le funzionalità di rilevamento comportamenti anomali.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_monitoring import AIMonitoringService
from models import User, GuestUser, AttivitaAI, AlertAI, db
from database import get_db

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_attivita_ai_creation():
    """Testa la creazione di record AttivitaAI."""
    print("🧪 Test creazione AttivitaAI...")
    
    try:
        # Simula un utente migrato
        user = User(
            username='test_user',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            role='user'
        )
        db.session.add(user)
        db.session.commit()
        
        # Crea record AttivitaAI
        attivita = AttivitaAI(
            user_id=user.id,
            stato_iniziale='nuovo_import',
            note='Utente migrato da DOCS standard in data 2024-01-15',
            created_at=datetime.utcnow() - timedelta(hours=12)  # 12 ore fa
        )
        db.session.add(attivita)
        db.session.commit()
        
        print(f"✅ AttivitaAI creata per utente {user.email}")
        print(f"   - Stato: {attivita.stato_iniziale}")
        print(f"   - Giorni da import: {attivita.giorni_da_import}")
        print(f"   - Badge class: {attivita.badge_class}")
        print(f"   - Display text: {attivita.display_text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore creazione AttivitaAI: {e}")
        return False

def test_alert_ai_creation():
    """Testa la creazione di record AlertAI."""
    print("\n🧪 Test creazione AlertAI...")
    
    try:
        # Simula un guest migrato
        guest = GuestUser(
            email='guest@example.com',
            registered_at=datetime.utcnow() - timedelta(days=1)
        )
        db.session.add(guest)
        db.session.commit()
        
        # Crea record AlertAI
        alert = AlertAI(
            guest_id=guest.id,
            tipo_alert='download_massivo',
            descrizione='Download massivo rilevato: 25 file scaricati nelle prime 24h post-migrazione',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            stato='nuovo'
        )
        db.session.add(alert)
        db.session.commit()
        
        print(f"✅ AlertAI creato per guest {guest.email}")
        print(f"   - Tipo: {alert.tipo_alert}")
        print(f"   - Stato: {alert.stato}")
        print(f"   - IP: {alert.ip_address}")
        print(f"   - Display: {alert.tipo_alert_display}")
        print(f"   - Badge class: {alert.stato_badge_class}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore creazione AlertAI: {e}")
        return False

def test_monitoring_service():
    """Testa il servizio di monitoraggio AI."""
    print("\n🧪 Test servizio monitoraggio AI...")
    
    try:
        monitoring_service = AIMonitoringService(db.session)
        
        # Test con utente esistente
        user = db.session.query(User).filter(User.email == 'test@example.com').first()
        if user:
            print(f"🔍 Testando controlli AI per utente: {user.email}")
            
            # Test controllo download massivo
            alert = monitoring_service.check_download_massivo(user_id=user.id)
            if alert:
                print(f"   ✅ Alert download massivo generato: {alert.descrizione}")
            else:
                print("   ℹ️ Nessun alert download massivo")
            
            # Test controllo accessi falliti
            alert = monitoring_service.check_accessi_falliti(user_id=user.id)
            if alert:
                print(f"   ✅ Alert accessi falliti generato: {alert.descrizione}")
            else:
                print("   ℹ️ Nessun alert accessi falliti")
            
            # Test controllo IP sospetto
            alert = monitoring_service.check_ip_sospetto(user_id=user.id, current_ip='192.168.1.100')
            if alert:
                print(f"   ✅ Alert IP sospetto generato: {alert.descrizione}")
            else:
                print("   ℹ️ Nessun alert IP sospetto")
            
            # Test controllo comportamento anomalo
            alert = monitoring_service.check_comportamento_anomalo(user_id=user.id)
            if alert:
                print(f"   ✅ Alert comportamento anomalo generato: {alert.descrizione}")
            else:
                print("   ℹ️ Nessun alert comportamento anomalo")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test servizio monitoraggio: {e}")
        return False

def test_statistics():
    """Testa le statistiche del monitoraggio AI."""
    print("\n🧪 Test statistiche monitoraggio AI...")
    
    try:
        # Conta record AttivitaAI
        total_attivita = db.session.query(AttivitaAI).count()
        nuovo_import = db.session.query(AttivitaAI).filter(
            AttivitaAI.stato_iniziale == 'nuovo_import'
        ).count()
        monitorato = db.session.query(AttivitaAI).filter(
            AttivitaAI.stato_iniziale == 'monitorato'
        ).count()
        stabile = db.session.query(AttivitaAI).filter(
            AttivitaAI.stato_iniziale == 'stabile'
        ).count()
        
        print(f"📊 Statistiche AttivitaAI:")
        print(f"   - Totale: {total_attivita}")
        print(f"   - Nuovo import: {nuovo_import}")
        print(f"   - Monitorato: {monitorato}")
        print(f"   - Stabile: {stabile}")
        
        # Conta record AlertAI
        total_alerts = db.session.query(AlertAI).count()
        nuovi_alerts = db.session.query(AlertAI).filter(
            AlertAI.stato == 'nuovo'
        ).count()
        in_revisione = db.session.query(AlertAI).filter(
            AlertAI.stato == 'in_revisione'
        ).count()
        chiusi = db.session.query(AlertAI).filter(
            AlertAI.stato == 'chiuso'
        ).count()
        
        print(f"📊 Statistiche AlertAI:")
        print(f"   - Totale: {total_alerts}")
        print(f"   - Nuovi: {nuovi_alerts}")
        print(f"   - In revisione: {in_revisione}")
        print(f"   - Chiusi: {chiusi}")
        
        # Alert per tipo
        from sqlalchemy import func
        alert_types = db.session.query(
            AlertAI.tipo_alert,
            func.count(AlertAI.id).label('count')
        ).group_by(AlertAI.tipo_alert).all()
        
        print(f"📊 Alert per tipo:")
        for tipo, count in alert_types:
            print(f"   - {tipo}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test statistiche: {e}")
        return False

def test_property_methods():
    """Testa i metodi property dei modelli."""
    print("\n🧪 Test metodi property...")
    
    try:
        # Test AttivitaAI properties
        attivita = db.session.query(AttivitaAI).first()
        if attivita:
            print(f"✅ AttivitaAI properties:")
            print(f"   - is_nuovo_import: {attivita.is_nuovo_import}")
            print(f"   - giorni_da_import: {attivita.giorni_da_import}")
            print(f"   - badge_class: {attivita.badge_class}")
            print(f"   - display_text: {attivita.display_text}")
        
        # Test AlertAI properties
        alert = db.session.query(AlertAI).first()
        if alert:
            print(f"✅ AlertAI properties:")
            print(f"   - is_nuovo: {alert.is_nuovo}")
            print(f"   - is_in_revisione: {alert.is_in_revisione}")
            print(f"   - is_chiuso: {alert.is_chiuso}")
            print(f"   - stato_badge_class: {alert.stato_badge_class}")
            print(f"   - tipo_alert_display: {alert.tipo_alert_display}")
            print(f"   - utente_display: {alert.utente_display}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test properties: {e}")
        return False

def cleanup_test_data():
    """Pulisce i dati di test."""
    print("\n🧹 Pulizia dati di test...")
    
    try:
        # Elimina record di test
        db.session.query(AlertAI).filter(
            AlertAI.descrizione.like('%test%')
        ).delete()
        
        db.session.query(AttivitaAI).filter(
            AttivitaAI.note.like('%test%')
        ).delete()
        
        db.session.query(User).filter(
            User.email == 'test@example.com'
        ).delete()
        
        db.session.query(GuestUser).filter(
            GuestUser.email == 'guest@example.com'
        ).delete()
        
        db.session.commit()
        print("✅ Dati di test puliti")
        
    except Exception as e:
        print(f"❌ Errore pulizia dati: {e}")

def main():
    """Funzione principale di test."""
    print("🚀 Avvio test monitoraggio AI post-migrazione")
    print("=" * 50)
    
    success_count = 0
    total_tests = 5
    
    # Esegui test
    if test_attivita_ai_creation():
        success_count += 1
    
    if test_alert_ai_creation():
        success_count += 1
    
    if test_monitoring_service():
        success_count += 1
    
    if test_statistics():
        success_count += 1
    
    if test_property_methods():
        success_count += 1
    
    # Risultati
    print("\n" + "=" * 50)
    print(f"📊 Risultati test: {success_count}/{total_tests} superati")
    
    if success_count == total_tests:
        print("✅ Tutti i test superati! Il monitoraggio AI è funzionante.")
        return True
    else:
        print("❌ Alcuni test falliti. Controllare i log per dettagli.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrotto dall'utente")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Errore critico: {e}")
        sys.exit(1)
    finally:
        cleanup_test_data() 