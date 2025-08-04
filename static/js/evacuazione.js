// 🔐 Gestione Firma Digitale via Canvas
let canvas, ctx, drawing = false, currentProvaId = null;

function apriModaleFirma(provaId) {
    currentProvaId = provaId;
    canvas = document.getElementById("firmaCanvas");
    ctx = canvas.getContext("2d");
    
    // Configura canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    
    // Mostra modale
    $('#modalFirma').modal('show');
    
    // Eventi mouse
    canvas.onmousedown = startDrawing;
    canvas.onmouseup = stopDrawing;
    canvas.onmouseleave = stopDrawing;
    canvas.onmousemove = draw;
}

function startDrawing(e) {
    drawing = true;
    const rect = canvas.getBoundingClientRect();
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
}

function stopDrawing() {
    drawing = false;
}

function draw(e) {
    if (!drawing) return;
    
    const rect = canvas.getBoundingClientRect();
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.stroke();
}

function clearFirma() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function salvaFirma() {
    if (!currentProvaId) {
        alert("Errore: ID prova non valido");
        return;
    }
    
    // Converti canvas in blob
    canvas.toBlob(blob => {
        const formData = new FormData();
        formData.append("firma", blob, "firma.png");
        
        // Invia al server
        fetch(`/prove_evacuazione/prove-evacuazione/${currentProvaId}/firma`, {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.ok) {
                $('#modalFirma').modal('hide');
                location.reload();
            } else {
                alert("Errore nel salvataggio della firma: " + (data.error || "Errore sconosciuto"));
            }
        })
        .catch(error => {
            console.error("Errore:", error);
            alert("Errore nella comunicazione con il server");
        });
    }, 'image/png');
}

// 🤖 Gestione Firma AI Simulata
function attivaFirmaAI(provaId) {
    if (!confirm("Sei sicuro di voler attivare la firma AI simulata per questa prova?")) {
        return;
    }
    
    fetch(`/prove_evacuazione/prove-evacuazione/${provaId}/firma_ai`, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            location.reload();
        } else {
            alert("Errore nell'attivazione della firma AI");
        }
    })
    .catch(error => {
        console.error("Errore:", error);
        alert("Errore nella comunicazione con il server");
    });
}

// 📊 Gestione Audit Trail
function mostraAuditTrail(provaId) {
    window.location.href = `/prove_evacuazione/prove-evacuazione/${provaId}/audit`;
}

// 🗑️ Eliminazione Prova
function eliminaProva(provaId) {
    if (!confirm("Sei sicuro di voler eliminare questa prova di evacuazione? Questa azione non può essere annullata.")) {
        return;
    }
    
    fetch(`/prove_evacuazione/prove-evacuazione/${provaId}/elimina`, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.ok) {
            location.reload();
        } else {
            alert("Errore durante l'eliminazione della prova");
        }
    })
    .catch(error => {
        console.error("Errore:", error);
        alert("Errore nella comunicazione con il server");
    });
}

// 📄 Download PDF
function downloadPDF(provaId) {
    window.open(`/prove_evacuazione/prove-evacuazione/${provaId}/export/pdf`, '_blank');
}

// 📥 Download Firma
function downloadFirma(provaId) {
    window.open(`/prove_evacuazione/prove-evacuazione/${provaId}/download_firma`, '_blank');
}

// 📦 Esportazione Archivio PDF
function esportaArchivioPDF() {
    const checked = Array.from(document.querySelectorAll(".checkbox-prova:checked"))
        .map(cb => parseInt(cb.value));
    
    if (checked.length === 0) {
        alert("Seleziona almeno una prova per esportare l'archivio PDF.");
        return;
    }
    
    if (checked.length > 50) {
        if (!confirm(`Stai per esportare ${checked.length} prove. Questo potrebbe richiedere molto tempo. Continuare?`)) {
            return;
        }
    }
    
    // Mostra indicatore di caricamento
    const loadingBtn = document.getElementById('btnEsportaArchivio');
    if (loadingBtn) {
        loadingBtn.disabled = true;
        loadingBtn.innerHTML = '⏳ Generazione archivio...';
    }
    
    fetch("/prove_evacuazione/prove-evacuazione/archivio_pdf", {
        method: "POST",
        headers: { 
            "Content-Type": "application/json" 
        },
        body: JSON.stringify({ prove_ids: checked })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Errore durante l\'esportazione');
            });
        }
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Archivio_Prove_Evacuazione_${new Date().toISOString().slice(0,10)}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        // Mostra messaggio di successo
        alert(`✅ Archivio PDF esportato con successo!\nContiene ${checked.length} prove di evacuazione.`);
    })
    .catch(error => {
        console.error("Errore:", error);
        alert("❌ Errore durante l'esportazione dell'archivio: " + error.message);
    })
    .finally(() => {
        // Ripristina pulsante
        if (loadingBtn) {
            loadingBtn.disabled = false;
            loadingBtn.innerHTML = '📦 Esporta Archivio PDF';
        }
    });
}

// ✅ Gestione checkbox selezione
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllProve');
    const proveCheckboxes = document.querySelectorAll('.checkbox-prova');
    
    proveCheckboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    
    updateExportButton();
}

function updateExportButton() {
    const checkedCount = document.querySelectorAll('.checkbox-prova:checked').length;
    const exportBtn = document.getElementById('btnEsportaArchivio');
    
    if (exportBtn) {
        if (checkedCount > 0) {
            exportBtn.disabled = false;
            exportBtn.innerHTML = `📦 Esporta Archivio PDF (${checkedCount})`;
        } else {
            exportBtn.disabled = true;
            exportBtn.innerHTML = '📦 Esporta Archivio PDF';
        }
    }
}

// Inizializzazione quando il documento è pronto
document.addEventListener('DOMContentLoaded', function() {
    // Aggiungi event listener per modale
    $('#modalFirma').on('hidden.bs.modal', function () {
        currentProvaId = null;
        if (canvas) {
            canvas.onmousedown = null;
            canvas.onmouseup = null;
            canvas.onmouseleave = null;
            canvas.onmousemove = null;
        }
    });
    
    // Event listener per checkbox
    document.querySelectorAll('.checkbox-prova').forEach(checkbox => {
        checkbox.addEventListener('change', updateExportButton);
    });
    
    // Event listener per select all
    const selectAllCheckbox = document.getElementById('selectAllProve');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', toggleSelectAll);
    }
    
    // Tooltip per i pulsanti
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Inizializza stato pulsante export
    updateExportButton();
}); 