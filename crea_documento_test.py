#!/usr/bin/env python3
"""
Script per creare un documento di test.
"""

import os
import sys
from datetime import datetime

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Document, User, Company, Department, AuditLog

def crea_documento_test():
    """
    Crea un documento di test per verificare il sistema di audit log.
    """
    with app.app_context():
        # Verifica se esistono aziende e reparti
        company = Company.query.first()
        if not company:
            company = Company(name="Azienda Test")
            db.session.add(company)
            db.session.commit()
        
        department = Department.query.first()
        if not department:
            department = Department(name="Reparto Test", company_id=company.id)
            db.session.add(department)
            db.session.commit()
        
        user = User.query.first()
        if not user:
            print("❌ Nessun utente trovato nel database")
            return
        
        # Crea un documento di test
        test_doc = Document(
            title="Documento Test Audit Log",
            filename="test_document.pdf",
            original_filename="test_document.pdf",
            description="Documento di test per verificare il sistema di audit log",
            user_id=user.id,
            uploader_email=user.email,
            company_id=company.id,
            department_id=department.id,
            visibility="privato",
            downloadable=True,
            created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(test_doc)
            db.session.commit()
            print("✅ Documento di test creato con successo!")
            print(f"   ID: {test_doc.id}")
            print(f"   Titolo: {test_doc.title}")
            print(f"   Uploader: {test_doc.uploader_email}")
            print(f"   Azienda: {test_doc.company.name}")
            print(f"   Reparto: {test_doc.department.name}")
            
            # Crea alcuni log di test
            test_logs = [
                AuditLog(
                    user_id=user.id,
                    document_id=test_doc.id,
                    azione='approvazione_admin',
                    note='Test approvazione admin'
                ),
                AuditLog(
                    user_id=user.id,
                    document_id=test_doc.id,
                    azione='approvazione_ceo',
                    note='Test approvazione CEO'
                ),
                AuditLog(
                    user_id=user.id,
                    document_id=test_doc.id,
                    azione='download',
                    note='Test download documento'
                )
            ]
            
            for log in test_logs:
                db.session.add(log)
            
            db.session.commit()
            print("✅ Log di test creati con successo!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Errore durante la creazione del documento: {e}")

if __name__ == "__main__":
    crea_documento_test() 