#!/usr/bin/env python3
"""
Script per creare la tabella firme_documenti nel database.
Questo script aggiunge direttamente la tabella senza usare Flask-Migrate.
"""

import sys
import os

# Aggiungi il percorso del progetto al Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Funzione principale per creare la tabella firme_documenti."""
    try:
        from app import app, db
        from models import FirmaDocumento
        
        print("🔧 Creazione tabella firme_documenti...")
        
        with app.app_context():
            # Crea la tabella
            FirmaDocumento.__table__.create(db.engine, checkfirst=True)
            
            print("✅ Tabella firme_documenti creata con successo!")
            
            # Test: verifica che la tabella esista
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT COUNT(*) FROM firme_documenti"))
                count = result.scalar()
                print(f"📊 Tabella verificata: {count} record presenti")
            
            # Test: inserisci un record di test
            print("🧪 Inserimento record di test...")
            
            # Cerca un utente e un documento di test
            from models import User, Document
            
            user = User.query.first()
            document = Document.query.first()
            
            if user and document:
                test_firma = FirmaDocumento(
                    user_id=user.id,
                    document_id=document.id,
                    ip_address="127.0.0.1",
                    user_agent="Test Script",
                    stato="firmato",
                    commento="Test di firma digitale"
                )
                db.session.add(test_firma)
                db.session.commit()
                
                print(f"✅ Record di test inserito: User {user.username} -> Document {document.title}")
                
                # Rimuovi il record di test
                db.session.delete(test_firma)
                db.session.commit()
                print("🧹 Record di test rimosso")
            else:
                print("⚠️  Impossibile creare record di test: mancano utenti o documenti")
            
            print("\n🎉 Setup completato con successo!")
            print("📋 Tabella firme_documenti pronta per l'uso")
            print("🔗 Route disponibili:")
            print("   - /documenti/<id>/firma (pagina firma)")
            print("   - /documenti/<id>/firma/action (azione firma)")
            print("   - /admin/firme-documenti (dashboard admin)")
            print("   - /admin/firme-documenti/export/csv (export CSV)")
            
            return True
            
    except Exception as e:
        print(f"❌ Errore durante la creazione della tabella: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
