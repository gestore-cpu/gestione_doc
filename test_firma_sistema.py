#!/usr/bin/env python3
"""
Script di test per il sistema di firma con conferma email.
"""

import os
import sys
from datetime import datetime

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import DocumentReadLog, User, Document, AuditLog

def test_sistema_firma():
    """
    Test del sistema di firma con conferma email.
    """
    with app.app_context():
        print("🔐 Test Sistema Firma con Conferma Email")
        print("=" * 60)
        
        # Ottieni utente e documento di test
        user = User.query.first()
        doc = Document.query.first()
        
        if not user or not doc:
            print("❌ Manca utente o documento di test")
            return
        
        print(f"👤 Utente: {user.username} ({user.email})")
        print(f"📄 Documento: {doc.title or doc.original_filename}")
        print()
        
        # Verifica firme esistenti
        firme_esistenti = DocumentReadLog.query.filter_by(
            user_id=user.id,
            document_id=doc.id
        ).all()
        
        print(f"📊 Firme esistenti: {len(firme_esistenti)}")
        
        for i, firma in enumerate(firme_esistenti, 1):
            print(f"   {i}. ID: {firma.id}")
            print(f"      Data: {firma.timestamp.strftime('%d/%m/%Y %H:%M')}")
            print(f"      Confermata: {'✅' if firma.confermata else '⏳'}")
            if firma.data_conferma:
                print(f"      Data conferma: {firma.data_conferma.strftime('%d/%m/%Y %H:%M')}")
            print(f"      Token: {firma.token_conferma[:20]}...")
            print()
        
        # Test creazione nuova firma
        print("🧪 Test creazione nuova firma...")
        
        # Rimuovi firme esistenti per test pulito
        for firma in firme_esistenti:
            db.session.delete(firma)
        db.session.commit()
        
        # Crea nuova firma di test
        nuova_firma = DocumentReadLog(
            user_id=user.id,
            document_id=doc.id,
            timestamp=datetime.utcnow(),
            confermata=False,
            token_conferma="test_token_123456789"
        )
        
        try:
            db.session.add(nuova_firma)
            db.session.commit()
            print(f"✅ Firma di test creata con ID: {nuova_firma.id}")
            print(f"   Token: {nuova_firma.token_conferma}")
            print(f"   Confermata: {'✅' if nuova_firma.confermata else '⏳'}")
            
            # Test conferma firma
            print("\n🧪 Test conferma firma...")
            nuova_firma.confermata = True
            nuova_firma.data_conferma = datetime.utcnow()
            db.session.commit()
            
            print(f"✅ Firma confermata!")
            print(f"   Data conferma: {nuova_firma.data_conferma.strftime('%d/%m/%Y %H:%M')}")
            
            # Verifica audit log
            audit_logs = AuditLog.query.filter_by(
                user_id=user.id,
                document_id=doc.id,
                azione='firma'
            ).all()
            
            print(f"\n📋 Audit log per firme: {len(audit_logs)}")
            for log in audit_logs:
                print(f"   - {log.timestamp.strftime('%d/%m/%Y %H:%M')}: {log.note}")
            
            # Rimuovi firma di test
            db.session.delete(nuova_firma)
            db.session.commit()
            print(f"\n🗑️ Firma di test rimossa")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Errore durante il test: {e}")
        
        print(f"\n✅ Test completato!")

if __name__ == "__main__":
    test_sistema_firma() 