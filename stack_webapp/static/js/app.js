const agentText = document.getElementById('agent-text');
const outputTitle = document.getElementById('output-title');
const outputArea = document.getElementById('output-area');
const debugArea = document.getElementById('debug-area');
const debugShell = document.getElementById('debug-shell');
const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const meetingPrepBtn = document.getElementById('meeting-prep-btn');
const myCompaniesBtn = document.getElementById('my-companies-btn');
const oppInsightsBtn = document.getElementById('opp-insights-btn');
const oppSearchBtn = document.getElementById('opp-search-btn');

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function setAgentText(text) {
  agentText.textContent = text || '';
}

function setLoggedIn(isLoggedIn) {
  loginBtn.disabled = isLoggedIn;
  loginBtn.textContent = isLoggedIn ? 'Connected' : 'Log In';
  logoutBtn.disabled = !isLoggedIn;
  meetingPrepBtn.disabled = !isLoggedIn;
  myCompaniesBtn.disabled = !isLoggedIn;
  oppInsightsBtn.disabled = true;
  oppSearchBtn.disabled = true;
}

function renderMessage(title, message) {
  outputTitle.textContent = title;
  outputArea.innerHTML = `<div class="stack-output-message">${escapeHtml(message)}</div>`;
}

function renderTableHtml(columns, rows) {
  if (!rows || rows.length === 0) {
    return '<div class="stack-output-message">No rows returned.</div>';
  }
  const thead = `<thead><tr>${columns.map(col => `<th>${escapeHtml(col)}</th>`).join('')}</tr></thead>`;
  const tbody = `<tbody>${rows.map(row => `<tr>${columns.map(col => `<td>${escapeHtml(row[col] ?? '')}</td>`).join('')}</tr>`).join('')}</tbody>`;
  return `<div class="stack-table-wrap"><table class="stack-table">${thead}${tbody}</table></div>`;
}

function renderTable(title, columns, rows) {
  outputTitle.textContent = title;
  outputArea.innerHTML = renderTableHtml(columns, rows);
}

function renderLoginPreload(title, preloadText, columns, rows) {
  outputTitle.textContent = title;
  outputArea.innerHTML = `
    <div class="stack-preload-text">${escapeHtml(preloadText || '')}</div>
    <div style="margin:18px 0 8px 0; font-weight:600;">my_meetings_seed_df</div>
    ${renderTableHtml(columns || [], rows || [])}`;
}

function renderCompaniesBrowser(title, rows, tokenUserId) {
  outputTitle.textContent = title;
  if (!rows || rows.length === 0) {
    outputArea.innerHTML = `<div class="stack-output-message">No companies found where hubspot_owner_id matches token user id ${escapeHtml(tokenUserId)}.</div>`;
    return;
  }

  const listHtml = rows.map((row, idx) => `
    <div class="stack-browser-row">
      <button class="stack-open-btn" data-company-index="${idx}" type="button">Open</button>
      <div class="stack-browser-detail">
        <div><b>${escapeHtml(row.company_label || row.name || row.id || '')}</b></div>
        <div>Website: ${escapeHtml(row.website_display || row.website || row.homepage_url || '')}</div>
      </div>
    </div>`).join('');

  outputArea.innerHTML = `
    <div class="stack-browser-list">${listHtml}</div>
    <div class="stack-browser-box">
      <div style="margin:0 0 8px 0; font-weight:600;">Selected Company Site</div>
      <div id="company-detail" class="stack-browser-card">Click Open to load the selected company site below.</div>
    </div>`;

  const detail = document.getElementById('company-detail');
  outputArea.querySelectorAll('[data-company-index]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const row = rows[Number(btn.dataset.companyIndex)];
      const label = row.company_label || row.name || row.id || '';
      const url = row.homepage_url || '';
      if (!url) {
        detail.innerHTML = `No homepage URL available for ${escapeHtml(label)}.`;
        return;
      }
      detail.innerHTML = `
        <div style="font-weight:600; margin:0 0 8px 0;">${escapeHtml(label)}</div>
        <div style="margin:0 0 8px 0;"><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(url)}</a></div>
        <iframe src="${escapeHtml(url)}" style="width:100%; height:520px; border:1px solid #d8d8d8; border-radius:8px; background:white;"></iframe>`;
    });
  });
}

function renderMeetingsBrowser(title, rows) {
  outputTitle.textContent = title;
  if (!rows || rows.length === 0) {
    outputArea.innerHTML = '<div class="stack-output-message">No meetings matched my_company_ids.</div>';
    return;
  }

  const listHtml = rows.map((row, idx) => {
    const rowTitle = row.matched_company_names || `Meeting ${row.id || ''}`;
    return `
      <div class="stack-browser-row">
        <button class="stack-open-btn" data-meeting-index="${idx}" type="button">Open</button>
        <div class="stack-browser-detail">
          <div><b>${escapeHtml(rowTitle)}</b></div>
          <div>Meeting ID: ${escapeHtml(row.id || '')}</div>
          <div>Start: ${escapeHtml(row.hs_meeting_start_time || '')}</div>
        </div>
      </div>`;
  }).join('');

  outputArea.innerHTML = `
    <div class="stack-browser-list">${listHtml}</div>
    <div class="stack-browser-box">
      <div style="margin:0 0 8px 0; font-weight:600;">Selected Meeting Details</div>
      <div id="meeting-detail" class="stack-browser-card">Click Open to load meeting details below.</div>
    </div>`;

  const detail = document.getElementById('meeting-detail');
  outputArea.querySelectorAll('[data-meeting-index]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const row = rows[Number(btn.dataset.meetingIndex)];
      const rowTitle = row.matched_company_names || `Meeting ${row.id || ''}`;
      detail.innerHTML = `
        <div style="font-weight:600; margin:0 0 8px 0;">${escapeHtml(rowTitle)}</div>
        <div style="margin:0 0 6px 0;"><b>Meeting ID:</b> ${escapeHtml(row.id || '')}</div>
        <div style="margin:0 0 6px 0;"><b>Date/Time:</b> ${escapeHtml(row.hs_meeting_start_time || '')} - ${escapeHtml(row.hs_meeting_end_time || '')}</div>
        <div style="margin:0 0 6px 0;"><b>Associated Company IDs:</b> ${escapeHtml(row.associated_company_ids || '')}</div>
        <div style="margin:0 0 6px 0;"><b>Matched Company IDs:</b> ${escapeHtml(row.matched_company_ids || '')}</div>
        <div style="margin:10px 0 6px 0;"><b>Meeting Notes / Preview:</b></div>
        <div style="white-space:pre-wrap; border:1px solid #d8d8d8; border-radius:8px; padding:10px; background:white;">${escapeHtml(row.hs_body_preview || '')}</div>`;
    });
  });
}

function renderDebug(debug) {
  if (!debug) {
    if (debugShell) debugShell.style.display = 'none';
    if (debugArea) debugArea.textContent = 'Debug output will appear here after login.';
    return;
  }
  if (debugShell) debugShell.style.display = '';
  const summaryRows = (debug.probes || []).map(p => ({
    label: p.label || '',
    status_code: p.status_code ?? '',
    ok: p.ok ?? false,
    url: p.url || '',
  }));
  const ownerIds = (debug.owner_ids || []).map(v => ({ company_owner_id: v }));
  const renderSimpleTable = (rows) => {
    if (!rows || rows.length === 0) return '<div class="stack-output-message">No rows returned.</div>';
    const cols = Object.keys(rows[0]);
    const head = `<thead><tr>${cols.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr></thead>`;
    const body = `<tbody>${rows.map(r => `<tr>${cols.map(c => `<td>${escapeHtml(r[c] ?? '')}</td>`).join('')}</tr>`).join('')}</tbody>`;
    return `<div class="stack-table-wrap"><table class="stack-table">${head}${body}</table></div>`;
  };

  let html = '<h4 style="margin:0 0 10px 0;">DEBUG_USERID</h4>';
  html += '<div style="margin:0 0 8px 0; font-weight:600;">Token / Portal Identity</div>' + renderSimpleTable([debug.login_info || {}]);
  html += '<div style="margin:14px 0 8px 0; font-weight:600;">Company Owner IDs Found</div>' + renderSimpleTable(ownerIds);
  html += '<div style="margin:14px 0 8px 0; font-weight:600;">Probe Summary</div>' + renderSimpleTable(summaryRows);
  (debug.probes || []).forEach((p) => {
    const payload = p.payload || {};
    const rows = Array.isArray(payload.results) ? payload.results.slice(0, 10) : [payload];
    html += `<div style="margin:14px 0 6px 0; font-weight:600;">${escapeHtml(p.label || '')} — status ${escapeHtml(p.status_code ?? '')} — ok=${escapeHtml(p.ok ?? false)}</div>`;
    html += renderSimpleTable(rows);
  });
  debugArea.innerHTML = html;
}

async function runAction(url, pendingText, pendingTitle, options = {}) {
  setAgentText(pendingText);
  renderMessage(pendingTitle, 'Working...');
  const response = await fetch(url, options);
  const payload = await response.json();
  setAgentText(payload.agent_text || 'Done.');

  if (payload.type === 'table') {
    renderTable(payload.title || pendingTitle, payload.columns || [], payload.rows || []);
  } else if (payload.type === 'login_preload') {
    renderLoginPreload(payload.title || pendingTitle, payload.preload_text || '', payload.columns || [], payload.rows || []);
  } else if (payload.type === 'companies_browser') {
    renderCompaniesBrowser(payload.title || pendingTitle, payload.rows || [], payload.token_user_id || '');
  } else if (payload.type === 'meetings_browser') {
    renderMeetingsBrowser(payload.title || pendingTitle, payload.rows || []);
  } else {
    renderMessage(payload.title || pendingTitle, payload.message || 'No response returned.');
  }

  renderDebug(payload.debug || null);

  if (!response.ok) throw new Error(payload.message || 'Request failed.');
  return payload;
}

loginBtn.addEventListener('click', async () => {
  try {
    const payload = await runAction('/api/login', 'Connecting to HubSpot...', 'Log In', { method: 'POST' });
    if (payload) setLoggedIn(true);
  } catch (error) {
    setLoggedIn(false);
    console.error(error);
  }
});

logoutBtn.addEventListener('click', async () => {
  try {
    await runAction('/api/logout', 'Logging out...', 'Logout', { method: 'POST' });
  } finally {
    setLoggedIn(false);
    renderDebug(null);
  }
});

meetingPrepBtn.addEventListener('click', () => {
  runAction('/api/meeting-prep', 'Preparing meeting summary...', 'Meeting Prep').catch(console.error);
});

myCompaniesBtn.addEventListener('click', () => {
  runAction('/api/my-companies', 'Loading My Companies...', 'My Companies').catch(console.error);
});

oppInsightsBtn.addEventListener('click', () => {
  runAction('/api/opp-insights', 'Running Opportunity Insights...', 'Opp Insights').catch(console.error);
});

oppSearchBtn.addEventListener('click', () => {
  runAction('/api/opp-search', 'Searching opportunities...', 'Opp Search').catch(console.error);
});

setLoggedIn(false);
