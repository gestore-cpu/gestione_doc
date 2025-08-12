"""
Servizio per aggregare i dati del registro invii PDF con stato avanzamento.
Gestisce la query complessa che unisce LogInvioPDF, LetturaPDF e FirmaDocumento.
"""

from datetime import datetime
from sqlalchemy import and_, or_, func
from models import LogInvioPDF, LetturaPDF, FirmaDocumento, User, Document, RegistroInviiDTO


class RegistroInviiService:
    """
    Servizio per gestire il registro invii PDF con stato avanzamento.
    """
    
    @staticmethod
    def get_registro_invii_completo():
        """
        Ottiene il registro completo degli invii PDF con stato avanzamento.
        
        Returns:
            list: Lista di RegistroInviiDTO con tutti i dati aggregati
        """
        try:
            # Query base per tutti gli invii PDF
            invii = LogInvioPDF.query.filter_by(tipo='user').all()
            registro = []
            
            for invio in invii:
                # Ottieni i dati dell'utente
                user = User.query.get(invio.id_utente_o_guest)
                if not user:
                    continue
                
                # Ottieni i dati del documento
                document = Document.query.get(invio.document_id) if hasattr(invio, 'document_id') else None
                if not document:
                    continue
                
                # Ottieni l'ultima lettura per questo utente e documento
                ultima_lettura = LetturaPDF.query.filter_by(
                    user_id=user.id,
                    document_id=document.id
                ).order_by(LetturaPDF.timestamp.desc()).first()
                
                # Ottieni la firma per questo utente e documento
                firma = FirmaDocumento.query.filter_by(
                    user_id=user.id,
                    document_id=document.id
                ).first()
                
                # Determina lo stato lettura
                stato_lettura = 'letto' if ultima_lettura else 'non_letto'
                data_lettura = ultima_lettura.timestamp if ultima_lettura else None
                ip_lettura = ultima_lettura.ip_address if ultima_lettura else None
                
                # Determina lo stato firma
                if firma:
                    stato_firma = firma.stato
                    data_firma = firma.timestamp
                    commento_firma = firma.commento
                    ip_firma = firma.ip_address
                else:
                    stato_firma = 'in_attesa'
                    data_firma = None
                    commento_firma = None
                    ip_firma = None
                
                # Crea il DTO
                registro_dto = RegistroInviiDTO(
                    documento_id=document.id,
                    documento_titolo=document.title,
                    utente_id=user.id,
                    utente_nome=f"{user.first_name or user.nome or ''} {user.last_name or user.cognome or ''}".strip() or user.username,
                    utente_email=user.email,
                    data_invio=invio.timestamp,
                    inviato_da=invio.inviato_da,
                    esito_invio=invio.esito,
                    data_lettura=data_lettura,
                    stato_lettura=stato_lettura,
                    data_firma=data_firma,
                    stato_firma=stato_firma,
                    commento_firma=commento_firma,
                    ip_lettura=ip_lettura,
                    ip_firma=ip_firma
                )
                
                registro.append(registro_dto)
            
            return registro
            
        except Exception as e:
            print(f"Errore nel recupero del registro invii: {str(e)}")
            return []
    
    @staticmethod
    def get_statistiche_registro():
        """
        Ottiene le statistiche del registro invii.
        
        Returns:
            dict: Dizionario con le statistiche
        """
        try:
            registro = RegistroInviiService.get_registro_invii_completo()
            
            if not registro:
                return {
                    'totali': 0,
                    'completati': 0,
                    'in_attesa': 0,
                    'rifiutati': 0,
                    'non_letti': 0,
                    'firmati': 0,
                    'percentuale_completamento': 0
                }
            
            totali = len(registro)
            completati = len([r for r in registro if r.is_completo])
            in_attesa = len([r for r in registro if r.is_in_attesa])
            rifiutati = len([r for r in registro if r.is_rifiutato])
            non_letti = len([r for r in registro if r.stato_lettura == 'non_letto'])
            firmati = len([r for r in registro if r.stato_firma == 'firmato'])
            
            percentuale_completamento = (completati / totali * 100) if totali > 0 else 0
            
            return {
                'totali': totali,
                'completati': completati,
                'in_attesa': in_attesa,
                'rifiutati': rifiutati,
                'non_letti': non_letti,
                'firmati': firmati,
                'percentuale_completamento': round(percentuale_completamento, 1)
            }
            
        except Exception as e:
            print(f"Errore nel calcolo statistiche registro: {str(e)}")
            return {
                'totali': 0,
                'completati': 0,
                'in_attesa': 0,
                'rifiutati': 0,
                'non_letti': 0,
                'firmati': 0,
                'percentuale_completamento': 0
            }
    
    @staticmethod
    def get_registro_filtrato(filtro_stato=None, filtro_documento=None, filtro_utente=None):
        """
        Ottiene il registro filtrato per stato, documento o utente.
        
        Args:
            filtro_stato (str): Filtro per stato ('completato', 'in_attesa', 'rifiutato')
            filtro_documento (int): ID documento per filtrare
            filtro_utente (int): ID utente per filtrare
            
        Returns:
            list: Lista filtrata di RegistroInviiDTO
        """
        try:
            registro = RegistroInviiService.get_registro_invii_completo()
            
            if filtro_stato:
                if filtro_stato == 'completato':
                    registro = [r for r in registro if r.is_completo]
                elif filtro_stato == 'in_attesa':
                    registro = [r for r in registro if r.is_in_attesa]
                elif filtro_stato == 'rifiutato':
                    registro = [r for r in registro if r.is_rifiutato]
            
            if filtro_documento:
                registro = [r for r in registro if r.documento_id == filtro_documento]
            
            if filtro_utente:
                registro = [r for r in registro if r.utente_id == filtro_utente]
            
            return registro
            
        except Exception as e:
            print(f"Errore nel filtraggio registro: {str(e)}")
            return []
    
    @staticmethod
    def get_dettagli_invio(invio_id):
        """
        Ottiene i dettagli completi di un singolo invio.
        
        Args:
            invio_id (int): ID dell'invio PDF
            
        Returns:
            RegistroInviiDTO: Dettagli dell'invio o None
        """
        try:
            invio = LogInvioPDF.query.get(invio_id)
            if not invio or invio.tipo != 'user':
                return None
            
            user = User.query.get(invio.id_utente_o_guest)
            if not user:
                return None
            
            # Cerca il documento associato
            # Nota: LogInvioPDF non ha document_id diretto, quindi cerchiamo nelle letture
            letture = LetturaPDF.query.filter_by(user_id=user.id).all()
            document = None
            
            for lettura in letture:
                doc = Document.query.get(lettura.document_id)
                if doc:
                    document = doc
                    break
            
            if not document:
                return None
            
            # Ottieni l'ultima lettura
            ultima_lettura = LetturaPDF.query.filter_by(
                user_id=user.id,
                document_id=document.id
            ).order_by(LetturaPDF.timestamp.desc()).first()
            
            # Ottieni la firma
            firma = FirmaDocumento.query.filter_by(
                user_id=user.id,
                document_id=document.id
            ).first()
            
            # Determina stati
            stato_lettura = 'letto' if ultima_lettura else 'non_letto'
            data_lettura = ultima_lettura.timestamp if ultima_lettura else None
            ip_lettura = ultima_lettura.ip_address if ultima_lettura else None
            
            if firma:
                stato_firma = firma.stato
                data_firma = firma.timestamp
                commento_firma = firma.commento
                ip_firma = firma.ip_address
            else:
                stato_firma = 'in_attesa'
                data_firma = None
                commento_firma = None
                ip_firma = None
            
            return RegistroInviiDTO(
                documento_id=document.id,
                documento_titolo=document.title,
                utente_id=user.id,
                utente_nome=f"{user.first_name or user.nome or ''} {user.last_name or user.cognome or ''}".strip() or user.username,
                utente_email=user.email,
                data_invio=invio.timestamp,
                inviato_da=invio.inviato_da,
                esito_invio=invio.esito,
                data_lettura=data_lettura,
                stato_lettura=stato_lettura,
                data_firma=data_firma,
                stato_firma=stato_firma,
                commento_firma=commento_firma,
                ip_lettura=ip_lettura,
                ip_firma=ip_firma
            )
            
        except Exception as e:
            print(f"Errore nel recupero dettagli invio: {str(e)}")
            return None
