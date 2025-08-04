#!/usr/bin/env python3
"""
Script per creare un utente CEO di test.
"""

import os
import sys
from datetime import datetime

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User
from extensions import bcrypt

def crea_ceo():
    """
    Crea un utente CEO di test.
    """
    with app.app_context():
        # Verifica se l'utente CEO esiste già
        ceo = User.query.filter_by(email='ceo@test.com').first()
        if ceo:
            print("✅ Utente CEO già esistente:")
            print(f"   Email: {ceo.email}")
            print(f"   Username: {ceo.username}")
            print(f"   Ruolo: {ceo.role}")
            return
        
        # Crea il nuovo utente CEO
        password = "CeoTest123!"
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        nuovo_ceo = User(
            username='ceo_test',
            email='ceo@test.com',
            password=hashed_password,
            first_name='CEO',
            last_name='Test',
            role='ceo',
            can_download=True,
            created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(nuovo_ceo)
            db.session.commit()
            print("✅ Utente CEO creato con successo!")
            print(f"   Email: {nuovo_ceo.email}")
            print(f"   Username: {nuovo_ceo.username}")
            print(f"   Password: {password}")
            print(f"   Ruolo: {nuovo_ceo.role}")
            print("\n🔗 Puoi accedere con:")
            print(f"   URL: http://localhost:5000")
            print(f"   Email: {nuovo_ceo.email}")
            print(f"   Password: {password}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Errore durante la creazione del CEO: {e}")

if __name__ == "__main__":
    crea_ceo() 