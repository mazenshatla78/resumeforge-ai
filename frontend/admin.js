const API = (window.API_BASE_URL || "").replace(/\/$/, "");
let token = localStorage.getItem("rf_admin_token");
let view = "overview";

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (token) headers["Authorization"] = "Bearer " + token;
  const res = await fetch(API + path, { ...opts, headers });
  let data = null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) { try { data = await res.json(); } catch {} }
  else data = await res.text();
  if (!res.ok) throw new Error((data && data.detail) || res.statusText);
  return data;
}

function toast(msg) { const el = document.createElement("div"); el.className="fixed bottom-6 right-6 bg-ink-900 text-white px-4 py-2 rounded-lg text-sm"; el.textContent=msg; document.body.appendChild(el); setTimeout(()=>el.remove(),2500); }

async function boot() {
  if (!token) { renderLogin(); return; }
  try { await api("/api/admin/overview"); renderShell(); renderView(); }
  catch { token = null; localStorage.removeItem("rf_admin_token"); renderLogin(); }
}

function renderLogin() {
  document.getElementById("app").innerHTML = `
    <div class="max-w-md mx-auto mt-20 card p-6">
      <h2 class="text-xl font-bold mb-4">Admin login</h2>
      <div id="err" class="hidden mb-3 p-2 rounded bg-red-50 text-red-700 text-sm"></div>
      <input id="username" class="input mb-3" placeholder="Username" />
      <input id="pw" type="password" class="input mb-4" placeholder="Password" />
      <button onclick="doLogin()" class="w-full py-2 rounded-xl bg-brand-600 text-white font-semibold">Sign in</button>
      <p class="mt-4 text-xs text-ink-400">First time? Run bootstrap via API: POST /api/admin/bootstrap with ADMIN_BOOTSTRAP_SECRET.</p>
    </div>`;
}

async function doLogin() {
  try {
    const data = await api("/api/admin/login", { method: "POST", body: JSON.stringify({ username: document.getElementById("username").value, password: document.getElementById("pw").value }) });
    token = data.token; localStorage.setItem("rf_admin_token", token);
    renderShell(); renderView();
  } catch (e) {
    const el = document.getElementById("err"); el.textContent = e.message; el.classList.remove("hidden");
  }
}

function logout() { token = null; localStorage.removeItem("rf_admin_token"); renderLogin(); }

function renderShell() {
  document.getElementById("admin-nav").innerHTML = ["overview","users","subscriptions","payments","ai","audit","settings","gateways"].map(v =>
    `<button onclick="setView('${v}')" class="px-3 py-1.5 rounded-lg text-sm ${view===v?'bg-brand-50 text-brand-700':'hover:bg-ink-100'}">${v}</button>`).join("");
}

function setView(v) { view = v; renderShell(); renderView(); }

async function renderView() {
  const app = document.getElementById("app");
  app.innerHTML = `<div class="text-ink-400">Loading...</div>`;
  try {
    switch (view) {
      case "overview": await viewOverview(app); break;
      case "users": await viewUsers(app); break;
      case "subscriptions": await viewSubs(app); break;
      case "payments": await viewPayments(app); break;
      case "ai": await viewAI(app); break;
      case "audit": await viewAudit(app); break;
      case "settings": await viewSettings(app); break;
      case "gateways": await viewGateways(app); break;
    }
  } catch (e) { app.innerHTML = `<div class="text-red-700">${e.message}</div>`; }
}

async function viewOverview(app) {
  const d = await api("/api/admin/overview");
  app.innerHTML = `
  <h2 class="text-xl font-bold mb-4">Overview</h2>
  <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
    ${card("Total users", d.total_users)}${card("Free", d.free_users)}${card("Premium", d.premium_users)}${card("Suspended", d.suspended_users)}
    ${card("Scans", d.total_scans)}${card("Optimizations", d.total_optimizations)}${card("New (30d)", d.new_users_30d)}${card("Revenue", "$"+d.revenue_total)}
    ${card("Payments", d.payments_total)}${card("Failed payments", d.payments_failed)}${card("Pending", d.payments_pending)}${card("Failed webhooks", d.webhooks_failed)}
  </div>
  <div class="grid md:grid-cols-2 gap-4">
    <div class="card p-4"><h3 class="font-semibold mb-2">Recent users</h3>
      ${d.recent_users.map(u=>`<div class="text-sm py-1 border-b border-ink-100">${u.email} · ${u.plan} · ${u.created_at.slice(0,10)}</div>`).join("")}
    </div>
    <div class="card p-4"><h3 class="font-semibold mb-2">Recent payments</h3>
      ${d.recent_payments.length? d.recent_payments.map(p=>`<div class="text-sm py-1 border-b border-ink-100">${p.provider} · ${p.status} · $${p.amount} · ${p.created_at.slice(0,10)}</div>`).join("") : '<p class="text-ink-400 text-sm">None</p>'}
    </div>
  </div>`;
}
function card(label, val) { return `<div class="card p-4"><div class="text-xs text-ink-400">${label}</div><div class="text-2xl font-bold mt-1">${val}</div></div>`; }

async function viewUsers(app) {
  const d = await api("/api/admin/users?page_size=50");
  app.innerHTML = `
  <h2 class="text-xl font-bold mb-4">Users (${d.total})</h2>
  <div class="card overflow-x-auto">
    <table class="w-full text-sm">
      <thead class="bg-ink-50"><tr><th class="p-2 text-left">Email</th><th class="p-2">Plan</th><th class="p-2">Role</th><th class="p-2">Suspended</th><th class="p-2">Created</th><th class="p-2">Actions</th></tr></thead>
      <tbody>
        ${d.users.map(u=>`<tr class="border-t border-ink-100">
          <td class="p-2">${u.username || u.email || '-'}</td><td class="p-2 text-center">${u.plan}</td><td class="p-2 text-center">${u.role}</td>
          <td class="p-2 text-center">${u.is_suspended?'yes':'no'}</td><td class="p-2 text-center">${u.created_at.slice(0,10)}</td>
          <td class="p-2 text-center flex gap-1 justify-center">
            ${u.is_suspended?`<button onclick="reactivate(${u.id})" class="text-xs px-2 py-1 bg-green-50 text-green-700 rounded">Reactivate</button>`:`<button onclick="suspend(${u.id})" class="text-xs px-2 py-1 bg-red-50 text-red-700 rounded">Suspend</button>`}
          </td></tr>`).join("")}
      </tbody>
    </table>
  </div>`;
}
async function suspend(id){ const r=prompt("Reason?"); await api(`/api/admin/users/${id}/suspend`,{method:"POST",body:JSON.stringify({reason:r||""})}); toast("Suspended"); renderView(); }
async function reactivate(id){ await api(`/api/admin/users/${id}/reactivate`,{method:"POST"}); toast("Reactivated"); renderView(); }

async function viewSubs(app) {
  const d = await api("/api/admin/subscriptions?page_size=50");
  app.innerHTML = `<h2 class="text-xl font-bold mb-4">Subscriptions (${d.total})</h2>
  <div class="card overflow-x-auto"><table class="w-full text-sm"><thead class="bg-ink-50"><tr><th class="p-2 text-left">User</th><th class="p-2">Provider</th><th class="p-2">Plan</th><th class="p-2">Status</th><th class="p-2">Period end</th></tr></thead><tbody>
  ${d.subscriptions.map(s=>`<tr class="border-t border-ink-100"><td class="p-2">${s.user||s.user_id}</td><td class="p-2 text-center">${s.provider}</td><td class="p-2 text-center">${s.plan}</td><td class="p-2 text-center">${s.status}</td><td class="p-2 text-center">${s.period_end?s.period_end.slice(0,10):'-'}</td></tr>`).join("")}
  </tbody></table></div>`;
}

async function viewPayments(app) {
  const d = await api("/api/admin/payments?page_size=50");
  app.innerHTML = `<h2 class="text-xl font-bold mb-4">Payments (${d.total})</h2>
  <div class="card overflow-x-auto"><table class="w-full text-sm"><thead class="bg-ink-50"><tr><th class="p-2 text-left">User</th><th class="p-2">Provider</th><th class="p-2">Plan</th><th class="p-2">Amount</th><th class="p-2">Status</th><th class="p-2">Date</th></tr></thead><tbody>
  ${d.payments.map(p=>`<tr class="border-t border-ink-100"><td class="p-2">${p.user_id}</td><td class="p-2 text-center">${p.provider}</td><td class="p-2 text-center">${p.plan}</td><td class="p-2 text-center">$${p.amount}</td><td class="p-2 text-center">${p.status}</td><td class="p-2 text-center">${p.created_at.slice(0,10)}</td></tr>`).join("")}
  </tbody></table></div>`;
}

async function viewAI(app) {
  const d = await api("/api/admin/ai-usage");
  app.innerHTML = `<h2 class="text-xl font-bold mb-4">AI Usage</h2>
  <div class="card overflow-x-auto"><table class="w-full text-sm"><thead class="bg-ink-50"><tr><th class="p-2 text-left">User</th><th class="p-2">Email</th><th class="p-2">Scans</th></tr></thead><tbody>
  ${d.per_user.map(u=>`<tr class="border-t border-ink-100"><td class="p-2">${u.user_id}</td><td class="p-2">${u.email||''}</td><td class="p-2 text-center">${u.scans}</td></tr>`).join("")}
  </tbody></table></div>`;
}

async function viewAudit(app) {
  const d = await api("/api/admin/audit-logs?page_size=50");
  app.innerHTML = `<h2 class="text-xl font-bold mb-4">Audit Logs (${d.total})</h2>
  <div class="card overflow-x-auto"><table class="w-full text-sm"><thead class="bg-ink-50"><tr><th class="p-2">When</th><th class="p-2">Actor</th><th class="p-2">Action</th><th class="p-2">Target</th><th class="p-2">IP</th></tr></thead><tbody>
  ${d.logs.map(l=>`<tr class="border-t border-ink-100"><td class="p-2">${l.created_at.slice(0,19)}</td><td class="p-2">${l.actor_user_id||'system'}</td><td class="p-2">${l.action}</td><td class="p-2">${l.target_type||''} ${l.target_id||''}</td><td class="p-2">${l.ip_address||''}</td></tr>`).join("")}
  </tbody></table></div>`;
}

async function viewSettings(app) {
  const d = await api("/api/admin/settings");
  app.innerHTML = `<h2 class="text-xl font-bold mb-4">System Settings</h2>
  <p class="text-sm text-ink-500 mb-4">Click Edit to modify a value, then Save.</p>
  <div class="card p-4 space-y-3">
    ${Object.keys(d).map(k=>`
      <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
        <label class="sm:w-48 text-sm font-medium">${k}</label>
        <input id="s-${k}" class="input flex-1" value="${d[k]}" disabled />
        <div class="flex gap-2">
          <button onclick="enableSetting('${k}')" class="px-3 py-1.5 rounded-lg bg-ink-100 text-ink-700 text-sm hover:bg-ink-200">Edit</button>
          <button onclick="saveSetting('${k}')" class="px-3 py-1.5 rounded-lg bg-brand-600 text-white text-sm hover:bg-brand-700">Save</button>
        </div>
      </div>`).join("")}
  </div>`;
}
function enableSetting(k){ const el=document.getElementById("s-"+k); el.disabled=false; el.focus(); }
async function saveSetting(k){ const el=document.getElementById("s-"+k); const v=el.value; await api(`/api/admin/settings/${k}`,{method:"PUT",body:JSON.stringify({value:v})}); el.disabled=true; toast("Saved"); }

async function viewGateways(app) {
  const d = await api("/api/admin/payment-gateways");
  app.innerHTML = `<h2 class="text-xl font-bold mb-4">Payment Gateways</h2>
  <div class="grid md:grid-cols-2 gap-4">
    ${["paddle","paymob"].map(name=>`
    <div class="card p-5">
      <div class="flex items-center justify-between mb-2"><span class="font-semibold">${name}</span>
        <span class="px-2 py-1 rounded-full text-xs ${d[name].enabled?'bg-green-100 text-green-700':'bg-red-100 text-red-700'}">${d[name].enabled?'Enabled':'Disabled'}</span>
      </div>
      <p class="text-sm text-ink-500">Configured: ${d[name].configured}</p>
      ${d[name].environment?`<p class="text-sm text-ink-500">Env: ${d[name].environment}</p>`:''}
    </div>`).join("")}
  </div>
  <div class="card p-4 mt-4 text-sm text-ink-500">Toggle gateways via System Settings (paddle_enabled / paymob_enabled). Configure credentials in .env.</div>`;
}

boot();
