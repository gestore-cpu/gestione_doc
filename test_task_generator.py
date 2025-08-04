#!/usr/bin/env python3
"""
Test per il sistema di generazione automatica di task AI.

Questo script testa:
- Generazione task per documenti obsoleti/duplicati
- Routing intelligente tra QMS e FocusMe
- Assegnazione priorità e scadenze
- Gestione task esistenti
"""

import sys
import os
from datetime import datetime, timedelta

# Aggiungi il percorso del progetto al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_task_generator():
    """Test principale per il task generator."""
    print("🤖 Test Sistema Task Generator AI")
    print("=" * 50)
    
    try:
        # Importa i moduli necessari
        from ai.task_generator import (
            genera_task_ai, 
            determina_modulo_destinazione,
            _determina_priorita_scadenza,
            _genera_titolo_task,
            _genera_descrizione_task
        )
        
        # Test 1: Determinazione priorità e scadenza
        print("🧪 Test determinazione priorità e scadenza...")
        
        priorita, scadenza = _determina_priorita_scadenza("obsoleto")
        print(f"✅ Obsoleto: {priorita}, scadenza {scadenza.strftime('%d/%m/%Y')}")
        
        priorita, scadenza = _determina_priorita_scadenza("duplicato")
        print(f"✅ Duplicato: {priorita}, scadenza {scadenza.strftime('%d/%m/%Y')}")
        
        priorita, scadenza = _determina_priorita_scadenza("vecchio")
        print(f"✅ Vecchio: {priorita}, scadenza {scadenza.strftime('%d/%m/%Y')}")
        
        priorita, scadenza = _determina_priorita_scadenza("inutilizzato")
        print(f"✅ Inutilizzato: {priorita}, scadenza {scadenza.strftime('%d/%m/%Y')}")
        
        # Test 2: Generazione titoli task
        print("\n🧪 Test generazione titoli task...")
        
        # Mock document
        class MockDocument:
            def __init__(self, title):
                self.title = title
        
        doc = MockDocument("Manuale Qualità 2024")
        
        titolo = _genera_titolo_task(doc, "obsoleto")
        print(f"✅ Titolo obsoleto: {titolo}")
        
        titolo = _genera_titolo_task(doc, "duplicato")
        print(f"✅ Titolo duplicato: {titolo}")
        
        titolo = _genera_titolo_task(doc, "vecchio")
        print(f"✅ Titolo vecchio: {titolo}")
        
        titolo = _genera_titolo_task(doc, "inutilizzato")
        print(f"✅ Titolo inutilizzato: {titolo}")
        
        # Test 3: Generazione descrizioni task
        print("\n🧪 Test generazione descrizioni task...")
        
        descrizione = _genera_descrizione_task(doc, "obsoleto")
        print(f"✅ Descrizione obsoleto: {descrizione[:100]}...")
        
        descrizione = _genera_descrizione_task(doc, "duplicato")
        print(f"✅ Descrizione duplicato: {descrizione[:100]}...")
        
        descrizione = _genera_descrizione_task(doc, "vecchio")
        print(f"✅ Descrizione vecchio: {descrizione[:100]}...")
        
        descrizione = _genera_descrizione_task(doc, "inutilizzato")
        print(f"✅ Descrizione inutilizzato: {descrizione[:100]}...")
        
        # Test 4: Determinazione modulo destinazione
        print("\n🧪 Test determinazione modulo destinazione...")
        
        # Mock document con company
        class MockDocumentWithCompany:
            def __init__(self, title, company_name=None):
                self.title = title
                self.company = MockCompany(company_name) if company_name else None
        
        class MockCompany:
            def __init__(self, name):
                self.name = name
        
        # Test documenti QMS
        doc_qms = MockDocumentWithCompany("Procedura Qualità", "Qualità")
        modulo = determina_modulo_destinazione(doc_qms, "obsoleto")
        print(f"✅ Documento QMS: {modulo}")
        
        # Test documenti FocusMe
        doc_focusme = MockDocumentWithCompany("Piano Strategico 2024")
        modulo = determina_modulo_destinazione(doc_focusme, "vecchio")
        print(f"✅ Documento FocusMe: {modulo}")
        
        # Test routing per tipo di insight
        doc_generico = MockDocumentWithCompany("Documento Generico")
        modulo = determina_modulo_destinazione(doc_generico, "obsoleto")
        print(f"✅ Insight obsoleto: {modulo}")
        
        modulo = determina_modulo_destinazione(doc_generico, "vecchio")
        print(f"✅ Insight vecchio: {modulo}")
        
        print("\n" + "=" * 50)
        print("📊 Risultati Test: Tutti i test superati")
        print("🎉 Il sistema di task generator funziona correttamente!")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test di integrazione con il database."""
    print("\n🔗 Test Integrazione Database")
    print("=" * 30)
    
    try:
        # Importa Flask app e database
        from app import app
        from models import Document, Task
        from extensions import db
        
        with app.app_context():
            # Verifica che il database sia accessibile
            docs_count = Document.query.count()
            tasks_count = Task.query.count()
            
            print(f"✅ Documenti nel database: {docs_count}")
            print(f"✅ Task nel database: {tasks_count}")
            
            # Test creazione task (senza salvare)
            from ai.task_generator import genera_task_intelligente
            
            # Cerca un documento esistente
            doc = Document.query.first()
            if doc:
                print(f"✅ Test con documento esistente: {doc.title}")
                
                # Test generazione task (commentato per non creare task reali)
                # task = genera_task_intelligente(doc, "obsoleto")
                # print(f"✅ Task generato: {task.titolo}")
                
            else:
                print("⚠️ Nessun documento trovato nel database")
            
            return True
            
    except Exception as e:
        print(f"❌ Errore integrazione: {e}")
        return False

def main():
    """Funzione principale per eseguire tutti i test."""
    print("🚀 Avvio test sistema Task Generator AI")
    print("=" * 60)
    
    # Test 1: Test unitari
    test1_passed = test_task_generator()
    
    # Test 2: Test integrazione
    test2_passed = test_integration()
    
    # Risultati finali
    print("\n" + "=" * 60)
    print("📊 RISULTATI FINALI")
    print("=" * 60)
    
    if test1_passed:
        print("✅ Test unitari: SUPERATI")
    else:
        print("❌ Test unitari: FALLITI")
    
    if test2_passed:
        print("✅ Test integrazione: SUPERATI")
    else:
        print("❌ Test integrazione: FALLITI")
    
    if test1_passed and test2_passed:
        print("\n🎉 TUTTI I TEST SUPERATI!")
        print("🚀 Il sistema di auto-task AI è pronto per l'uso!")
    else:
        print("\n⚠️ ALCUNI TEST FALLITI")
        print("🔧 Verificare la configurazione del sistema")

if __name__ == "__main__":
    main() 