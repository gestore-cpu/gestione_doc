import qrcode
import os

def generate_qr_for_document(document_id: int, filename: str, metadata: dict, base_url: str = "https://docs.mercurysurgelati.org/view") -> str:
    """
    Genera un QR code PNG per il documento e lo salva su disco. Ritorna il path del file generato.
    """
    qr_data = {
        "id": document_id,
        "filename": filename,
        "url": f"{base_url}/{document_id}",
        "area": metadata.get("area"),
        "azienda": metadata.get("azienda"),
        "reparti": metadata.get("reparti", [])
    }

    qr = qrcode.make(str(qr_data))
    qr_dir = "static/qrcodes"
    os.makedirs(qr_dir, exist_ok=True)

    qr_path = os.path.join(qr_dir, f"{document_id}.png")
    qr.save(qr_path)
    return qr_path 