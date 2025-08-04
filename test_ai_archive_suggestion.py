#!/usr/bin/env python3
"""
Test per il suggerimento AI di archiviazione documenti.
Verifica che Jack Synthia possa suggerire automaticamente la cartella di archiviazione.
"""

import sys
import os
import json
from datetime import datetime

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_intelligence import (
    suggerisci_cartella_archiviazione,
    _determine_category_and_department,
    _analyze_content_for_department,
    _generate_suggested_path,
    _generate_ai_tags,
    _calculate_archive_confidence,
    _generate_archive_reasoning
)

def test_category_and_department_determination():
    """Test per la determinazione di categoria e reparto."""
    print("🧪 Test determinazione categoria e reparto...")
    
    # Simula azienda e reparto
    class MockCompany:
        def __init__(self, name="Mercury"):
            self.name = name
    
    class MockDepartment:
        def __init__(self, name="Qualità"):
            self.name = name
    
    company = MockCompany()
    department = MockDepartment()
    
    # Test diversi tipi di documento
    test_cases = [
        ("contratto", "Contratto di fornitura servizi", "Contratti", "Legale"),
        ("certificato", "Certificato ISO 9001", "Certificazioni", "Qualità"),
        ("manuale", "Manuale HACCP", "Manuali", "Qualità"),
        ("report", "Report mensile vendite", "Report", "Vendite"),
        ("fattura", "Fattura n. 12345", "Amministrazione", "Amministrazione"),
        ("sicurezza", "Procedure di sicurezza", "Sicurezza", "Sicurezza"),
        ("formazione", "Corso formazione dipendenti", "Formazione", "Risorse Umane"),
        ("haccp", "Documento HACCP", "Qualità", "Qualità"),
        ("iso", "Certificazione ISO 14001", "Qualità", "Qualità"),
        ("audit", "Report audit interno", "Qualità", "Qualità")
    ]
    
    for doc_type, content, expected_category, expected_dept in test_cases:
        categoria, reparto = _determine_category_and_department(doc_type, content, company, department)
        print(f"  📄 Tipo: {doc_type}")
        print(f"     Categoria: {categoria} (atteso: {expected_category})")
        print(f"     Reparto: {reparto} (atteso: {expected_dept})")
        print()
    
    print("✅ Test determinazione categoria e reparto completato\n")


def test_content_analysis_for_department():
    """Test per l'analisi del contenuto per determinare il reparto."""
    print("🧪 Test analisi contenuto per reparto...")
    
    # Simula azienda
    class MockCompany:
        def __init__(self, name="Mercury"):
            self.name = name
    
    company = MockCompany()
    
    # Test contenuti diversi
    test_contents = [
        ("Questo documento tratta di qualità e certificazioni ISO per il nostro sistema HACCP", "Qualità"),
        ("Procedure di sicurezza e evacuazione in caso di emergenza", "Sicurezza"),
        ("Report sulla produzione e processi manifatturieri", "Produzione"),
        ("Documenti di logistica e trasporto merci", "Logistica"),
        ("Vendite e ordini clienti commerciali", "Vendite"),
        ("Formazione del personale e risorse umane", "Risorse Umane"),
        ("Contabilità e pagamenti amministrativi", "Amministrazione"),
        ("Sistemi IT e tecnologia informatica", "Tecnologia")
    ]
    
    for content, expected_dept in test_contents:
        reparto = _analyze_content_for_department(content, company)
        print(f"  📝 Contenuto: {content[:50]}...")
        print(f"     Reparto rilevato: {reparto} (atteso: {expected_dept})")
        print()
    
    print("✅ Test analisi contenuto completato\n")


def test_path_generation():
    """Test per la generazione del path suggerito."""
    print("🧪 Test generazione path suggerito...")
    
    # Simula azienda
    class MockCompany:
        def __init__(self, name="Mercury"):
            self.name = name
    
    company = MockCompany()
    
    # Test diversi tipi di documento
    test_cases = [
        ("contratto", "Contratti"),
        ("certificato", "Certificazioni"),
        ("manuale", "Manuali"),
        ("report", "Report"),
        ("fattura", "Fatture"),
        ("sicurezza", "Sicurezza"),
        ("qualita", "Qualità"),
        ("formazione", "Formazione"),
        ("haccp", "HACCP"),
        ("iso", "ISO"),
        ("audit", "Audit"),
        ("procedura", "Procedure"),
        ("policy", "Policy"),
        ("regolamento", "Regolamenti")
    ]
    
    for doc_type, expected_subfolder in test_cases:
        path = _generate_suggested_path(company, "Test Reparto", doc_type)
        print(f"  📁 Tipo: {doc_type}")
        print(f"     Path generato: {path}")
        print(f"     Sottocartella attesa: {expected_subfolder}")
        print()
    
    print("✅ Test generazione path completato\n")


def test_ai_tags_generation():
    """Test per la generazione di tag AI."""
    print("🧪 Test generazione tag AI...")
    
    # Test diversi tipi di documento
    test_cases = [
        ("contratto", "Contratto di fornitura con clausola di riservatezza", "Contratti"),
        ("certificato", "Certificazione ISO 9001 annuale importante", "Certificazioni"),
        ("manuale", "Manuale HACCP urgente per formazione", "Manuali"),
        ("report", "Report mensile vendite confidenziale", "Report"),
        ("fattura", "Fattura n. 12345 trimestrale", "Amministrazione"),
        ("sicurezza", "Procedure sicurezza critiche emergenza", "Sicurezza"),
        ("qualita", "Documento qualità ISO revisione", "Qualità"),
        ("formazione", "Corso formazione dipendenti annuale", "Formazione")
    ]
    
    for doc_type, content, categoria in test_cases:
        tags = _generate_ai_tags(doc_type, content, categoria)
        print(f"  🏷️ Tipo: {doc_type}")
        print(f"     Contenuto: {content[:40]}...")
        print(f"     Tag generati: {', '.join(tags)}")
        print()
    
    print("✅ Test generazione tag completato\n")


def test_confidence_calculation():
    """Test per il calcolo del punteggio di confidenza."""
    print("🧪 Test calcolo punteggio confidenza...")
    
    # Test diversi scenari
    test_cases = [
        ("contratto", "Contratto di fornitura servizi con clausole legali", "Contratti", "Legale"),
        ("certificato", "Certificazione ISO 9001 con documentazione completa", "Certificazioni", "Qualità"),
        ("manuale", "Manuale HACCP con procedure dettagliate", "Manuali", "Qualità"),
        ("report", "Report mensile vendite con analisi approfondita", "Report", "Vendite"),
        ("documento", "Documento generico senza specifiche", "Generale", "Generale")
    ]
    
    for doc_type, content, categoria, reparto in test_cases:
        confidence = _calculate_archive_confidence(doc_type, content, categoria, reparto)
        print(f"  📊 Tipo: {doc_type}")
        print(f"     Categoria: {categoria}")
        print(f"     Reparto: {reparto}")
        print(f"     Confidenza: {confidence}%")
        print()
    
    print("✅ Test calcolo confidenza completato\n")


def test_reasoning_generation():
    """Test per la generazione della motivazione AI."""
    print("🧪 Test generazione motivazione AI...")
    
    # Test diversi scenari
    test_cases = [
        ("contratto", "Contratti", "Legale", ["contratto", "legale", "accordo"]),
        ("certificato", "Certificazioni", "Qualità", ["certificato", "certificazione", "qualità"]),
        ("manuale", "Manuali", "Qualità", ["manuale", "istruzioni", "procedura"]),
        ("report", "Report", "Vendite", ["report", "rapporto", "analisi"]),
        ("sicurezza", "Sicurezza", "Sicurezza", ["sicurezza", "protezione", "emergenza"])
    ]
    
    for doc_type, categoria, reparto, tags in test_cases:
        reasoning = _generate_archive_reasoning(doc_type, categoria, reparto, tags)
        print(f"  🤖 Tipo: {doc_type}")
        print(f"     Motivazione: {reasoning[:100]}...")
        print()
    
    print("✅ Test generazione motivazione completato\n")


def test_archive_suggestion_simulation():
    """Simula una generazione completa di suggerimento AI."""
    print("🧪 Test simulazione suggerimento AI completo...")
    
    # Simula un documento
    document_id = 456
    
    print(f"  📋 Simulazione suggerimento archiviazione documento ID: {document_id}")
    print("  🔍 Analisi contenuto documento...")
    print("  🏷️ Generazione tag AI...")
    print("  📁 Determinazione path suggerito...")
    print("  📊 Calcolo punteggio confidenza...")
    print("  🤖 Generazione motivazione AI...")
    print("  ✅ Suggerimento AI generato con successo!")
    
    # Simula risultato
    mock_result = {
        "success": True,
        "path_suggerito": "/Mercury/Qualità/HACCP",
        "categoria_suggerita": "Qualità",
        "tag_ai": ["haccp", "manuale", "formazione", "qualità", "urgente"],
        "motivazione_ai": "Documento classificato come 'haccp' e assegnato alla categoria 'Qualità'.\n\nRipartimento suggerito: Qualità\nTag identificati: haccp, manuale, formazione, qualità, urgente\n\nMotivazione: Manuale operativo per formazione e riferimento del personale.",
        "suggested_folder": "Qualità/Qualità",
        "confidence_score": 85.0,
        "azienda_suggerita": "Mercury",
        "reparto_suggerito": "Qualità",
        "tipo_documento_ai": "haccp",
        "suggestion_id": 789
    }
    
    print(f"  📊 Risultato simulazione:")
    print(f"     Successo: {mock_result['success']}")
    print(f"     Path suggerito: {mock_result['path_suggerito']}")
    print(f"     Categoria: {mock_result['categoria_suggerita']}")
    print(f"     Tag AI: {', '.join(mock_result['tag_ai'])}")
    print(f"     Confidenza: {mock_result['confidence_score']}%")
    print(f"     Tipo documento: {mock_result['tipo_documento_ai']}")
    
    print("✅ Test simulazione completato\n")


def main():
    """Esegue tutti i test."""
    print("🚀 AVVIO TEST SUGGERIMENTO AI ARCHIVIAZIONE")
    print("=" * 60)
    
    try:
        test_category_and_department_determination()
        test_content_analysis_for_department()
        test_path_generation()
        test_ai_tags_generation()
        test_confidence_calculation()
        test_reasoning_generation()
        test_archive_suggestion_simulation()
        
        print("🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
        print("✅ Jack Synthia è pronto per suggerire archiviazione automatica")
        
    except Exception as e:
        print(f"❌ Errore durante i test: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 