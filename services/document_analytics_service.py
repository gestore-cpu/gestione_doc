"""
Servizio per l'analisi aggregata dei documenti e reparti.
Fornisce dati strutturati per l'analisi AI e il monitoraggio compliance.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, case, desc
from models import (
    Document, Department, User, LogInvioPDF, LetturaPDF, 
    FirmaDocumento, DownloadLog, DocumentReadLog
)
from extensions import db
import logging

logger = logging.getLogger(__name__)


class DocumentAnalyticsService:
    """
    Servizio per l'analisi aggregata dei documenti e reparti.
    """
    
    @staticmethod
    def get_analisi_aggregata_documenti():
        """
        Ottiene l'analisi aggregata completa di tutti i documenti per reparto.
        
        Returns:
            list: Lista di dizionari con i dati aggregati
        """
        try:
            logger.info("🔍 Avvio analisi aggregata documenti...")
            
            # Query principale per aggregare i dati
            result = (
                db.session.query(
                    Document.id.label("document_id"),
                    Document.title.label("documento_nome"),
                    Document.filename.label("documento_filename"),
                    Document.created_at.label("data_creazione"),
                    Document.uploader_email.label("uploader"),
                    Department.name.label("reparto_nome"),
                    Department.id.label("reparto_id"),
                    func.count(DownloadLog.id.distinct()).label("n_download"),
                    func.count(LetturaPDF.id.distinct()).label("n_letture"),
                    func.count(FirmaDocumento.id.distinct()).label("n_firme"),
                    func.max(FirmaDocumento.timestamp).label("ultima_firma"),
                    func.max(LetturaPDF.timestamp).label("ultima_lettura"),
                    func.max(DownloadLog.timestamp).label("ultimo_download"),
                    # Calcola anomalie
                    func.count(case([(FirmaDocumento.stato == 'rifiutato', 1)])).label("firme_rifiutate"),
                    func.count(case([(LetturaPDF.id.is_(None), 1)])).label("non_letti"),
                    func.count(case([(FirmaDocumento.id.is_(None), 1)])).label("non_firmati")
                )
                .join(User, Document.user_id == User.id)
                .join(Department, Document.department_id == Department.id)
                .outerjoin(DownloadLog, DownloadLog.document_id == Document.id)
                .outerjoin(LetturaPDF, LetturaPDF.document_id == Document.id)
                .outerjoin(FirmaDocumento, FirmaDocumento.document_id == Document.id)
                .group_by(
                    Document.id,
                    Document.title,
                    Document.filename,
                    Document.created_at,
                    Document.uploader_email,
                    Department.name,
                    Department.id
                )
                .order_by(Department.name, Document.title)
                .all()
            )
            
            # Converti i risultati in formato JSON
            analisi_data = []
            
            for row in result:
                # Calcola anomalie
                anomalie = []
                if row.n_firme == 0 and row.n_letture > 0:
                    anomalie.append("Letto ma non firmato")
                if row.n_letture == 0 and row.n_download > 0:
                    anomalie.append("Scaricato ma non letto")
                if row.firme_rifiutate > 0:
                    anomalie.append(f"{row.firme_rifiutate} firme rifiutate")
                if row.non_letti > 0:
                    anomalie.append(f"{row.non_letti} utenti non hanno letto")
                if row.non_firmati > 0:
                    anomalie.append(f"{row.non_firmati} utenti non hanno firmato")
                
                # Calcola percentuali
                totale_utenti = max(row.n_download, row.n_letture, row.n_firme, 1)
                percentuale_lettura = round((row.n_letture / totale_utenti) * 100, 1) if totale_utenti > 0 else 0
                percentuale_firma = round((row.n_firme / totale_utenti) * 100, 1) if totale_utenti > 0 else 0
                
                # Determina stato compliance
                if row.n_firme > 0:
                    stato_compliance = "✅ Compliant"
                elif row.n_letture > 0:
                    stato_compliance = "⚠️ In Attesa Firma"
                elif row.n_download > 0:
                    stato_compliance = "📄 Scaricato"
                else:
                    stato_compliance = "❌ Non Utilizzato"
                
                analisi_item = {
                    "document_id": row.document_id,
                    "documento": row.documento_nome,
                    "reparto": row.reparto_nome,
                    "reparto_id": row.reparto_id,
                    "uploader": row.uploader,
                    "data_creazione": row.data_creazione.strftime('%d/%m/%Y') if row.data_creazione else None,
                    "download": row.n_download,
                    "letture": row.n_letture,
                    "firme": row.n_firme,
                    "firme_rifiutate": row.firme_rifiutate,
                    "ultima_firma": row.ultima_firma.strftime('%d/%m/%Y %H:%M') if row.ultima_firma else None,
                    "ultima_lettura": row.ultima_lettura.strftime('%d/%m/%Y %H:%M') if row.ultima_lettura else None,
                    "ultimo_download": row.ultimo_download.strftime('%d/%m/%Y %H:%M') if row.ultimo_download else None,
                    "percentuale_lettura": percentuale_lettura,
                    "percentuale_firma": percentuale_firma,
                    "stato_compliance": stato_compliance,
                    "anomalie": anomalie,
                    "anomalie_count": len(anomalie)
                }
                
                analisi_data.append(analisi_item)
            
            logger.info(f"✅ Analisi aggregata completata - {len(analisi_data)} documenti analizzati")
            return analisi_data
            
        except Exception as e:
            logger.error(f"❌ Errore nell'analisi aggregata documenti: {str(e)}")
            return []
    
    @staticmethod
    def get_analisi_per_reparto():
        """
        Ottiene l'analisi aggregata per reparto.
        
        Returns:
            dict: Dizionario con analisi per reparto
        """
        try:
            # Ottieni tutti i dati aggregati
            analisi_completa = DocumentAnalyticsService.get_analisi_aggregata_documenti()
            
            # Raggruppa per reparto
            analisi_per_reparto = {}
            
            for item in analisi_completa:
                reparto = item['reparto']
                
                if reparto not in analisi_per_reparto:
                    analisi_per_reparto[reparto] = {
                        'reparto': reparto,
                        'documenti': [],
                        'statistiche': {
                            'total_documenti': 0,
                            'total_download': 0,
                            'total_letture': 0,
                            'total_firme': 0,
                            'documenti_compliant': 0,
                            'documenti_in_attesa': 0,
                            'documenti_non_utilizzati': 0,
                            'anomalie_totali': 0
                        }
                    }
                
                # Aggiungi documento
                analisi_per_reparto[reparto]['documenti'].append(item)
                
                # Aggiorna statistiche
                stats = analisi_per_reparto[reparto]['statistiche']
                stats['total_documenti'] += 1
                stats['total_download'] += item['download']
                stats['total_letture'] += item['letture']
                stats['total_firme'] += item['firme']
                stats['anomalie_totali'] += item['anomalie_count']
                
                # Conta stati compliance
                if item['stato_compliance'] == "✅ Compliant":
                    stats['documenti_compliant'] += 1
                elif item['stato_compliance'] == "⚠️ In Attesa Firma":
                    stats['documenti_in_attesa'] += 1
                else:
                    stats['documenti_non_utilizzati'] += 1
            
            # Calcola percentuali per reparto
            for reparto_data in analisi_per_reparto.values():
                stats = reparto_data['statistiche']
                total_doc = stats['total_documenti']
                
                if total_doc > 0:
                    stats['percentuale_compliant'] = round((stats['documenti_compliant'] / total_doc) * 100, 1)
                    stats['percentuale_attesa'] = round((stats['documenti_in_attesa'] / total_doc) * 100, 1)
                    stats['percentuale_non_utilizzati'] = round((stats['documenti_non_utilizzati'] / total_doc) * 100, 1)
                else:
                    stats['percentuale_compliant'] = 0
                    stats['percentuale_attesa'] = 0
                    stats['percentuale_non_utilizzati'] = 0
            
            return analisi_per_reparto
            
        except Exception as e:
            logger.error(f"❌ Errore nell'analisi per reparto: {str(e)}")
            return {}
    
    @staticmethod
    def get_statistiche_generali():
        """
        Ottiene statistiche generali dell'analisi.
        
        Returns:
            dict: Statistiche generali
        """
        try:
            analisi_completa = DocumentAnalyticsService.get_analisi_aggregata_documenti()
            
            if not analisi_completa:
                return {
                    'total_documenti': 0,
                    'total_reparti': 0,
                    'total_download': 0,
                    'total_letture': 0,
                    'total_firme': 0,
                    'documenti_compliant': 0,
                    'documenti_in_attesa': 0,
                    'documenti_non_utilizzati': 0,
                    'anomalie_totali': 0,
                    'percentuale_compliant': 0,
                    'percentuale_attesa': 0,
                    'percentuale_non_utilizzati': 0
                }
            
            # Calcola totali
            total_documenti = len(analisi_completa)
            total_reparti = len(set(item['reparto'] for item in analisi_completa))
            total_download = sum(item['download'] for item in analisi_completa)
            total_letture = sum(item['letture'] for item in analisi_completa)
            total_firme = sum(item['firme'] for item in analisi_completa)
            anomalie_totali = sum(item['anomalie_count'] for item in analisi_completa)
            
            # Conta stati compliance
            documenti_compliant = len([item for item in analisi_completa if item['stato_compliance'] == "✅ Compliant"])
            documenti_in_attesa = len([item for item in analisi_completa if item['stato_compliance'] == "⚠️ In Attesa Firma"])
            documenti_non_utilizzati = len([item for item in analisi_completa if item['stato_compliance'] in ["❌ Non Utilizzato", "📄 Scaricato"]])
            
            # Calcola percentuali
            percentuale_compliant = round((documenti_compliant / total_documenti) * 100, 1) if total_documenti > 0 else 0
            percentuale_attesa = round((documenti_in_attesa / total_documenti) * 100, 1) if total_documenti > 0 else 0
            percentuale_non_utilizzati = round((documenti_non_utilizzati / total_documenti) * 100, 1) if total_documenti > 0 else 0
            
            return {
                'total_documenti': total_documenti,
                'total_reparti': total_reparti,
                'total_download': total_download,
                'total_letture': total_letture,
                'total_firme': total_firme,
                'documenti_compliant': documenti_compliant,
                'documenti_in_attesa': documenti_in_attesa,
                'documenti_non_utilizzati': documenti_non_utilizzati,
                'anomalie_totali': anomalie_totali,
                'percentuale_compliant': percentuale_compliant,
                'percentuale_attesa': percentuale_attesa,
                'percentuale_non_utilizzati': percentuale_non_utilizzati
            }
            
        except Exception as e:
            logger.error(f"❌ Errore nel calcolo statistiche generali: {str(e)}")
            return {
                'total_documenti': 0,
                'total_reparti': 0,
                'total_download': 0,
                'total_letture': 0,
                'total_firme': 0,
                'documenti_compliant': 0,
                'documenti_in_attesa': 0,
                'documenti_non_utilizzati': 0,
                'anomalie_totali': 0,
                'percentuale_compliant': 0,
                'percentuale_attesa': 0,
                'percentuale_non_utilizzati': 0
            }
    
    @staticmethod
    def get_documenti_con_anomalie():
        """
        Ottiene solo i documenti che presentano anomalie.
        
        Returns:
            list: Lista di documenti con anomalie
        """
        try:
            analisi_completa = DocumentAnalyticsService.get_analisi_aggregata_documenti()
            
            # Filtra documenti con anomalie
            documenti_con_anomalie = [
                item for item in analisi_completa 
                if item['anomalie_count'] > 0
            ]
            
            # Ordina per numero di anomalie (decrescente)
            documenti_con_anomalie.sort(key=lambda x: x['anomalie_count'], reverse=True)
            
            return documenti_con_anomalie
            
        except Exception as e:
            logger.error(f"❌ Errore nel recupero documenti con anomalie: {str(e)}")
            return []
    
    @staticmethod
    def get_analisi_periodo(inizio, fine):
        """
        Ottiene l'analisi per un periodo specifico.
        
        Args:
            inizio (datetime): Data inizio periodo
            fine (datetime): Data fine periodo
            
        Returns:
            list: Analisi per il periodo specificato
        """
        try:
            # Query con filtro temporale
            result = (
                db.session.query(
                    Document.id.label("document_id"),
                    Document.title.label("documento_nome"),
                    Department.name.label("reparto_nome"),
                    func.count(DownloadLog.id.distinct()).label("n_download"),
                    func.count(LetturaPDF.id.distinct()).label("n_letture"),
                    func.count(FirmaDocumento.id.distinct()).label("n_firme"),
                    func.max(FirmaDocumento.timestamp).label("ultima_firma")
                )
                .join(User, Document.user_id == User.id)
                .join(Department, Document.department_id == Department.id)
                .outerjoin(DownloadLog, and_(
                    DownloadLog.document_id == Document.id,
                    DownloadLog.timestamp.between(inizio, fine)
                ))
                .outerjoin(LetturaPDF, and_(
                    LetturaPDF.document_id == Document.id,
                    LetturaPDF.timestamp.between(inizio, fine)
                ))
                .outerjoin(FirmaDocumento, and_(
                    FirmaDocumento.document_id == Document.id,
                    FirmaDocumento.timestamp.between(inizio, fine)
                ))
                .group_by(Document.id, Document.title, Department.name)
                .all()
            )
            
            # Converti risultati
            analisi_periodo = []
            for row in result:
                analisi_item = {
                    "document_id": row.document_id,
                    "documento": row.documento_nome,
                    "reparto": row.reparto_nome,
                    "download": row.n_download,
                    "letture": row.n_letture,
                    "firme": row.n_firme,
                    "ultima_firma": row.ultima_firma.strftime('%d/%m/%Y %H:%M') if row.ultima_firma else None,
                    "periodo_inizio": inizio.strftime('%d/%m/%Y'),
                    "periodo_fine": fine.strftime('%d/%m/%Y')
                }
                analisi_periodo.append(analisi_item)
            
            return analisi_periodo
            
        except Exception as e:
            logger.error(f"❌ Errore nell'analisi periodo: {str(e)}")
            return []
