#!/usr/bin/env python3
"""
Script di test per l'API AI dei documenti.
Verifica le funzionalità dell'analisi AI tramite chiamate HTTP.
"""

import requests
import json
import sys
from datetime import datetime


def test_ai_analisi_utilizzo():
    """
    Test della route /docs/ai/analizza_utilizzo
    """
    print("🧪 Test API AI - Analisi Utilizzo Documenti")
    print("=" * 50)
    
    try:
        # URL dell'API (assumendo che sia in esecuzione su localhost:5000)
        url = "http://localhost:5000/docs/ai/analizza_utilizzo"
        
        print(f"📡 Chiamata API: {url}")
        
        # Effettua la chiamata GET
        response = requests.get(url, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Risposta API ricevuta con successo!")
            print(f"📄 Documenti analizzati: {data.get('documenti_analizzati', 0)}")
            print(f"🏢 Reparti coinvolti: {data.get('reparti_coinvolti', 0)}")
            print(f"⏰ Timestamp: {data.get('timestamp', 'N/A')}")
            
            # Mostra statistiche
            statistiche = data.get('statistiche', {})
            if statistiche:
                print("\n📈 Statistiche:")
                print(f"   • Compliance Rate: {statistiche.get('compliance_rate', 0)}%")
                print(f"   • Documenti Compliant: {statistiche.get('compliant', 0)}")
                print(f"   • In Attesa: {statistiche.get('in_attesa', 0)}")
                print(f"   • Non Utilizzati: {statistiche.get('non_utilizzati', 0)}")
                print(f"   • Anomalie Totali: {statistiche.get('total_anomalie', 0)}")
            
            # Mostra parte del report AI
            report = data.get('report', '')
            if report:
                print(f"\n🤖 Report AI (primi 500 caratteri):")
                print("-" * 50)
                print(report[:500] + "..." if len(report) > 500 else report)
                print("-" * 50)
            
            return True
            
        else:
            print(f"❌ Errore API: {response.status_code}")
            print(f"📝 Risposta: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Errore di connessione: il server non è in esecuzione")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout: la richiesta ha impiegato troppo tempo")
        return False
    except Exception as e:
        print(f"❌ Errore generico: {str(e)}")
        return False


def test_ai_statistiche():
    """
    Test della route /docs/ai/statistiche
    """
    print("\n🧪 Test API AI - Statistiche")
    print("=" * 30)
    
    try:
        url = "http://localhost:5000/docs/ai/statistiche"
        
        print(f"📡 Chiamata API: {url}")
        
        response = requests.get(url, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Statistiche AI ricevute con successo!")
            print(f"📄 Documenti analizzati: {data.get('documenti_analizzati', 0)}")
            print(f"📈 Compliance Rate: {data.get('compliance_rate', 0)}%")
            print(f"🚨 Alert Critici: {data.get('alert_critici', 0)}")
            print(f"🏆 Reparti Virtuosi: {data.get('reparti_virtuosi', 0)}")
            print(f"⚠️ Reparti Problematici: {data.get('reparti_problematici', 0)}")
            print(f"📋 Documenti Prioritari: {data.get('documenti_prioritari', 0)}")
            print(f"💡 Raccomandazioni: {data.get('raccomandazioni', 0)}")
            print(f"⏰ Timestamp: {data.get('timestamp', 'N/A')}")
            
            return True
            
        else:
            print(f"❌ Errore API: {response.status_code}")
            print(f"📝 Risposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Errore: {str(e)}")
        return False


def test_ai_report():
    """
    Test della route /docs/ai/report
    """
    print("\n🧪 Test API AI - Report Completo")
    print("=" * 35)
    
    try:
        url = "http://localhost:5000/docs/ai/report"
        
        print(f"📡 Chiamata API: {url}")
        
        response = requests.get(url, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Report AI ricevuto con successo!")
            print(f"⏰ Timestamp: {data.get('timestamp', 'N/A')}")
            
            # Mostra parte del report
            report = data.get('report', '')
            if report:
                print(f"\n📋 Report AI (primi 300 caratteri):")
                print("-" * 40)
                print(report[:300] + "..." if len(report) > 300 else report)
                print("-" * 40)
            
            return True
            
        else:
            print(f"❌ Errore API: {response.status_code}")
            print(f"📝 Risposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Errore: {str(e)}")
        return False


def test_curl_commands():
    """
    Mostra i comandi curl per testare l'API manualmente
    """
    print("\n🔧 Comandi cURL per test manuale:")
    print("=" * 40)
    
    base_url = "http://localhost:5000"
    
    print(f"\n1. Analisi utilizzo documenti:")
    print(f"curl -X GET '{base_url}/docs/ai/analizza_utilizzo'")
    
    print(f"\n2. Statistiche AI:")
    print(f"curl -X GET '{base_url}/docs/ai/statistiche'")
    
    print(f"\n3. Report AI completo:")
    print(f"curl -X GET '{base_url}/docs/ai/report'")
    
    print(f"\n4. Test con jq (se installato):")
    print(f"curl -s '{base_url}/docs/ai/analizza_utilizzo' | jq '.statistiche'")
    print(f"curl -s '{base_url}/docs/ai/statistiche' | jq '.'")


def main():
    """
    Funzione principale per eseguire tutti i test
    """
    print("🚀 Test API AI Documenti")
    print("=" * 30)
    print(f"⏰ Avvio test: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Esegui i test
    test1_success = test_ai_analisi_utilizzo()
    test2_success = test_ai_statistiche()
    test3_success = test_ai_report()
    
    # Mostra comandi curl
    test_curl_commands()
    
    # Riepilogo
    print("\n📊 Riepilogo Test:")
    print("=" * 20)
    print(f"✅ Analisi Utilizzo: {'PASS' if test1_success else 'FAIL'}")
    print(f"✅ Statistiche AI: {'PASS' if test2_success else 'FAIL'}")
    print(f"✅ Report AI: {'PASS' if test3_success else 'FAIL'}")
    
    total_tests = 3
    passed_tests = sum([test1_success, test2_success, test3_success])
    
    print(f"\n🎯 Risultato: {passed_tests}/{total_tests} test passati")
    
    if passed_tests == total_tests:
        print("🎉 Tutti i test sono passati! L'API AI funziona correttamente.")
        return 0
    else:
        print("⚠️ Alcuni test sono falliti. Verificare la configurazione del server.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
