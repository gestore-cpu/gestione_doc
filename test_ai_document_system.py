#!/usr/bin/env python3
"""
Test del sistema AI per l'analisi automatica dei documenti.

Questo script testa:
- Estrazione testo da diversi formati
- Analisi di similarità tra documenti
- Generazione di insight AI
- Creazione di task automatici
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

# Aggiungi il percorso del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.document_ai_utils import (
    estrai_testo, 
    similarita_testi, 
    analizza_documento, 
    genera_insight_ai,
    suggerisci_task_automatico
)

def test_estrazione_testo():
    """Test dell'estrazione testo da diversi formati."""
    print("🧪 Test estrazione testo...")
    
    # Crea file di test temporanei
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Questo è un documento di test per verificare l'estrazione del testo.")
        txt_path = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Documento Markdown\n\nQuesto è un documento in formato Markdown.")
        md_path = f.name
    
    try:
        # Test estrazione da file di testo
        testo_txt = estrai_testo(txt_path)
        print(f"✅ Testo estratto da TXT: {testo_txt[:50]}...")
        
        # Test estrazione da file Markdown
        testo_md = estrai_testo(md_path)
        print(f"✅ Testo estratto da MD: {testo_md[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nell'estrazione testo: {e}")
        return False
    finally:
        # Pulisci file temporanei
        os.unlink(txt_path)
        os.unlink(md_path)


def test_similarita_testi():
    """Test del calcolo di similarità tra testi."""
    print("\n🧪 Test similarità testi...")
    
    testo1 = "Questo è un documento di test per verificare la similarità."
    testo2 = "Questo è un documento di test per verificare la similarità tra testi."
    testo3 = "Questo è un documento completamente diverso."
    
    try:
        # Test similarità alta
        sim_alta = similarita_testi(testo1, testo2)
        print(f"✅ Similarità alta: {sim_alta:.3f}")
        
        # Test similarità bassa
        sim_bassa = similarita_testi(testo1, testo3)
        print(f"✅ Similarità bassa: {sim_bassa:.3f}")
        
        # Test con testo vuoto
        sim_vuoto = similarita_testi(testo1, "")
        print(f"✅ Similarità con testo vuoto: {sim_vuoto:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel calcolo similarità: {e}")
        return False


def test_generazione_insight():
    """Test della generazione di insight AI."""
    print("\n🧪 Test generazione insight AI...")
    
    # Simula un documento
    class MockDocument:
        def __init__(self):
            self.id = 1
            self.title = "Documento di Test"
            self.file_path = "/tmp/test.txt"
            self.created_at = datetime.utcnow() - timedelta(days=400)  # Vecchio
            self.expiry_date = datetime.utcnow() - timedelta(days=10)  # Scaduto
    
    documento = MockDocument()
    
    # Simula risultato analisi
    risultato_analisi = {
        'obsoleto': {
            'tipo': 'scaduto',
            'data_scadenza': documento.expiry_date.isoformat(),
            'giorni_scaduto': 10
        },
        'vecchio': {
            'tipo': 'documento_antico',
            'eta_giorni': 400,
            'data_creazione': documento.created_at.isoformat()
        }
    }
    
    try:
        # Genera insight
        insight = genera_insight_ai(risultato_analisi, documento)
        
        print(f"✅ Insight generato: {insight['insight_text']}")
        print(f"✅ Tipo: {insight['insight_type']}")
        print(f"✅ Severità: {insight['severity']}")
        
        # Test suggerimento task
        task = suggerisci_task_automatico(insight)
        print(f"✅ Task suggerito: {task['titolo']}")
        print(f"✅ Priorità: {task['priorita']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nella generazione insight: {e}")
        return False


def test_analisi_documento():
    """Test dell'analisi completa di un documento."""
    print("\n🧪 Test analisi documento...")
    
    # Crea file di test
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Questo è un documento di test per verificare l'analisi AI.")
        test_path = f.name
    
    # Simula documenti
    class MockDocument:
        def __init__(self, doc_id, title, content):
            self.id = doc_id
            self.title = title
            self.file_path = test_path
            self.created_at = datetime.utcnow() - timedelta(days=200)
            self.expiry_date = None
    
    documento_principale = MockDocument(1, "Documento Principale", "test")
    altri_documenti = [
        MockDocument(2, "Documento Simile", "Questo è un documento di test per verificare l'analisi AI."),
        MockDocument(3, "Documento Diverso", "Questo è un documento completamente diverso.")
    ]
    
    try:
        # Analizza documento
        risultato = analizza_documento(documento_principale, altri_documenti)
        
        print(f"✅ Risultato analisi: {risultato}")
        
        if 'duplicati' in risultato:
            print(f"✅ Duplicati trovati: {len(risultato['duplicati'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nell'analisi documento: {e}")
        return False
    finally:
        # Pulisci file temporaneo
        os.unlink(test_path)


def main():
    """Esegue tutti i test del sistema AI."""
    print("🤖 Test Sistema AI per Analisi Documenti")
    print("=" * 50)
    
    tests = [
        test_estrazione_testo,
        test_similarita_testi,
        test_generazione_insight,
        test_analisi_documento
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Errore nel test {test.__name__}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Risultati Test: {passed}/{total} test superati")
    
    if passed == total:
        print("🎉 Tutti i test sono stati superati!")
        return True
    else:
        print("⚠️ Alcuni test sono falliti.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 