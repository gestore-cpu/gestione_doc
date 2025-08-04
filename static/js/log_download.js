document.addEventListener("DOMContentLoaded", () => {
  applyFilters(); // Caricamento iniziale
});

function applyFilters() {
  const spinner = document.getElementById("spinner");
  const results = document.getElementById("log-results");
  const count = document.getElementById("result-count");

  // Mostra spinner
  spinner.classList.remove("d-none");
  results.innerHTML = "";

  const params = new URLSearchParams();
  ['start_date', 'end_date', 'utente', 'azienda', 'reparto'].forEach(id => {
    const val = document.getElementById(id).value;
    if (val) params.append(id, val);
  });

  fetch(`/admin/log_download?${params.toString()}&ajax=1`)
    .then(res => res.json())
    .then(data => {
      count.textContent = data.length;
      results.innerHTML = generateTable(data);
      spinner.classList.add("d-none");
    })
    .catch(err => {
      console.error("Errore fetch:", err);
      spinner.classList.add("d-none");
    });
}

function generateTable(data) {
  if (data.length === 0) return "<p>Nessun risultato trovato.</p>";

  let html = `<table class="table table-bordered table-hover">
    <thead>
      <tr>
        <th>Data</th><th>Utente</th><th>Azienda</th><th>Reparto</th><th>Documento</th><th>Protetta</th><th>IP</th>
      </tr>
    </thead><tbody>`;

  for (const row of data) {
    const protetta = row.protetta ? `<span class="badge bg-danger" title="Accesso protetto">Protetta</span>` : "";
    const expiredClass = row.scaduto ? 'table-warning' : '';
    html += `<tr class="${expiredClass}">
      <td>${row.timestamp}</td>
      <td>${row.user}</td>
      <td>${row.azienda}</td>
      <td>${row.reparto}</td>
      <td>${row.documento}</td>
      <td>${protetta}</td>
      <td>${row.ip || '-'}</td>
    </tr>`;
  }

  html += `</tbody></table>`;
  return html;
}

function resetFilters() {
  ['start_date', 'end_date', 'utente', 'azienda', 'reparto'].forEach(id => {
    document.getElementById(id).value = '';
  });
  applyFilters();
}

function exportCSV() {
  const params = new URLSearchParams();
  ['start_date', 'end_date', 'utente', 'azienda', 'reparto'].forEach(id => {
    const val = document.getElementById(id).value;
    if (val) params.append(id, val);
  });
  window.open(`/admin/log_download/export?${params.toString()}`, '_blank');
} 