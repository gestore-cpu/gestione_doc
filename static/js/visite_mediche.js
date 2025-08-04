// 🏥 Gestione Visite Mediche - JavaScript
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 Visite Mediche JS caricato");
  
  // Inizializza componenti
  initFormHandlers();
  initFilters();
  initToast();
});

// ===== GESTIONE FORM =====
function initFormHandlers() {
  const form = document.getElementById('formVisita');
  const modal = document.getElementById('modalVisita');
  
  // Reset form quando si apre per nuova visita
  document.querySelector('[data-bs-target="#modalVisita"]').addEventListener('click', () => {
    resetForm();
    document.getElementById('modalTitle').textContent = '➕ Nuova Visita Medica';
  });
  
  // Gestione submit form
  form.addEventListener('submit', handleFormSubmit);
  
  // Validazione date
  document.getElementById('data_visita').addEventListener('change', validateDates);
  document.getElementById('scadenza').addEventListener('change', validateDates);
}

function resetForm() {
  document.getElementById('formVisita').reset();
  document.getElementById('visitaId').value = '';
  document.getElementById('modalTitle').textContent = '➕ Nuova Visita Medica';
}

function validateDates() {
  const dataVisita = document.getElementById('data_visita').value;
  const scadenza = document.getElementById('scadenza').value;
  
  if (dataVisita && scadenza && dataVisita > scadenza) {
    showToast('⚠️ Attenzione', 'La data di scadenza deve essere successiva alla data visita', 'warning');
    document.getElementById('scadenza').value = '';
  }
}

async function handleFormSubmit(e) {
  e.preventDefault();
  
  const form = e.target;
  const formData = new FormData(form);
  const visitaId = formData.get('visitaId');
  
  // Mostra spinner
  const submitBtn = form.querySelector('button[type="submit"]');
  const submitText = document.getElementById('submitText');
  const submitSpinner = document.getElementById('submitSpinner');
  
  submitText.classList.add('d-none');
  submitSpinner.classList.remove('d-none');
  submitBtn.disabled = true;
  
  try {
    const method = visitaId ? 'PATCH' : 'POST';
    const url = visitaId ? `/visite_mediche/${visitaId}` : '/visite_mediche';
    
    const response = await fetch(url, {
      method: method,
      body: formData
    });
    
    if (response.ok) {
      const result = await response.json();
      showToast('✅ Successo', result.message || 'Visita salvata con successo', 'success');
      
      // Chiudi modal e ricarica pagina
      const modal = bootstrap.Modal.getInstance(document.getElementById('modalVisita'));
      modal.hide();
      
      setTimeout(() => location.reload(), 1000);
    } else {
      const error = await response.json();
      showToast('❌ Errore', error.message || 'Errore nel salvataggio', 'error');
    }
  } catch (error) {
    console.error('Errore form:', error);
    showToast('❌ Errore', 'Errore di connessione', 'error');
  } finally {
    // Nascondi spinner
    submitText.classList.remove('d-none');
    submitSpinner.classList.add('d-none');
    submitBtn.disabled = false;
  }
}

// ===== CRUD OPERATIONS =====
async function modificaVisita(id) {
  try {
    const response = await fetch(`/visite_mediche/${id}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });
    
    if (response.ok) {
      const visita = await response.json();
      populateForm(visita);
      document.getElementById('modalTitle').textContent = '✏️ Modifica Visita Medica';
      
      const modal = new bootstrap.Modal(document.getElementById('modalVisita'));
      modal.show();
    } else {
      showToast('❌ Errore', 'Impossibile caricare i dati della visita', 'error');
    }
  } catch (error) {
    console.error('Errore caricamento visita:', error);
    showToast('❌ Errore', 'Errore di connessione', 'error');
  }
}

function populateForm(visita) {
  document.getElementById('visitaId').value = visita.id;
  document.getElementById('user_id').value = visita.user_id;
  document.getElementById('ruolo').value = visita.ruolo;
  document.getElementById('tipo_visita').value = visita.tipo_visita;
  document.getElementById('data_visita').value = visita.data_visita;
  document.getElementById('scadenza').value = visita.scadenza;
  document.getElementById('esito').value = visita.esito;
  document.getElementById('note').value = visita.note || '';
}

async function eliminaVisita(id) {
  if (!confirm('🗑️ Sei sicuro di voler eliminare questa visita medica?')) {
    return;
  }
  
  try {
    const response = await fetch(`/visite_mediche/${id}`, {
      method: 'DELETE'
    });
    
    if (response.ok) {
      const result = await response.json();
      showToast('✅ Eliminata', result.message || 'Visita eliminata con successo', 'success');
      
      // Rimuovi riga dalla tabella
      const row = document.querySelector(`tr[data-visita-id="${id}"]`);
      if (row) {
        row.remove();
      }
    } else {
      const error = await response.json();
      showToast('❌ Errore', error.message || 'Errore nell\'eliminazione', 'error');
    }
  } catch (error) {
    console.error('Errore eliminazione:', error);
    showToast('❌ Errore', 'Errore di connessione', 'error');
  }
}

async function scaricaCertificato(id) {
  try {
    const response = await fetch(`/visite_mediche/${id}/certificato`);
    
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `certificato_visita_${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      showToast('📥 Download', 'Certificato scaricato con successo', 'success');
    } else {
      showToast('❌ Errore', 'Impossibile scaricare il certificato', 'error');
    }
  } catch (error) {
    console.error('Errore download:', error);
    showToast('❌ Errore', 'Errore di connessione', 'error');
  }
}

async function visualizzaDettagli(id) {
  try {
    const response = await fetch(`/visite_mediche/${id}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });
    
    if (response.ok) {
      const visita = await response.json();
      showDettagliModal(visita);
    } else {
      showToast('❌ Errore', 'Impossibile caricare i dettagli', 'error');
    }
  } catch (error) {
    console.error('Errore dettagli:', error);
    showToast('❌ Errore', 'Errore di connessione', 'error');
  }
}

function showDettagliModal(visita) {
  const modalBody = document.getElementById('dettagliVisita');
  
  modalBody.innerHTML = `
    <div class="row">
      <div class="col-md-6">
        <h6>👤 Informazioni Utente</h6>
        <p><strong>Nome:</strong> ${visita.user?.username || 'N/A'}</p>
        <p><strong>Email:</strong> ${visita.user?.email || 'N/A'}</p>
        <p><strong>Ruolo:</strong> ${visita.ruolo}</p>
      </div>
      <div class="col-md-6">
        <h6>🏥 Dettagli Visita</h6>
        <p><strong>Tipo:</strong> ${visita.tipo_visita}</p>
        <p><strong>Esito:</strong> ${visita.esito}</p>
        <p><strong>Stato:</strong> <span class="badge ${visita.badge_class}">${visita.status_display}</span></p>
      </div>
    </div>
    <div class="row mt-3">
      <div class="col-md-6">
        <h6>📅 Date</h6>
        <p><strong>Data Visita:</strong> ${formatDate(visita.data_visita)}</p>
        <p><strong>Scadenza:</strong> ${formatDate(visita.scadenza)}</p>
        <p><strong>Giorni Rimanenti:</strong> ${visita.days_until_expiry}</p>
      </div>
      <div class="col-md-6">
        <h6>📄 Certificato</h6>
        <p><strong>Presente:</strong> ${visita.certificato_filename ? 'Sì' : 'No'}</p>
        ${visita.certificato_filename ? `<button class="btn btn-sm btn-outline-info" onclick="scaricaCertificato(${visita.id})">📥 Scarica</button>` : ''}
      </div>
    </div>
    ${visita.note ? `
    <div class="row mt-3">
      <div class="col-12">
        <h6>📝 Note</h6>
        <p>${visita.note}</p>
      </div>
    </div>
    ` : ''}
  `;
  
  const modal = new bootstrap.Modal(document.getElementById('modalDettagli'));
  modal.show();
}

// ===== FILTRI AVANZATI =====
function initFilters() {
  // Applica filtri con debounce
  let timeout;
  document.getElementById('filtroRuolo').addEventListener('input', () => {
    clearTimeout(timeout);
    timeout = setTimeout(applicaFiltri, 300);
  });
  
  document.getElementById('filtroTipo').addEventListener('input', () => {
    clearTimeout(timeout);
    timeout = setTimeout(applicaFiltri, 300);
  });
  
  document.getElementById('filtroStato').addEventListener('change', applicaFiltri);
}

function applicaFiltri() {
  const stato = document.getElementById('filtroStato').value;
  const ruolo = document.getElementById('filtroRuolo').value.toLowerCase();
  const tipo = document.getElementById('filtroTipo').value.toLowerCase();
  
  const rows = document.querySelectorAll('#tabellaVisite tbody tr');
  
  rows.forEach(row => {
    const statoCell = row.querySelector('td:nth-child(6) .badge').textContent;
    const ruoloCell = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
    const tipoCell = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
    
    let show = true;
    
    // Filtro stato
    if (stato && !statoCell.includes(stato)) {
      show = false;
    }
    
    // Filtro ruolo
    if (ruolo && !ruoloCell.includes(ruolo)) {
      show = false;
    }
    
    // Filtro tipo
    if (tipo && !tipoCell.includes(tipo)) {
      show = false;
    }
    
    row.style.display = show ? '' : 'none';
  });
  
  showToast('🔍 Filtri', 'Filtri applicati', 'info');
}

function resetFiltri() {
  document.getElementById('filtroStato').value = '';
  document.getElementById('filtroRuolo').value = '';
  document.getElementById('filtroTipo').value = '';
  
  const rows = document.querySelectorAll('#tabellaVisite tbody tr');
  rows.forEach(row => row.style.display = '');
  
  showToast('🔄 Reset', 'Filtri resettati', 'info');
}

// ===== EXPORT CSV =====
async function exportCSV() {
  try {
    const response = await fetch('/visite_mediche/export/csv');
    
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `visite_mediche_${new Date().toISOString().slice(0,10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      showToast('📊 Export', 'CSV esportato con successo', 'success');
    } else {
      showToast('❌ Errore', 'Impossibile esportare il CSV', 'error');
    }
  } catch (error) {
    console.error('Errore export:', error);
    showToast('❌ Errore', 'Errore di connessione', 'error');
  }
}

// ===== TOAST NOTIFICHE =====
function initToast() {
  // Inizializza toast container se non esiste
  if (!document.querySelector('.toast-container')) {
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(toastContainer);
  }
}

function showToast(title, message, type = 'info') {
  const toastContainer = document.querySelector('.toast-container');
  
  // Rimuovi toast esistenti
  const existingToasts = toastContainer.querySelectorAll('.toast');
  existingToasts.forEach(toast => toast.remove());
  
  // Crea nuovo toast
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.setAttribute('role', 'alert');
  
  const bgClass = type === 'success' ? 'bg-success' : 
                  type === 'error' ? 'bg-danger' : 
                  type === 'warning' ? 'bg-warning' : 'bg-info';
  
  toast.innerHTML = `
    <div class="toast-header ${bgClass} text-white">
      <strong class="me-auto">${title}</strong>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
    </div>
    <div class="toast-body">
      ${message}
    </div>
  `;
  
  toastContainer.appendChild(toast);
  
  // Mostra toast
  const bsToast = new bootstrap.Toast(toast);
  bsToast.show();
  
  // Auto-hide dopo 5 secondi
  setTimeout(() => {
    bsToast.hide();
  }, 5000);
}

// ===== UTILITY FUNCTIONS =====
function formatDate(dateString) {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('it-IT');
}

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener('keydown', (e) => {
  // Ctrl+N per nuova visita
  if (e.ctrlKey && e.key === 'n') {
    e.preventDefault();
    document.querySelector('[data-bs-target="#modalVisita"]').click();
  }
  
  // Ctrl+F per focus sui filtri
  if (e.ctrlKey && e.key === 'f') {
    e.preventDefault();
    document.getElementById('filtroRuolo').focus();
  }
  
  // Escape per chiudere modali
  if (e.key === 'Escape') {
    const modals = document.querySelectorAll('.modal.show');
    modals.forEach(modal => {
      const bsModal = bootstrap.Modal.getInstance(modal);
      if (bsModal) bsModal.hide();
    });
  }
});

// ===== AUTO-REFRESH STATISTICHE =====
setInterval(() => {
  // Aggiorna statistiche ogni 5 minuti
  updateStatistiche();
}, 5 * 60 * 1000);

async function updateStatistiche() {
  try {
    const response = await fetch('/visite_mediche/statistiche');
    if (response.ok) {
      const stats = await response.json();
      
      // Aggiorna i contatori
      document.querySelector('.bg-primary h3').textContent = stats.statistiche.totali;
      document.querySelector('.bg-success h3').textContent = stats.statistiche.valide;
      document.querySelector('.bg-warning h3').textContent = stats.statistiche.in_scadenza;
      document.querySelector('.bg-danger h3').textContent = stats.statistiche.scadute;
    }
  } catch (error) {
    console.log('Errore aggiornamento statistiche:', error);
  }
} 