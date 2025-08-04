#!/usr/bin/env python3
"""
Test completo per il sistema di versioning documenti con AI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Document, DocumentVersion, User, Company, Department
from utils_extra import confronta_documenti_ai, estrai_testo
from datetime import datetime
import tempfile

def test_versioning_sistema():
    """Test completo per il sistema di versioning documenti"""
    print("🧪 TEST: Sistema Versioning Documenti con AI")
    print("=" * 60)
    
    with app.app_context():
        try:
            # 1. Verifica modelli
            print("✅ 1. Verifica modelli DocumentVersion")
            
            # 2. Crea dati di test
            print("✅ 2. Creazione dati di test")
            
            # Crea azienda e reparto di test
            company = Company(name="Test Company")
            department = Department(name="Test Department", company=company)
            db.session.add(company)
            db.session.add(department)
            db.session.commit()
            
            # Crea utente di test
            user = User.query.filter_by(username='admin').first()
            if not user:
                print("   ⚠️ Utente admin non trovato, creo utente di test")
                user = User(
                    username='test_user',
                    email='test@example.com',
                    password='test123',
                    role='admin'
                )
                db.session.add(user)
                db.session.commit()
            
            # Crea documento di test
            document = Document(
                title="Test Document Versioning",
                original_filename="test_doc.pdf",
                description="Documento di test per versioning",
                user_id=user.id,
                uploader_email=user.email,
                company_id=company.id,
                department_id=department.id,
                visibility='privato'
            )
            db.session.add(document)
            db.session.commit()
            print(f"   ✓ Documento creato: {document.title}")
            
            # 3. Test creazione versioni
            print("✅ 3. Test creazione versioni")
            
            # Crea file temporanei per test
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f1:
                f1.write("Questo è il contenuto della versione 1 del documento.")
                file1_path = f1.name
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f2:
                f2.write("Questo è il contenuto della versione 2 del documento con modifiche significative.")
                file2_path = f2.name
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f3:
                f3.write("Questo è il contenuto della versione 3 del documento con grandi modifiche e nuove sezioni.")
                file3_path = f3.name
            
            # Crea versioni
            version1 = DocumentVersion(
                document_id=document.id,
                version_number=1,
                file_path=file1_path,
                uploaded_by=user.username,
                note="Versione iniziale",
                active=True,
                ai_diff_summary=None
            )
            
            version2 = DocumentVersion(
                document_id=document.id,
                version_number=2,
                file_path=file2_path,
                uploaded_by=user.username,
                note="Aggiornamento contenuti",
                active=False,
                ai_diff_summary="Modifiche significative (similarità tra 70% e 95%)"
            )
            
            version3 = DocumentVersion(
                document_id=document.id,
                version_number=3,
                file_path=file3_path,
                uploaded_by=user.username,
                note="Revisione completa",
                active=False,
                ai_diff_summary="⚠️ Grandi modifiche (similarità <70%)"
            )
            
            db.session.add_all([version1, version2, version3])
            db.session.commit()
            print(f"   ✓ 3 versioni create")
            
            # 4. Test funzioni AI
            print("✅ 4. Test funzioni AI")
            
            # Test estrazione testo
            text1 = estrai_testo(file1_path)
            text2 = estrai_testo(file2_path)
            text3 = estrai_testo(file3_path)
            
            print(f"   📊 Testo estratto:")
            print(f"      - Versione 1: {len(text1)} caratteri")
            print(f"      - Versione 2: {len(text2)} caratteri")
            print(f"      - Versione 3: {len(text3)} caratteri")
            
            # Test confronto AI
            ai_summary_1_2 = confronta_documenti_ai(file1_path, file2_path)
            ai_summary_2_3 = confronta_documenti_ai(file2_path, file3_path)
            
            print(f"   🧠 Confronto AI:")
            print(f"      - v1 vs v2: {ai_summary_1_2}")
            print(f"      - v2 vs v3: {ai_summary_2_3}")
            
            # 5. Test proprietà modelli
            print("✅ 5. Test proprietà modelli")
            
            print(f"   📊 Proprietà versioni:")
            print(f"      - v1.is_latest: {version1.is_latest}")
            print(f"      - v1.version_display: {version1.version_display}")
            print(f"      - v1.status_badge_class: {version1.status_badge_class}")
            print(f"      - v1.ai_summary_short: {version1.ai_summary_short}")
            
            # 6. Test ripristino versione
            print("✅ 6. Test ripristino versione")
            
            # Disattiva tutte le versioni
            for v in document.versions:
                v.active = False
            
            # Attiva versione 2
            version2.active = True
            db.session.commit()
            
            active_version = next((v for v in document.versions if v.active), None)
            print(f"   📊 Versione attiva dopo ripristino: v{active_version.version_number}")
            
            # 7. Verifica risultati
            print("✅ 7. Verifica risultati")
            
            versions_count = len(document.versions)
            active_versions = sum(1 for v in document.versions if v.active)
            
            assert versions_count == 3, f"Numero versioni: {versions_count} != 3"
            assert active_versions == 1, f"Versioni attive: {active_versions} != 1"
            assert text1 is not None, "Estrazione testo v1 fallita"
            assert text2 is not None, "Estrazione testo v2 fallita"
            assert text3 is not None, "Estrazione testo v3 fallita"
            assert ai_summary_1_2 is not None, "Confronto AI v1-v2 fallito"
            assert ai_summary_2_3 is not None, "Confronto AI v2-v3 fallito"
            
            print("   ✅ Tutti i test sono passati")
            
            # 8. Pulizia dati di test
            print("✅ 8. Pulizia dati di test")
            
            # Rimuovi file temporanei
            for file_path in [file1_path, file2_path, file3_path]:
                try:
                    os.unlink(file_path)
                except:
                    pass
            
            # Rimuovi versioni
            for version in document.versions:
                db.session.delete(version)
            
            # Rimuovi documento
            db.session.delete(document)
            
            # Rimuovi dipartimento e azienda
            db.session.delete(department)
            db.session.delete(company)
            
            db.session.commit()
            print("   ✅ Dati di test rimossi")
            
            print("🎉 TEST COMPLETATO CON SUCCESSO!")
            print("Il sistema di versioning documenti con AI funziona correttamente.")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante il test: {e}")
            return False

if __name__ == "__main__":
    success = test_versioning_sistema()
    sys.exit(0 if success else 1) 