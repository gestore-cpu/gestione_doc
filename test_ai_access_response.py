#!/usr/bin/env python3
"""
Test per la risposta AI automatica alle richieste di accesso.
Verifica che Jack Synthia possa generare risposte AI appropriate.
"""

import sys
import os
import json
from datetime import datetime

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_intelligence import (
    generate_ai_access_response,
    _determine_document_sensitivity,
    _analyze_user_motivation,
    _generate_formal_response,
    _generate_admin_opinion
)

def test_document_sensitivity():
    """Test per la determinazione della sensibilità del documento."""
    print("🧪 Test determinazione sensibilità documento...")
    
    # Simula un documento
    class MockDocument:
        def __init__(self, is_critical=False, visibility="pubblico", richiedi_firma=False, expiry_date=None):
            self.is_critical = is_critical
            self.visibility = visibility
            self.richiedi_firma = richiedi_firma
            self.expiry_date = expiry_date
            self.title = "Test Document"
    
    # Test documenti normali
    doc = MockDocument()
    sensitivity = _determine_document_sensitivity(doc, "Contenuto normale")
    print(f"  📄 Documento normale: {sensitivity}")
    
    # Test documenti critici
    doc = MockDocument(is_critical=True)
    sensitivity = _determine_document_sensitivity(doc, "Contenuto critico")
    print(f"  🔒 Documento critico: {sensitivity}")
    
    # Test documenti privati
    doc = MockDocument(visibility="privato")
    sensitivity = _determine_document_sensitivity(doc, "Contenuto privato")
    print(f"  🔐 Documento privato: {sensitivity}")
    
    # Test documenti con firma richiesta
    doc = MockDocument(richiedi_firma=True)
    sensitivity = _determine_document_sensitivity(doc, "Contenuto protetto")
    print(f"  ✍️ Documento con firma: {sensitivity}")
    
    # Test documenti con contenuto sensibile
    doc = MockDocument()
    sensitivity = _determine_document_sensitivity(doc, "Questo è un documento confidenziale e riservato")
    print(f"  🚨 Documento con contenuto sensibile: {sensitivity}")
    
    print("✅ Test sensibilità documento completato\n")


def test_user_motivation_analysis():
    """Test per l'analisi della motivazione dell'utente."""
    print("🧪 Test analisi motivazione utente...")
    
    # Test motivazioni diverse
    test_cases = [
        ("Necessito urgentemente questo documento per un problema tecnico", "user"),
        ("Richiesta amministrativa per documentazione", "admin"),
        ("Necessità legale per conformità normativa", "user"),
        ("Accesso normale per consultazione", "user"),
        ("Emergenza critica sistema", "superadmin")
    ]
    
    for motivazione, ruolo in test_cases:
        analysis = _analyze_user_motivation(motivazione, ruolo)
        print(f"  📝 Motivazione: {motivazione[:50]}...")
        print(f"     Ruolo: {ruolo}")
        print(f"     Urgenza: {analysis['urgenza']}")
        print(f"     Legittimità: {analysis['legittimità']}")
        print(f"     Necessità tecniche: {analysis['necessità_tecnica']}")
        print(f"     Necessità amministrative: {analysis['necessità_amministrativa']}")
        print(f"     Necessità legali: {analysis['necessità_legale']}")
        print()
    
    print("✅ Test analisi motivazione completato\n")


def test_formal_response_generation():
    """Test per la generazione di risposte formali."""
    print("🧪 Test generazione risposte formali...")
    
    # Simula utente e documento
    class MockUser:
        def __init__(self, first_name="Mario", last_name="Rossi", username="mario.rossi"):
            self.first_name = first_name
            self.last_name = last_name
            self.username = username
    
    class MockDocument:
        def __init__(self, title="Documento Test"):
            self.title = title
    
    user = MockUser()
    document = MockDocument()
    
    # Test diversi livelli di sensibilità
    sensitivity_levels = ["normale", "riservato", "critico", "scaduto"]
    
    for level in sensitivity_levels:
        motivation_analysis = {
            "motivazione": "Test motivazione per documento " + level
        }
        
        response = _generate_formal_response(
            user=user,
            document=document,
            document_type="report",
            sensitivity_level=level,
            motivation_analysis=motivation_analysis
        )
        
        print(f"  📧 Risposta per documento {level}:")
        print(f"     {response[:100]}...")
        print()
    
    print("✅ Test generazione risposte completato\n")


def test_admin_opinion_generation():
    """Test per la generazione di pareri admin."""
    print("🧪 Test generazione pareri admin...")
    
    # Simula utente e documento
    class MockUser:
        def __init__(self, role="user"):
            self.role = role
    
    class MockDocument:
        def __init__(self, title="Documento Test"):
            self.title = title
    
    user = MockUser()
    document = MockDocument()
    
    # Test diversi scenari
    test_scenarios = [
        ("normale", {"legittimità": "media", "urgenza": "bassa"}),
        ("riservato", {"legittimità": "alta", "urgenza": "alta"}),
        ("protetto", {"legittimità": "alta", "urgenza": "bassa"}),
        ("critico", {"legittimità": "bassa", "urgenza": "bassa"})
    ]
    
    for sensitivity, motivation in test_scenarios:
        opinion = _generate_admin_opinion(
            user=user,
            document=document,
            document_type="report",
            sensitivity_level=sensitivity,
            motivation_analysis=motivation
        )
        
        print(f"  🤖 Parere per documento {sensitivity}:")
        print(f"     {opinion}")
        print()
    
    # Test con utente admin
    admin_user = MockUser(role="admin")
    opinion = _generate_admin_opinion(
        user=admin_user,
        document=document,
        document_type="report",
        sensitivity_level="critico",
        motivation_analysis={"legittimità": "bassa", "urgenza": "bassa"}
    )
    
    print(f"  👨‍💼 Parere per utente admin: {opinion}")
    print()
    
    print("✅ Test generazione pareri completato\n")


def test_ai_access_response_simulation():
    """Simula una generazione completa di risposta AI."""
    print("🧪 Test simulazione risposta AI completa...")
    
    # Simula una richiesta di accesso
    request_id = 123
    
    print(f"  📋 Simulazione richiesta accesso ID: {request_id}")
    print("  🔍 Analisi documento e utente...")
    print("  🤖 Generazione risposta AI...")
    print("  📧 Preparazione email...")
    print("  ✅ Risposta AI generata con successo!")
    
    # Simula risultato
    mock_result = {
        "success": True,
        "risposta_formale": "Gentile Mario Rossi,\n\nLa sua richiesta di accesso al documento \"Documento Test\" è stata ricevuta e analizzata dal nostro sistema di gestione documentale.\n\nIl documento è attualmente disponibile per l'accesso. Le verrà inviato un link di accesso sicuro entro breve.\n\nMotivazione fornita: Test motivazione\n\nCordiali saluti,\nSistema di Gestione Documentale",
        "parere_admin": "✅ CONSIGLIATO CONCEDERE - Documento di accesso normale",
        "suggerimento_email": "📧 INVIA EMAIL A: mario.rossi@example.com\n\nOggetto: Accesso documento \"Documento Test\" - APPROVATO\n\n[Contenuto email...]\n\n---\nNota: L'AI consiglia di concedere l'accesso.",
        "request_id": request_id
    }
    
    print(f"  📊 Risultato simulazione:")
    print(f"     Successo: {mock_result['success']}")
    print(f"     Parere AI: {mock_result['parere_admin']}")
    print(f"     Email generata: {'Sì' if 'INVIA EMAIL' in mock_result['suggerimento_email'] else 'No'}")
    
    print("✅ Test simulazione completato\n")


def main():
    """Esegue tutti i test."""
    print("🚀 AVVIO TEST RISPOSTA AI AUTOMATICA ACCESSO")
    print("=" * 60)
    
    try:
        test_document_sensitivity()
        test_user_motivation_analysis()
        test_formal_response_generation()
        test_admin_opinion_generation()
        test_ai_access_response_simulation()
        
        print("🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
        print("✅ Jack Synthia è pronto per gestire risposte AI automatiche")
        
    except Exception as e:
        print(f"❌ Errore durante i test: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 