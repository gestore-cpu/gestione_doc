"""
Servizio per la classificazione AI dei documenti.
Analizza il contenuto dei documenti e assegna tag, categoria e modulo di destinazione.
"""

import os
import re
from typing import Tuple, Optional
import PyPDF2
from PIL import Image
import pytesseract


def estrai_testo_pdf(file_path: str) -> str:
    """
    Estrae il testo da un file PDF.
    
    Args:
        file_path (str): Percorso del file PDF.
        
    Returns:
        str: Testo estratto dal PDF.
    """
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            testo = ""
            for page in pdf_reader.pages:
                testo += page.extract_text() + " "
            return testo.lower()
    except Exception as e:
        print(f"Errore estrazione testo PDF: {e}")
        return ""


def estrai_testo_immagine(file_path: str) -> str:
    """
    Estrae il testo da un'immagine usando OCR.
    
    Args:
        file_path (str): Percorso del file immagine.
        
    Returns:
        str: Testo estratto dall'immagine.
    """
    try:
        image = Image.open(file_path)
        testo = pytesseract.image_to_string(image, lang='ita')
        return testo.lower()
    except Exception as e:
        print(f"Errore OCR immagine: {e}")
        return ""


def estrai_testo_documento(file_path: str) -> str:
    """
    Estrae il testo da un documento in base alla sua estensione.
    
    Args:
        file_path (str): Percorso del file.
        
    Returns:
        str: Testo estratto dal documento.
    """
    if not os.path.exists(file_path):
        return ""
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return estrai_testo_pdf(file_path)
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        return estrai_testo_immagine(file_path)
    elif ext in ['.txt', '.csv']:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().lower()
        except:
            return ""
    else:
        # Per altri formati, restituisce il nome del file
        return os.path.basename(file_path).lower()


def classifica_documento_ai(file_path: str, contenuto_testuale: str = "") -> Tuple[str, str, Optional[str]]:
    """
    Classifica un documento usando AI basata su contenuto e nome file.
    
    Args:
        file_path (str): Percorso del file.
        contenuto_testuale (str): Testo estratto dal documento.
        
    Returns:
        Tuple[str, str, Optional[str]]: (tag, categoria, modulo_destinazione)
    """
    # Se non è stato fornito contenuto, estrailo
    if not contenuto_testuale:
        contenuto_testuale = estrai_testo_documento(file_path)
    
    nome_file = os.path.basename(file_path).lower()
    contenuto_completo = f"{nome_file} {contenuto_testuale}"
    
    # === CLASSIFICAZIONE PER DANNI/INCIDENTI ===
    if any(parola in contenuto_completo for parola in [
        "verbale", "incidente", "danno", "sinistro", "accidente", "guasto",
        "rottura", "malfunzionamento", "emergenza", "urgenza"
    ]):
        return "Danno", "Verbale incidente", "service"
    
    # === CLASSIFICAZIONE PER CERTIFICAZIONI ISO ===
    if any(parola in contenuto_completo for parola in [
        "iso 9001", "iso 14001", "iso 45001", "certificazione", "manuale",
        "procedura", "istruzione", "haccp", "qualità", "sicurezza"
    ]):
        return "Certificazione", "Manuale ISO", "qms"
    
    # === CLASSIFICAZIONE PER FATTURE/CONTABILITÀ ===
    if any(parola in contenuto_completo for parola in [
        "fattura", "importo", "euro", "€", "totale", "iva", "pagamento",
        "ricevuta", "scontrino", "prezzo", "costo"
    ]):
        return "Contabilità", "Fattura", "acquisti"
    
    # === CLASSIFICAZIONE PER POLICY/RISORSE UMANE ===
    if any(parola in contenuto_completo for parola in [
        "policy", "dpi", "regolamento", "norme", "procedure hr",
        "risorse umane", "personale", "dipendenti", "contratto"
    ]):
        return "Risorse Umane", "Regolamento", "elevate"
    
    # === CLASSIFICAZIONE PER MANUTENZIONE ===
    if any(parola in contenuto_completo for parola in [
        "manutenzione", "revisione", "controllo", "verifica",
        "pulizia", "sanitizzazione", "calibrazione"
    ]):
        return "Manutenzione", "Piano manutenzione", "service"
    
    # === CLASSIFICAZIONE PER FORMAZIONE ===
    if any(parola in contenuto_completo for parola in [
        "formazione", "corso", "training", "addestramento",
        "attestato", "certificato", "partecipanti"
    ]):
        return "Formazione", "Corso formazione", "elevate"
    
    # === CLASSIFICAZIONE PER INVENTARIO ===
    if any(parola in contenuto_completo for parola in [
        "inventario", "stock", "magazzino", "quantità",
        "listino", "catalogo", "prodotti"
    ]):
        return "Inventario", "Listino prodotti", "acquisti"
    
    # === CLASSIFICAZIONE PER DOCUMENTI LEGALI ===
    if any(parola in contenuto_completo for parola in [
        "contratto", "accordo", "clausola", "legale",
        "avvocato", "notaio", "firma"
    ]):
        return "Legale", "Contratto", "elevate"
    
    # === CLASSIFICAZIONE PER DOCUMENTI TECNICI ===
    if any(parola in contenuto_completo for parola in [
        "specifiche", "tecnico", "disegno", "schema",
        "diagramma", "progetto", "installazione"
    ]):
        return "Tecnico", "Specifiche tecniche", "service"
    
    # === CLASSIFICAZIONE PER DOCUMENTI AMMINISTRATIVI ===
    if any(parola in contenuto_completo for parola in [
        "amministrazione", "burocrazia", "pratica",
        "domanda", "richiesta", "autorizzazione"
    ]):
        return "Amministrativo", "Pratica amministrativa", "elevate"
    
    # === DEFAULT ===
    return "Altro", "Generico", None


def genera_task_ai_documentale(modulo: str, document) -> bool:
    """
    Genera automaticamente un task nel modulo corrispondente.
    
    Args:
        modulo (str): Modulo di destinazione.
        document: Oggetto documento.
        
    Returns:
        bool: True se il task è stato generato con successo.
    """
    try:
        from models import Task
        from extensions import db
        from datetime import datetime, timedelta
        
        # Determina il titolo e la descrizione del task in base al modulo
        task_config = {
            "service": {
                "titolo": f"Gestione documento: {document.title}",
                "descrizione": f"Documento classificato come {document.categoria_ai}. Richiede attenzione del team service.",
                "priorita": "Media",
                "scadenza": datetime.utcnow() + timedelta(days=7)
            },
            "qms": {
                "titolo": f"Revisione documento QMS: {document.title}",
                "descrizione": f"Documento certificazione {document.categoria_ai} da revisionare per compliance.",
                "priorita": "Alta",
                "scadenza": datetime.utcnow() + timedelta(days=14)
            },
            "elevate": {
                "titolo": f"Gestione documento Elevate: {document.title}",
                "descrizione": f"Documento {document.categoria_ai} per il modulo Elevate.",
                "priorita": "Media",
                "scadenza": datetime.utcnow() + timedelta(days=10)
            },
            "acquisti": {
                "titolo": f"Processo documento acquisti: {document.title}",
                "descrizione": f"Documento {document.categoria_ai} da processare nel modulo acquisti.",
                "priorita": "Media",
                "scadenza": datetime.utcnow() + timedelta(days=5)
            }
        }
        
        if modulo not in task_config:
            return False
        
        config = task_config[modulo]
        
        # Crea il task
        task = Task(
            titolo=config["titolo"],
            descrizione=config["descrizione"],
            priorita=config["priorita"],
            scadenza=config["scadenza"],
            created_by=document.uploader_email,
            stato="Da fare"
        )
        
        db.session.add(task)
        db.session.commit()
        
        print(f"✅ Task generato per modulo {modulo}: {task.titolo}")
        return True
        
    except Exception as e:
        print(f"❌ Errore generazione task: {e}")
        return False


def classifica_e_processa_documento(document) -> bool:
    """
    Classifica un documento e genera task se necessario.
    
    Args:
        document: Oggetto documento da processare.
        
    Returns:
        bool: True se il processo è completato con successo.
    """
    try:
        from extensions import db
        from utils_extra import log_ai_analysis
        
        # Costruisci il percorso del file
        file_path = os.path.join("uploads", document.filename)
        
        # Classifica il documento
        tag, categoria, modulo = classifica_documento_ai(file_path)
        
        # Aggiorna il documento
        document.tag = tag
        document.categoria_ai = categoria
        document.collegato_a_modulo = modulo
        
        # Log della classificazione AI
        log_ai_analysis(
            document_id=document.id,
            action_type="classificazione_ai",
            payload={
                "tag_suggerito": tag,
                "categoria_ai": categoria,
                "modulo_destinazione": modulo,
                "file_path": file_path
            }
        )
        
        # Genera task se necessario
        if modulo and not document.auto_task_generato:
            if genera_task_ai_documentale(modulo, document):
                document.auto_task_generato = True
                
                # Log della generazione task
                log_ai_analysis(
                    document_id=document.id,
                    action_type="task_generato",
                    payload={
                        "modulo": modulo,
                        "task_titolo": f"Gestione documento: {document.title}",
                        "priorita": "Media"
                    }
                )
        
        db.session.commit()
        
        print(f"✅ Documento classificato: {tag} - {categoria} - {modulo}")
        return True
        
    except Exception as e:
        print(f"❌ Errore classificazione documento: {e}")
        return False 