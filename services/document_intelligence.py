"""
Servizio per l'analisi AI dei documenti PDF.
Integra Document Intelligence di FocusMe AI nel modulo DOCS.
"""

import os
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path

# Import per analisi PDF
try:
    import PyPDF2
    from PyPDF2 import PdfReader
except ImportError:
    PyPDF2 = None

# Import per analisi semantica
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
except ImportError:
    SentenceTransformer = None

from models import db, Document, Task, User
from utils.audit_logger import log_event

logger = logging.getLogger(__name__)

class DocumentIntelligence:
    """
    Servizio per l'analisi AI dei documenti PDF.
    
    Funzionalità:
    - Analisi contenuto semantico
    - Verifica coerenza con principi attivi
    - Rilevamento scadenze, firme mancanti, incompletezze
    - Generazione task automatici
    """
    
    def __init__(self):
        """Inizializza il servizio Document Intelligence."""
        self.model = None
        self.principi_attivi = []
        self.load_semantic_model()
        self.load_principi_attivi()
    
    def load_semantic_model(self):
        """Carica il modello semantico per l'analisi."""
        try:
            if SentenceTransformer:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ Modello semantico caricato per Document Intelligence")
            else:
                logger.warning("⚠️ SentenceTransformer non disponibile, analisi semantica limitata")
        except Exception as e:
            logger.error(f"❌ Errore caricamento modello semantico: {e}")
    
    def load_principi_attivi(self):
        """Carica i principi attivi per la verifica di coerenza."""
        try:
            # TODO: Carica da database o file di configurazione
            self.principi_attivi = [
                "sicurezza alimentare",
                "qualità",
                "compliance",
                "sostenibilità",
                "innovazione",
                "eccellenza operativa"
            ]
            logger.info(f"✅ Caricati {len(self.principi_attivi)} principi attivi")
        except Exception as e:
            logger.error(f"❌ Errore caricamento principi attivi: {e}")
    
    def analyze_pdf_content(self, pdf_path: str) -> Dict:
        """
        Analizza il contenuto di un PDF.
        
        Args:
            pdf_path: Percorso del file PDF
            
        Returns:
            Dict con analisi del contenuto
        """
        try:
            if not os.path.exists(pdf_path):
                return {"error": "File PDF non trovato"}
            
            if not PyPDF2:
                return {"error": "PyPDF2 non disponibile"}
            
            # Estrai testo dal PDF
            text_content = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
            
            # Analisi base
            analysis = {
                "text_length": len(text_content),
                "pages": len(pdf_reader.pages),
                "content": text_content[:1000],  # Primi 1000 caratteri
                "keywords": self.extract_keywords(text_content),
                "scadenze": self.detect_scadenze(text_content),
                "firme": self.detect_firme(text_content),
                "incompletezze": self.detect_incompletezze(text_content),
                "coerenza_principi": self.check_principi_coerenza(text_content)
            }
            
            logger.info(f"✅ Analisi PDF completata: {len(text_content)} caratteri")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Errore analisi PDF: {e}")
            return {"error": str(e)}
    
    def extract_keywords(self, text: str) -> List[str]:
        """Estrae parole chiave dal testo."""
        # Implementazione base - può essere migliorata con NLP
        keywords = []
        important_words = [
            "scadenza", "firma", "approvazione", "revisione", "aggiornamento",
            "compliance", "qualità", "sicurezza", "audit", "certificazione",
            "procedura", "istruzione", "manuale", "policy", "regolamento"
        ]
        
        text_lower = text.lower()
        for word in important_words:
            if word in text_lower:
                keywords.append(word)
        
        return keywords
    
    def detect_scadenze(self, text: str) -> List[Dict]:
        """Rileva scadenze nel testo."""
        scadenze = []
        
        # Pattern per date (implementazione base)
        import re
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
            r'scadenza.*?(\d{1,2})/(\d{1,2})/(\d{4})',
            r'valido.*?(\d{1,2})/(\d{1,2})/(\d{4})'
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match.groups()) == 3:
                        day, month, year = match.groups()
                        scadenza_date = date(int(year), int(month), int(day))
                        scadenze.append({
                            "date": scadenza_date.isoformat(),
                            "context": match.group(0),
                            "position": match.start()
                        })
                except ValueError:
                    continue
        
        return scadenze
    
    def detect_firme(self, text: str) -> Dict:
        """Rileva firme nel testo."""
        firme_info = {
            "firme_presenti": [],
            "firme_mancanti": [],
            "ruoli_richiesti": []
        }
        
        # Ruoli tipici che richiedono firma
        ruoli_richiesti = [
            "RSPP", "RLS", "Dirigente", "Responsabile", "CEO", "Amministratore",
            "Responsabile Qualità", "Responsabile Sicurezza", "Responsabile HSE"
        ]
        
        text_lower = text.lower()
        
        # Cerca firme presenti
        firma_patterns = [
            r'firmato.*?da.*?([A-Z][a-z]+ [A-Z][a-z]+)',
            r'firma.*?([A-Z][a-z]+ [A-Z][a-z]+)',
            r'approvato.*?da.*?([A-Z][a-z]+ [A-Z][a-z]+)'
        ]
        
        import re
        for pattern in firma_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                firme_info["firme_presenti"].append(match.group(1))
        
        # Identifica ruoli richiesti
        for ruolo in ruoli_richiesti:
            if ruolo.lower() in text_lower:
                firme_info["ruoli_richiesti"].append(ruolo)
        
        # Identifica firme mancanti (ruoli richiesti senza firma)
        for ruolo in firme_info["ruoli_richiesti"]:
            if not any(ruolo.lower() in firma.lower() for firma in firme_info["firme_presenti"]):
                firme_info["firme_mancanti"].append(ruolo)
        
        return firme_info
    
    def detect_incompletezze(self, text: str) -> List[str]:
        """Rileva incompletezze nel documento."""
        incompletezze = []
        
        # Controlli base
        checks = [
            ("scadenza", "Manca data di scadenza"),
            ("firma", "Manca firma"),
            ("approvazione", "Manca approvazione"),
            ("revisione", "Manca data di revisione"),
            ("responsabile", "Manca responsabile"),
            ("procedura", "Procedura incompleta"),
            ("istruzione", "Istruzioni incomplete")
        ]
        
        text_lower = text.lower()
        
        for keyword, message in checks:
            if keyword in text_lower:
                # Verifica se è completato
                if not self.is_complete(text_lower, keyword):
                    incompletezze.append(message)
        
        return incompletezze
    
    def is_complete(self, text: str, keyword: str) -> bool:
        """Verifica se una sezione è completa."""
        # Logica base per verificare completezza
        completion_indicators = [
            "completato", "approvato", "firmato", "valido", "conforme"
        ]
        
        # Cerca indicatori di completamento vicino alla keyword
        keyword_pos = text.find(keyword)
        if keyword_pos != -1:
            # Controlla 100 caratteri prima e dopo
            start = max(0, keyword_pos - 100)
            end = min(len(text), keyword_pos + 100)
            context = text[start:end]
            
            return any(indicator in context for indicator in completion_indicators)
        
        return False
    
    def check_principi_coerenza(self, text: str) -> Dict:
        """Verifica coerenza con principi attivi."""
        if not self.model or not self.principi_attivi:
            return {"coerenza": "non_analizzabile", "principi_rilevanti": []}
        
        try:
            # Calcola embedding del testo
            text_embedding = self.model.encode(text[:1000])  # Primi 1000 caratteri
            
            # Calcola embedding dei principi
            principi_embeddings = self.model.encode(self.principi_attivi)
            
            # Calcola similarità
            similarities = []
            for i, principio in enumerate(self.principi_attivi):
                similarity = np.dot(text_embedding, principi_embeddings[i]) / (
                    np.linalg.norm(text_embedding) * np.linalg.norm(principi_embeddings[i])
                )
                similarities.append((principio, similarity))
            
            # Ordina per similarità
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Determina coerenza
            top_similarity = similarities[0][1] if similarities else 0
            if top_similarity > 0.7:
                coerenza = "alta"
            elif top_similarity > 0.4:
                coerenza = "media"
            else:
                coerenza = "bassa"
            
            return {
                "coerenza": coerenza,
                "principi_rilevanti": [p for p, s in similarities[:3] if s > 0.3],
                "similarity_scores": similarities[:5]
            }
            
        except Exception as e:
            logger.error(f"❌ Errore analisi coerenza principi: {e}")
            return {"coerenza": "errore", "principi_rilevanti": []}
    
    def generate_ai_status(self, analysis: Dict) -> Dict:
        """
        Genera lo stato AI basato sull'analisi.
        
        Returns:
            Dict con status, explain e task_id
        """
        status = "completo"
        explain_parts = []
        task_id = None
        
        # Verifica scadenze
        if analysis.get("scadenze"):
            scadenze = analysis["scadenze"]
            oggi = date.today()
            for scadenza in scadenze:
                try:
                    scadenza_date = datetime.fromisoformat(scadenza["date"]).date()
                    if scadenza_date < oggi:
                        status = "scaduto"
                        explain_parts.append(f"Documento scaduto il {scadenza_date.strftime('%d/%m/%Y')}")
                    elif scadenza_date <= oggi + timedelta(days=30):
                        status = "in_scadenza"
                        explain_parts.append(f"Documento in scadenza il {scadenza_date.strftime('%d/%m/%Y')}")
                except:
                    continue
        
        # Verifica firme mancanti
        if analysis.get("firme", {}).get("firme_mancanti"):
            if status == "completo":
                status = "incompleto"
            explain_parts.append(f"Mancano firme: {', '.join(analysis['firme']['firme_mancanti'])}")
        
        # Verifica incompletezze
        if analysis.get("incompletezze"):
            if status == "completo":
                status = "incompleto"
            explain_parts.append(f"Incompletezze rilevate: {', '.join(analysis['incompletezze'])}")
        
        # Verifica coerenza principi
        coerenza = analysis.get("coerenza_principi", {}).get("coerenza", "non_analizzabile")
        if coerenza == "bassa":
            if status == "completo":
                status = "incompleto"
            explain_parts.append("Bassa coerenza con principi aziendali")
        
        # Genera explain
        if explain_parts:
            explain = " | ".join(explain_parts)
        else:
            explain = "Documento completo e conforme"
        
        # Crea task se necessario
        if status != "completo":
            task_id = self.create_ai_task(status, explain, analysis)
        
        return {
            "status": status,
            "explain": explain,
            "task_id": task_id,
            "analysis": analysis
        }
    
    def create_ai_task(self, status: str, explain: str, analysis: Dict) -> Optional[int]:
        """Crea un task automatico basato sull'analisi AI."""
        try:
            # Determina priorità e tipo task
            if status == "scaduto":
                priority = "alta"
                task_type = "urgenza"
            elif status == "in_scadenza":
                priority = "media"
                task_type = "attenzione"
            else:
                priority = "bassa"
                task_type = "miglioramento"
            
            # Crea task
            task = Task(
                title=f"Document Intelligence - {status.upper()}",
                description=explain,
                priority=priority,
                status="aperto",
                assigned_to=None,  # Assegnato automaticamente
                created_by=1,  # Sistema
                task_type=task_type,
                ai_generated=True,
                metadata=json.dumps(analysis)
            )
            
            db.session.add(task)
            db.session.commit()
            
            logger.info(f"✅ Task AI creato: {task.id} - {status}")
            return task.id
            
        except Exception as e:
            logger.error(f"❌ Errore creazione task AI: {e}")
            return None
    
    def analyze_document(self, document_id: int) -> Dict:
        """
        Analizza un documento completo.
        
        Args:
            document_id: ID del documento da analizzare
            
        Returns:
            Dict con risultato analisi AI
        """
        try:
            # Recupera documento
            document = Document.query.get(document_id)
            if not document:
                return {"error": "Documento non trovato"}
            
            # Verifica se esiste il file
            if not document.file_path or not os.path.exists(document.file_path):
                return {"error": "File documento non trovato"}
            
            # Analizza PDF
            analysis = self.analyze_pdf_content(document.file_path)
            if "error" in analysis:
                return analysis
            
            # Genera stato AI
            ai_result = self.generate_ai_status(analysis)
            
            # Aggiorna documento con risultati AI
            document.ai_status = ai_result["status"]
            document.ai_explain = ai_result["explain"]
            document.ai_task_id = ai_result["task_id"]
            document.ai_analysis = json.dumps(analysis)
            document.ai_analyzed_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log audit
            log_event(
                "document_ai_analysis",
                user_id=1,  # Sistema
                details={
                    "document_id": document_id,
                    "ai_status": ai_result["status"],
                    "task_id": ai_result["task_id"]
                }
            )
            
            logger.info(f"✅ Analisi AI completata per documento {document_id}: {ai_result['status']}")
            
            return {
                "success": True,
                "status": ai_result["status"],
                "explain": ai_result["explain"],
                "task_id": ai_result["task_id"],
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"❌ Errore analisi documento {document_id}: {e}")
            return {"error": str(e)}

# Istanza globale del servizio
document_intelligence = DocumentIntelligence() 

# === FUNZIONALITÀ AI 2.0 - JACK SYNTHIA AVANZATO ===

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from models import Document, DocumentAIFlag, AIAlert, AIArchiveSuggestion, AIReply, User, DownloadLog

class JackSynthiaAI2:
    """
    Classe per le funzionalità AI 2.0 di Jack Synthia.
    Gestisce auto-verifica contenuto, risposte automatiche, suggerimenti archiviazione e alert.
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def auto_verify_document_content(self, document: Document, extracted_text: str) -> DocumentAIFlag:
        """
        Auto-verifica il contenuto del documento per conformità.
        
        Args:
            document: Documento da verificare
            extracted_text: Testo estratto dal documento
            
        Returns:
            DocumentAIFlag: Risultato della verifica
        """
        try:
            # Analisi AI del contenuto
            analysis_result = self._analyze_document_compliance(extracted_text, document.title)
            
            # Calcolo punteggio compliance
            compliance_score = self._calculate_compliance_score(analysis_result)
            
            # Determinazione flag type
            flag_type = self._determine_flag_type(compliance_score, analysis_result)
            
            # Creazione flag AI
            ai_flag = DocumentAIFlag(
                document_id=document.id,
                flag_type=flag_type,
                ai_analysis=json.dumps(analysis_result, indent=2),
                missing_sections=analysis_result.get('missing_sections', ''),
                compliance_score=compliance_score
            )
            
            self.db.add(ai_flag)
            self.db.commit()
            
            return ai_flag
            
        except Exception as e:
            print(f"Errore auto-verifica documento {document.id}: {e}")
            return None
    
    def _analyze_document_compliance(self, text: str, title: str) -> Dict:
        """
        Analizza la conformità del documento usando AI.
        
        Args:
            text: Testo del documento
            title: Titolo del documento
            
        Returns:
            Dict: Risultato analisi
        """
        # Sezioni obbligatorie per tipo documento
        required_sections = self._get_required_sections(title)
        
        # Analisi del testo
        analysis = {
            'has_header': self._check_header(text),
            'has_footer': self._check_footer(text),
            'has_signature': self._check_signature(text),
            'has_date': self._check_date(text),
            'has_company_info': self._check_company_info(text),
            'missing_sections': [],
            'compliance_issues': [],
            'document_type': self._classify_document_type(title, text)
        }
        
        # Verifica sezioni obbligatorie
        for section in required_sections:
            if not self._check_section_presence(text, section):
                analysis['missing_sections'].append(section)
                analysis['compliance_issues'].append(f"Sezione mancante: {section}")
        
        # Verifica integrità generale
        if len(text.strip()) < 100:
            analysis['compliance_issues'].append("Documento troppo breve")
        
        if not analysis['has_header']:
            analysis['compliance_issues'].append("Intestazione mancante")
        
        if not analysis['has_date']:
            analysis['compliance_issues'].append("Data documento mancante")
        
        return analysis
    
    def _get_required_sections(self, title: str) -> List[str]:
        """Restituisce le sezioni obbligatorie per tipo documento."""
        title_lower = title.lower()
        
        if 'contratto' in title_lower or 'contract' in title_lower:
            return ['parti contraenti', 'oggetto', 'durata', 'firma']
        elif 'certificato' in title_lower or 'certificate' in title_lower:
            return ['ente certificatore', 'data rilascio', 'validità', 'firma']
        elif 'manuale' in title_lower or 'procedure' in title_lower:
            return ['indice', 'procedure', 'responsabilità', 'revisione']
        elif 'report' in title_lower or 'rapporto' in title_lower:
            return ['introduzione', 'metodologia', 'risultati', 'conclusioni']
        else:
            return ['introduzione', 'contenuto', 'conclusioni']
    
    def _check_header(self, text: str) -> bool:
        """Verifica presenza intestazione."""
        header_patterns = [
            r'^.*?[A-Z][A-Z\s]+$',  # Titolo in maiuscolo
            r'^.*?[A-Z][a-z\s]+[A-Z][A-Z\s]+',  # Titolo con sottotitolo
            r'^.*?[A-Z][a-z\s]+[0-9]{4}',  # Titolo con anno
        ]
        
        lines = text.split('\n')[:5]  # Prime 5 righe
        for line in lines:
            for pattern in header_patterns:
                if re.search(pattern, line.strip()):
                    return True
        return False
    
    def _check_footer(self, text: str) -> bool:
        """Verifica presenza footer."""
        footer_patterns = [
            r'pagina\s+\d+',  # Pagina X
            r'page\s+\d+',
            r'©\s+\d{4}',  # Copyright
            r'confidenziale',  # Confidenziale
            r'confidential'
        ]
        
        lines = text.split('\n')[-5:]  # Ultime 5 righe
        for line in lines:
            for pattern in footer_patterns:
                if re.search(pattern, line.strip(), re.IGNORECASE):
                    return True
        return False
    
    def _check_signature(self, text: str) -> bool:
        """Verifica presenza firma."""
        signature_patterns = [
            r'firmato\s+da',
            r'signed\s+by',
            r'firma\s+del',
            r'signature\s+of',
            r'_________________',  # Linea firma
            r'________________',   # Linea firma
        ]
        
        for pattern in signature_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _check_date(self, text: str) -> bool:
        """Verifica presenza data."""
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',  # DD/MM/YYYY
            r'\d{1,2}-\d{1,2}-\d{4}',  # DD-MM-YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
            r'\d{1,2}\s+[a-zA-Z]+\s+\d{4}',  # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _check_company_info(self, text: str) -> bool:
        """Verifica presenza informazioni aziendali."""
        company_patterns = [
            r's\.p\.a\.',
            r's\.r\.l\.',
            r's\.n\.c\.',
            r'p\.i\.va',
            r'partita\s+iva',
            r'codice\s+fiscale',
            r'via\s+[a-zA-Z\s]+',
            r'strada\s+[a-zA-Z\s]+',
        ]
        
        for pattern in company_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _check_section_presence(self, text: str, section: str) -> bool:
        """Verifica presenza di una sezione specifica."""
        section_patterns = {
            'parti contraenti': [r'parti\s+contraenti', r'contraenti', r'parti'],
            'oggetto': [r'oggetto', r'oggetto\s+del', r'scopo'],
            'durata': [r'durata', r'termine', r'periodo'],
            'firma': [r'firma', r'signature', r'sottoscritto'],
            'ente certificatore': [r'ente', r'certificatore', r'istituto'],
            'data rilascio': [r'data\s+rilascio', r'rilasciato\s+il'],
            'validità': [r'validità', r'valido\s+fino', r'scade'],
            'indice': [r'indice', r'index', r'sommario'],
            'procedure': [r'procedure', r'procedura', r'processo'],
            'responsabilità': [r'responsabilità', r'responsabile', r'ruolo'],
            'revisione': [r'revisione', r'aggiornamento', r'versione'],
            'introduzione': [r'introduzione', r'premessa', r'prefazione'],
            'metodologia': [r'metodologia', r'metodo', r'approccio'],
            'risultati': [r'risultati', r'risultato', r'output'],
            'conclusioni': [r'conclusioni', r'conclusione', r'summary'],
            'contenuto': [r'contenuto', r'contenuti', r'argomenti'],
        }
        
        if section in section_patterns:
            patterns = section_patterns[section]
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
        return False
    
    def _classify_document_type(self, title: str, text: str) -> str:
        """Classifica il tipo di documento."""
        title_lower = title.lower()
        text_lower = text.lower()
        
        if any(word in title_lower for word in ['contratto', 'contract', 'accordo']):
            return 'contratto'
        elif any(word in title_lower for word in ['certificato', 'certificate', 'attestato']):
            return 'certificato'
        elif any(word in title_lower for word in ['manuale', 'procedure', 'istruzioni']):
            return 'manuale'
        elif any(word in title_lower for word in ['report', 'rapporto', 'relazione']):
            return 'report'
        elif any(word in title_lower for word in ['fattura', 'invoice', 'ricevuta']):
            return 'fattura'
        else:
            return 'generico'
    
    def _calculate_compliance_score(self, analysis: Dict) -> float:
        """Calcola il punteggio di compliance (0-100)."""
        score = 100.0
        issues = analysis.get('compliance_issues', [])
        missing_sections = analysis.get('missing_sections', [])
        
        # Penalità per sezioni mancanti
        score -= len(missing_sections) * 15
        
        # Penalità per problemi di compliance
        score -= len(issues) * 10
        
        # Bonus per elementi presenti
        if analysis.get('has_header'):
            score += 5
        if analysis.get('has_footer'):
            score += 5
        if analysis.get('has_signature'):
            score += 10
        if analysis.get('has_date'):
            score += 5
        if analysis.get('has_company_info'):
            score += 5
        
        return max(0.0, min(100.0, score))
    
    def _determine_flag_type(self, compliance_score: float, analysis: Dict) -> str:
        """Determina il tipo di flag basato sul punteggio."""
        if compliance_score >= 80:
            return 'conforme'
        elif compliance_score >= 50:
            return 'sospetto'
        else:
            return 'non_conforme'
    
    def generate_auto_reply(self, request_type: str, user: User, document: Document = None) -> AIReply:
        """
        Genera una risposta automatica per richieste di accesso negato.
        
        Args:
            request_type: Tipo di richiesta
            user: Utente richiedente
            document: Documento coinvolto (opzionale)
            
        Returns:
            AIReply: Risposta automatica generata
        """
        try:
            # Generazione risposta AI
            ai_reply_text = self._generate_ai_reply_text(request_type, user, document)
            
            # Creazione risposta
            ai_reply = AIReply(
                request_type=request_type,
                user_id=user.id,
                document_id=document.id if document else None,
                ai_generated_reply=ai_reply_text,
                sent_via='email',
                status='generato'
            )
            
            self.db.add(ai_reply)
            self.db.commit()
            
            return ai_reply
            
        except Exception as e:
            print(f"Errore generazione risposta automatica: {e}")
            return None
    
    def _generate_ai_reply_text(self, request_type: str, user: User, document: Document = None) -> str:
        """Genera il testo della risposta automatica."""
        user_name = f"{user.first_name} {user.last_name}" if user.first_name else user.username
        
        if request_type == 'accesso_negato':
            return f"""
Gentile {user_name},

La sua richiesta di accesso al documento è stata negata per motivi di sicurezza e conformità.

Motivazioni:
- Permessi insufficienti per questo tipo di documento
- Documento riservato o confidenziale
- Necessaria approvazione da parte del responsabile

Per richiedere l'accesso, contatti il suo responsabile diretto o l'amministratore del sistema.

Cordiali saluti,
Sistema di Gestione Documentale
            """.strip()
        
        elif request_type == 'documento_bloccato':
            doc_name = document.title if document else "il documento richiesto"
            return f"""
Gentile {user_name},

Il documento "{doc_name}" è attualmente bloccato per le seguenti ragioni:

- Documento in fase di revisione
- Mancano firme o approvazioni necessarie
- Documento scaduto o obsoleto

Il documento sarà disponibile una volta completate le procedure di validazione.

Cordiali saluti,
Sistema di Gestione Documentale
            """.strip()
        
        elif request_type == 'permessi_insufficienti':
            return f"""
Gentile {user_name},

Non possiede i permessi necessari per accedere a questa risorsa.

Per richiedere i permessi aggiuntivi:
1. Contatti il suo responsabile diretto
2. Specificare il motivo della richiesta
3. Attendere l'approvazione

Cordiali saluti,
Sistema di Gestione Documentale
            """.strip()
        
        else:
            return f"""
Gentile {user_name},

La sua richiesta non può essere processata al momento.

Per assistenza, contatti l'amministratore del sistema.

Cordiali saluti,
Sistema di Gestione Documentale
            """.strip()
    
    def suggest_archive_location(self, document: Document, extracted_text: str) -> AIArchiveSuggestion:
        """
        Suggerisce la posizione di archiviazione per un nuovo documento.
        
        Args:
            document: Documento da archiviare
            extracted_text: Testo estratto dal documento
            
        Returns:
            AIArchiveSuggestion: Suggerimento di archiviazione
        """
        try:
            # Analisi del contenuto per determinare la cartella
            suggested_folder, confidence, reasoning = self._analyze_archive_suggestion(
                document.title, extracted_text, document.company.name if document.company else ""
            )
            
            # Creazione suggerimento
            suggestion = AIArchiveSuggestion(
                document_id=document.id,
                suggested_folder=suggested_folder,
                confidence_score=confidence,
                reasoning=reasoning,
                accepted=False
            )
            
            self.db.add(suggestion)
            self.db.commit()
            
            return suggestion
            
        except Exception as e:
            print(f"Errore suggerimento archiviazione: {e}")
            return None
    
    def _analyze_archive_suggestion(self, title: str, text: str, company: str) -> Tuple[str, float, str]:
        """Analizza e suggerisce la cartella di archiviazione."""
        title_lower = title.lower()
        text_lower = text.lower()
        
        # Regole di classificazione
        classification_rules = [
            {
                'keywords': ['contratto', 'contract', 'accordo', 'convenzione'],
                'folder': 'Contratti',
                'confidence': 90,
                'reasoning': 'Documento identificato come contratto o accordo'
            },
            {
                'keywords': ['fattura', 'invoice', 'ricevuta', 'pagamento'],
                'folder': 'Fatture',
                'confidence': 85,
                'reasoning': 'Documento identificato come fattura o ricevuta'
            },
            {
                'keywords': ['certificato', 'certificate', 'attestato', 'diploma'],
                'folder': 'Certificati',
                'confidence': 80,
                'reasoning': 'Documento identificato come certificato o attestato'
            },
            {
                'keywords': ['manuale', 'procedure', 'istruzioni', 'guide'],
                'folder': 'Manuali',
                'confidence': 75,
                'reasoning': 'Documento identificato come manuale o procedure'
            },
            {
                'keywords': ['report', 'rapporto', 'relazione', 'analisi'],
                'folder': 'Report',
                'confidence': 70,
                'reasoning': 'Documento identificato come report o relazione'
            },
            {
                'keywords': ['sicurezza', 'hse', 'ambiente', 'salute'],
                'folder': 'Sicurezza',
                'confidence': 85,
                'reasoning': 'Documento relativo a sicurezza e ambiente'
            },
            {
                'keywords': ['hr', 'risorse umane', 'personale', 'dipendenti'],
                'folder': 'Risorse Umane',
                'confidence': 80,
                'reasoning': 'Documento relativo a risorse umane'
            },
            {
                'keywords': ['finanziario', 'bilancio', 'contabilità', 'economico'],
                'folder': 'Finanziario',
                'confidence': 85,
                'reasoning': 'Documento relativo a finanza e contabilità'
            }
        ]
        
        # Analisi del contenuto
        for rule in classification_rules:
            if any(keyword in title_lower or keyword in text_lower for keyword in rule['keywords']):
                return rule['folder'], rule['confidence'], rule['reasoning']
        
        # Default se non viene trovata corrispondenza
        return 'Generale', 50, 'Documento non classificabile automaticamente'
    
    def check_suspicious_behavior(self, user: User, action: str, document: Document = None, 
                                 ip_address: str = None, user_agent: str = None) -> Optional[AIAlert]:
        """
        Controlla comportamenti sospetti e genera alert se necessario.
        
        Args:
            user: Utente che ha eseguito l'azione
            action: Tipo di azione ('download', 'access', 'upload')
            document: Documento coinvolto (opzionale)
            ip_address: IP del client
            user_agent: User agent del browser
            
        Returns:
            AIAlert: Alert generato se necessario
        """
        try:
            # Controllo download massivo
            if action == 'download':
                alert = self._check_massive_download(user, document, ip_address, user_agent)
                if alert:
                    return alert
            
            # Controllo IP sospetto
            if ip_address:
                alert = self._check_suspicious_ip(user, ip_address, action, document)
                if alert:
                    return alert
            
            # Controllo accesso insolito
            alert = self._check_unusual_access(user, action, document, ip_address, user_agent)
            if alert:
                return alert
            
            return None
            
        except Exception as e:
            print(f"Errore controllo comportamenti sospetti: {e}")
            return None
    
    def _check_massive_download(self, user: User, document: Document, ip_address: str, user_agent: str) -> Optional[AIAlert]:
        """Controlla download massivo negli ultimi 10 minuti."""
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        
        # Conta download recenti dell'utente
        recent_downloads = self.db.query(DownloadLog).filter(
            DownloadLog.user_id == user.id,
            DownloadLog.timestamp >= ten_minutes_ago
        ).count()
        
        if recent_downloads > 10:  # Più di 10 download in 10 minuti
            description = f"Utente {user.username} ha scaricato {recent_downloads} documenti negli ultimi 10 minuti"
            
            alert = AIAlert(
                alert_type='download_massivo',
                user_id=user.id,
                document_id=document.id if document else None,
                severity='alta' if recent_downloads > 20 else 'media',
                description=description,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(alert)
            self.db.commit()
            return alert
        
        return None
    
    def _check_suspicious_ip(self, user: User, ip_address: str, action: str, document: Document) -> Optional[AIAlert]:
        """Controlla IP sospetti."""
        # Lista di IP sospetti (esempio)
        suspicious_ips = [
            '192.168.1.100',  # IP interno sospetto
            '10.0.0.50',      # IP interno sospetto
        ]
        
        if ip_address in suspicious_ips:
            description = f"Accesso da IP sospetto {ip_address} per utente {user.username}"
            
            alert = AIAlert(
                alert_type='ip_sospetto',
                user_id=user.id,
                document_id=document.id if document else None,
                severity='alta',
                description=description,
                ip_address=ip_address
            )
            
            self.db.add(alert)
            self.db.commit()
            return alert
        
        return None
    
    def _check_unusual_access(self, user: User, action: str, document: Document, 
                             ip_address: str, user_agent: str) -> Optional[AIAlert]:
        """Controlla accessi insoliti."""
        # Controllo accesso fuori orario (esempio: dopo le 22:00)
        current_hour = datetime.utcnow().hour
        if current_hour >= 22 or current_hour <= 6:
            description = f"Accesso fuori orario ({current_hour}:00) per utente {user.username}"
            
            alert = AIAlert(
                alert_type='accesso_insolito',
                user_id=user.id,
                document_id=document.id if document else None,
                severity='media',
                description=description,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(alert)
            self.db.commit()
            return alert
        
        return None
    
    def get_ai_flags_for_document(self, document_id: int) -> List[DocumentAIFlag]:
        """Restituisce i flag AI per un documento."""
        return self.db.query(DocumentAIFlag).filter(
            DocumentAIFlag.document_id == document_id
        ).order_by(DocumentAIFlag.created_at.desc()).all()
    
    def get_active_alerts(self, user_id: int = None) -> List[AIAlert]:
        """Restituisce gli alert attivi."""
        query = self.db.query(AIAlert).filter(AIAlert.resolved == False)
        
        if user_id:
            query = query.filter(AIAlert.user_id == user_id)
        
        return query.order_by(AIAlert.created_at.desc()).all()
    
    def get_archive_suggestions(self, document_id: int) -> List[AIArchiveSuggestion]:
        """Restituisce i suggerimenti di archiviazione per un documento."""
        return self.db.query(AIArchiveSuggestion).filter(
            AIArchiveSuggestion.document_id == document_id
        ).order_by(AIArchiveSuggestion.created_at.desc()).all()
    
    def get_ai_replies(self, user_id: int = None) -> List[AIReply]:
        """Restituisce le risposte AI generate."""
        query = self.db.query(AIReply)
        
        if user_id:
            query = query.filter(AIReply.user_id == user_id)
        
        return query.order_by(AIReply.created_at.desc()).all() 

# === FUNZIONE AUTO-VERIFICA DOCUMENTI ===

def extract_text_from_document(document: Document) -> str:
    """
    Estrae il testo da un documento (PDF o Word).
    
    Args:
        document: Documento da analizzare
        
    Returns:
        str: Testo estratto dal documento
    """
    try:
        if not document.filename:
            return ""
        
        # Costruisci il percorso del file
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        file_path = os.path.join(upload_folder, document.filename)
        
        if not os.path.exists(file_path):
            logger.error(f"File non trovato: {file_path}")
            return ""
        
        # Estrai testo in base all'estensione
        file_extension = document.filename.lower().split('.')[-1]
        
        if file_extension == 'pdf':
            return extract_text_from_pdf(file_path)
        elif file_extension in ['doc', 'docx']:
            return extract_text_from_word(file_path)
        else:
            logger.warning(f"Formato file non supportato: {file_extension}")
            return ""
            
    except Exception as e:
        logger.error(f"Errore estrazione testo documento {document.id}: {e}")
        return ""

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Estrae testo da un file PDF.
    
    Args:
        pdf_path: Percorso del file PDF
        
    Returns:
        str: Testo estratto
    """
    try:
        if not PyPDF2:
            logger.error("PyPDF2 non disponibile")
            return ""
        
        text_content = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
        
        return text_content.strip()
        
    except Exception as e:
        logger.error(f"Errore estrazione testo PDF {pdf_path}: {e}")
        return ""

def extract_text_from_word(word_path: str) -> str:
    """
    Estrae testo da un file Word.
    
    Args:
        word_path: Percorso del file Word
        
    Returns:
        str: Testo estratto
    """
    try:
        # Per ora restituiamo una stringa vuota
        # TODO: Implementare estrazione da Word con python-docx
        logger.warning("Estrazione da Word non ancora implementata")
        return ""
        
    except Exception as e:
        logger.error(f"Errore estrazione testo Word {word_path}: {e}")
        return ""

def auto_verifica_documento(document_id: int) -> Dict:
    """
    Auto-verifica il contenuto di un documento usando AI.
    
    Args:
        document_id: ID del documento da verificare
        
    Returns:
        Dict: Risultato della verifica AI
    """
    try:
        from models import Document, DocumentAIFlag
        from sqlalchemy.orm import Session
        from database import get_db
        
        db = get_db()
        
        # Recupera documento
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {
                "success": False,
                "error": "Documento non trovato"
            }
        
        # Estrai testo dal documento
        extracted_text = extract_text_from_document(document)
        if not extracted_text:
            return {
                "success": False,
                "error": "Impossibile estrarre testo dal documento"
            }
        
        # Analizza il contenuto con AI
        analysis_result = analyze_document_content_ai(extracted_text, document.title)
        
        # Calcola punteggio compliance
        compliance_score = calculate_compliance_score(analysis_result)
        
        # Determina se conforme
        is_conforme = compliance_score >= 70
        
        # Salva risultato nel database
        ai_flag = save_ai_verification_result(
            db, document, analysis_result, compliance_score, is_conforme
        )
        
        return {
            "success": True,
            "conforme": is_conforme,
            "compliance_score": compliance_score,
            "criticita": analysis_result.get("criticita", []),
            "suggerimenti": analysis_result.get("suggerimenti", []),
            "analisi_dettagliata": analysis_result,
            "flag_id": ai_flag.id if ai_flag else None
        }
        
    except Exception as e:
        logger.error(f"Errore auto-verifica documento {document_id}: {e}")
        return {
            "success": False,
            "error": f"Errore durante la verifica: {str(e)}"
        }

def analyze_document_content_ai(text: str, title: str) -> Dict:
    """
    Analizza il contenuto di un documento usando AI.
    
    Args:
        text: Testo del documento
        title: Titolo del documento
        
    Returns:
        Dict: Risultato analisi AI
    """
    try:
        # Analisi con GPT/OpenAI (simulata per ora)
        # TODO: Integrare con OpenAI API
        
        analysis = {
            "has_header": check_header_presence(text),
            "has_footer": check_footer_presence(text),
            "has_signature": check_signature_presence(text),
            "has_date": check_date_presence(text),
            "has_company_info": check_company_info_presence(text),
            "has_security_info": check_security_info_presence(text),
            "document_type": classify_document_type(title, text),
            "missing_sections": [],
            "criticita": [],
            "suggerimenti": []
        }
        
        # Verifica sezioni obbligatorie
        required_sections = get_required_sections_for_type(analysis["document_type"])
        for section in required_sections:
            if not check_section_presence(text, section):
                analysis["missing_sections"].append(section)
                analysis["criticita"].append(f"Sezione mancante: {section}")
        
        # Verifica integrità generale
        if len(text.strip()) < 100:
            analysis["criticita"].append("Documento troppo breve")
        
        if not analysis["has_header"]:
            analysis["criticita"].append("Intestazione mancante")
        
        if not analysis["has_date"]:
            analysis["criticita"].append("Data documento mancante")
        
        if not analysis["has_signature"]:
            analysis["criticita"].append("Firma mancante")
        
        # Genera suggerimenti
        analysis["suggerimenti"] = generate_ai_suggestions(analysis)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Errore analisi AI contenuto: {e}")
        return {
            "error": f"Errore analisi AI: {str(e)}",
            "criticita": ["Errore durante l'analisi AI"],
            "suggerimenti": ["Contattare l'amministratore"]
        }

def check_header_presence(text: str) -> bool:
    """Verifica presenza intestazione."""
    header_patterns = [
        r'^.*?[A-Z][A-Z\s]+$',  # Titolo in maiuscolo
        r'^.*?[A-Z][a-z\s]+[A-Z][A-Z\s]+',  # Titolo con sottotitolo
        r'^.*?[A-Z][a-z\s]+[0-9]{4}',  # Titolo con anno
    ]
    
    lines = text.split('\n')[:5]  # Prime 5 righe
    for line in lines:
        for pattern in header_patterns:
            if re.search(pattern, line.strip()):
                return True
    return False

def check_footer_presence(text: str) -> bool:
    """Verifica presenza footer."""
    footer_patterns = [
        r'pagina\s+\d+',  # Pagina X
        r'page\s+\d+',
        r'©\s+\d{4}',  # Copyright
        r'confidenziale',  # Confidenziale
        r'confidential'
    ]
    
    lines = text.split('\n')[-5:]  # Ultime 5 righe
    for line in lines:
        for pattern in footer_patterns:
            if re.search(pattern, line.strip(), re.IGNORECASE):
                return True
    return False

def check_signature_presence(text: str) -> bool:
    """Verifica presenza firma."""
    signature_patterns = [
        r'firmato\s+da',
        r'signed\s+by',
        r'firma\s+del',
        r'signature\s+of',
        r'_________________',  # Linea firma
        r'________________',   # Linea firma
    ]
    
    for pattern in signature_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def check_date_presence(text: str) -> bool:
    """Verifica presenza data."""
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{4}',  # DD/MM/YYYY
        r'\d{1,2}-\d{1,2}-\d{4}',  # DD-MM-YYYY
        r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
        r'\d{1,2}\s+[a-zA-Z]+\s+\d{4}',  # DD Month YYYY
    ]
    
    for pattern in date_patterns:
        if re.search(pattern, text):
            return True
    return False

def check_company_info_presence(text: str) -> bool:
    """Verifica presenza informazioni aziendali."""
    company_patterns = [
        r's\.p\.a\.',
        r's\.r\.l\.',
        r's\.n\.c\.',
        r'p\.i\.va',
        r'partita\s+iva',
        r'codice\s+fiscale',
        r'via\s+[a-zA-Z\s]+',
        r'strada\s+[a-zA-Z\s]+',
    ]
    
    for pattern in company_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def check_security_info_presence(text: str) -> bool:
    """Verifica presenza informazioni di sicurezza."""
    security_patterns = [
        r'confidenziale',
        r'confidential',
        r'riservato',
        r'secret',
        r'sicurezza',
        r'security',
        r'protezione',
        r'protection'
    ]
    
    for pattern in security_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def classify_document_type(title: str, text: str) -> str:
    """Classifica il tipo di documento."""
    title_lower = title.lower()
    text_lower = text.lower()
    
    if any(word in title_lower for word in ['contratto', 'contract', 'accordo']):
        return 'contratto'
    elif any(word in title_lower for word in ['certificato', 'certificate', 'attestato']):
        return 'certificato'
    elif any(word in title_lower for word in ['manuale', 'procedure', 'istruzioni']):
        return 'manuale'
    elif any(word in title_lower for word in ['report', 'rapporto', 'relazione']):
        return 'report'
    elif any(word in title_lower for word in ['fattura', 'invoice', 'ricevuta']):
        return 'fattura'
    elif any(word in title_lower for word in ['sicurezza', 'hse', 'ambiente']):
        return 'sicurezza'
    else:
        return 'generico'

def get_required_sections_for_type(doc_type: str) -> List[str]:
    """Restituisce le sezioni obbligatorie per tipo documento."""
    sections_map = {
        'contratto': ['parti contraenti', 'oggetto', 'durata', 'firma'],
        'certificato': ['ente certificatore', 'data rilascio', 'validità', 'firma'],
        'manuale': ['indice', 'procedure', 'responsabilità', 'revisione'],
        'report': ['introduzione', 'metodologia', 'risultati', 'conclusioni'],
        'fattura': ['intestazione', 'dettagli', 'totale', 'pagamento'],
        'sicurezza': ['procedure', 'responsabilità', 'emergenze', 'contatti'],
        'generico': ['introduzione', 'contenuto', 'conclusioni']
    }
    
    return sections_map.get(doc_type, ['introduzione', 'contenuto', 'conclusioni'])

def check_section_presence(text: str, section: str) -> bool:
    """Verifica presenza di una sezione specifica."""
    section_patterns = {
        'parti contraenti': [r'parti\s+contraenti', r'contraenti', r'parti'],
        'oggetto': [r'oggetto', r'oggetto\s+del', r'scopo'],
        'durata': [r'durata', r'termine', r'periodo'],
        'firma': [r'firma', r'signature', r'sottoscritto'],
        'ente certificatore': [r'ente', r'certificatore', r'istituto'],
        'data rilascio': [r'data\s+rilascio', r'rilasciato\s+il'],
        'validità': [r'validità', r'valido\s+fino', r'scade'],
        'indice': [r'indice', r'index', r'sommario'],
        'procedure': [r'procedure', r'procedura', r'processo'],
        'responsabilità': [r'responsabilità', r'responsabile', r'ruolo'],
        'revisione': [r'revisione', r'aggiornamento', r'versione'],
        'introduzione': [r'introduzione', r'premessa', r'prefazione'],
        'metodologia': [r'metodologia', r'metodo', r'approccio'],
        'risultati': [r'risultati', r'risultato', r'output'],
        'conclusioni': [r'conclusioni', r'conclusione', r'summary'],
        'contenuto': [r'contenuto', r'contenuti', r'argomenti'],
        'intestazione': [r'intestazione', r'header', r'titolo'],
        'dettagli': [r'dettagli', r'particolari', r'descrizione'],
        'totale': [r'totale', r'somma', r'importo'],
        'pagamento': [r'pagamento', r'pagare', r'versamento'],
        'emergenze': [r'emergenze', r'emergenza', r'urgenza'],
        'contatti': [r'contatti', r'contatto', r'telefono']
    }
    
    if section in section_patterns:
        patterns = section_patterns[section]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
    return False

def calculate_compliance_score(analysis: Dict) -> float:
    """Calcola il punteggio di compliance (0-100)."""
    score = 100.0
    issues = analysis.get("criticita", [])
    missing_sections = analysis.get("missing_sections", [])
    
    # Penalità per sezioni mancanti
    score -= len(missing_sections) * 15
    
    # Penalità per problemi di compliance
    score -= len(issues) * 10
    
    # Bonus per elementi presenti
    if analysis.get("has_header"):
        score += 5
    if analysis.get("has_footer"):
        score += 5
    if analysis.get("has_signature"):
        score += 10
    if analysis.get("has_date"):
        score += 5
    if analysis.get("has_company_info"):
        score += 5
    if analysis.get("has_security_info"):
        score += 5
    
    return max(0.0, min(100.0, score))

def generate_ai_suggestions(analysis: Dict) -> List[str]:
    """Genera suggerimenti AI basati sull'analisi."""
    suggestions = []
    
    if not analysis.get("has_header"):
        suggestions.append("Aggiungere un'intestazione chiara con titolo e data")
    
    if not analysis.get("has_signature"):
        suggestions.append("Includere una sezione per le firme dei responsabili")
    
    if not analysis.get("has_date"):
        suggestions.append("Inserire la data di creazione del documento")
    
    if not analysis.get("has_company_info"):
        suggestions.append("Includere informazioni aziendali complete")
    
    if analysis.get("missing_sections"):
        suggestions.append(f"Completare le sezioni mancanti: {', '.join(analysis['missing_sections'])}")
    
    if len(analysis.get("criticita", [])) > 3:
        suggestions.append("Considerare una revisione completa del documento")
    
    if not suggestions:
        suggestions.append("Documento ben strutturato e completo")
    
    return suggestions

def save_ai_verification_result(db: Session, document: Document, analysis: Dict, 
                               compliance_score: float, is_conforme: bool) -> Optional[DocumentAIFlag]:
    """Salva il risultato della verifica AI nel database."""
    try:
        from models import DocumentAIFlag
        
        # Determina il tipo di flag
        if is_conforme:
            flag_type = "conforme"
        elif compliance_score >= 50:
            flag_type = "sospetto"
        else:
            flag_type = "non_conforme"
        
        # Crea il flag AI
        ai_flag = DocumentAIFlag(
            document_id=document.id,
            flag_type=flag_type,
            ai_analysis=json.dumps(analysis, indent=2),
            missing_sections=", ".join(analysis.get("missing_sections", [])),
            compliance_score=compliance_score
        )
        
        db.add(ai_flag)
        db.commit()
        
        return ai_flag
        
    except Exception as e:
        logger.error(f"Errore salvataggio risultato AI: {e}")
        return None


# === FUNZIONI PER RISPOSTA AI AUTOMATICA ALLE RICHIESTE DI ACCESSO ===

def generate_ai_access_response(request_id: int, override_motivazione: str = None) -> Dict:
    """
    Genera una risposta AI automatica per una richiesta di accesso.
    
    Args:
        request_id: ID della richiesta di accesso
        override_motivazione: Motivazione opzionale da sovrascrivere
        
    Returns:
        Dict: Risultato della generazione risposta
    """
    try:
        from models import AccessRequest, User, Document
        from sqlalchemy.orm import Session
        from database import get_db
        
        db = get_db()
        
        # Recupera la richiesta di accesso
        access_request = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
        if not access_request:
            return {
                "success": False,
                "error": "Richiesta di accesso non trovata"
            }
        
        # Recupera utente e documento
        user = db.query(User).filter(User.id == access_request.user_id).first()
        document = db.query(Document).filter(Document.id == access_request.document_id).first()
        
        if not user or not document:
            return {
                "success": False,
                "error": "Utente o documento non trovato"
            }
        
        # Estrai contenuto del documento
        document_text = extract_text_from_document(document)
        if not document_text:
            document_text = f"Documento: {document.title} - Tipo: {document.visibility}"
        
        # Usa motivazione override o quella originale
        motivazione = override_motivazione or access_request.note or "Nessuna motivazione fornita"
        
        # Genera risposta AI
        ai_response = _generate_access_response_ai(
            user=user,
            document=document,
            document_content=document_text,
            motivazione=motivazione
        )
        
        # Aggiorna la richiesta con la risposta AI
        access_request.risposta_ai = ai_response["risposta_formale"]
        access_request.parere_ai = ai_response["parere_admin"]
        access_request.ai_analyzed_at = datetime.utcnow()
        
        db.commit()
        
        # Log dell'evento
        log_event(
            'access_request_ai_response_generated',
            user_id=user.id,
            document_id=document.id,
            details={
                'request_id': request_id,
                'ai_parere': ai_response["parere_admin"],
                'has_formal_response': bool(ai_response["risposta_formale"])
            }
        )
        
        return {
            "success": True,
            "risposta_formale": ai_response["risposta_formale"],
            "parere_admin": ai_response["parere_admin"],
            "suggerimento_email": ai_response["suggerimento_email"],
            "request_id": request_id
        }
        
    except Exception as e:
        logger.error(f"❌ Errore generazione risposta AI accesso {request_id}: {e}")
        return {
            "success": False,
            "error": f"Errore durante la generazione: {str(e)}"
        }


def _generate_access_response_ai(user: User, document: Document, document_content: str, motivazione: str) -> Dict:
    """
    Genera la risposta AI per una richiesta di accesso.
    
    Args:
        user: Utente richiedente
        document: Documento richiesto
        document_content: Contenuto del documento
        motivazione: Motivazione della richiesta
        
    Returns:
        Dict: Risposta AI strutturata
    """
    try:
        # Analizza il contenuto del documento
        document_type = classify_document_type(document.title, document_content)
        
        # Determina la sensibilità del documento
        sensitivity_level = _determine_document_sensitivity(document, document_content)
        
        # Analizza la motivazione dell'utente
        motivation_analysis = _analyze_user_motivation(motivazione, user.role)
        
        # Genera risposta formale
        formal_response = _generate_formal_response(
            user=user,
            document=document,
            document_type=document_type,
            sensitivity_level=sensitivity_level,
            motivation_analysis=motivation_analysis
        )
        
        # Genera parere per admin
        admin_opinion = _generate_admin_opinion(
            user=user,
            document=document,
            document_type=document_type,
            sensitivity_level=sensitivity_level,
            motivation_analysis=motivation_analysis
        )
        
        # Suggerimento email
        email_suggestion = _generate_email_suggestion(
            user=user,
            document=document,
            formal_response=formal_response,
            admin_opinion=admin_opinion
        )
        
        return {
            "risposta_formale": formal_response,
            "parere_admin": admin_opinion,
            "suggerimento_email": email_suggestion
        }
        
    except Exception as e:
        logger.error(f"❌ Errore generazione risposta AI: {e}")
        return {
            "risposta_formale": "Errore nella generazione della risposta automatica.",
            "parere_admin": "Errore nell'analisi AI.",
            "suggerimento_email": "Contattare l'amministratore."
        }


def _determine_document_sensitivity(document: Document, content: str) -> str:
    """Determina il livello di sensibilità del documento."""
    # Documenti critici
    if document.is_critical:
        return "critico"
    
    # Documenti scaduti
    if document.expiry_date and document.expiry_date < datetime.utcnow():
        return "scaduto"
    
    # Documenti privati
    if document.visibility == "privato":
        return "riservato"
    
    # Documenti con firma richiesta
    if document.richiedi_firma:
        return "protetto"
    
    # Contenuto sensibile
    sensitive_keywords = ["confidenziale", "riservato", "interno", "segreto", "protetto"]
    content_lower = content.lower()
    if any(keyword in content_lower for keyword in sensitive_keywords):
        return "sensibile"
    
    return "normale"


def _analyze_user_motivation(motivazione: str, user_role: str) -> Dict:
    """Analizza la motivazione dell'utente."""
    motivazione_lower = motivazione.lower()
    
    # Analisi basata su parole chiave
    analysis = {
        "urgenza": "bassa",
        "legittimità": "media",
        "necessità_tecnica": False,
        "necessità_amministrativa": False,
        "necessità_legale": False,
        "motivazione": motivazione
    }
    
    # Rileva urgenza
    urgent_words = ["urgente", "immediato", "subito", "critico", "emergenza"]
    if any(word in motivazione_lower for word in urgent_words):
        analysis["urgenza"] = "alta"
    
    # Rileva tipo di necessità
    if any(word in motivazione_lower for word in ["tecnico", "manutenzione", "sistema", "configurazione"]):
        analysis["necessità_tecnica"] = True
    
    if any(word in motivazione_lower for word in ["amministrativo", "burocratico", "procedura", "documentazione"]):
        analysis["necessità_amministrativa"] = True
    
    if any(word in motivazione_lower for word in ["legale", "conformità", "compliance", "normativo"]):
        analysis["necessità_legale"] = True
    
    # Valuta legittimità basata su ruolo
    if user_role in ["admin", "superadmin"]:
        analysis["legittimità"] = "alta"
    elif user_role == "user":
        analysis["legittimità"] = "media"
    else:
        analysis["legittimità"] = "bassa"
    
    return analysis


def _generate_formal_response(user: User, document: Document, document_type: str, 
                           sensitivity_level: str, motivation_analysis: Dict) -> str:
    """Genera una risposta formale personalizzata."""
    
    user_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.username
    
    if sensitivity_level == "critico":
        return f"""Gentile {user_name},

La sua richiesta di accesso al documento "{document.title}" è stata ricevuta e analizzata dal nostro sistema di gestione documentale.

Il documento richiesto è classificato come CRITICO e richiede autorizzazione speciale. La sua richiesta è stata inoltrata al responsabile competente per la valutazione.

Motivazione fornita: {motivation_analysis.get('motivazione', 'Nessuna')}

Le verrà comunicato l'esito della valutazione entro 24 ore lavorative.

Cordiali saluti,
Sistema di Gestione Documentale"""

    elif sensitivity_level == "scaduto":
        return f"""Gentile {user_name},

La sua richiesta di accesso al documento "{document.title}" non può essere accolta poiché il documento risulta SCADUTO.

Il documento ha superato la data di scadenza prevista e non è più disponibile per l'accesso.

Se ritiene che sia necessario accedere a questo documento per motivi specifici, contatti direttamente il responsabile del reparto.

Cordiali saluti,
Sistema di Gestione Documentale"""

    elif sensitivity_level == "riservato":
        return f"""Gentile {user_name},

La sua richiesta di accesso al documento "{document.title}" è stata ricevuta.

Il documento richiesto è classificato come RISERVATO e l'accesso è limitato. La sua richiesta è stata registrata e sarà valutata dal responsabile competente.

Motivazione fornita: {motivation_analysis.get('motivazione', 'Nessuna')}

Riceverà una comunicazione sull'esito della valutazione.

Cordiali saluti,
Sistema di Gestione Documentale"""

    else:
        return f"""Gentile {user_name},

La sua richiesta di accesso al documento "{document.title}" è stata ricevuta e analizzata.

Il documento è attualmente disponibile per l'accesso. Le verrà inviato un link di accesso sicuro entro breve.

Motivazione fornita: {motivation_analysis.get('motivazione', 'Nessuna')}

Cordiali saluti,
Sistema di Gestione Documentale"""


def _generate_admin_opinion(user: User, document: Document, document_type: str,
                          sensitivity_level: str, motivation_analysis: Dict) -> str:
    """Genera un parere per l'amministratore."""
    
    # Valuta se concedere l'accesso
    should_grant = False
    reason = ""
    
    if sensitivity_level == "normale":
        should_grant = True
        reason = "Documento di accesso normale"
    elif sensitivity_level == "protetto" and motivation_analysis["legittimità"] == "alta":
        should_grant = True
        reason = "Utente autorizzato per documento protetto"
    elif sensitivity_level == "riservato" and motivation_analysis["urgenza"] == "alta":
        should_grant = True
        reason = "Richiesta urgente per documento riservato"
    elif user.role in ["admin", "superadmin"]:
        should_grant = True
        reason = "Utente amministratore"
    else:
        should_grant = False
        reason = f"Documento {sensitivity_level}, utente non autorizzato"
    
    if should_grant:
        return f"✅ CONSIGLIATO CONCEDERE - {reason}"
    else:
        return f"❌ CONSIGLIATO NEGARE - {reason}"


def _generate_email_suggestion(user: User, document: Document, formal_response: str, admin_opinion: str) -> str:
    """Genera un suggerimento per l'invio email."""
    
    if "CONSIGLIATO CONCEDERE" in admin_opinion:
        return f"""📧 INVIA EMAIL A: {user.email}

Oggetto: Accesso documento "{document.title}" - APPROVATO

{formal_response}

---
Nota: L'AI consiglia di concedere l'accesso."""
    
    elif "CONSIGLIATO NEGARE" in admin_opinion:
        return f"""📧 INVIA EMAIL A: {user.email}

Oggetto: Accesso documento "{document.title}" - NEGATO

{formal_response}

---
Nota: L'AI consiglia di negare l'accesso."""
    
    else:
        return f"""📧 INVIA EMAIL A: {user.email}

Oggetto: Accesso documento "{document.title}" - IN VALUTAZIONE

{formal_response}

---
Nota: Richiede valutazione manuale."""


# === FUNZIONI PER SUGGERIMENTO AI ARCHIVIAZIONE ===

def suggerisci_cartella_archiviazione(document_id: int) -> Dict:
    """
    Suggerisce automaticamente la cartella di archiviazione per un documento.
    
    Args:
        document_id: ID del documento da analizzare
        
    Returns:
        Dict: Risultato del suggerimento AI
    """
    try:
        from models import Document, User, Company, Department, AIArchiveSuggestion
        from sqlalchemy.orm import Session
        from database import get_db
        
        db = get_db()
        
        # Recupera documento
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {
                "success": False,
                "error": "Documento non trovato"
            }
        
        # Recupera azienda e reparto
        company = db.query(Company).filter(Company.id == document.company_id).first()
        department = db.query(Department).filter(Department.id == document.department_id).first()
        
        # Estrai contenuto del documento
        document_text = extract_text_from_document(document)
        if not document_text:
            document_text = f"Documento: {document.title} - Descrizione: {document.description or 'Nessuna descrizione'}"
        
        # Genera suggerimento AI
        ai_suggestion = _generate_archive_suggestion_ai(
            document=document,
            document_content=document_text,
            company=company,
            department=department
        )
        
        # Salva suggerimento nel database
        suggestion = AIArchiveSuggestion(
            document_id=document.id,
            suggested_folder=ai_suggestion["suggested_folder"],
            confidence_score=ai_suggestion["confidence_score"],
            reasoning=ai_suggestion["reasoning"],
            path_suggerito=ai_suggestion["path_suggerito"],
            categoria_suggerita=ai_suggestion["categoria_suggerita"],
            tag_ai=json.dumps(ai_suggestion["tag_ai"], ensure_ascii=False),
            motivazione_ai=ai_suggestion["motivazione_ai"],
            azienda_suggerita=ai_suggestion["azienda_suggerita"],
            reparto_suggerito=ai_suggestion["reparto_suggerito"],
            tipo_documento_ai=ai_suggestion["tipo_documento_ai"]
        )
        
        db.add(suggestion)
        db.commit()
        
        # Log audit
        log_event(
            'archive_suggestion_generated',
            user_id=document.user_id,
            document_id=document.id,
            details={
                'suggested_folder': ai_suggestion["suggested_folder"],
                'confidence_score': ai_suggestion["confidence_score"],
                'categoria': ai_suggestion["categoria_suggerita"]
            }
        )
        
        return {
            "success": True,
            "path_suggerito": ai_suggestion["path_suggerito"],
            "categoria_suggerita": ai_suggestion["categoria_suggerita"],
            "tag_ai": ai_suggestion["tag_ai"],
            "motivazione_ai": ai_suggestion["motivazione_ai"],
            "suggested_folder": ai_suggestion["suggested_folder"],
            "confidence_score": ai_suggestion["confidence_score"],
            "azienda_suggerita": ai_suggestion["azienda_suggerita"],
            "reparto_suggerito": ai_suggestion["reparto_suggerito"],
            "tipo_documento_ai": ai_suggestion["tipo_documento_ai"],
            "suggestion_id": suggestion.id
        }
        
    except Exception as e:
        logger.error(f"❌ Errore suggerimento archiviazione documento {document_id}: {e}")
        return {
            "success": False,
            "error": f"Errore durante il suggerimento: {str(e)}"
        }


def _generate_archive_suggestion_ai(document: Document, document_content: str, 
                                  company: Company, department: Department) -> Dict:
    """
    Genera il suggerimento AI per l'archiviazione.
    
    Args:
        document: Documento da analizzare
        document_content: Contenuto estratto del documento
        company: Azienda del documento
        department: Reparto del documento
        
    Returns:
        Dict: Suggerimento AI completo
    """
    try:
        # Analizza il contenuto del documento
        document_type = classify_document_type(document.title, document_content)
        
        # Determina categoria e reparto
        categoria, reparto = _determine_category_and_department(document_type, document_content, company, department)
        
        # Genera path suggerito
        path_suggerito = _generate_suggested_path(company, reparto, document_type)
        
        # Genera tag AI
        tag_ai = _generate_ai_tags(document_type, document_content, categoria)
        
        # Calcola punteggio confidenza
        confidence_score = _calculate_archive_confidence(document_type, document_content, categoria, reparto)
        
        # Genera motivazione AI
        motivazione_ai = _generate_archive_reasoning(document_type, categoria, reparto, tag_ai)
        
        return {
            "suggested_folder": f"{categoria}/{reparto}",
            "path_suggerito": path_suggerito,
            "categoria_suggerita": categoria,
            "tag_ai": tag_ai,
            "motivazione_ai": motivazione_ai,
            "azienda_suggerita": company.name if company else "Azienda",
            "reparto_suggerito": reparto,
            "tipo_documento_ai": document_type,
            "confidence_score": confidence_score,
            "reasoning": f"Suggerimento basato su tipo documento '{document_type}' e categoria '{categoria}'"
        }
        
    except Exception as e:
        logger.error(f"❌ Errore generazione suggerimento archiviazione: {e}")
        return {
            "suggested_folder": "Generale/Documenti",
            "path_suggerito": "/Generale/Documenti",
            "categoria_suggerita": "Generale",
            "tag_ai": ["documento"],
            "motivazione_ai": "Suggerimento di default per errore nell'analisi AI",
            "azienda_suggerita": company.name if company else "Azienda",
            "reparto_suggerito": "Generale",
            "tipo_documento_ai": "documento",
            "confidence_score": 30.0,
            "reasoning": "Suggerimento di fallback per errore AI"
        }


def _determine_category_and_department(document_type: str, content: str, 
                                     company: Company, department: Department) -> Tuple[str, str]:
    """Determina categoria e reparto basandosi sul tipo documento e contenuto."""
    
    # Mappatura tipo documento -> categoria
    type_to_category = {
        "contratto": "Contratti",
        "certificato": "Certificazioni",
        "manuale": "Manuali",
        "report": "Report",
        "fattura": "Amministrazione",
        "sicurezza": "Sicurezza",
        "qualita": "Qualità",
        "formazione": "Formazione",
        "haccp": "Qualità",
        "iso": "Qualità",
        "audit": "Qualità",
        "procedura": "Procedure",
        "policy": "Policy",
        "regolamento": "Regolamenti"
    }
    
    # Determina categoria
    categoria = type_to_category.get(document_type, "Generale")
    
    # Se è un documento di qualità, usa il reparto esistente
    if categoria == "Qualità" and department:
        reparto = department.name
    elif categoria == "Sicurezza":
        reparto = "Sicurezza"
    elif categoria == "Formazione":
        reparto = "Risorse Umane"
    elif categoria == "Amministrazione":
        reparto = "Amministrazione"
    elif categoria == "Contratti":
        reparto = "Legale"
    else:
        # Analizza il contenuto per determinare il reparto
        reparto = _analyze_content_for_department(content, company)
    
    return categoria, reparto


def _analyze_content_for_department(content: str, company: Company) -> str:
    """Analizza il contenuto per determinare il reparto appropriato."""
    content_lower = content.lower()
    
    # Parole chiave per reparti
    department_keywords = {
        "Qualità": ["qualità", "iso", "haccp", "certificazione", "audit", "procedure"],
        "Sicurezza": ["sicurezza", "protezione", "emergenza", "evacuazione", "antincendio"],
        "Produzione": ["produzione", "manifattura", "linea", "macchina", "processo"],
        "Logistica": ["logistica", "trasporto", "magazzino", "spedizione", "consegna"],
        "Vendite": ["vendita", "commerciale", "cliente", "ordine", "fattura"],
        "Risorse Umane": ["personale", "dipendente", "assunzione", "formazione", "hr"],
        "Amministrazione": ["amministrativo", "contabilità", "bilancio", "pagamento"],
        "Tecnologia": ["tecnologia", "it", "sistema", "software", "hardware"]
    }
    
    # Trova il reparto con più parole chiave
    best_department = "Generale"
    max_matches = 0
    
    for dept, keywords in department_keywords.items():
        matches = sum(1 for keyword in keywords if keyword in content_lower)
        if matches > max_matches:
            max_matches = matches
            best_department = dept
    
    return best_department


def _generate_suggested_path(company: Company, reparto: str, document_type: str) -> str:
    """Genera il path suggerito per l'archiviazione."""
    company_name = company.name if company else "Azienda"
    
    # Path base
    base_path = f"/{company_name}/{reparto}"
    
    # Aggiungi sottocartella basata sul tipo documento
    type_subfolders = {
        "contratto": "Contratti",
        "certificato": "Certificazioni",
        "manuale": "Manuali",
        "report": "Report",
        "fattura": "Fatture",
        "sicurezza": "Sicurezza",
        "qualita": "Qualità",
        "formazione": "Formazione",
        "haccp": "HACCP",
        "iso": "ISO",
        "audit": "Audit",
        "procedura": "Procedure",
        "policy": "Policy",
        "regolamento": "Regolamenti"
    }
    
    subfolder = type_subfolders.get(document_type, "Documenti")
    
    return f"{base_path}/{subfolder}"


def _generate_ai_tags(document_type: str, content: str, categoria: str) -> List[str]:
    """Genera tag AI basati sul tipo documento e contenuto."""
    tags = []
    
    # Tag basati sul tipo documento
    type_tags = {
        "contratto": ["contratto", "legale", "accordo"],
        "certificato": ["certificato", "certificazione", "qualità"],
        "manuale": ["manuale", "istruzioni", "procedura"],
        "report": ["report", "rapporto", "analisi"],
        "fattura": ["fattura", "billing", "pagamento"],
        "sicurezza": ["sicurezza", "protezione", "emergenza"],
        "qualita": ["qualità", "iso", "standard"],
        "formazione": ["formazione", "training", "corso"],
        "haccp": ["haccp", "alimentare", "sicurezza"],
        "iso": ["iso", "certificazione", "standard"],
        "audit": ["audit", "verifica", "controllo"],
        "procedura": ["procedura", "processo", "istruzioni"],
        "policy": ["policy", "politica", "regola"],
        "regolamento": ["regolamento", "norma", "legge"]
    }
    
    # Aggiungi tag del tipo documento
    tags.extend(type_tags.get(document_type, [document_type]))
    
    # Aggiungi tag della categoria
    tags.append(categoria.lower())
    
    # Analizza contenuto per tag aggiuntivi
    content_lower = content.lower()
    
    # Tag basati su parole chiave nel contenuto
    content_keywords = [
        "urgente", "critico", "importante", "confidenziale", "riservato",
        "annuale", "mensile", "trimestrale", "biennale",
        "revisione", "aggiornamento", "versione", "edizione"
    ]
    
    for keyword in content_keywords:
        if keyword in content_lower:
            tags.append(keyword)
    
    # Rimuovi duplicati e limita a 10 tag
    unique_tags = list(set(tags))[:10]
    
    return unique_tags


def _calculate_archive_confidence(document_type: str, content: str, categoria: str, reparto: str) -> float:
    """Calcola il punteggio di confidenza per il suggerimento."""
    score = 50.0  # Base score
    
    # Bonus per tipo documento riconosciuto
    if document_type in ["contratto", "certificato", "manuale", "report", "fattura", "sicurezza", "qualita"]:
        score += 20
    
    # Bonus per categoria specifica
    if categoria != "Generale":
        score += 15
    
    # Bonus per contenuto ricco
    if len(content) > 500:
        score += 10
    
    # Bonus per parole chiave specifiche
    content_lower = content.lower()
    specific_keywords = ["haccp", "iso", "sicurezza", "qualità", "formazione", "contratto", "certificato"]
    keyword_matches = sum(1 for keyword in specific_keywords if keyword in content_lower)
    score += keyword_matches * 5
    
    return min(100.0, max(0.0, score))


def _generate_archive_reasoning(document_type: str, categoria: str, reparto: str, tag_ai: List[str]) -> str:
    """Genera la motivazione AI per il suggerimento di archiviazione."""
    
    reasoning = f"Documento classificato come '{document_type}' e assegnato alla categoria '{categoria}'.\n\n"
    
    reasoning += f"Ripartimento suggerito: {reparto}\n"
    reasoning += f"Tag identificati: {', '.join(tag_ai)}\n\n"
    
    # Aggiungi spiegazione specifica per tipo documento
    type_explanations = {
        "contratto": "Documento legale che richiede archiviazione in area contratti per facile recupero.",
        "certificato": "Certificazione di qualità che deve essere archiviata in area certificazioni.",
        "manuale": "Manuale operativo per formazione e riferimento del personale.",
        "report": "Report analitico per decisioni strategiche e monitoraggio.",
        "fattura": "Documento amministrativo per gestione contabile.",
        "sicurezza": "Documento di sicurezza per compliance normativa.",
        "qualita": "Documento di qualità per certificazioni e audit.",
        "formazione": "Materiale formativo per sviluppo competenze."
    }
    
    explanation = type_explanations.get(document_type, "Documento generale per archiviazione standard.")
    reasoning += f"Motivazione: {explanation}"
    
    return reasoning 