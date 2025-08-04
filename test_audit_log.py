#!/usr/bin/env python3
"""
Script di test per il sistema di audit log.
"""

import os
import sys
from datetime import datetime

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import AuditLog, User, Document

def test_audit_log():
    """
    Test del sistema di audit log.
    """
    with app.app_context():
        print("🔍 Test Sistema Audit Log")
        print("=" * 50)
        
        # Conta i log esistenti
        total_logs = AuditLog.query.count()
        print(f"📊 Totale log esistenti: {total_logs}")
        
        # Statistiche per tipo di azione
        azioni = db.session.query(AuditLog.azione, db.func.count(AuditLog.id)).group_by(AuditLog.azione).all()
        print("\n📈 Statistiche per tipo di azione:")
        for azione, count in azioni:
            print(f"   {azione}: {count}")
        
        # Ultimi 5 log
        recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()
        print(f"\n📋 Ultimi 5 log:")
        for log in recent_logs:
            print(f"   [{log.timestamp.strftime('%d/%m/%Y %H:%M')}] "
                  f"{log.user.username if log.user else 'N/A'} - "
                  f"{log.azione_display} - "
                  f"{log.document.title if log.document else 'N/A'}")
        
        # Test creazione log di test
        print(f"\n🧪 Creazione log di test...")
        test_user = User.query.first()
        test_doc = Document.query.first()
        
        if test_user and test_doc:
            test_log = AuditLog(
                user_id=test_user.id,
                document_id=test_doc.id,
                azione='test',
                note='Log di test per verifica sistema'
            )
            db.session.add(test_log)
            db.session.commit()
            print(f"✅ Log di test creato con ID: {test_log.id}")
            
            # Rimuovi il log di test
            db.session.delete(test_log)
            db.session.commit()
            print(f"🗑️ Log di test rimosso")
        else:
            print("❌ Impossibile creare log di test: mancano utenti o documenti")
        
        print(f"\n✅ Test completato!")

if __name__ == "__main__":
    test_audit_log() 