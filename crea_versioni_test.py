#!/usr/bin/env python3
"""
Script per creare versioni di test per visualizzare la timeline.
"""

import os
import sys
from datetime import datetime, timedelta

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import DocumentVersion, User, Document, DocumentReadLog

def crea_versioni_test():
    """
    Crea versioni di test per visualizzare la timeline.
    """
    with app.app_context():
        print("📄 Creazione Versioni di Test")
        print("=" * 50)
        
        # Ottieni documento di test
        doc = Document.query.first()
        
        if not doc:
            print("❌ Nessun documento trovato")
            return
        
        print(f"📄 Documento: {doc.title or doc.original_filename}")
        
        # Rimuovi versioni esistenti
        versioni_esistenti = DocumentVersion.query.filter_by(document_id=doc.id).all()
        for versione in versioni_esistenti:
            db.session.delete(versione)
        db.session.commit()
        print(f"🗑️ Rimosse {len(versioni_esistenti)} versioni esistenti")
        
        # Crea versioni di test con date diverse
        versioni_test = [
            {
                'numero_versione': 'v1',
                'filename': 'v1_manuale_iso_2024.pdf',
                'note': 'Prima versione del manuale ISO 9001:2015',
                'data_caricamento': datetime.utcnow() - timedelta(days=30)
            },
            {
                'numero_versione': 'v2',
                'filename': 'v2_manuale_iso_aggiornato.pdf',
                'note': 'Aggiornamento sezione 7.5 - Controllo della documentazione',
                'data_caricamento': datetime.utcnow() - timedelta(days=20)
            },
            {
                'numero_versione': 'v3',
                'filename': 'v3_manuale_iso_revisione_completa.pdf',
                'note': 'Revisione completa con nuove procedure operative',
                'data_caricamento': datetime.utcnow() - timedelta(days=10)
            },
            {
                'numero_versione': 'v4',
                'filename': 'v4_manuale_iso_finale.pdf',
                'note': 'Versione finale approvata dal management',
                'data_caricamento': datetime.utcnow() - timedelta(days=5)
            }
        ]
        
        try:
            for versione_data in versioni_test:
                versione = DocumentVersion(
                    document_id=doc.id,
                    numero_versione=versione_data['numero_versione'],
                    filename=versione_data['filename'],
                    note=versione_data['note'],
                    data_caricamento=versione_data['data_caricamento']
                )
                db.session.add(versione)
            
            db.session.commit()
            
            print("✅ Versioni di test create:")
            for versione_data in versioni_test:
                print(f"   - {versione_data['numero_versione']}: {versione_data['filename']}")
                print(f"     Note: {versione_data['note']}")
                print(f"     Data: {versione_data['data_caricamento'].strftime('%d/%m/%Y')}")
                print()
            
            # Crea alcune firme di test per le versioni
            utenti = User.query.limit(3).all()
            versioni = DocumentVersion.query.filter_by(document_id=doc.id).all()
            
            print("👥 Creazione firme di test...")
            
            for i, versione in enumerate(versioni):
                # Per ogni versione, crea firme per alcuni utenti
                for j, utente in enumerate(utenti[:2]):  # Solo primi 2 utenti
                    firma = DocumentReadLog(
                        user_id=utente.id,
                        document_id=doc.id,
                        version_id=versione.id,
                        timestamp=versione.data_caricamento + timedelta(hours=j+1),
                        confermata=(i % 2 == 0),  # Alterna confermate/non confermate
                        data_conferma=versione.data_caricamento + timedelta(hours=j+1) if i % 2 == 0 else None
                    )
                    db.session.add(firma)
            
            db.session.commit()
            print("✅ Firme di test create")
            
            # Mostra statistiche
            print("\n📊 Statistiche versioni:")
            for versione in versioni:
                print(f"   {versione.numero_versione}: {len(versione.firme_confermate)} confermate, {len(versione.firme_in_attesa)} in attesa")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Errore durante la creazione: {e}")
            return
        
        print(f"\n✅ Versioni di test create con successo!")
        print(f"🔗 Puoi visualizzare la timeline in: http://localhost:5000/admin/document/{doc.id}/versioni")

if __name__ == "__main__":
    crea_versioni_test() 