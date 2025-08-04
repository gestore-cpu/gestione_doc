"""
Servizio per la ricerca semantica AI nei documenti.
Utilizza sentence-transformers per analizzare il contenuto dei documenti.
"""

import os
import logging
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer, util
import torch
from models import Document

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SemanticSearchService:
    """
    Servizio per la ricerca semantica nei documenti.
    
    Utilizza il modello all-MiniLM-L6-v2 per generare embeddings
    e calcolare similarità semantica tra query e documenti.
    """
    
    def __init__(self):
        """Inizializza il modello di embedding."""
        try:
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ Modello di ricerca semantica caricato con successo")
        except Exception as e:
            logger.error(f"❌ Errore nel caricamento del modello: {e}")
            self.model = None
    
    def estrai_testo_documento(self, file_path: str) -> str:
        """
        Estrae il testo da un documento.
        
        Args:
            file_path (str): Percorso del file
            
        Returns:
            str: Testo estratto dal documento
        """
        try:
            from services.ai_classifier import estrai_testo_documento
            return estrai_testo_documento(file_path)
        except Exception as e:
            logger.error(f"❌ Errore nell'estrazione testo da {file_path}: {e}")
            return ""
    
    def genera_embedding(self, testo: str) -> Optional[torch.Tensor]:
        """
        Genera l'embedding per un testo.
        
        Args:
            testo (str): Testo da processare
            
        Returns:
            torch.Tensor: Embedding del testo
        """
        if not self.model or not testo:
            return None
        
        try:
            return self.model.encode(testo, convert_to_tensor=True)
        except Exception as e:
            logger.error(f"❌ Errore nella generazione embedding: {e}")
            return None
    
    def calcola_similarita(self, query_embedding: torch.Tensor, doc_embedding: torch.Tensor) -> float:
        """
        Calcola la similarità coseno tra due embedding.
        
        Args:
            query_embedding (torch.Tensor): Embedding della query
            doc_embedding (torch.Tensor): Embedding del documento
            
        Returns:
            float: Score di similarità (0-1)
        """
        try:
            return util.cos_sim(query_embedding, doc_embedding).item()
        except Exception as e:
            logger.error(f"❌ Errore nel calcolo similarità: {e}")
            return 0.0
    
    def cerca_documenti(self, query: str, documenti: List[Document], max_results: int = 20) -> List[Tuple[Document, float]]:
        """
        Cerca documenti semanticamente simili alla query.
        
        Args:
            query (str): Query di ricerca
            documenti (List[Document]): Lista dei documenti da cercare
            max_results (int): Numero massimo di risultati
            
        Returns:
            List[Tuple[Document, float]]: Lista di (documento, score) ordinata per rilevanza
        """
        if not self.model:
            logger.warning("⚠️ Modello non disponibile, restituendo risultati vuoti")
            return []
        
        if not query.strip():
            return []
        
        try:
            # Genera embedding per la query
            query_embedding = self.genera_embedding(query)
            if query_embedding is None:
                return []
            
            risultati = []
            
            for doc in documenti:
                # Prepara il testo del documento per l'analisi
                testo_doc = self._prepara_testo_documento(doc)
                
                if not testo_doc:
                    continue
                
                # Genera embedding per il documento
                doc_embedding = self.genera_embedding(testo_doc)
                if doc_embedding is None:
                    continue
                
                # Calcola similarità
                score = self.calcola_similarita(query_embedding, doc_embedding)
                
                # Aggiungi solo se score > 0.1 (soglia minima)
                if score > 0.1:
                    risultati.append((doc, score))
            
            # Ordina per score decrescente
            risultati.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"🔍 Ricerca completata: {len(risultati)} risultati per query '{query}'")
            return risultati[:max_results]
            
        except Exception as e:
            logger.error(f"❌ Errore nella ricerca semantica: {e}")
            return []
    
    def _prepara_testo_documento(self, doc: Document) -> str:
        """
        Prepara il testo del documento per l'analisi semantica.
        
        Args:
            doc (Document): Documento da analizzare
            
        Returns:
            str: Testo preparato per l'analisi
        """
        parti_testo = []
        
        # Aggiungi titolo/filename
        if doc.title:
            parti_testo.append(doc.title)
        if doc.filename:
            parti_testo.append(doc.filename)
        
        # Aggiungi categoria AI
        if doc.categoria_ai:
            parti_testo.append(doc.categoria_ai)
        
        # Aggiungi tag
        if doc.tag:
            parti_testo.append(doc.tag)
        
        # Aggiungi contenuto testuale
        if doc.contenuto_testuale:
            parti_testo.append(doc.contenuto_testuale)
        
        # Aggiungi descrizione
        if doc.description:
            parti_testo.append(doc.description)
        
        # Aggiungi note
        if doc.note:
            parti_testo.append(doc.note)
        
        return " ".join(parti_testo)
    
    def indicizza_documento(self, doc: Document, file_path: str) -> bool:
        """
        Indicizza un documento estraendo e salvando il contenuto testuale.
        
        Args:
            doc (Document): Documento da indicizzare
            file_path (str): Percorso del file
            
        Returns:
            bool: True se l'indicizzazione è riuscita
        """
        try:
            # Estrai il testo dal documento
            contenuto = self.estrai_testo_documento(file_path)
            
            if contenuto:
                # Salva il contenuto nel database
                doc.contenuto_testuale = contenuto
                return True
            else:
                logger.warning(f"⚠️ Nessun contenuto estratto da {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Errore nell'indicizzazione di {file_path}: {e}")
            return False
    
    def aggiorna_indicizzazione_massiva(self, documenti: List[Document]) -> dict:
        """
        Aggiorna l'indicizzazione per tutti i documenti.
        
        Args:
            documenti (List[Document]): Lista dei documenti da indicizzare
            
        Returns:
            dict: Statistiche dell'aggiornamento
        """
        stats = {
            'totali': len(documenti),
            'aggiornati': 0,
            'errori': 0,
            'saltati': 0
        }
        
        for doc in documenti:
            try:
                # Costruisci il percorso del file
                file_path = os.path.join(doc.file_path, doc.filename)
                
                if not os.path.exists(file_path):
                    stats['saltati'] += 1
                    continue
                
                # Indicizza il documento
                if self.indicizza_documento(doc, file_path):
                    stats['aggiornati'] += 1
                else:
                    stats['errori'] += 1
                    
            except Exception as e:
                logger.error(f"❌ Errore nell'aggiornamento di {doc.filename}: {e}")
                stats['errori'] += 1
        
        logger.info(f"📊 Indicizzazione massiva completata: {stats}")
        return stats


# Istanza globale del servizio
semantic_search_service = SemanticSearchService()


def cerca_documenti(query: str, documenti: List[Document], max_results: int = 20) -> List[Tuple[Document, float]]:
    """
    Funzione di utilità per cercare documenti semanticamente.
    
    Args:
        query (str): Query di ricerca
        documenti (List[Document]): Lista dei documenti
        max_results (int): Numero massimo di risultati
        
    Returns:
        List[Tuple[Document, float]]: Risultati ordinati per rilevanza
    """
    from utils_extra import log_ai_analysis
    
    risultati = semantic_search_service.cerca_documenti(query, documenti, max_results)
    
    # Log della ricerca semantica AI
    if risultati:
        # Prendi il primo documento come esempio per il log
        primo_doc = risultati[0][0]
        log_ai_analysis(
            document_id=primo_doc.id,
            action_type="ricerca_semantica",
            payload={
                "query": query,
                "num_risultati": len(risultati),
                "max_results": max_results,
                "top_score": risultati[0][1] if risultati else 0.0
            }
        )
    
    return risultati


def indicizza_documento(doc: Document, file_path: str) -> bool:
    """
    Funzione di utilità per indicizzare un documento.
    
    Args:
        doc (Document): Documento da indicizzare
        file_path (str): Percorso del file
        
    Returns:
        bool: True se l'indicizzazione è riuscita
    """
    return semantic_search_service.indicizza_documento(doc, file_path) 