"""
Utility AI per l'analisi automatica dei documenti.

Questo modulo fornisce funzioni per:
- Rilevare documenti duplicati o simili
- Identificare documenti obsoleti o scaduti
- Suggerire azioni automatiche per la gestione documentale
- Generare insight AI per la dashboard
"""

import os
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional
import json

# Importazioni per estrazione testo da diversi formati
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def estrai_testo(file_path: str) -> str:
    """
    Estrae il testo da un file supportando diversi formati.
    
    Args:
        file_path (str): Percorso del file da analizzare.
        
    Returns:
        str: Testo estratto dal file.
    """
    if not os.path.exists(file_path):
        return ""
    
    file_extension = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_extension == '.pdf' and PDF_AVAILABLE:
            return _estrai_testo_pdf(file_path)
        elif file_extension in ['.docx', '.doc'] and DOCX_AVAILABLE:
            return _estrai_testo_docx(file_path)
        elif file_extension in ['.txt', '.md']:
            return _estrai_testo_plain(file_path)
        elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff'] and OCR_AVAILABLE:
            return _estrai_testo_ocr(file_path)
        else:
            # Fallback: prova a leggere come testo
            return _estrai_testo_plain(file_path)
    except Exception as e:
        print(f"Errore nell'estrazione testo da {file_path}: {e}")
        return ""


def _estrai_testo_pdf(file_path: str) -> str:
    """Estrae testo da file PDF."""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Errore estrazione PDF {file_path}: {e}")
        return ""


def _estrai_testo_docx(file_path: str) -> str:
    """Estrae testo da file DOCX."""
    try:
        doc = DocxDocument(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Errore estrazione DOCX {file_path}: {e}")
        return ""


def _estrai_testo_plain(file_path: str) -> str:
    """Estrae testo da file di testo semplice."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read().strip()
        except Exception as e:
            print(f"Errore lettura file {file_path}: {e}")
            return ""


def _estrai_testo_ocr(file_path: str) -> str:
    """Estrae testo da immagini usando OCR."""
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang='ita+eng')
        return text.strip()
    except Exception as e:
        print(f"Errore OCR {file_path}: {e}")
        return ""


def similarita_testi(testo1: str, testo2: str) -> float:
    """
    Calcola la similarità tra due testi usando SequenceMatcher.
    
    Args:
        testo1 (str): Primo testo da confrontare.
        testo2 (str): Secondo testo da confrontare.
        
    Returns:
        float: Valore di similarità tra 0 e 1.
    """
    if not testo1 or not testo2:
        return 0.0
    
    # Normalizza i testi per migliorare il confronto
    testo1_norm = _normalizza_testo(testo1)
    testo2_norm = _normalizza_testo(testo2)
    
    return SequenceMatcher(None, testo1_norm, testo2_norm).ratio()


def _normalizza_testo(testo: str) -> str:
    """
    Normalizza il testo per migliorare il confronto.
    
    Args:
        testo (str): Testo da normalizzare.
        
    Returns:
        str: Testo normalizzato.
    """
    # Rimuove spazi extra e converte in minuscolo
    testo = re.sub(r'\s+', ' ', testo.lower().strip())
    # Rimuove caratteri speciali mantenendo lettere e numeri
    testo = re.sub(r'[^\w\s]', '', testo)
    return testo


def analizza_documento(documento, altri_documenti: List) -> Dict:
    """
    Analizza un documento per rilevare duplicati, obsolescenza e suggerire azioni.
    
    Args:
        documento: Oggetto Document da analizzare.
        altri_documenti (List): Lista di altri documenti per il confronto.
        
    Returns:
        Dict: Dizionario con i risultati dell'analisi.
    """
    output = {}
    
    # Estrai testo dal documento corrente
    testo_doc = estrai_testo(documento.file_path)
    if not testo_doc:
        output["errore"] = "Impossibile estrarre testo dal documento"
        return output
    
    # Cerca duplicati
    simili = []
    for altro in altri_documenti:
        if altro.id == documento.id:
            continue
        
        testo_altro = estrai_testo(altro.file_path)
        if testo_altro:
            sim = similarita_testi(testo_doc, testo_altro)
            if sim > 0.85:  # Soglia alta per duplicati
                simili.append({
                    'id': altro.id,
                    'titolo': altro.title,
                    'similarita': round(sim, 3),
                    'data_creazione': altro.created_at.isoformat() if altro.created_at else None
                })
    
    if simili:
        output["duplicati"] = simili
    
    # Analizza obsolescenza
    oggi = datetime.utcnow()
    
    # Controlla scadenza
    if documento.expiry_date and documento.expiry_date < oggi:
        output["obsoleto"] = {
            'tipo': 'scaduto',
            'data_scadenza': documento.expiry_date.isoformat(),
            'giorni_scaduto': (oggi - documento.expiry_date).days
        }
    
    # Controlla età del documento
    if documento.created_at:
        eta_documento = oggi - documento.created_at
        if eta_documento.days > 365:  # Più di un anno
            output["vecchio"] = {
                'tipo': 'documento_antico',
                'eta_giorni': eta_documento.days,
                'data_creazione': documento.created_at.isoformat()
            }
    
    # Analizza pattern di utilizzo
    if hasattr(documento, 'download_logs') and documento.download_logs:
        ultimo_accesso = max(log.timestamp for log in documento.download_logs)
        giorni_senza_accesso = (oggi - ultimo_accesso).days
        
        if giorni_senza_accesso > 180:  # Più di 6 mesi
            output["inutilizzato"] = {
                'tipo': 'documento_non_acceduto',
                'giorni_senza_accesso': giorni_senza_accesso,
                'ultimo_accesso': ultimo_accesso.isoformat()
            }
    
    return output


def genera_insight_ai(risultato_analisi: Dict, documento) -> Dict:
    """
    Genera insight AI basati sui risultati dell'analisi.
    
    Args:
        risultato_analisi (Dict): Risultati dell'analisi del documento.
        documento: Oggetto Document analizzato.
        
    Returns:
        Dict: Insight AI generati.
    """
    insight = {
        'documento_id': documento.id,
        'titolo_documento': documento.title,
        'insight_text': "",
        'insight_type': "",
        'severity': "informativo",
        'suggerimenti': []
    }
    
    # Gestisce duplicati
    if 'duplicati' in risultato_analisi:
        duplicati = risultato_analisi['duplicati']
        insight['insight_type'] = 'duplicato'
        insight['severity'] = 'attenzione'
        
        if len(duplicati) == 1:
            insight['insight_text'] = f"Documento potenzialmente duplicato con {duplicati[0]['titolo']} (similarità: {duplicati[0]['similarita']})"
        else:
            insight['insight_text'] = f"Documento con {len(duplicati)} potenziali duplicati rilevati"
        
        insight['suggerimenti'].append("Verificare se i documenti sono effettivamente duplicati")
        insight['suggerimenti'].append("Considerare l'archiviazione di uno dei duplicati")
    
    # Gestisce documenti obsoleti
    elif 'obsoleto' in risultato_analisi:
        obsoleto = risultato_analisi['obsoleto']
        insight['insight_type'] = 'obsoleto'
        insight['severity'] = 'critico'
        
        if obsoleto['tipo'] == 'scaduto':
            insight['insight_text'] = f"Documento scaduto da {obsoleto['giorni_scaduto']} giorni"
            insight['suggerimenti'].append("Aggiornare il documento con una nuova versione")
            insight['suggerimenti'].append("Verificare se il documento è ancora necessario")
    
    # Gestisce documenti vecchi
    elif 'vecchio' in risultato_analisi:
        vecchio = risultato_analisi['vecchio']
        insight['insight_type'] = 'vecchio'
        insight['severity'] = 'attenzione'
        
        insight['insight_text'] = f"Documento creato {vecchio['eta_giorni']} giorni fa"
        insight['suggerimenti'].append("Verificare se il contenuto è ancora aggiornato")
        insight['suggerimenti'].append("Considerare una revisione del documento")
    
    # Gestisce documenti inutilizzati
    elif 'inutilizzato' in risultato_analisi:
        inutilizzato = risultato_analisi['inutilizzato']
        insight['insight_type'] = 'inutilizzato'
        insight['severity'] = 'attenzione'
        
        insight['insight_text'] = f"Documento non accesso da {inutilizzato['giorni_senza_accesso']} giorni"
        insight['suggerimenti'].append("Verificare se il documento è ancora necessario")
        insight['suggerimenti'].append("Considerare l'archiviazione se non più utilizzato")
    
    else:
        insight['insight_text'] = "Documento in buono stato"
        insight['suggerimenti'].append("Nessuna azione richiesta")
    
    return insight


def suggerisci_task_automatico(insight: Dict) -> Dict:
    """
    Suggerisce task automatici basati sugli insight AI.
    
    Args:
        insight (Dict): Insight AI generato.
        
    Returns:
        Dict: Task suggerito.
    """
    task = {
        'titolo': "",
        'descrizione': "",
        'priorita': "Media",
        'stato': "Da fare",
        'scadenza': None
    }
    
    if insight['insight_type'] == 'duplicato':
        task['titolo'] = f"Verifica duplicati - {insight['titolo_documento']}"
        task['descrizione'] = f"Verificare se il documento '{insight['titolo_documento']}' è effettivamente duplicato e decidere quale mantenere."
        task['priorita'] = "Alta"
        task['scadenza'] = datetime.utcnow() + timedelta(days=7)
    
    elif insight['insight_type'] == 'obsoleto':
        task['titolo'] = f"Aggiornamento documento scaduto - {insight['titolo_documento']}"
        task['descrizione'] = f"Il documento '{insight['titolo_documento']}' è scaduto e necessita di aggiornamento o sostituzione."
        task['priorita'] = "Critica"
        task['scadenza'] = datetime.utcnow() + timedelta(days=3)
    
    elif insight['insight_type'] == 'vecchio':
        task['titolo'] = f"Revisione documento antico - {insight['titolo_documento']}"
        task['descrizione'] = f"Verificare se il documento '{insight['titolo_documento']}' è ancora aggiornato e rilevante."
        task['priorita'] = "Media"
        task['scadenza'] = datetime.utcnow() + timedelta(days=14)
    
    elif insight['insight_type'] == 'inutilizzato':
        task['titolo'] = f"Verifica documento inutilizzato - {insight['titolo_documento']}"
        task['descrizione'] = f"Verificare se il documento '{insight['titolo_documento']}' è ancora necessario o può essere archiviato."
        task['priorita'] = "Bassa"
        task['scadenza'] = datetime.utcnow() + timedelta(days=30)
    
    return task 