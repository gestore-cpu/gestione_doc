"""
Servizio per la generazione di preview di file.
Gestisce PDF, immagini e file Office.
"""

import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from PIL import Image
import pikepdf
from flask import current_app


def generate_pdf_preview(pdf_path: str, file_id: int) -> Optional[str]:
    """
    Genera preview della prima pagina di un PDF.
    
    Args:
        pdf_path: Percorso del file PDF
        file_id: ID del file per naming cache
        
    Returns:
        Percorso del file preview PNG o None se errore
    """
    try:
        # Crea directory cache se non esiste
        cache_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'previews')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Nome file preview
        preview_filename = f"preview_{file_id}.png"
        preview_path = os.path.join(cache_dir, preview_filename)
        
        # Se esiste già, restituisci
        if os.path.exists(preview_path):
            return preview_path
        
        # Apri PDF con pikepdf
        with pikepdf.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                return None
            
            # Prendi prima pagina
            first_page = pdf.pages[0]
            
            # Converti in immagine
            # Nota: pikepdf non ha conversione diretta PDF->PNG
            # Usiamo un approccio alternativo con subprocess
            return _convert_pdf_to_image_subprocess(pdf_path, preview_path)
            
    except Exception as e:
        current_app.logger.error(f"Errore generazione preview PDF {pdf_path}: {e}")
        return None


def _convert_pdf_to_image_subprocess(pdf_path: str, output_path: str) -> Optional[str]:
    """
    Converte PDF in immagine usando subprocess (pdftoppm, convert, etc.).
    
    Args:
        pdf_path: Percorso PDF
        output_path: Percorso output PNG
        
    Returns:
        Percorso file generato o None se errore
    """
    try:
        # Prova con pdftoppm (poppler-utils)
        cmd = ['pdftoppm', '-png', '-singlefile', '-f', '1', '-l', '1', pdf_path, output_path.replace('.png', '')]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
        
        # Fallback con convert (ImageMagick)
        cmd = ['convert', f'{pdf_path}[0]', output_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
        
        # Fallback con gs (Ghostscript)
        cmd = ['gs', '-sDEVICE=pngalpha', '-dNOPAUSE', '-dBATCH', '-dSAFER', 
               '-dFirstPage=1', '-dLastPage=1', '-r150', 
               f'-sOutputFile={output_path}', pdf_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
            
        return None
        
    except Exception as e:
        current_app.logger.error(f"Errore conversione PDF->PNG: {e}")
        return None


def convert_office_to_pdf(office_path: str, file_id: int) -> Optional[str]:
    """
    Converte file Office in PDF usando LibreOffice.
    
    Args:
        office_path: Percorso file Office
        file_id: ID del file per naming cache
        
    Returns:
        Percorso del file PDF convertito o None se errore
    """
    try:
        # Crea directory cache se non esiste
        cache_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'converted')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Nome file PDF convertito
        pdf_filename = f"converted_{file_id}.pdf"
        pdf_path = os.path.join(cache_dir, pdf_filename)
        
        # Se esiste già, restituisci
        if os.path.exists(pdf_path):
            return pdf_path
        
        # Converte con LibreOffice headless
        cmd = [
            'libreoffice', '--headless', '--convert-to', 'pdf',
            '--outdir', cache_dir, office_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # LibreOffice genera il file con nome originale + .pdf
            original_name = Path(office_path).stem
            generated_pdf = os.path.join(cache_dir, f"{original_name}.pdf")
            
            if os.path.exists(generated_pdf):
                # Rinomina nel formato standard
                os.rename(generated_pdf, pdf_path)
                return pdf_path
        
        return None
        
    except Exception as e:
        current_app.logger.error(f"Errore conversione Office->PDF {office_path}: {e}")
        return None


def resize_image(image_path: str, max_width: int = 800, max_height: int = 600) -> Optional[str]:
    """
    Ridimensiona un'immagine mantenendo le proporzioni.
    
    Args:
        image_path: Percorso immagine
        max_width: Larghezza massima
        max_height: Altezza massima
        
    Returns:
        Percorso immagine ridimensionata o None se errore
    """
    try:
        with Image.open(image_path) as img:
            # Calcola nuove dimensioni mantenendo proporzioni
            width, height = img.size
            ratio = min(max_width / width, max_height / height)
            
            if ratio >= 1:
                # Immagine già più piccola, restituisci originale
                return image_path
            
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            # Ridimensiona
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Salva in cache
            cache_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'thumbnails')
            os.makedirs(cache_dir, exist_ok=True)
            
            filename = Path(image_path).name
            thumbnail_path = os.path.join(cache_dir, f"thumb_{filename}")
            
            resized_img.save(thumbnail_path, optimize=True, quality=85)
            
            return thumbnail_path
            
    except Exception as e:
        current_app.logger.error(f"Errore ridimensionamento immagine {image_path}: {e}")
        return None


def get_preview_path(file_path: str, file_id: int, mime_type: str) -> Optional[str]:
    """
    Ottiene il percorso del preview per un file.
    
    Args:
        file_path: Percorso del file
        file_id: ID del file
        mime_type: Tipo MIME del file
        
    Returns:
        Percorso del preview o None se non disponibile
    """
    try:
        file_ext = Path(file_path).suffix.lower()
        
        if mime_type.startswith('image/'):
            # Immagini: ridimensiona
            return resize_image(file_path)
        
        elif mime_type == 'application/pdf':
            # PDF: genera preview
            return generate_pdf_preview(file_path, file_id)
        
        elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
            # Office: converti in PDF e poi genera preview
            pdf_path = convert_office_to_pdf(file_path, file_id)
            if pdf_path:
                return generate_pdf_preview(pdf_path, f"{file_id}_converted")
        
        return None
        
    except Exception as e:
        current_app.logger.error(f"Errore ottenimento preview {file_path}: {e}")
        return None


def cleanup_old_previews(max_age_days: int = 7):
    """
    Pulisce i preview più vecchi di max_age_days giorni.
    
    Args:
        max_age_days: Età massima in giorni
    """
    try:
        import time
        from datetime import datetime, timedelta
        
        cache_dirs = [
            os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'previews'),
            os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'converted'),
            os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'thumbnails')
        ]
        
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        
        for cache_dir in cache_dirs:
            if not os.path.exists(cache_dir):
                continue
                
            for filename in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, filename)
                
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_time < cutoff_time:
                        try:
                            os.remove(file_path)
                            current_app.logger.info(f"Rimosso preview vecchio: {file_path}")
                        except Exception as e:
                            current_app.logger.error(f"Errore rimozione preview {file_path}: {e}")
                            
    except Exception as e:
        current_app.logger.error(f"Errore pulizia preview: {e}")
