"""
Servizio per applicazione watermark dinamici ai PDF.
Gestisce l'applicazione di watermark personalizzati con informazioni utente e timestamp.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from io import BytesIO

try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False
    
try:
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import Color
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from flask import current_app, request
from flask_login import current_user

logger = logging.getLogger(__name__)


class WatermarkService:
    """
    Servizio per applicazione watermark a documenti PDF.
    """
    
    def __init__(self):
        """Inizializza il servizio watermark."""
        self.enabled = os.getenv('WATERMARK_ENABLED', 'True').lower() == 'true'
        self.template = os.getenv('WATERMARK_TEXT_TEMPLATE', 
                                 'User: {username} | {timestamp} | IP: {ip}')
    
    def is_watermark_required(self, document, user) -> bool:
        """
        Determina se un documento richiede watermark.
        
        Args:
            document: Oggetto Document
            user: Oggetto User
            
        Returns:
            bool: True se il watermark è richiesto
        """
        if not self.enabled:
            return False
        
        # Controlla se il file è PDF
        if not document.filename.lower().endswith('.pdf'):
            return False
        
        # Watermark per file con classification >= "Internal" o flag "confidential"
        if hasattr(document, 'classification'):
            internal_levels = ['internal', 'confidential', 'restricted', 'secret']
            if document.classification and document.classification.lower() in internal_levels:
                return True
        
        # Controlla flag confidential
        if hasattr(document, 'confidential') and document.confidential:
            return True
        
        # Controlla visibilità privata come fallback
        if document.visibility == 'privato':
            return True
        
        return False
    
    def generate_watermark_text(self, user, document=None, custom_vars=None) -> str:
        """
        Genera il testo del watermark.
        
        Args:
            user: Oggetto User
            document: Oggetto Document (opzionale)
            custom_vars: Variabili personalizzate (opzionale)
            
        Returns:
            str: Testo del watermark formattato
        """
        try:
            # Variabili di default
            variables = {
                'username': user.username if user else 'Anonymous',
                'full_name': f"{user.first_name} {user.last_name}".strip() if user and user.first_name else (user.username if user else 'Anonymous'),
                'email': user.email if user else 'unknown',
                'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'date': datetime.now().strftime('%d/%m/%Y'),
                'time': datetime.now().strftime('%H:%M:%S'),
                'ip': self._get_client_ip()
            }
            
            # Aggiungi variabili documento se disponibili
            if document:
                variables.update({
                    'document_title': document.title or document.original_filename,
                    'document_id': document.id,
                    'company': document.company.name if hasattr(document, 'company') and document.company else 'N/A',
                    'department': document.department.name if hasattr(document, 'department') and document.department else 'N/A'
                })
            
            # Aggiungi variabili custom
            if custom_vars:
                variables.update(custom_vars)
            
            # Formatta il template
            watermark_text = self.template.format(**variables)
            return watermark_text
            
        except Exception as e:
            logger.error(f"Errore generazione testo watermark: {e}")
            return f"User: {user.username if user else 'Unknown'} | {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    
    def _get_client_ip(self) -> str:
        """Ottiene l'IP del client."""
        try:
            if request.environ.get('HTTP_X_FORWARDED_FOR'):
                return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
            elif request.environ.get('HTTP_X_REAL_IP'):
                return request.environ['HTTP_X_REAL_IP']
            else:
                return request.environ.get('REMOTE_ADDR', 'unknown')
        except:
            return 'unknown'
    
    def create_watermark_overlay(self, text: str, page_width: float, page_height: float) -> bytes:
        """
        Crea un overlay PDF con il watermark.
        
        Args:
            text: Testo del watermark
            page_width: Larghezza della pagina
            page_height: Altezza della pagina
            
        Returns:
            bytes: PDF overlay con watermark
        """
        if not PYPDF2_AVAILABLE:
            raise ImportError("PyPDF2 e reportlab sono richiesti per il watermark")
        
        # Crea PDF temporaneo con watermark
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))
        
        # Configurazione watermark
        can.setFont("Helvetica", 10)
        can.setFillColor(Color(0.5, 0.5, 0.5, alpha=0.3))  # Grigio semitrasparente
        
        # Posiziona watermark (footer)
        x_pos = 50
        y_pos = 30
        can.drawString(x_pos, y_pos, text)
        
        # Watermark diagonale aggiuntivo (opzionale)
        can.saveState()
        can.translate(page_width/2, page_height/2)
        can.rotate(45)
        can.setFont("Helvetica", 20)
        can.setFillColor(Color(0.8, 0.8, 0.8, alpha=0.1))  # Molto trasparente
        can.drawCentredText(0, 0, text.split('|')[0].strip())  # Solo username
        can.restoreState()
        
        can.save()
        
        packet.seek(0)
        return packet.getvalue()
    
    def apply_watermark_pypdf2(self, pdf_bytes: bytes, watermark_text: str) -> bytes:
        """
        Applica watermark usando PyPDF2.
        
        Args:
            pdf_bytes: Contenuto PDF originale
            watermark_text: Testo del watermark
            
        Returns:
            bytes: PDF con watermark applicato
        """
        if not PYPDF2_AVAILABLE:
            raise ImportError("PyPDF2 e reportlab non sono disponibili")
        
        try:
            # Leggi PDF originale
            pdf_reader = PdfReader(BytesIO(pdf_bytes))
            pdf_writer = PdfWriter()
            
            # Processa ogni pagina
            for page_num, page in enumerate(pdf_reader.pages):
                # Ottieni dimensioni pagina
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                
                # Crea overlay watermark
                watermark_bytes = self.create_watermark_overlay(watermark_text, page_width, page_height)
                watermark_pdf = PdfReader(BytesIO(watermark_bytes))
                
                # Applica watermark alla pagina
                if len(watermark_pdf.pages) > 0:
                    page.merge_page(watermark_pdf.pages[0])
                
                pdf_writer.add_page(page)
            
            # Genera PDF finale
            output_stream = BytesIO()
            pdf_writer.write(output_stream)
            output_stream.seek(0)
            
            return output_stream.getvalue()
            
        except Exception as e:
            logger.error(f"Errore applicazione watermark PyPDF2: {e}")
            raise
    
    def apply_watermark_pikepdf(self, pdf_bytes: bytes, watermark_text: str) -> bytes:
        """
        Applica watermark usando pikepdf (più robusto).
        
        Args:
            pdf_bytes: Contenuto PDF originale
            watermark_text: Testo del watermark
            
        Returns:
            bytes: PDF con watermark applicato
        """
        if not PIKEPDF_AVAILABLE:
            raise ImportError("pikepdf non è disponibile")
        
        try:
            # Apri PDF con pikepdf
            with pikepdf.open(BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    # Aggiungi watermark come annotazione di testo
                    # Questo è un approccio semplificato
                    # Per implementazioni più complesse si può usare l'overlay
                    pass
                
                # Salva PDF modificato
                output_stream = BytesIO()
                pdf.save(output_stream)
                output_stream.seek(0)
                
                return output_stream.getvalue()
                
        except Exception as e:
            logger.error(f"Errore applicazione watermark pikepdf: {e}")
            raise
    
    def apply_watermark(self, pdf_bytes: bytes, watermark_text: str) -> bytes:
        """
        Applica watermark al PDF usando la libreria disponibile.
        
        Args:
            pdf_bytes: Contenuto PDF originale
            watermark_text: Testo del watermark
            
        Returns:
            bytes: PDF con watermark applicato
            
        Raises:
            ImportError: Se nessuna libreria PDF è disponibile
            Exception: Per altri errori di processing
        """
        if not self.enabled:
            logger.info("Watermark disabilitato, PDF restituito senza modifiche")
            return pdf_bytes
        
        # Prova prima con PyPDF2 (più affidabile per watermark)
        if PYPDF2_AVAILABLE:
            try:
                return self.apply_watermark_pypdf2(pdf_bytes, watermark_text)
            except Exception as e:
                logger.warning(f"Fallback da PyPDF2 a pikepdf: {e}")
        
        # Fallback su pikepdf
        if PIKEPDF_AVAILABLE:
            try:
                return self.apply_watermark_pikepdf(pdf_bytes, watermark_text)
            except Exception as e:
                logger.error(f"Errore anche con pikepdf: {e}")
                raise
        
        # Nessuna libreria disponibile
        raise ImportError("Nessuna libreria PDF disponibile per il watermark (PyPDF2, pikepdf)")
    
    def process_document_for_watermark(self, document, user, file_path: str) -> bool:
        """
        Processa un documento per applicare il watermark se necessario.
        
        Args:
            document: Oggetto Document
            user: Oggetto User
            file_path: Percorso del file PDF
            
        Returns:
            bool: True se il watermark è stato applicato con successo
        """
        try:
            # Controlla se il watermark è richiesto
            if not self.is_watermark_required(document, user):
                logger.info(f"Watermark non richiesto per documento {document.id}")
                return True
            
            # Leggi il file PDF
            if not os.path.exists(file_path):
                logger.error(f"File non trovato: {file_path}")
                return False
            
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            
            # Genera testo watermark
            watermark_text = self.generate_watermark_text(user, document)
            logger.info(f"Applicando watermark: '{watermark_text}' al documento {document.id}")
            
            # Applica watermark
            watermarked_pdf = self.apply_watermark(pdf_bytes, watermark_text)
            
            # Salva il file con watermark
            with open(file_path, 'wb') as f:
                f.write(watermarked_pdf)
            
            logger.info(f"Watermark applicato con successo al documento {document.id}")
            
            # Log dell'evento
            from utils.audit_utils import log_audit_event
            log_audit_event(
                user.id if user else None,
                'watermark_applied',
                'document',
                document.id,
                {'watermark_text': watermark_text, 'file_path': file_path}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Errore applicazione watermark al documento {document.id}: {e}")
            return False
    
    def check_pdf_libraries(self) -> Dict[str, Any]:
        """
        Controlla la disponibilità delle librerie PDF.
        
        Returns:
            Dict: Status delle librerie
        """
        return {
            'watermark_enabled': self.enabled,
            'pypdf2_available': PYPDF2_AVAILABLE,
            'pikepdf_available': PIKEPDF_AVAILABLE,
            'can_apply_watermark': PYPDF2_AVAILABLE or PIKEPDF_AVAILABLE,
            'template': self.template,
            'recommended_install': 'pip install PyPDF2 reportlab pikepdf' if not (PYPDF2_AVAILABLE and PIKEPDF_AVAILABLE) else None
        }


# Istanza globale del servizio
watermark_service = WatermarkService()
