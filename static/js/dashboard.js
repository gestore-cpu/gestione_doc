document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('searchInput');
  const documentGrid = document.getElementById('documentGrid');

  // Ricerca documenti
  searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase();
    document.querySelectorAll('.document-card').forEach(card => {
      const text = card.innerText.toLowerCase();
      card.style.display = text.includes(query) ? '' : 'none';
    });
  });

  // QR da immagine
  const fileInput = document.getElementById('qrImageInput');
  const video = document.getElementById('qrVideo');

  fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const result = await QrScanner.scanImage(file, { returnDetailedScanResult: true });
    alert(`QR trovato: ${result.data}`);
  });

  // QR da webcam
  document.getElementById('startWebcam').addEventListener('click', () => {
    const scanner = new QrScanner(video, result => {
      alert(`QR scannerizzato: ${result}`);
      scanner.stop();
    });
    scanner.start();
  });
});
