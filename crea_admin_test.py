#!/usr/bin/env python3
"""
Script per creare un utente Admin di test.
"""

import os
import sys
from datetime import datetime

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User
from extensions import bcrypt

def crea_admin():
    """
    Crea un utente Admin di test.
    """
    with app.app_context():
        # Verifica se l'utente Admin esiste già
        admin = User.query.filter_by(email='admin@test.com').first()
        if admin:
            print("✅ Utente Admin già esistente:")
            print(f"   Email: {admin.email}")
            print(f"   Username: {admin.username}")
            print(f"   Ruolo: {admin.role}")
            return
        
        # Crea il nuovo utente Admin
        password = "AdminTest123!"
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        nuovo_admin = User(
            username='admin_test',
            email='admin@test.com',
            password=hashed_password,
            first_name='Admin',
            last_name='Test',
            role='admin',
            can_download=True,
            created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(nuovo_admin)
            db.session.commit()
            print("✅ Utente Admin creato con successo!")
            print(f"   Email: {nuovo_admin.email}")
            print(f"   Username: {nuovo_admin.username}")
            print(f"   Password: {password}")
            print(f"   Ruolo: {nuovo_admin.role}")
            print("\n🔗 Puoi accedere con:")
            print(f"   URL: http://localhost:5000")
            print(f"   Email: {nuovo_admin.email}")
            print(f"   Password: {password}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Errore durante la creazione dell'Admin: {e}")

if __name__ == "__main__":
    crea_admin() 