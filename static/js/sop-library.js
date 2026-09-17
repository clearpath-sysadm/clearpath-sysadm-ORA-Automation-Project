(function () {
  const root = document.getElementById('sop-library');
  if (!root) return;
  const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const meta = (label, value) => `<div class="sop-meta"><strong>${label}</strong>${escapeHtml(value)}</div>`;
  const metadata = sop => `<div class="sop-metadata">${meta('SOP ID', sop.sop_id)}${meta('Revision', sop.revision)}${meta('Status', sop.status)}${meta('Effective date', sop.effective_date)}${meta('Approval status', sop.approval_status)}${meta('Document status', sop.document_status)}</div>`;

  async function getJson(url) {
    const response = await fetch(url, {credentials: 'same-origin'});
    if (!response.ok) throw new Error(response.status === 503 ? 'The SOP library has not been generated.' : 'Unable to load the SOP library.');
    return response.json();
  }

  function renderCatalog(catalog) {
    root.innerHTML = `<div class="sop-grid">${catalog.map(sop => `<article class="sop-card">
      <h2>${escapeHtml(sop.title)}</h2>${metadata(sop)}
      <div class="sop-actions">
        <a class="sop-open" href="/help/${encodeURIComponent(sop.slug)}">Read in app</a>
        <a class="sop-download" href="/sops/${encodeURIComponent(sop.slug)}/download">Download PDF</a>
      </div>
    </article>`).join('')}</div>`;
  }

  function renderBlocks(blocks) {
    let output = '', listType = null;
    const closeList = () => { if (listType) { output += `</${listType}>`; listType = null; } };
    blocks.forEach(block => {
      if (block.type === 'ordered' || block.type === 'bullet') {
        const wanted = block.type === 'ordered' ? 'ol' : 'ul';
        if (listType !== wanted) { closeList(); output += `<${wanted}>`; listType = wanted; }
        output += `<li>${escapeHtml(block.text)}</li>`;
        return;
      }
      closeList();
      if (block.type === 'heading') output += `<h${block.level + 1} id="${escapeHtml(block.anchor)}">${escapeHtml(block.text)}</h${block.level + 1}>`;
      else if (block.type === 'warning') output += `<div class="sop-warning" role="note">${escapeHtml(block.text)}</div>`;
      else if (block.type === 'paragraph') output += `<p>${escapeHtml(block.text)}</p>`;
      else if (block.type === 'table') output += `<div class="sop-table-wrap"><table><thead><tr>${block.rows[0].map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr></thead><tbody>${block.rows.slice(1).map(row => `<tr>${row.map(c => `<td>${escapeHtml(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    });
    closeList();
    return output;
  }

  function renderDocument(sop) {
    const headings = sop.blocks.filter(block => block.type === 'heading');
    root.innerHTML = `<a class="sop-back" href="/help.html">← All SOPs</a><div class="sop-reader">
      <nav class="sop-toc" aria-label="Table of contents"><strong>Contents</strong>${headings.map(h => `<a href="#${escapeHtml(h.anchor)}">${escapeHtml(h.text)}</a>`).join('')}</nav>
      <article class="sop-document"><h1>${escapeHtml(sop.title)}</h1>${metadata(sop)}
        <div class="sop-actions"><a class="sop-download" href="/sops/${encodeURIComponent(sop.slug)}/download">Download this revision as PDF</a></div>
        ${renderBlocks(sop.blocks)}
      </article></div>`;
  }

  const match = window.location.pathname.match(/^\/help\/([a-z0-9-]+)$/);
  (match ? getJson(`/api/sops/${match[1]}`).then(renderDocument) : getJson('/api/sops').then(renderCatalog))
    .catch(error => { root.innerHTML = `<div class="card"><strong>Help library unavailable.</strong><p>${escapeHtml(error.message)}</p></div>`; });
}());