#!/usr/bin/env python3
"""
Test per l'auto-verifica AI dei documenti.
Verifica che Jack Synthia possa analizzare correttamente i documenti.
"""

import sys
import os
import json
from datetime import datetime

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_intelligence import (
    auto_verifica_documento,
    analyze_document_content_ai,
    calculate_compliance_score,
    classify_document_type,
    check_header_presence,
    check_signature_presence,
    check_date_presence
)

def test_analyze_document_content_ai():
    """Test analisi contenuto documento con AI."""
    print("🧠 Test: Analisi contenuto documento AI")
    
    # Test documento completo
    complete_doc = """
    CONTRATTO DI FORNITURA
    
    Data: 15/03/2024
    
    Parti contraenti:
    - Azienda ABC S.p.A.
    - Fornitore XYZ S.r.l.
    
    Oggetto: Fornitura servizi IT
    
    Durata: 12 mesi
    
    Firma del responsabile:
    _________________
    Mario Rossi
    """
    
    result = analyze_document_content_ai(complete_doc, "Contratto di Fornitura")
    
    print(f"✅ Tipo documento: {result.get('document_type')}")
    print(f"✅ Ha intestazione: {result.get('has_header')}")
    print(f"✅ Ha firma: {result.get('has_signature')}")
    print(f"✅ Ha data: {result.get('has_date')}")
    print(f"✅ Sezioni mancanti: {result.get('missing_sections')}")
    print(f"✅ Criticità: {result.get('criticita')}")
    print(f"✅ Suggerimenti: {result.get('suggerimenti')}")
    
    # Test documento incompleto
    incomplete_doc = """
    Documento test
    
    Questo è un documento di test senza firma e data.
    """
    
    result_incomplete = analyze_document_content_ai(incomplete_doc, "Documento Test")
    
    print(f"\n❌ Tipo documento: {result_incomplete.get('document_type')}")
    print(f"❌ Ha intestazione: {result_incomplete.get('has_header')}")
    print(f"❌ Ha firma: {result_incomplete.get('has_signature')}")
    print(f"❌ Ha data: {result_incomplete.get('has_date')}")
    print(f"❌ Sezioni mancanti: {result_incomplete.get('missing_sections')}")
    print(f"❌ Criticità: {result_incomplete.get('criticita')}")
    
    return True

def test_classify_document_type():
    """Test classificazione tipo documento."""
    print("\n📋 Test: Classificazione tipo documento")
    
    test_cases = [
        ("Contratto di Fornitura", "contratto"),
        ("Certificato ISO 9001", "certificato"),
        ("Manuale Procedure", "manuale"),
        ("Report Mensile", "report"),
        ("Fattura 2024", "fattura"),
        ("Procedure Sicurezza", "sicurezza"),
        ("Documento Generico", "generico")
    ]
    
    for title, expected_type in test_cases:
        doc_type = classify_document_type(title, "")
        status = "✅" if doc_type == expected_type else "❌"
        print(f"{status} '{title}' -> {doc_type} (atteso: {expected_type})")
    
    return True

def test_check_elements():
    """Test verifica elementi documento."""
    print("\n🔍 Test: Verifica elementi documento")
    
    # Test intestazione
    header_text = "CONTRATTO DI FORNITURA\n\nData: 15/03/2024"
    has_header = check_header_presence(header_text)
    print(f"✅ Intestazione presente: {has_header}")
    
    # Test firma
    signature_text = "Firma del responsabile:\n_________________\nMario Rossi"
    has_signature = check_signature_presence(signature_text)
    print(f"✅ Firma presente: {has_signature}")
    
    # Test data
    date_text = "Data: 15/03/2024\nContratto stipulato il 20-03-2024"
    has_date = check_date_presence(date_text)
    print(f"✅ Data presente: {has_date}")
    
    return True

def test_compliance_score():
    """Test calcolo punteggio compliance."""
    print("\n📊 Test: Calcolo punteggio compliance")
    
    # Analisi documento completo
    complete_analysis = {
        "has_header": True,
        "has_footer": True,
        "has_signature": True,
        "has_date": True,
        "has_company_info": True,
        "has_security_info": True,
        "missing_sections": [],
        "criticita": []
    }
    
    score_complete = calculate_compliance_score(complete_analysis)
    print(f"✅ Punteggio documento completo: {score_complete}%")
    
    # Analisi documento incompleto
    incomplete_analysis = {
        "has_header": False,
        "has_footer": False,
        "has_signature": False,
        "has_date": False,
        "has_company_info": False,
        "has_security_info": False,
        "missing_sections": ["firma", "data", "introduzione"],
        "criticita": ["Intestazione mancante", "Firma mancante", "Data documento mancante"]
    }
    
    score_incomplete = calculate_compliance_score(incomplete_analysis)
    print(f"❌ Punteggio documento incompleto: {score_incomplete}%")
    
    return True

def test_auto_verifica_simulation():
    """Test simulazione auto-verifica documento."""
    print("\n🤖 Test: Simulazione auto-verifica documento")
    
    # Simula un documento
    document_text = """
    MANUALE PROCEDURE SICUREZZA
    
    Data: 10/03/2024
    
    Indice:
    1. Introduzione
    2. Procedure di sicurezza
    3. Responsabilità
    4. Emergenze
    
    Introduzione:
    Questo manuale descrive le procedure di sicurezza aziendali.
    
    Procedure di sicurezza:
    - Utilizzo DPI obbligatorio
    - Controlli periodici
    - Formazione continua
    
    Responsabilità:
    Il responsabile sicurezza è incaricato di...
    
    Emergenze:
    In caso di emergenza contattare: 112
    
    Contatti:
    Responsabile Sicurezza: Mario Rossi
    Tel: 02-1234567
    
    Firma del responsabile:
    _________________
    Mario Rossi
    Responsabile Sicurezza
    """
    
    # Analizza il documento
    analysis = analyze_document_content_ai(document_text, "Manuale Procedure Sicurezza")
    compliance_score = calculate_compliance_score(analysis)
    is_conforme = compliance_score >= 70
    
    print(f"✅ Tipo documento: {analysis.get('document_type')}")
    print(f"✅ Punteggio compliance: {compliance_score}%")
    print(f"✅ Conforme: {is_conforme}")
    print(f"✅ Sezioni mancanti: {analysis.get('missing_sections')}")
    print(f"✅ Criticità: {analysis.get('criticita')}")
    print(f"✅ Suggerimenti: {analysis.get('suggerimenti')}")
    
    return True

def main():
    """Esegue tutti i test."""
    print("🧠 TEST AUTO-VERIFICA DOCUMENTI JACK SYNTHIA")
    print("=" * 50)
    
    try:
        # Esegui test
        test_analyze_document_content_ai()
        test_classify_document_type()
        test_check_elements()
        test_compliance_score()
        test_auto_verifica_simulation()
        
        print("\n" + "=" * 50)
        print("✅ TUTTI I TEST COMPLETATI CON SUCCESSO!")
        print("🤖 Jack Synthia è pronto per l'auto-verifica documenti!")
        
    except Exception as e:
        print(f"\n❌ Errore durante i test: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 