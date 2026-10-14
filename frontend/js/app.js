import { renderShop, bindShop } from './shop.js';
import { api, get, post, patch, del, auth } from './api.js';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
const usd = n => (Number(n) || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
const list = d => Array.isArray(d) ? d : (d && Object.values(d).find(Array.isArray)) || [];
const first = (o, ...k) => { for (const x of k) if (o?.[x] != null) return o[x]; };
const toast = (m, bad) => { const t = $('#toast'); t.textContent = m; t.className = 'show' + (bad ? ' bad' : ''); clearTimeout(t._t); t._t = setTimeout(() => t.className = '', 3500); };
const skeleton = '<div class="grid"><div class="card sk"></div><div class="card sk"></div><div class="card sk"></div></div>';
const empty = (t, s) => `<div class="card empty"><b>${esc(t)}</b><p>${esc(s || '')}</p></div>`;
const missing = what => `<div class="card note">Needs backend support: ${esc(what)}</div>`;

/* ---------- charts (inline SVG, responsive) ---------- */
const COLORS = ['#8b5cf6','#a78bfa','#c4b5fd','#6d28d9','#38bdf8','#f472b6','#34d399'];
function donut(items) {
  const total = items.reduce((a, i) => a + i.v, 0); if (!total) return '<p class="muted">No spending in this period.</p>';
  let off = 0; const r = 15.9;
  const arcs = items.map((i, n) => { const p = i.v / total * 100; const s = `<circle r="${r}" cx="18" cy="18" fill="none" stroke="${COLORS[n % 7]}" stroke-width="4" stroke-dasharray="${p} ${100 - p}" stroke-dashoffset="${-off}" transform="rotate(-90 18 18)"/>`; off += p; return s; }).join('');
  return `<div class="donut"><svg viewBox="0 0 36 36" role="img" aria-label="Spending by category">${arcs}</svg><ul>${items.map((i, n) => `<li><span style="background:${COLORS[n % 7]}"></span>${esc(i.k)}<b>${usd(i.v)}</b></li>`).join('')}</ul></div>`;
}
const bar = (pct, over) => `<div class="bar" role="progressbar" aria-valuenow="${Math.round(pct)}" aria-valuemin="0" aria-valuemax="100"><i class="${over ? 'over' : ''}" style="width:${Math.min(100, pct)}%"></i></div>`;

/* ---------- dialog helper ---------- */
function form(title, fields, onSubmit, submitLabel = 'Save') {
  const f = $('#dlgForm');
  f.innerHTML = `<h3>${esc(title)}</h3>${fields.map(x => x.type === 'select'
    ? `<label>${x.label}<select name="${x.name}">${x.options.map(o => `<option value="${esc(o[0])}">${esc(o[1])}</option>`).join('')}</select></label>`
    : `<label>${x.label}<input name="${x.name}" type="${x.type || 'text'}" ${x.step ? `step="${x.step}"` : ''} ${x.min != null ? `min="${x.min}"` : ''} ${x.max != null ? `max="${x.max}"` : ''} value="${esc(x.value ?? '')}" ${x.required === false ? '' : 'required'}></label>`).join('')}
    <p class="err" id="dlgErr" role="alert"></p><div class="row"><button type="button" class="btn ghost" id="dlgCancel">Cancel</button><button class="btn primary">${submitLabel}</button></div>`;
  $('#dlg').showModal(); $('#dlgCancel').onclick = () => $('#dlg').close();
  f.onsubmit = async e => { e.preventDefault(); if (!f.reportValidity()) return;
    try { await onSubmit(Object.fromEntries(new FormData(f))); $('#dlg').close(); await render(); } catch (err) { $('#dlgErr').textContent = err.message; } };
}
const confirmDo = (m, fn) => form(m, [], async () => { await fn(); toast('Done'); }, 'Confirm');

/* ---------- views ---------- */
const views = {
  async dashboard() {
    const [acc, ov, bp, up] = await Promise.allSettled([get('/api/accounts'), get('/api/intelligence/overview'), get('/api/budgets/progress'), get('/api/subscriptions/upcoming')]);
    const o = ov.value, accounts = list(acc.value);
    const cats = (o?.top_spending_categories || []).map(c => ({ k: c.category, v: +c.amount }));
    const budgets = list(bp.value).slice(0, 4);
    return `<div class="actions"><button class="btn primary" data-act="plaid">＋ Connect bank (Plaid sandbox)</button><button class="btn ghost" data-act="sync">Sync transactions</button></div>
    ${o ? `<div class="grid stats">
      <div class="card"><span class="lbl">Total balance</span><div class="big">${usd(o.balance.current)}</div><small class="muted">30-day estimate ${usd(o.balance.estimated_in_30_days)}</small></div>
      <div class="card"><span class="lbl">Income (${o.period_days}d)</span><div class="big pos">${usd(o.cash_flow.inflow)}</div></div>
      <div class="card"><span class="lbl">Expenses (${o.period_days}d)</span><div class="big">${usd(o.cash_flow.spending)}</div></div>
      <div class="card"><span class="lbl">Net cash flow</span><div class="big ${+o.cash_flow.net < 0 ? 'neg' : 'pos'}">${usd(o.cash_flow.net)}</div><small class="muted">${o.cash_flow.savings_rate_percent != null ? o.cash_flow.savings_rate_percent + '% savings rate' : ''}</small></div></div>
    <div class="grid two"><div class="card"><h3>Spending breakdown</h3>${donut(cats)}</div>
    <div class="card"><h3>Financial health</h3>${o.alerts.map(a => `<div class="alert ${a.severity}"><b>${esc(a.title)}</b><p>${esc(a.detail)}</p></div>`).join('')}</div></div>`
    : empty('Dashboard unavailable', ov.reason?.message)}
    <div class="grid two"><div class="card"><h3>Accounts</h3>${accounts.length ? accounts.map(a => `<div class="li"><div><b>${esc(a.name)}</b><small>${esc(a.institution_name || a.account_type)}</small></div><b>${usd(a.balance)}</b></div>`).join('') : '<p class="muted">No accounts yet. Connect a bank above.</p>'}</div>
    <div class="card"><h3>Budgets</h3>${budgets.length ? budgets.map(budgetRow).join('') : '<p class="muted">No budgets yet.</p>'}
    <h3 class="mt">Upcoming payments</h3>${list(up.value).slice(0, 4).map(s => `<div class="li"><div><b>${esc(s.name)}</b><small>${esc(first(s, 'next_billing_date', 'date'))}</small></div><b>${usd(s.amount)}</b></div>`).join('') || '<p class="muted">Nothing due.</p>'}</div></div>`;
  },
  async transactions() {
    const [tx, acc] = await Promise.all([get('/api/transactions'), get('/api/accounts')]);
    const rows = list(tx).sort((a, b) => String(b.transaction_date).localeCompare(a.transaction_date)); window._tx = rows; window._acc = list(acc);
    const cats = [...new Set(rows.map(t => t.category).filter(Boolean))];
    return `<div class="actions"><input id="q" type="search" placeholder="Search merchant or description" aria-label="Search"><select id="cat"><option value="">All categories</option>${cats.map(c => `<option>${esc(c)}</option>`).join('')}</select><button class="btn primary" data-act="addTx">＋ Add</button></div>
    <div class="card" id="txList">${txRows(rows)}</div>`;
  },
  async budgets() {
    let d; try { d = await get('/api/budgets/progress'); } catch { d = await get('/api/budgets'); }
    const b = list(d);
    return `<div class="actions"><button class="btn primary" data-act="addBudget">＋ New budget</button></div>${b.length ? `<div class="grid">${b.map(x => `<div class="card">${budgetRow(x)}<div class="row"><button class="btn ghost" data-act="editBudget" data-id="${x.id ?? x.budget_id}" data-v="${first(x, 'monthly_limit', 'limit')}">Edit</button><button class="btn ghost" data-act="delBudget" data-id="${x.id ?? x.budget_id}">Delete</button></div></div>`).join('')}</div>` : empty('No budgets', 'Create a monthly limit for a category.')}`;
  },
  async subscriptions() {
    const [s, u, dc] = await Promise.allSettled([get('/api/subscriptions'), get('/api/subscriptions/upcoming', { days: 60 }), get('/api/ov/subscriptions/decisions')]);
    if (s.status !== 'fulfilled') throw s.reason;
    const subs = list(s.value), dec = list(dc.value);
    window._subs = subs;
    const active = subs.filter(x => x.is_active !== false);
    const monthly = active.reduce((a, x) => a + (+x.amount) * ({ weekly: 52/12, biweekly: 26/12, quarterly: 1/3, yearly: 1/12, annual: 1/12 }[x.billing_frequency] ?? 1), 0);
    return `<div class="actions"><button class="btn primary" data-act="addSub">＋ Add subscription</button><button class="btn ghost" data-act="classify">Classify a merchant</button></div>
    <div class="grid stats"><div class="card"><span class="lbl">Est. tracked monthly cost</span><div class="big">${usd(monthly)}</div></div><div class="card"><span class="lbl">Tracked as active</span><div class="big">${active.length}</div></div></div>
    <div class="card note"><b>Cancellation vs. tracking</b><p>Manage / Cancel opens merchant guidance. Stopping tracking only changes OmniVault's records; it does not cancel billing. Never assume charges have stopped until the merchant confirms cancellation.</p></div>
    <div class="card"><h3>Subscriptions</h3>${subs.map(x => `<div class="sub-row"><div><b>${esc(x.name)}</b><small>${esc(x.billing_frequency || 'Unknown frequency')} · ${x.is_active === false ? 'Not tracked as active' : 'Tracked as active'} · next ${esc(x.next_billing_date || 'unknown')}</small></div><div class="sub-controls"><b>${usd(x.amount)}</b><button class="btn primary sm" data-act="manageSub" data-id="${esc(x.id)}">Manage / Cancel</button><button class="btn ghost sm" data-act="toggleSub" data-id="${esc(x.id)}" data-on="${x.is_active !== false}">${x.is_active !== false ? 'Stop tracking' : 'Resume tracking'}</button></div></div>`).join('') || '<p class="muted">No subscriptions recorded yet.</p>'}</div>
    <div class="card"><h3>Upcoming (60 days)</h3>${list(u.value).map(x => `<div class="li"><div><b>${esc(x.name)}</b><small>${esc(first(x, 'next_billing_date', 'date'))}</small></div><b>${usd(x.amount)}</b></div>`).join('') || '<p class="muted">No upcoming charges identified.</p>'}</div>
    <div class="card"><h3>Recurring merchant classifications</h3>${dec.map(x => `<div class="li"><b>${esc(x.merchant_key)}</b><span class="chip">${esc(x.decision)}</span></div>`).join('') || '<p class="muted">No classifications saved.</p>'}</div>`;
  },
  async goals() {
    const g = list(await get('/api/ov/goals'));
    return `<div class="actions"><button class="btn primary" data-act="addGoal">＋ New goal</button></div><p class="note card">Contributions record progress only. No money moves from your bank.</p>
    ${g.length ? `<div class="grid">${g.map(x => `<div class="card"><h3>${esc(x.name)}</h3><div class="big">${usd(x.saved_amount)} <small>of ${usd(x.target_amount)}</small></div>${bar(x.progress_percent)}<small class="muted">${usd(x.remaining)} remaining${x.target_date ? ' · by ' + esc(x.target_date) : ''}</small><div class="row"><button class="btn primary sm" data-act="contribute" data-id="${x.id}">Add funds</button><button class="btn ghost sm" data-act="delGoal" data-id="${x.id}">Delete</button></div></div>`).join('')}</div>` : empty('No goals yet', 'Create one to start tracking.')}`;
  },
  async insights() {
    const [o, i, f] = await Promise.allSettled([get('/api/intelligence/overview'), get('/api/ov/insights'), get('/api/forecast', { days: 30 })]);
    const ov = o.value;
    return `${ov ? `<div class="grid stats"><div class="card"><span class="lbl">Subscriptions / mo</span><div class="big">${usd(ov.subscriptions.estimated_monthly_cost)}</div></div><div class="card"><span class="lbl">Balance in 30 days</span><div class="big">${usd(ov.balance.estimated_in_30_days)}</div></div></div>` : ''}
    <div class="card"><h3>Insights</h3>${list(i.value?.insights ? i.value : { a: [] }).length ? i.value.insights.map(c => `<div class="alert ${c.level}"><b>${esc(c.title)}</b><p>${esc(c.message)}</p></div>`).join('') : '<p class="muted">Unavailable.</p>'}</div>
    <div class="card"><h3>Alerts</h3>${(ov?.alerts || []).map(a => `<div class="alert ${a.severity}"><b>${esc(a.title)}</b><p>${esc(a.detail)}</p></div>`).join('') || '<p class="muted">None.</p>'}</div>
    <div class="card"><h3>Forecast</h3>${f.status === 'fulfilled' ? `<pre class="raw">${esc(JSON.stringify(f.value, null, 2).slice(0, 1500))}</pre>` : `<p class="muted">${esc(f.reason.message)}</p>`}</div>
    <div class="card note"><b>How this works</b><p>${esc(ov?.method || 'Rule-based analysis.')}</p><ul>${(ov?.limitations || []).map(l => `<li>${esc(l)}</li>`).join('')}</ul></div>`;
  },
  async about() { return aboutHTML(true); },
  async shop() {
    return renderShop();
  }
};
const budgetRow = x => { const lim = +first(x, 'monthly_limit', 'limit') || 0, sp = +first(x, 'spent', 'amount_spent', 'total_spent') || 0, pct = lim ? sp / lim * 100 : 0;
  return `<div class="bud"><div class="li"><b>${esc(x.category)}</b><span>${usd(sp)} / ${usd(lim)}</span></div>${bar(pct, pct > 100)}${pct > 100 ? '<small class="neg">Over budget</small>' : pct >= 80 ? '<small class="warn">Nearing limit</small>' : ''}</div>`; };
const txRows = rows => rows.length ? rows.map(t => `<button class="li tx" data-act="editTx" data-id="${t.id}"><div><b>${esc(t.description)}</b><small>${esc(t.transaction_date)} · ${esc(t.category || 'Uncategorized')}${t.pending ? ' · pending' : ''}</small></div><b class="${+t.amount < 0 ? 'pos' : ''}">${+t.amount < 0 ? '+' : '−'}${usd(Math.abs(t.amount))}</b></button>`).join('') : '<p class="muted">No matching transactions.</p>';

/* ---------- actions ---------- */
const A = {
  addTx: () => form('Add transaction', [{ name: 'account_id', label: 'Account', type: 'select', options: window._acc.map(a => [a.id, a.name]) }, { name: 'description', label: 'Description' }, { name: 'amount', label: 'Amount (positive = spending)', type: 'number', step: '0.01' }, { name: 'category', label: 'Category', required: false }, { name: 'transaction_date', label: 'Date', type: 'date', value: new Date().toISOString().slice(0, 10) }],
    d => post('/api/transactions', { ...d, account_id: +d.account_id, amount: +d.amount, category: d.category || null })),
  editTx: el => { const t = window._tx.find(x => x.id == el.dataset.id); form('Edit transaction', [{ name: 'description', label: 'Description', value: t.description }, { name: 'category', label: 'Category', value: t.category, required: false }], d => patch('/api/ov/transactions/' + t.id, { description: d.description, category: d.category || null })); },
  addBudget: () => form('New budget', [{ name: 'category', label: 'Category' }, { name: 'monthly_limit', label: 'Monthly limit', type: 'number', step: '0.01', min: 0.01 }], d => post('/api/budgets', { category: d.category, monthly_limit: +d.monthly_limit })),
  editBudget: el => form('Edit limit', [{ name: 'monthly_limit', label: 'Monthly limit', type: 'number', step: '0.01', min: 0.01, value: el.dataset.v }], d => patch('/api/ov/budgets/' + el.dataset.id, { monthly_limit: +d.monthly_limit })),
  delBudget: el => confirmDo('Delete this budget?', () => del('/api/ov/budgets/' + el.dataset.id)),
  addSub: () => form('Add subscription', [{ name: 'name', label: 'Name' }, { name: 'amount', label: 'Amount', type: 'number', step: '0.01', min: 0 }, { name: 'billing_frequency', label: 'Frequency', type: 'select', options: ['monthly', 'weekly', 'biweekly', 'quarterly', 'yearly'].map(x => [x, x]) }, { name: 'next_billing_date', label: 'Next billing date', type: 'date', required: false }],
    d => post('/api/subscriptions', { ...d, amount: +d.amount, next_billing_date: d.next_billing_date || null })),
  toggleSub: el => confirmDo(el.dataset.on === 'true' ? 'Stop tracking this subscription in OmniVault? This does NOT cancel merchant billing.' : 'Resume tracking this subscription?', async () => {
    await post(`/api/subscriptions/${el.dataset.id}/${el.dataset.on === 'true' ? 'deactivate' : 'activate'}`);
    toast('OmniVault tracking updated — merchant billing unchanged');
  }),
  manageSub: el => {
    const sub = (window._subs || []).find(x => String(x.id) === String(el.dataset.id));
    if (!sub) return toast('Subscription not found', true);
    const known = {
      spotify: 'https://support.spotify.com/article/cancel-premium/',
      netflix: 'https://help.netflix.com/en/node/407',
      hulu: 'https://help.hulu.com/article/hulu-cancel-hulu-subscription',
      'disney+': 'https://help.disneyplus.com/article/disneyplus-cancel',
      'apple': 'https://support.apple.com/en-us/118428',
      'youtube': 'https://support.google.com/youtube/answer/6308278'
    };
    const key = Object.keys(known).find(k => String(sub.name || '').toLowerCase().includes(k));
    const url = key ? known[key] : null;
    const f = $('#dlgForm');
    f.innerHTML = `<h3>Manage ${esc(sub.name)}</h3><p>To stop actual charges, cancel with the merchant or the platform through which you subscribed. OmniVault cannot cancel it automatically.</p>
      ${url ? `<p><a class="btn primary" href="${url}" target="_blank" rel="noopener noreferrer">Open cancellation guidance ↗</a></p>` : `<p class="note">We don't have a verified cancellation link for this merchant. Check your receipt, the merchant's official account settings, or your app store subscriptions.</p>`}
      <p class="note">Only mark the subscription inactive in OmniVault after confirming cancellation. This action is not proof of cancellation.</p>
      <div class="row"><button class="btn ghost" type="button" id="dlgCancel">Close</button></div>`;
    $('#dlg').showModal(); $('#dlgCancel').onclick = () => $('#dlg').close();
  },
  classify: () => form('Classify merchant', [{ name: 'merchant_name', label: 'Merchant' }, { name: 'decision', label: 'Decision', type: 'select', options: [['confirmed', 'Confirm recurring'], ['rejected', 'Reject recurring'], ['review', 'Needs review']] }], d => post('/api/ov/subscriptions/decision', d)),
  addGoal: () => form('New goal', [{ name: 'name', label: 'Name' }, { name: 'target_amount', label: 'Target amount', type: 'number', step: '0.01', min: 0.01 }, { name: 'target_date', label: 'Target date', type: 'date', required: false }], d => post('/api/ov/goals', { name: d.name, target_amount: +d.target_amount, target_date: d.target_date || null })),
  contribute: el => form('Add to goal', [{ name: 'amount', label: 'Amount', type: 'number', step: '0.01', min: 0.01 }], d => post(`/api/ov/goals/${el.dataset.id}/contributions`, { amount: +d.amount })),
  delGoal: el => confirmDo('Delete this goal?', () => del('/api/ov/goals/' + el.dataset.id)),
  addBrand: () => form('Add brand', [{ name: 'name', label: 'Name' }, { name: 'category', label: 'Category', required: false }, { name: 'website', label: 'Website (https://…)', type: 'url', required: false }], d => post('/api/ov/shop/brands', { name: d.name, category: d.category || null, website: d.website || null })),
  addProduct: () => form('Add product', [{ name: 'brand_id', label: 'Brand', type: 'select', options: window._brands.map(b => [b.id, b.name]) }, { name: 'name', label: 'Name' }, { name: 'category', label: 'Category' }, { name: 'price', label: 'Price', type: 'number', step: '0.01', min: 0 }, { name: 'product_url', label: 'Product URL (https)', type: 'url' }, { name: 'image_url', label: 'Image URL (https)', type: 'url', required: false }],
    d => post('/api/ov/shop/products', { ...d, brand_id: +d.brand_id, price: +d.price, image_url: d.image_url || null })),
  pref: el => form('Brand preference (0–100)', [{ name: 'score', label: 'How much do you like this brand?', type: 'number', min: 0, max: 100, value: 50 }], d => post('/api/ov/shop/preferences', { brand_id: +el.dataset.id, score: +d.score })),
  sync: async () => { try { const r = await post('/api/ov/plaid/sync'); toast('Sync complete'); render(); } catch (e) { toast(e.message, 1); } },
  plaid: async () => { try {
    await new Promise((ok, no) => { if (window.Plaid) return ok(); const s = document.createElement('script'); s.src = 'https://cdn.plaid.com/link/v2/stable/link-initialize.js'; s.onload = ok; s.onerror = () => no(new Error('Could not load Plaid Link')); document.head.appendChild(s); });
    const { link_token } = await post('/api/ov/plaid/link-token');
    window.Plaid.create({ token: link_token, onSuccess: async public_token => { try { await post('/api/ov/plaid/exchange-token', { public_token }); await post('/api/ov/plaid/sync'); toast('Bank connected'); render(); } catch (e) { toast(e.message, 1); } } }).open();
  } catch (e) { toast(e.message, 1); } }
};

/* ---------- shell ---------- */
const NAV = [['dashboard', 'Home', '⌂'], ['transactions', 'Activity', '⇄'], ['budgets', 'Budgets', '◔'], ['subscriptions', 'Recurring', '↻'], ['goals', 'Goals', '★'], ['insights', 'Insights', '✦'], ['shop', 'Shop', '❖'], ['about', 'About', 'ⓘ']];
const route = () => (location.hash.slice(1) in views ? location.hash.slice(1) : 'dashboard');
async function render() {
  const r = route(); $('#pageTitle').textContent = NAV.find(n => n[0] === r)[1];
  document.querySelectorAll('#nav a').forEach(a => a.setAttribute('aria-current', a.dataset.r === r ? 'page' : 'false'));
  $('#view').innerHTML = skeleton;
  try { $('#view').innerHTML = await views[r](); bindView(); }
  catch (e) { if (e.status !== 401) $('#view').innerHTML = `<div class="card err-card"><b>Couldn’t load this page</b><p>${esc(e.message)}</p><button class="btn primary" onclick="location.reload()">Retry</button></div>`; }
}
function bindView() {
  $('#view').onclick = e => { const el = e.target.closest('[data-act]'); if (el) A[el.dataset.act]?.(el); };
  if (route() === 'shop') bindShop();
  const q = $('#q'); if (q) { const f = () => { const s = q.value.toLowerCase(), c = $('#cat').value; $('#txList').innerHTML = txRows(window._tx.filter(t => (!c || t.category === c) && (!s || (t.description + (t.category || '')).toLowerCase().includes(s)))); }; q.oninput = f; $('#cat').onchange = f; }
}
function showApp(on) { $('#shell').hidden = !on; $('#auth').hidden = true; $('#publicSite').hidden = on; if (on) { $('#nav').innerHTML = `<div class="logo">◆ <span>OmniVault</span></div>` + NAV.map(n => `<a href="#${n[0]}" data-r="${n[0]}"><i>${n[2]}</i><span>${n[1]}</span></a>`).join(''); render(); } }
let mode = 'login';
$('#authSwitch').onclick = () => { mode = mode === 'login' ? 'register' : 'login'; $('#authTitle').textContent = mode === 'login' ? 'Welcome back' : 'Create your account'; $('#authBtn').textContent = mode === 'login' ? 'Sign in' : 'Create account'; $('#authSwitch').textContent = mode === 'login' ? 'Create an account' : 'I already have an account'; };
$('#authForm').onsubmit = async e => { e.preventDefault(); const f = e.target; $('#authErr').textContent = ''; if (!f.reportValidity()) return; $('#authBtn').disabled = true;
  try { const body = Object.fromEntries(new FormData(f));
    let d = await post('/auth/' + mode, body);
    if (mode === 'register' && !(d.access_token || d.token)) d = await post('/auth/login', body);
    const t = d.access_token || d.token || d.jwt; if (!t) throw new Error('Login succeeded but no token field was found in the response: ' + Object.keys(d).join(', '));
    auth.set(t); f.reset(); if (location.hash === '#login' || location.hash === '#register' || location.hash === '#welcome') location.hash = '#dashboard'; showApp(true);
  } catch (err) { $('#authErr').textContent = err.message; } finally { $('#authBtn').disabled = false; } };
$('#logout').onclick = () => { auth.clear(); location.hash = '#welcome'; showPublic(); };
$('#refresh').onclick = render;
window.addEventListener('hashchange', () => { if (auth.get() && !['#welcome','#login','#register'].includes(location.hash)) showApp(true); else showPublic(); });
window.addEventListener('ov:expired', () => { location.hash = '#login'; showPublic(); $('#authErr').textContent = 'Your session expired. Please sign in again.'; });
function aboutHTML(inApp = false) { return `<section class="about-content"><div class="eyebrow">ABOUT OMNIVAULT</div><h2>Built to make money feel manageable.</h2><p>OmniVault brings budgets, spending activity, recurring subscriptions, financial insights, and shopping discovery into one connected experience.</p><div class="grid two"><div class="card"><h3>Our purpose</h3><p>Help people understand their financial habits and make more informed everyday decisions.</p></div><div class="card"><h3>How it works</h3><p>Financial information comes from your connected services and records. Forecasts and recommendations are estimates, not financial advice.</p></div></div><div class="card"><h3>Creator & credits</h3><p><strong>Created by Shadrach Morris.</strong></p><p>OmniVault is an independently developed personal finance application. Third-party trademarks and services belong to their respective owners.</p><p class="note">Development build · Plaid sandbox integration · Not a bank or a subscription cancellation provider.</p></div>${inApp ? '' : '<p><button type="button" class="btn primary" id="aboutStart">Explore OmniVault →</button></p>'}</section>`; }
function welcomeHTML() { return `<section class="public-hero"><div class="eyebrow">ONE PLACE FOR YOUR MONEY</div><h1>Your finances. <em>In focus.</em></h1><p>Track spending, understand subscriptions, set goals, and discover brands you love — in one thoughtfully designed workspace.</p><div class="hero-actions"><button id="heroStart" class="btn primary">Get started →</button><button id="heroLogin" class="btn ghost">Sign in</button></div><div class="hero-caption">Currently in development · Financial connections use Plaid sandbox</div></section><section class="public-features"><div class="eyebrow">BUILT FOR CLARITY</div><h2>Less guesswork. More control.</h2><div class="feature-grid"><article class="feature"><span>◉</span><h3>See the whole picture</h3><p>Accounts, transactions, and cash flow in one dashboard.</p></article><article class="feature"><span>↻</span><h3>Stay on top of recurring costs</h3><p>Understand subscriptions and find cancellation guidance.</p></article><article class="feature"><span>✦</span><h3>Make informed choices</h3><p>Explore spending insights, forecasts, and personal goals.</p></article><article class="feature"><span>◇</span><h3>Discover your next favorite</h3><p>Browse a personalized directory of brands in OmniVault Shop.</p></article></div></section><section class="public-bottom"><h2>Ready for a clearer view?</h2><p>Explore the OmniVault development experience.</p><button id="bottomStart" class="btn primary">Get started →</button></section>`; }
function showPublic() {
  const hash = location.hash;
  if (auth.get() && !['#welcome','#login','#register'].includes(hash)) { showApp(true); return; }
  $('#shell').hidden = true;
  const login = hash === '#login' || hash === '#register';
  $('#auth').hidden = !login; $('#publicSite').hidden = login;
  if (login) {
    const want = hash === '#register' ? 'register' : 'login';
    if (mode !== want) $('#authSwitch').click();
    return;
  }
  $('#publicContent').innerHTML = hash === '#about' ? aboutHTML() : welcomeHTML();
  const go = which => { location.hash = '#' + which; showPublic(); };
  $('#publicLogin').onclick = () => go('login'); $('#publicRegister').onclick = () => go('register');
  ['#heroStart','#bottomStart','#aboutStart'].forEach(sel => { const el = $(sel); if (el) el.onclick = () => go('register'); });
  const loginButton = $('#heroLogin'); if (loginButton) loginButton.onclick = () => go('login');
}
$('#backPublic').onclick = () => { location.hash = '#welcome'; showPublic(); };
if (auth.get() && !['#welcome','#login','#register','#about'].includes(location.hash)) showApp(true);
else showPublic();
