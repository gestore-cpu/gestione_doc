#!/usr/bin/env python3
"""
Script per aggiungere la tabella notifiche_ceo al database.
"""
import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app
from extensions import db
from models import NotificaCEO

def create_notifiche_ceo_table():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tabelle create con successo!")
            
            # Verifica che la tabella sia stata creata
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'notifiche_ceo' in tables:
                print("✅ Tabella 'notifiche_ceo' creata")
            else:
                print("❌ Tabella 'notifiche_ceo' non trovata")
            
            # Verifica che la tabella log_invio_pdf esista (dipendenza)
            if 'log_invio_pdf' in tables:
                print("✅ Tabella 'log_invio_pdf' trovata (dipendenza)")
            else:
                print("⚠️ Tabella 'log_invio_pdf' non trovata (dipendenza)")
            
            print("\n🎉 Setup completato! Ora puoi utilizzare il sistema di notifiche CEO.")
            
        except Exception as e:
            print(f"❌ Errore durante la creazione delle tabelle: {e}")
            return False
    return True

if __name__ == "__main__":
    create_notifiche_ceo_table()
