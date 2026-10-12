'use strict';
const $ = (selector) => document.querySelector(selector);
const state = {mode: 'sample', models: [], busy: false, session: null, example: null};
const labels = {A: 'Builder A is proposing a solution', B: 'Builder B is exploring another approach', critique: 'The skeptic is checking both proposals', judgment: 'The judge is weighing the evidence'};
const escapeHTML = (value) => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const list = (items, tag = 'ul') => `<${tag}>${items.map(item => `<li>${escapeHTML(item)}</li>`).join('')}</${tag}>`;
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

function showError(message) { $('#error-box').textContent = message; $('#error-box').hidden = false; }
function countChars() { $('#char-count').textContent = `${$('#issue').value.length.toLocaleString()} / 8,000`; }
function status(message, active = false) {
  $('#run-status').replaceChildren();
  const dot = document.createElement('span'); dot.className = `status-dot${active ? ' online' : ''}`;
  $('#run-status').append(dot, document.createTextNode(message));
}
function syncControls() {
  document.querySelectorAll('[data-mode]').forEach(button => {
    button.classList.toggle('active', button.dataset.mode === state.mode);
    button.setAttribute('aria-pressed', String(button.dataset.mode === state.mode));
    button.disabled = state.busy;
  });
  $('#issue').disabled = state.busy || state.mode === 'sample';
  $('#context').disabled = state.busy || state.mode === 'sample';
  $('#model').disabled = state.busy || state.mode === 'sample' || !state.models.length;
  $('#run-button').disabled = state.busy || (state.mode === 'live' && !state.models.length);
  $('#run-button').textContent = state.busy ? 'Arena in progress…' : 'Enter the arena →';
  $('#load-example').disabled = state.busy;
  $('#refresh-models').disabled = state.busy;
  $('#export-button').disabled = !state.session || state.busy;
  $('#export-side').disabled = !state.session || state.busy;
  $('#mode-notice').textContent = state.mode === 'sample'
    ? 'Sample replay uses a fixed password-reset challenge and curated responses. No AI inference runs.'
    : 'Runs four inference calls on your selected Ollama model. On a laptop, a full debate may take several minutes.';
}
function renderModels() {
  const previous = $('#model').value;
  $('#model').replaceChildren();
  const names = state.mode === 'sample' ? ['Curated sample'] : state.models.length ? state.models : ['Connect Ollama to run live'];
  names.forEach(name => { const option = document.createElement('option'); option.value = state.mode === 'sample' ? '' : name; option.textContent = name; $('#model').append(option); });
  if (state.mode === 'live' && state.models.includes(previous)) $('#model').value = previous;
  syncControls();
}
async function refreshModels() {
  $('#connection-label').textContent = 'Checking Ollama';
  try {
    const response = await fetch('/api/models');
    if (!response.ok) throw new Error('Model discovery failed');
    const data = await response.json();
    state.models = data.models || [];
    const ready = data.available && state.models.length > 0;
    $('#connection-dot').classList.toggle('online', ready);
    $('#connection-label').textContent = ready ? 'Ollama connected' : data.available ? 'No models installed' : 'Ollama not connected';
    $('#connection-detail').textContent = ready ? `${state.models.length} model${state.models.length === 1 ? '' : 's'} available` : 'Sample replay is available';
    $('#connection-box')?.setAttribute('title', data.error || '');
    if (state.mode === 'live' && !ready) showError(data.error || 'Pull an instruction model with Ollama, then refresh the connection.');
  } catch (error) {
    state.models = []; $('#connection-label').textContent = 'Connection unavailable'; $('#connection-dot').classList.remove('online');
  }
  renderModels();
}
async function loadExample() {
  if (!state.example) {
    const response = await fetch('/api/example');
    if (!response.ok) throw new Error('Could not load the example challenge.');
    state.example = await response.json();
  }
  $('#issue').value = state.example.issue;
  $('#context').value = state.example.context;
  countChars();
}
function resetResults() {
  state.session = null;
  $('#error-box').hidden = true;
  ['critique-card','verdict-card','trace-panel','session-banner'].forEach(id => $(`#${id}`).hidden = true);
  $('#trace-content').replaceChildren();
  document.querySelectorAll('[data-step]').forEach(step => step.classList.remove('running','done'));
  for (const candidate of ['A','B']) $(`#proposal-${candidate}`).innerHTML = '<div class="empty-state"><div class="empty-glyph">⌁</div><h4>Ready for a new perspective.</h4><p>Waiting for this builder’s turn.</p></div>';
}
function renderProposal(event) {
  const {result, stage, metrics} = event;
  $(`#proposal-${stage}`).innerHTML = `<h4>${escapeHTML(result.title)}</h4><p>${escapeHTML(result.summary)}</p><h5>THE APPROACH</h5>${list(result.steps,'ol')}<h5>TRADEOFFS</h5>${list(result.tradeoffs)}<div class="stage-metric">${state.mode === 'sample' ? 'Curated sample response' : `${metrics.seconds}s · ${metrics.output_tokens ?? '—'} output tokens`}</div>`;
}
function renderCritique(result) {
  $('#critique-card').hidden = false;
  $('#critique-content').innerHTML = ['A','B'].map(candidate => `<div><h4>CANDIDATE ${candidate}</h4><h5>Pressure points</h5>${list(result[candidate].risks)}<h5>Tests to write</h5>${list(result[candidate].tests)}</div>`).join('');
}
function renderVerdict(result) {
  $('#verdict-card').hidden = false;
  $('#winner-title').textContent = result.winner === 'tie' ? 'An even match. Look closer.' : `Candidate ${result.winner} takes the edge.`;
  $('#verdict-badge').textContent = state.mode === 'sample' ? 'SAMPLE VERDICT' : 'MODEL ASSESSMENT';
  $('#verdict-reason').textContent = result.reasoning;
  const criteria = [['correctness','Correctness','40%'],['security','Security','35%'],['testability','Testability','25%']];
  $('#score-table').innerHTML = `<table><caption class="muted">Rubric scores · out of 10</caption><thead><tr><th scope="col">CRITERION</th><th scope="col">WEIGHT</th><th scope="col">A</th><th scope="col">B</th></tr></thead><tbody>${criteria.map(([key,label,weight]) => `<tr><td>${label}</td><td>${weight}</td><td>${result.scores.A[key]}</td><td>${result.scores.B[key]}</td></tr>`).join('')}<tr><td>Weighted total</td><td>100%</td><td class="${result.winner === 'A' ? 'score-winner' : ''}">${result.totals.A.toFixed(2)}</td><td class="${result.winner === 'B' ? 'score-winner' : ''}">${result.totals.B.toFixed(2)}</td></tr></tbody></table>`;
  $('#next-steps').innerHTML = result.next_steps.map(item => `<li>${escapeHTML(item)}</li>`).join('');
}
function addTrace(event) {
  $('#trace-panel').hidden = false;
  const section = document.createElement('section');
  const title = document.createElement('h4'); title.textContent = `Stage: ${event.stage}`;
  const pre = document.createElement('pre'); pre.textContent = JSON.stringify({system_prompt:event.system_prompt, prompt:JSON.parse(event.prompt), raw_response:event.raw_response, metrics:event.metrics},null,2);
  section.append(title,pre); $('#trace-content').append(section);
}
async function handleEvent(event) {
  if (event.type === 'error') throw new Error(event.error);
  if (event.type === 'session') {
    $('#session-banner').hidden = false;
    $('#session-banner').textContent = event.session.mode === 'sample' ? 'SAMPLE REPLAY — fixed challenge, curated responses, no model inference.' : `LIVE RUN — ${event.session.model} · session ${event.session.id.slice(0,8)}`;
  } else if (event.type === 'stage_start') {
    status(labels[event.stage],true);
    $(`[data-step="${event.stage}"]`).classList.add('running');
    if (['A','B'].includes(event.stage)) $(`#proposal-${event.stage}`).innerHTML = `<div class="loading-copy"><span class="spinner"></span>${state.mode === 'sample' ? 'Replaying sample proposal…' : 'Thinking through the problem…'}</div>`;
    if (state.mode === 'sample') await sleep(550);
  } else if (event.type === 'stage_complete') {
    const step = $(`[data-step="${event.stage}"]`); step.classList.remove('running'); step.classList.add('done');
    if (['A','B'].includes(event.stage)) renderProposal(event);
    if (event.stage === 'critique') renderCritique(event.result);
    if (event.stage === 'judgment') renderVerdict(event.result);
    addTrace(event);
  } else if (event.type === 'complete') {
    state.session = event.session;
    status(state.mode === 'sample' ? 'Sample replay complete' : 'Debate complete',true);
  }
}
async function runArena(event) {
  event.preventDefault();
  if (state.busy) return;
  resetResults(); state.busy = true; syncControls();
  try {
    const response = await fetch('/api/arena',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:state.mode,issue:$('#issue').value,context:$('#context').value,model:$('#model').value})});
    if (!response.ok) { const error = await response.json(); throw new Error(error.error || `Request failed (${response.status})`); }
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let pending = '';
    while (true) {
      const {done,value} = await reader.read();
      pending += decoder.decode(value || new Uint8Array(),{stream:!done});
      let newline;
      while ((newline = pending.indexOf('\n')) >= 0) {
        const line = pending.slice(0,newline); pending = pending.slice(newline+1);
        if (line.trim()) await handleEvent(JSON.parse(line));
      }
      if (done) break;
    }
    if (pending.trim()) await handleEvent(JSON.parse(pending));
    if (!state.session) throw new Error('The run ended before a verdict was completed. Please retry.');
  } catch (error) {
    showError(error.message || 'The arena could not finish. Please retry.'); status('Run interrupted');
    document.querySelectorAll('.pipeline .running').forEach(step => step.classList.remove('running'));
    document.querySelectorAll('.loading-copy').forEach(node => {node.textContent='This stage could not finish. See the error above.';});
  } finally {state.busy = false; syncControls();}
}
function exportSession() {
  if (!state.session) return;
  const blob = new Blob([JSON.stringify(state.session,null,2)],{type:'application/json'});
  const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
  anchor.href = url; anchor.download = `repoarena-${state.session.mode}-${state.session.id.slice(0,8)}.json`;
  document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url),1000);
}
$('#arena-form').addEventListener('submit',runArena);
$('#issue').addEventListener('input',countChars);
$('#load-example').addEventListener('click',() => loadExample().catch(error => showError(error.message)));
$('#refresh-models').addEventListener('click',refreshModels);
$('#export-button').addEventListener('click',exportSession);
$('#export-side').addEventListener('click',exportSession);
document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click',async () => {
  state.mode = button.dataset.mode; $('#error-box').hidden = true; renderModels();
  if (state.mode === 'sample') {try {await loadExample();} catch(error) {showError(error.message);}}
  else if (!state.models.length) showError("Start Ollama next to this app, run 'ollama pull qwen2.5:3b', then refresh the connection. Cloud localhost cannot reach Ollama on your laptop.");
}));
syncControls();
loadExample().catch(error => showError(error.message));
refreshModels();
