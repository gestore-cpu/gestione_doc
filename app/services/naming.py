from datetime import datetime
import re


def genera_nome_file(obj: str, cognome: str, data: datetime, revisione: int = 0) -> str:
    """Genera un nome file standardizzato per i documenti caricati.

    Args:
        obj (str): Oggetto del documento (es. 'Qualità').
        cognome (str): Cognome del referente o nome azienda.
        data (datetime): Data di creazione del documento.
        revisione (int, optional): Numero revisione. Default 0 (nessuna revisione).

    Returns:
        str: Nome file formattato secondo lo standard richiesto.
    """
    ogg = obj[:3].upper()  # Prime 3 lettere dell’oggetto
    cog = cognome[:3].upper()  # Prime 3 lettere del cognome/azienda
    data_str = data.strftime("%Y%m%d")  # Data in formato YYYYMMDD
    rev = f"_rev{revisione}" if revisione > 0 else ""
    return f"{ogg}-{cog}_{data_str}{rev}.pdf"


def estrai_metadati_da_nome(nome_file: str) -> dict:
    """Estrae i metadati dal nome file secondo la convenzione standard.

    Args:
        nome_file (str): Nome del file (es. 'QUA-ROS_20250724_rev2.pdf').

    Returns:
        dict: Metadati estratti (oggetto, referente, data_creazione, revisione).
    """
    pattern = r"([A-Z]{3})-([A-Z]{3})_(\d{8})(?:_rev(\d+))?"
    match = re.match(pattern, nome_file)
    if not match:
        return {}

    ogg, cog, data_str, rev = match.groups()
    return {
        "oggetto": ogg,
        "referente": cog,
        "data_creazione": datetime.strptime(data_str, "%Y%m%d"),
        "revisione": int(rev) if rev else 0
    }


def trova_nome_unico(percorso, nome_base):
    """Trova un nome file unico incrementando la revisione se necessario."""
    import os
    revisione = 0
    nome_file = nome_base
    while os.path.exists(os.path.join(percorso, nome_file)):
        revisione += 1
        nome_file = nome_base.replace('.pdf', f'_rev{revisione}.pdf')
    return nome_file, revisione


def estrai_metadati_da_contenuto(testo: str) -> dict:
    """Estrae metadati dal contenuto tramite AI (placeholder, da integrare con modello AI).

    Args:
        testo (str): Testo del documento.

    Returns:
        dict: Metadati suggeriti da AI.
    """
    prompt = f"""Analizza il seguente contenuto e restituisci:\n- oggetto (una parola chiave)\n- referente (cognome)\n- reparto\n- revisione (numero)\n\nTEXTO:\n{testo[:3000]}\n"""
    # TODO: Integrare con chiamata al modello AI e parsing della risposta
    return {}  # Placeholder 