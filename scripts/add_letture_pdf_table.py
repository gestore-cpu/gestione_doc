#!/usr/bin/env python3
"""
Script per creare la tabella letture_pdf nel database.
Questo script aggiunge direttamente la tabella senza usare Flask-Migrate.
"""

import sys
import os

# Aggiungi il percorso del progetto al Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Funzione principale per creare la tabella letture_pdf."""
    try:
        from app import app, db
        from models import LetturaPDF
        
        print("🔧 Creazione tabella letture_pdf...")
        
        with app.app_context():
            # Crea la tabella
            LetturaPDF.__table__.create(db.engine, checkfirst=True)
            
            print("✅ Tabella letture_pdf creata con successo!")
            
            # Test: verifica che la tabella esista
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT COUNT(*) FROM letture_pdf"))
                count = result.scalar()
                print(f"📊 Tabella verificata: {count} record presenti")
            
            # Test: inserisci un record di test
            print("🧪 Inserimento record di test...")
            
            # Cerca un utente e un documento di test
            from models import User, Document
            
            user = User.query.first()
            document = Document.query.first()
            
            if user and document:
                test_lettura = LetturaPDF(
                    user_id=user.id,
                    document_id=document.id,
                    ip_address="127.0.0.1",
                    user_agent="Test Script"
                )
                db.session.add(test_lettura)
                db.session.commit()
                
                print(f"✅ Record di test inserito: User {user.username} -> Document {document.title}")
                
                # Rimuovi il record di test
                db.session.delete(test_lettura)
                db.session.commit()
                print("🧹 Record di test rimosso")
            else:
                print("⚠️  Impossibile creare record di test: mancano utenti o documenti")
            
            print("\n🎉 Setup completato con successo!")
            print("📋 Tabella letture_pdf pronta per l'uso")
            print("🔗 Route disponibili:")
            print("   - /documenti/<id>/view/pdf (visualizzazione tracciata)")
            print("   - /admin/letture-pdf (dashboard admin)")
            print("   - /admin/letture-pdf/export/csv (export CSV)")
            
            return True
            
    except Exception as e:
        print(f"❌ Errore durante la creazione della tabella: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
