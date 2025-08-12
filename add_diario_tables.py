#!/usr/bin/env python3
"""
Script per aggiungere le tabelle del diario CEO al database.
"""

import os
import sys
from datetime import datetime

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models import DiarioEntry, PrincipioPersonale

def create_diario_tables():
    """Crea le tabelle per il diario CEO."""
    with app.app_context():
        try:
            # Crea le tabelle
            db.create_all()
            print("✅ Tabelle create con successo!")
            
            # Verifica che le tabelle esistano
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'diario_entries' in tables:
                print("✅ Tabella 'diario_entries' creata")
            else:
                print("❌ Tabella 'diario_entries' non trovata")
                
            if 'principi_personali' in tables:
                print("✅ Tabella 'principi_personali' creata")
            else:
                print("❌ Tabella 'principi_personali' non trovata")
                
            if 'diario_principi_association' in tables:
                print("✅ Tabella 'diario_principi_association' creata")
            else:
                print("❌ Tabella 'diario_principi_association' non trovata")
                
            print("\n🎉 Setup completato! Ora puoi utilizzare il diario CEO.")
            
        except Exception as e:
            print(f"❌ Errore durante la creazione delle tabelle: {e}")
            return False
    
    return True

if __name__ == "__main__":
    create_diario_tables()
