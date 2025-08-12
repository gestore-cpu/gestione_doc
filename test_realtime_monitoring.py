#!/usr/bin/env python3
"""
Script per testare il sistema di monitoraggio AI in tempo reale.
Simula comportamenti anomali per verificare la generazione di alert.
"""

import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_realtime_monitoring():
    """Testa il sistema di monitoraggio AI in tempo reale."""
    
    print("🚨 Test Sistema Monitoraggio AI Tempo Reale")
    print("=" * 50)
    
    base_url = "http://localhost:5000"  # Modifica se necessario
    
    # Test 1: Analisi tempo reale
    print("\n1. Test Analisi Tempo Reale")
    print("-" * 30)
    
    try:
        response = requests.post(f"{base_url}/admin/ai/realtime/analyze", 
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Analisi completata: {data.get('alerts_generated', 0)} alert generati")
                if data.get('alerts'):
                    for alert in data['alerts']:
                        print(f"   - Alert {alert['id']}: {alert['tipo_alert']} ({alert['livello']})")
            else:
                print(f"❌ Errore analisi: {data.get('error')}")
        else:
            print(f"❌ Errore HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
    
    # Test 2: Recupero alert in tempo reale
    print("\n2. Test Recupero Alert Tempo Reale")
    print("-" * 30)
    
    try:
        response = requests.get(f"{base_url}/admin/ai/alerts/realtime")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                alerts = data.get('alerts', [])
                print(f"✅ Recuperati {len(alerts)} alert")
                
                for alert in alerts[:5]:  # Mostra solo i primi 5
                    print(f"   - {alert['tipo_alert_display']} ({alert['livello']}): {alert['descrizione']}")
            else:
                print(f"❌ Errore recupero: {data.get('error')}")
        else:
            print(f"❌ Errore HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
    
    # Test 3: Dashboard overview
    print("\n3. Test Dashboard Overview")
    print("-" * 30)
    
    try:
        response = requests.get(f"{base_url}/admin/ai/dashboard/overview")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                overview = data.get('overview', {})
                print(f"✅ Overview caricato:")
                print(f"   - Alert totali 24h: {overview.get('total_alerts_24h', 0)}")
                print(f"   - Nuovi alert: {overview.get('nuovi_alert_24h', 0)}")
                
                # Statistiche per livello
                for item in overview.get('alert_per_livello', []):
                    print(f"   - {item['livello']}: {item['count']}")
            else:
                print(f"❌ Errore overview: {data.get('error')}")
        else:
            print(f"❌ Errore HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
    
    # Test 4: Filtri avanzati
    print("\n4. Test Filtri Avanzati")
    print("-" * 30)
    
    try:
        # Test filtro per livello critico
        response = requests.get(f"{base_url}/admin/ai/alerts/realtime?livello=critico")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                alerts = data.get('alerts', [])
                critici = [a for a in alerts if a['livello'] == 'critico']
                print(f"✅ Filtro critico: {len(critici)} alert critici trovati")
            else:
                print(f"❌ Errore filtro: {data.get('error')}")
        else:
            print(f"❌ Errore HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
    
    # Test 5: Aggiornamento stato alert
    print("\n5. Test Aggiornamento Stato Alert")
    print("-" * 30)
    
    try:
        # Prima recupera un alert
        response = requests.get(f"{base_url}/admin/ai/alerts/realtime?stato=nuovo")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('alerts'):
                alert_id = data['alerts'][0]['id']
                
                # Aggiorna stato
                update_data = {'stato': 'in_revisione'}
                response = requests.post(f"{base_url}/admin/ai/alerts/{alert_id}/update",
                                      json=update_data,
                                      headers={'Content-Type': 'application/json'})
                
                if response.status_code == 200:
                    update_result = response.json()
                    if update_result.get('success'):
                        print(f"✅ Alert {alert_id} aggiornato a 'in_revisione'")
                    else:
                        print(f"❌ Errore aggiornamento: {update_result.get('error')}")
                else:
                    print(f"❌ Errore HTTP aggiornamento: {response.status_code}")
            else:
                print("ℹ️ Nessun alert nuovo trovato per il test")
        else:
            print(f"❌ Errore HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
    
    # Test 6: Bulk update
    print("\n6. Test Bulk Update")
    print("-" * 30)
    
    try:
        # Recupera alert da chiudere
        response = requests.get(f"{base_url}/admin/ai/alerts/realtime?stato=in_revisione")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('alerts'):
                alert_ids = [a['id'] for a in data['alerts'][:3]]  # Primi 3
                
                bulk_data = {
                    'alert_ids': alert_ids,
                    'nuovo_stato': 'chiuso'
                }
                
                response = requests.post(f"{base_url}/admin/ai/alerts/bulk-update",
                                      json=bulk_data,
                                      headers={'Content-Type': 'application/json'})
                
                if response.status_code == 200:
                    bulk_result = response.json()
                    if bulk_result.get('success'):
                        print(f"✅ Bulk update completato: {bulk_result.get('updated_count', 0)} alert aggiornati")
                    else:
                        print(f"❌ Errore bulk update: {bulk_result.get('error')}")
                else:
                    print(f"❌ Errore HTTP bulk update: {response.status_code}")
            else:
                print("ℹ️ Nessun alert in revisione trovato per il test")
        else:
            print(f"❌ Errore HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test completato!")

def simulate_anomalous_behavior():
    """Simula comportamenti anomali per testare il sistema."""
    
    print("\n🎭 Simulazione Comportamenti Anomali")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # Simula download massivo
    print("\n1. Simulazione Download Massivo")
    print("-" * 30)
    
    try:
        # Simula 60 download in un'ora (dovrebbe generare alert)
        for i in range(60):
            download_data = {
                'user_id': 1,  # Sostituisci con un user_id valido
                'document_id': i + 1,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Invia richiesta di download (se hai un endpoint per questo)
            # response = requests.post(f"{base_url}/api/download", json=download_data)
            print(f"   - Download {i+1}/60 simulato")
            
        print("✅ Download massivo simulato")
        
    except Exception as e:
        print(f"❌ Errore simulazione download: {e}")
    
    # Simula accessi fuori orario
    print("\n2. Simulazione Accessi Fuori Orario")
    print("-" * 30)
    
    try:
        # Simula accessi notturni
        for i in range(5):
            access_data = {
                'user_id': 1,
                'document_id': i + 1,
                'timestamp': datetime.utcnow().replace(hour=2, minute=30).isoformat(),
                'ip_address': '192.168.1.100'
            }
            
            # Invia richiesta di accesso
            # response = requests.post(f"{base_url}/api/access", json=access_data)
            print(f"   - Accesso notturno {i+1}/5 simulato")
            
        print("✅ Accessi fuori orario simulati")
        
    except Exception as e:
        print(f"❌ Errore simulazione accessi: {e}")
    
    # Simula errori login ripetuti
    print("\n3. Simulazione Errori Login Ripetuti")
    print("-" * 30)
    
    try:
        # Simula 15 tentativi falliti
        for i in range(15):
            login_data = {
                'email': 'test@example.com',
                'password': 'wrong_password',
                'timestamp': datetime.utcnow().isoformat(),
                'ip_address': '192.168.1.101'
            }
            
            # Invia tentativo login fallito
            # response = requests.post(f"{base_url}/api/login", json=login_data)
            print(f"   - Tentativo login fallito {i+1}/15 simulato")
            
        print("✅ Errori login ripetuti simulati")
        
    except Exception as e:
        print(f"❌ Errore simulazione login: {e}")
    
    print("\n" + "=" * 50)
    print("🎭 Simulazioni completate!")
    print("💡 Esegui ora 'test_realtime_monitoring()' per verificare gli alert generati")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Sistema Monitoraggio AI Tempo Reale')
    parser.add_argument('--simulate', action='store_true', 
                       help='Simula comportamenti anomali prima del test')
    
    args = parser.parse_args()
    
    if args.simulate:
        simulate_anomalous_behavior()
        print("\n⏳ Attendi 30 secondi per permettere l'analisi AI...")
        time.sleep(30)
    
    test_realtime_monitoring() 