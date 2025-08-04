from datetime import datetime

def firma_ai_documento(esito: str, motivazione: str = "") -> dict:
    """Genera la firma AI per un documento analizzato.

    Args:
        esito (str): Esito dell’analisi ("conforme", "incompleto", "non_conforme").
        motivazione (str, optional): Motivo dell’esito, se presente.

    Returns:
        dict: Dizionario con firma AI, esito, motivo e timestamp.
    """
    return {
        "firma_ai": {
            "esito": esito,
            "motivo": motivazione,
            "timestamp": datetime.utcnow().isoformat()
        }
    } 