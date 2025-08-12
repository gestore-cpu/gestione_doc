"""
Servizio AI per l'analisi intelligente dei documenti e reparti.
Fornisce insights automatici basati sui dati di utilizzo dei documenti.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from services.document_analytics_service import DocumentAnalyticsService

logger = logging.getLogger(__name__)


class AIDocumentAnalysisService:
    """
    Servizio per l'analisi AI dei documenti e reparti.
    """
    
    @staticmethod
    def prompt_ai_analisi_documenti(dati_documenti: List[Dict[str, Any]]) -> str:
        """
        Genera il prompt AI per l'analisi dei documenti.
        
        Args:
            dati_documenti: Lista di dizionari con i dati dei documenti
            
        Returns:
            str: Prompt formattato per l'AI
        """
        # Formatta i dati per il prompt
        dati_formattati = []
        for item in dati_documenti:
            dati_formattati.append({
                "documento": item.get('documento', 'N/A'),
                "reparto": item.get('reparto', 'N/A'),
                "uploader": item.get('uploader', 'N/A'),
                "data_creazione": item.get('data_creazione', 'N/A'),
                "download": item.get('download', 0),
                "letture": item.get('letture', 0),
                "firme": item.get('firme', 0),
                "firme_rifiutate": item.get('firme_rifiutate', 0),
                "ultima_firma": item.get('ultima_firma', None),
                "ultima_lettura": item.get('ultima_lettura', None),
                "ultimo_download": item.get('ultimo_download', None),
                "percentuale_lettura": item.get('percentuale_lettura', 0),
                "percentuale_firma": item.get('percentuale_firma', 0),
                "stato_compliance": item.get('stato_compliance', 'N/A'),
                "anomalie": item.get('anomalie', []),
                "anomalie_count": item.get('anomalie_count', 0)
            })
        
        return f"""
Sei un assistente esperto in gestione qualità e sicurezza aziendale, specializzato nell'analisi di compliance documentale.

Ricevi un elenco di documenti aziendali con dati sull'uso reale da parte dei reparti:

{dati_formattati}

## 🎯 Obiettivo dell'Analisi

Per ciascun documento e reparto, analizza:

### 📊 **Metriche di Utilizzo**
- Se il documento è effettivamente scaricato, letto, firmato
- Percentuali di compliance (lettura e firma)
- Frequenza di utilizzo e ultime attività

### 🔍 **Rilevamento Anomalie**
- Reparti inattivi o poco formati
- Documenti non utilizzati o sottoutilizzati
- Firme rifiutate e motivi potenziali
- Incongruenze tra attività e compliance

### ⚠️ **Problemi di Compliance**
- Documenti scaricati ma non letti
- Documenti letti ma non firmati
- Reparti che ignorano documenti importanti
- Versioni obsolete o non aggiornate

### 🎯 **Suggerimenti Azioni Correttive**
- Formazione specifica per reparti carenti
- Reminder automatici per documenti in sospeso
- Obbligo di firma per documenti critici
- Allineamento versioni e invalidazione firme obsolete
- Procedure di follow-up per compliance

## 📋 Formato Output Richiesto

Restituisci un'analisi dettagliata strutturata così:

### 📄 **Analisi per Documento**
Per ogni documento, evidenzia:
- Stato compliance generale
- Reparti virtuosi vs problematici
- Anomalie specifiche rilevate
- Azioni correttive prioritarie

### 🏢 **Analisi per Reparto**
Per ogni reparto, identifica:
- Livello di engagement documentale
- Documenti critici non utilizzati
- Necessità formative specifiche
- Trend di compliance nel tempo

### 🚨 **Alert e Priorità**
- Situazioni critiche da risolvere entro 24h
- Problemi di compliance da monitorare
- Opportunità di miglioramento
- Raccomandazioni per la direzione

### 📈 **Metriche e KPI**
- Compliance rate generale
- Reparti più virtuosi
- Documenti più problematici
- Trend di miglioramento suggeriti

L'analisi deve essere pratica, actionable e orientata al miglioramento continuo della compliance aziendale.
"""
    
    @staticmethod
    def analizza_documenti_con_ai() -> Dict[str, Any]:
        """
        Esegue l'analisi AI completa dei documenti.
        
        Returns:
            dict: Risultati dell'analisi AI
        """
        try:
            logger.info("🤖 Avvio analisi AI documenti...")
            
            # Ottieni i dati aggregati
            dati_documenti = DocumentAnalyticsService.get_analisi_aggregata_documenti()
            
            if not dati_documenti:
                return {
                    "success": False,
                    "error": "Nessun dato disponibile per l'analisi",
                    "analisi": "Nessun documento trovato nel sistema."
                }
            
            # Genera il prompt AI
            prompt = AIDocumentAnalysisService.prompt_ai_analisi_documenti(dati_documenti)
            
            # Calcola statistiche aggiuntive per l'AI
            statistiche_ai = AIDocumentAnalysisService._calcola_statistiche_ai(dati_documenti)
            
            # Analisi automatica basata su regole
            analisi_automatica = AIDocumentAnalysisService._analisi_automatica(dati_documenti)
            
            # Prepara il risultato
            risultato = {
                "success": True,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "documenti_analizzati": len(dati_documenti),
                "prompt_ai": prompt,
                "statistiche_ai": statistiche_ai,
                "analisi_automatica": analisi_automatica,
                "dati_bruti": dati_documenti
            }
            
            logger.info(f"✅ Analisi AI completata - {len(dati_documenti)} documenti analizzati")
            return risultato
            
        except Exception as e:
            logger.error(f"❌ Errore nell'analisi AI documenti: {str(e)}")
            return {
                "success": False,
                "error": f"Errore nell'analisi AI: {str(e)}",
                "analisi": "Impossibile completare l'analisi AI."
            }
    
    @staticmethod
    def _calcola_statistiche_ai(dati_documenti: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcola statistiche avanzate per l'analisi AI.
        
        Args:
            dati_documenti: Lista dei dati documenti
            
        Returns:
            dict: Statistiche per l'AI
        """
        try:
            # Statistiche generali
            total_documenti = len(dati_documenti)
            total_reparti = len(set(item['reparto'] for item in dati_documenti))
            
            # Conta stati compliance
            compliant = len([item for item in dati_documenti if item['stato_compliance'] == "✅ Compliant"])
            in_attesa = len([item for item in dati_documenti if item['stato_compliance'] == "⚠️ In Attesa Firma"])
            non_utilizzati = len([item for item in dati_documenti if item['stato_compliance'] in ["❌ Non Utilizzato", "📄 Scaricato"]])
            
            # Analisi per reparto
            reparti_stats = {}
            for item in dati_documenti:
                reparto = item['reparto']
                if reparto not in reparti_stats:
                    reparti_stats[reparto] = {
                        'documenti': 0,
                        'compliant': 0,
                        'in_attesa': 0,
                        'non_utilizzati': 0,
                        'anomalie': 0,
                        'download_totali': 0,
                        'letture_totali': 0,
                        'firme_totali': 0
                    }
                
                reparti_stats[reparto]['documenti'] += 1
                reparti_stats[reparto]['download_totali'] += item['download']
                reparti_stats[reparto]['letture_totali'] += item['letture']
                reparti_stats[reparto]['firme_totali'] += item['firme']
                reparti_stats[reparto]['anomalie'] += item['anomalie_count']
                
                if item['stato_compliance'] == "✅ Compliant":
                    reparti_stats[reparto]['compliant'] += 1
                elif item['stato_compliance'] == "⚠️ In Attesa Firma":
                    reparti_stats[reparto]['in_attesa'] += 1
                else:
                    reparti_stats[reparto]['non_utilizzati'] += 1
            
            # Calcola compliance rate per reparto
            for reparto, stats in reparti_stats.items():
                if stats['documenti'] > 0:
                    stats['compliance_rate'] = round((stats['compliant'] / stats['documenti']) * 100, 1)
                    stats['engagement_rate'] = round(((stats['letture_totali'] + stats['firme_totali']) / (stats['documenti'] * 10)) * 100, 1)
                else:
                    stats['compliance_rate'] = 0
                    stats['engagement_rate'] = 0
            
            # Trova reparti problematici
            reparti_problematici = []
            for reparto, stats in reparti_stats.items():
                if stats['compliance_rate'] < 50 or stats['anomalie'] > 0:
                    reparti_problematici.append({
                        'reparto': reparto,
                        'compliance_rate': stats['compliance_rate'],
                        'anomalie': stats['anomalie'],
                        'documenti_non_utilizzati': stats['non_utilizzati']
                    })
            
            # Trova documenti critici
            documenti_critici = []
            for item in dati_documenti:
                if (item['anomalie_count'] > 0 or 
                    item['stato_compliance'] in ["❌ Non Utilizzato", "📄 Scaricato"] or
                    item['firme_rifiutate'] > 0):
                    documenti_critici.append({
                        'documento': item['documento'],
                        'reparto': item['reparto'],
                        'stato': item['stato_compliance'],
                        'anomalie': item['anomalie'],
                        'firme_rifiutate': item['firme_rifiutate']
                    })
            
            return {
                'total_documenti': total_documenti,
                'total_reparti': total_reparti,
                'compliant': compliant,
                'in_attesa': in_attesa,
                'non_utilizzati': non_utilizzati,
                'compliance_rate_generale': round((compliant / total_documenti) * 100, 1) if total_documenti > 0 else 0,
                'reparti_stats': reparti_stats,
                'reparti_problematici': reparti_problematici,
                'documenti_critici': documenti_critici
            }
            
        except Exception as e:
            logger.error(f"❌ Errore nel calcolo statistiche AI: {str(e)}")
            return {}
    
    @staticmethod
    def _analisi_automatica(dati_documenti: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Esegue analisi automatica basata su regole.
        
        Args:
            dati_documenti: Lista dei dati documenti
            
        Returns:
            dict: Analisi automatica
        """
        try:
            analisi = {
                'alert_critici': [],
                'raccomandazioni': [],
                'reparti_virtuosi': [],
                'reparti_problematici': [],
                'documenti_prioritari': []
            }
            
            # Analizza ogni documento
            for item in dati_documenti:
                # Alert critici
                if item['stato_compliance'] == "❌ Non Utilizzato":
                    analisi['alert_critici'].append({
                        'tipo': 'Documento non utilizzato',
                        'documento': item['documento'],
                        'reparto': item['reparto'],
                        'severita': 'ALTA',
                        'azione': 'Inviare reminder urgente e verificare formazione'
                    })
                
                elif item['stato_compliance'] == "⚠️ In Attesa Firma" and item['letture'] > 0:
                    analisi['alert_critici'].append({
                        'tipo': 'Documento letto ma non firmato',
                        'documento': item['documento'],
                        'reparto': item['reparto'],
                        'severita': 'MEDIA',
                        'azione': 'Sollecitare firma e verificare comprensione'
                    })
                
                # Documenti prioritari
                if item['anomalie_count'] > 0:
                    analisi['documenti_prioritari'].append({
                        'documento': item['documento'],
                        'reparto': item['reparto'],
                        'anomalie': item['anomalie'],
                        'priorita': 'ALTA' if item['anomalie_count'] > 2 else 'MEDIA'
                    })
            
            # Analizza reparti
            reparti_stats = {}
            for item in dati_documenti:
                reparto = item['reparto']
                if reparto not in reparti_stats:
                    reparti_stats[reparto] = {
                        'documenti': 0,
                        'compliant': 0,
                        'anomalie': 0
                    }
                
                reparti_stats[reparto]['documenti'] += 1
                if item['stato_compliance'] == "✅ Compliant":
                    reparti_stats[reparto]['compliant'] += 1
                reparti_stats[reparto]['anomalie'] += item['anomalie_count']
            
            # Classifica reparti
            for reparto, stats in reparti_stats.items():
                compliance_rate = (stats['compliant'] / stats['documenti']) * 100 if stats['documenti'] > 0 else 0
                
                if compliance_rate >= 80 and stats['anomalie'] == 0:
                    analisi['reparti_virtuosi'].append({
                        'reparto': reparto,
                        'compliance_rate': compliance_rate,
                        'documenti': stats['documenti']
                    })
                elif compliance_rate < 50 or stats['anomalie'] > 2:
                    analisi['reparti_problematici'].append({
                        'reparto': reparto,
                        'compliance_rate': compliance_rate,
                        'anomalie': stats['anomalie'],
                        'azione': 'Formazione urgente e monitoraggio intensivo'
                    })
            
            # Raccomandazioni generali
            if len(analisi['alert_critici']) > 0:
                analisi['raccomandazioni'].append({
                    'tipo': 'CRITICO',
                    'descrizione': f"Ci sono {len(analisi['alert_critici'])} situazioni critiche da risolvere immediatamente",
                    'azione': 'Revisione urgente delle procedure di compliance'
                })
            
            if len(analisi['reparti_problematici']) > 0:
                analisi['raccomandazioni'].append({
                    'tipo': 'FORMATIVO',
                    'descrizione': f"{len(analisi['reparti_problematici'])} reparti necessitano formazione specifica",
                    'azione': 'Pianificare sessioni formative dedicate'
                })
            
            return analisi
            
        except Exception as e:
            logger.error(f"❌ Errore nell'analisi automatica: {str(e)}")
            return {
                'alert_critici': [],
                'raccomandazioni': [],
                'reparti_virtuosi': [],
                'reparti_problematici': [],
                'documenti_prioritari': []
            }
    
    @staticmethod
    def genera_report_ai() -> str:
        """
        Genera un report AI completo in formato testo.
        
        Returns:
            str: Report AI formattato
        """
        try:
            # Esegui l'analisi AI
            risultato_ai = AIDocumentAnalysisService.analizza_documenti_con_ai()
            
            if not risultato_ai['success']:
                return f"❌ Errore nell'analisi AI: {risultato_ai.get('error', 'Errore sconosciuto')}"
            
            # Estrai i dati
            statistiche = risultato_ai['statistiche_ai']
            analisi_auto = risultato_ai['analisi_automatica']
            dati_documenti = risultato_ai['dati_bruti']
            
            # Genera il report
            report = f"""
# 🤖 REPORT ANALISI AI DOCUMENTI
*Generato il: {risultato_ai['timestamp']}*

## 📊 PANORAMICA GENERALE
- **Documenti analizzati:** {risultato_ai['documenti_analizzati']}
- **Reparti coinvolti:** {statistiche['total_reparti']}
- **Compliance rate generale:** {statistiche['compliance_rate_generale']}%
- **Documenti compliant:** {statistiche['compliant']}/{statistiche['total_documenti']}
- **Documenti in attesa:** {statistiche['in_attesa']}
- **Documenti non utilizzati:** {statistiche['non_utilizzati']}

## 🚨 ALERT CRITICI ({len(analisi_auto['alert_critici'])})
"""
            
            for alert in analisi_auto['alert_critici']:
                report += f"""
### {alert['tipo']}
- **Documento:** {alert['documento']}
- **Reparto:** {alert['reparto']}
- **Severità:** {alert['severita']}
- **Azione richiesta:** {alert['azione']}
"""
            
            report += f"""
## 🏆 REPARTI VIRTUOSI ({len(analisi_auto['reparti_virtuosi'])})
"""
            
            for reparto in analisi_auto['reparti_virtuosi']:
                report += f"""
### {reparto['reparto']}
- **Compliance rate:** {reparto['compliance_rate']}%
- **Documenti gestiti:** {reparto['documenti']}
- **Stato:** ✅ Eccellente
"""
            
            report += f"""
## ⚠️ REPARTI PROBLEMATICI ({len(analisi_auto['reparti_problematici'])})
"""
            
            for reparto in analisi_auto['reparti_problematici']:
                report += f"""
### {reparto['reparto']}
- **Compliance rate:** {reparto['compliance_rate']}%
- **Anomalie rilevate:** {reparto['anomalie']}
- **Azione richiesta:** {reparto['azione']}
"""
            
            report += f"""
## 📋 DOCUMENTI PRIORITARI ({len(analisi_auto['documenti_prioritari'])})
"""
            
            for doc in analisi_auto['documenti_prioritari']:
                report += f"""
### {doc['documento']} ({doc['reparto']})
- **Priorità:** {doc['priorita']}
- **Anomalie:** {', '.join(doc['anomalie'])}
"""
            
            report += f"""
## 💡 RACCOMANDAZIONI ({len(analisi_auto['raccomandazioni'])})
"""
            
            for racc in analisi_auto['raccomandazioni']:
                report += f"""
### {racc['tipo']}
- **Descrizione:** {racc['descrizione']}
- **Azione suggerita:** {racc['azione']}
"""
            
            report += f"""
## 📈 STATISTICHE DETTAGLIATE PER REPARTO

"""
            
            for reparto, stats in statistiche['reparti_stats'].items():
                report += f"""
### {reparto}
- **Documenti:** {stats['documenti']}
- **Compliance rate:** {stats['compliance_rate']}%
- **Engagement rate:** {stats['engagement_rate']}%
- **Download totali:** {stats['download_totali']}
- **Letture totali:** {stats['letture_totali']}
- **Firme totali:** {stats['firme_totali']}
- **Anomalie:** {stats['anomalie']}
"""
            
            report += f"""

---
*Report generato automaticamente dal sistema AI di analisi documenti*
"""
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Errore nella generazione report AI: {str(e)}")
            return f"❌ Errore nella generazione report AI: {str(e)}"
