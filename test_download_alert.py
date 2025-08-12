#!/usr/bin/env python3
"""
Script di test per il sistema Download Alert
Simula:
- R1: Burst download (>10 in 5 min)
- R2: Orari insoliti (>5 tra 00:00-05:59 in 30 min)  
- R3: IP anomalo (≥8 in 1h da nuovo IP)
"""

import requests
import time
from datetime import datetime, timedelta
import random
import json

# Configurazione
BASE_URL = "https://docs.mercurysurgelati.org"  # Cambia se necessario
SESSION_COOKIE = "INSERISCI_COOKIE_SESSIONE"    # Cookie di sessione valido

# File di esempio (sostituisci con ID reale)
FILE_ID = "1"  # Cambia con un ID file valido

def get_session():
    """Crea una sessione con cookie di autenticazione"""
    session = requests.Session()
    
    # Cookie di sessione (sostituisci con cookie valido)
    if SESSION_COOKIE != "INSERISCI_COOKIE_SESSIONE":
        session.headers.update({
            'Cookie': SESSION_COOKIE
        })
    
    # Headers per simulare browser reale
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    return session

def download_file(session, file_id, ip_address=None):
    """Simula download di un file"""
    url = f"{BASE_URL}/download_file/{file_id}"
    
    # Aggiungi IP personalizzato se specificato
    if ip_address:
        session.headers.update({'X-Forwarded-For': ip_address})
    
    try:
        response = session.get(url, timeout=10)
        status = response.status_code
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Download {file_id}: Status {status}")
        
        if status == 200:
            print(f"  ✅ Download riuscito")
        elif status == 403:
            print(f"  ❌ Accesso negato (normale per test)")
        else:
            print(f"  ⚠️ Status inaspettato: {status}")
            
        return status == 200
        
    except Exception as e:
        print(f"  ❌ Errore: {str(e)}")
        return False

def test_r1_burst_download(session):
    """Test R1: Burst download (>10 in 5 min)"""
    print("\n" + "="*50)
    print("🚀 TEST R1: Burst Download (>10 in 5 min)")
    print("="*50)
    
    success_count = 0
    for i in range(12):  # >10 download per triggerare R1
        if download_file(session, FILE_ID):
            success_count += 1
        time.sleep(0.5)  # Pausa breve tra download
    
    print(f"\n📊 R1 Completato: {success_count}/12 download riusciti")
    print("💡 Aspetta 5-10 minuti e controlla /admin/download-alerts per R1")

def test_r2_unusual_hours(session):
    """Test R2: Orari insoliti (>5 tra 00:00-05:59 in 30 min)"""
    print("\n" + "="*50)
    print("🌙 TEST R2: Orari Insoliti (>5 tra 00:00-05:59 in 30 min)")
    print("="*50)
    print("⚠️  Nota: Questo test simula orari notturni")
    
    success_count = 0
    for i in range(6):  # >5 download per triggerare R2
        if download_file(session, FILE_ID):
            success_count += 1
        time.sleep(0.5)
    
    print(f"\n📊 R2 Completato: {success_count}/6 download riusciti")
    print("💡 Aspetta 5-10 minuti e controlla /admin/download-alerts per R2")

def test_r3_anomalous_ip(session):
    """Test R3: IP anomalo (≥8 in 1h da nuovo IP)"""
    print("\n" + "="*50)
    print("🌐 TEST R3: IP Anomalo (≥8 in 1h da nuovo IP)")
    print("="*50)
    
    # Genera IP casuale per simulare nuovo IP
    new_ip = f"203.0.113.{random.randint(1, 254)}"
    print(f"🔧 Simulando IP: {new_ip}")
    
    success_count = 0
    for i in range(8):  # ≥8 download per triggerare R3
        if download_file(session, FILE_ID, ip_address=new_ip):
            success_count += 1
        time.sleep(0.5)
    
    print(f"\n📊 R3 Completato: {success_count}/8 download riusciti da IP {new_ip}")
    print("💡 Aspetta 5-10 minuti e controlla /admin/download-alerts per R3")
    print("📧 Controlla email per alert critico!")

def check_alerts_dashboard(session):
    """Controlla la dashboard degli alert"""
    print("\n" + "="*50)
    print("🔍 Controllo Dashboard Alert")
    print("="*50)
    
    try:
        url = f"{BASE_URL}/admin/download-alerts"
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Dashboard accessibile")
            if "download_alerts" in response.text:
                print("✅ Template alert caricato correttamente")
            else:
                print("⚠️  Template alert non trovato")
        else:
            print(f"❌ Dashboard non accessibile: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Errore accesso dashboard: {str(e)}")

def main():
    """Funzione principale"""
    print("🚀 AVVIO TEST SISTEMA DOWNLOAD ALERT")
    print("="*60)
    print(f"📍 URL Base: {BASE_URL}")
    print(f"📁 File ID: {FILE_ID}")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Verifica configurazione
    if SESSION_COOKIE == "INSERISCI_COOKIE_SESSIONE":
        print("\n❌ ERRORE: Devi configurare SESSION_COOKIE!")
        print("📝 Istruzioni:")
        print("1. Accedi a https://docs.mercurysurgelati.org")
        print("2. Apri DevTools (F12) → Network")
        print("3. Fai una richiesta → Copia il cookie 'session'")
        print("4. Sostituisci SESSION_COOKIE con il valore copiato")
        return
    
    if FILE_ID == "1":
        print("\n⚠️  ATTENZIONE: FILE_ID è ancora quello di default!")
        print("📝 Sostituisci con un ID file valido per test realistici")
    
    # Crea sessione
    session = get_session()
    
    # Test di connessione
    print("\n🔗 Test connessione...")
    try:
        response = session.get(BASE_URL, timeout=10)
        if response.status_code == 200:
            print("✅ Connessione OK")
        else:
            print(f"⚠️  Connessione: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Errore connessione: {str(e)}")
        return
    
    # Esegui test
    test_r1_burst_download(session)
    time.sleep(2)
    
    test_r2_unusual_hours(session)
    time.sleep(2)
    
    test_r3_anomalous_ip(session)
    time.sleep(2)
    
    # Controlla dashboard
    check_alerts_dashboard(session)
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETATO!")
    print("="*60)
    print("📋 Prossimi passi:")
    print("1. ⏰ Aspetta 5-10 minuti per l'esecuzione del job scheduler")
    print("2. 🔍 Controlla /admin/download-alerts")
    print("3. 📧 Verifica email per alert critici (R3)")
    print("4. 📊 Controlla statistiche e filtri")
    print("5. 🔧 Testa azioni 'Segna visto' e 'Risolvi'")
    print("\n🎯 Il sistema dovrebbe aver rilevato:")
    print("   • R1: Burst download (Warning)")
    print("   • R2: Orari insoliti (Warning)") 
    print("   • R3: IP anomalo (Critical + Email)")

if __name__ == "__main__":
    main()
