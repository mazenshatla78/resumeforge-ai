// ---------- State ----------
const state = {
  token: localStorage.getItem("rf_token") || null,
  user: null,
  view: "dashboard",
  resumes: [],
  jds: [],
  optimizations: [],
  currentOpt: null,
  usage: null,
};

const API = (window.API_BASE_URL || "").replace(/\/$/, "");

// ---------- HTTP helper ----------
async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const res = await fetch(API + path, { ...opts, headers });
  let data = null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) { try { data = await res.json(); } catch { data = null; } }
  else data = await res.text();
  if (!res.ok) {
    const msg = (data && data.detail) ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : (typeof data === "string" ? data : res.statusText);
    throw new Error(msg || "Request failed");
  }
  return data;
}

// ---------- Toast ----------
function toast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-lg text-sm font-medium fade-in " +
    (type === "error" ? "bg-red-600 text-white" : type === "success" ? "bg-green-600 text-white" : "bg-ink-900 text-white");
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .3s"; setTimeout(() => el.remove(), 300); }, 3200);
}

// ---------- Auth ----------
let authMode = "login";
function showAuth(mode) {
  authMode = mode;
  const m = document.getElementById("auth-modal");
  m.classList.remove("hidden");
  requestAnimationFrame(() => m.classList.add("open"));
  document.getElementById("auth-title").textContent = mode === "login" ? "Sign in" : "Create account";
  document.getElementById("name-field").classList.toggle("hidden", mode === "login");
  document.getElementById("auth-switch-text").textContent = mode === "login" ? "No account?" : "Already have an account?";
  document.getElementById("auth-switch-btn").textContent = mode === "login" ? "Create one" : "Sign in";
  document.getElementById("auth-error").classList.add("hidden");
}
function closeAuth() { const m = document.getElementById("auth-modal"); m.classList.remove("open"); setTimeout(() => m.classList.add("hidden"), 200); }
function toggleAuthMode() { showAuth(authMode === "login" ? "register" : "login"); }

async function submitAuth(e) {
  e.preventDefault();
  const f = e.target;
  const fd = new FormData(f);
  const payload = { email: fd.get("email"), password: fd.get("password") };
  if (authMode === "register") payload.name = fd.get("name") || "";
  try {
    const data = await api("/api/auth/" + (authMode === "login" ? "login" : "register"), { method: "POST", body: JSON.stringify(payload) });
    if (data.mfa_required) {
      const code = prompt("Enter your 6-digit MFA code:");
      if (!code) { toast("MFA code required", "error"); return; }
      const data2 = await api("/api/auth/mfa/complete", { method: "POST", body: JSON.stringify({ mfa_token: data.mfa_token, code }) });
      state.token = data2.token;
      localStorage.setItem("rf_token", data2.token);
      state.user = { id: data2.id, email: data2.email, name: data2.name, plan: data2.plan, role: data2.role, email_verified: data2.email_verified };
      closeAuth();
      toast("Welcome back!", "success");
      await boot();
      return;
    }
    state.token = data.token;
    localStorage.setItem("rf_token", data.token);
    state.user = { id: data.id, email: data.email, name: data.name, plan: data.plan, role: data.role, email_verified: data.email_verified };
    closeAuth();
    toast("Welcome back!", "success");
    await boot();
  } catch (err) {
    const el = document.getElementById("auth-error");
    el.textContent = err.message; el.classList.remove("hidden");
  }
}

function logout() {
  state.token = null; state.user = null;
  localStorage.removeItem("rf_token");
  render();
}

// ---------- Boot ----------
async function boot() {
  // handle email verification / password reset tokens in URL
  const params = new URLSearchParams(window.location.search);
  const verifyToken = params.get("verify_token");
  const resetToken = params.get("reset_token");
  if (verifyToken) {
    try { await api("/api/auth/verify-email", { method: "POST", body: JSON.stringify({ token: verifyToken }) }); toast("Email verified!", "success"); }
    catch (e) { toast(e.message, "error"); }
    window.history.replaceState({}, "", "/");
  }
  if (resetToken) {
    const newPw = prompt("Enter your new password (min 6 chars):");
    if (newPw) {
      try { await api("/api/auth/reset-password", { method: "POST", body: JSON.stringify({ token: resetToken, new_password: newPw }) }); toast("Password updated. Please sign in.", "success"); }
      catch (e) { toast(e.message, "error"); }
    }
    window.history.replaceState({}, "", "/");
  }
  if (!state.token) { render(); return; }
  try {
    const u = await api("/api/auth/me");
    state.user = u;
    await loadAll();
    render();
  } catch (e) { logout(); }
}

async function loadAll() {
  try {
    const [resumes, jds, opts, usage] = await Promise.all([
      api("/api/resumes").catch(() => []),
      api("/api/job-descriptions").catch(() => []),
      api("/api/optimizations").catch(() => []),
      api("/api/usage").catch(() => null),
    ]);
    state.resumes = resumes || [];
    state.jds = jds || [];
    state.optimizations = opts || [];
    state.usage = usage;
  } catch (e) {}
}

// ---------- Helpers ----------
function escapeHtml(s) { return (s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function fmtDate(s) { try { return new Date(s).toLocaleString(); } catch { return s; } }
function scoreColor(s) { if (s >= 80) return "text-green-600"; if (s >= 60) return "text-amber-600"; return "text-red-600"; }
function featureCard(icon, title, desc) { return `<div class="card p-5 hover:-translate-y-1 transition"><div class="text-2xl mb-2">${icon}</div><div class="font-semibold">${title}</div><div class="text-sm text-ink-500 mt-1">${desc}</div></div>`; }
function problemCard(stat, problem, solution) { return `<div class="card p-6 fade-in"><div class="text-sm font-bold text-brand-600 mb-2">${stat}</div><div class="font-semibold mb-2">${problem}</div><div class="text-sm text-ink-500">${solution}</div></div>`; }
function stepCard(n, title, desc) { return `<div class="card p-6 text-center fade-in"><div class="w-10 h-10 mx-auto rounded-full bg-gradient-to-br from-brand-500 to-purple-600 text-white font-bold flex items-center justify-center mb-3">${n}</div><div class="font-semibold mb-1">${title}</div><div class="text-sm text-ink-500">${desc}</div></div>`; }
function reviewCard(title, subtitle, desc) { return `<div class="card p-6 fade-in"><div class="font-semibold text-brand-600 mb-1">${title}</div><div class="text-xs text-ink-400 mb-2">${subtitle}</div><p class="text-sm text-ink-700">${desc}</p></div>`; }
function faq(q, a) { return `<details class="card p-4 group"><summary class="font-medium cursor-pointer list-none flex items-center justify-between">${q}<span class="text-brand-600 group-open:rotate-180 transition">▾</span></summary><p class="mt-3 text-sm text-ink-600">${a}</p></details>`; }

// ---------- Sidebar ----------
function toggleSidebar() {
  const sb = document.getElementById("sidebar");
  const bd = document.getElementById("sidebar-backdrop");
  if (!sb) return;
  const open = !sb.classList.contains("-translate-x-full");
  if (open) { sb.classList.add("-translate-x-full"); bd.classList.add("hidden"); }
  else { sb.classList.remove("-translate-x-full"); bd.classList.remove("hidden"); }
}

// ---------- Render ----------
function render() {
  const landing = document.getElementById("landing");
  const app = document.getElementById("app");
  if (!state.user) {
    if (landing) { landing.classList.remove("hidden"); renderLandingContent(); }
    app.classList.add("hidden");
    return;
  }
  if (landing) landing.classList.add("hidden");
  app.classList.remove("hidden");
  const views = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "optimize", label: "Optimize", icon: "✨" },
    { id: "resumes", label: "Resumes", icon: "📄" },
    { id: "history", label: "History", icon: "🕐" },
    { id: "billing", label: "Billing", icon: "💳" },
    { id: "profile", label: "Profile", icon: "👤" },
  ];
  if (state.user.role === "admin") views.push({ id: "admin", label: "Admin", icon: "🛡️" });
  const sidebar = document.getElementById("sidebar-links");
  if (sidebar) sidebar.innerHTML = views.map(v =>
    `<button onclick="setView('${v.id}'); if(window.innerWidth<768) toggleSidebar();" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${state.view===v.id?'bg-brand-50 text-brand-700':'text-ink-600 hover:bg-ink-100 hover:text-ink-900'}">
      <span>${v.icon}</span><span>${v.label}</span>
    </button>`).join("");
  const su = document.getElementById("sidebar-user");
  if (su) su.innerHTML = `<div class="font-medium text-ink-700 truncate">${escapeHtml(state.user.name||state.user.email||state.user.username||'')}</div><div class="truncate text-xs text-ink-400">${escapeHtml(state.user.email||state.user.username||'')}</div>`;
  const topbar = document.getElementById("topbar-auth");
  if (topbar) topbar.innerHTML = `
    <span class="px-2 py-1 rounded-full text-xs font-semibold ${state.user.plan==='premium'?'bg-amber-100 text-amber-700':'bg-ink-100 text-ink-600'}">${state.user.plan}</span>
    <button onclick="logout()" class="px-3 py-1.5 rounded-lg text-sm hover:bg-ink-100 transition">Logout</button>`;
  renderView();
}

function renderView() {
  const content = document.getElementById("content");
  if (!content) return;
  content.classList.remove("fade-in");
  void content.offsetWidth;
  content.classList.add("fade-in");
  switch (state.view) {
    case "dashboard": content.innerHTML = viewDashboard(); break;
    case "optimize": content.innerHTML = viewOptimize(); bindOptimize(); break;
    case "resumes": content.innerHTML = viewResumes(); bindResumes(); break;
    case "history": content.innerHTML = viewHistory(); break;
    case "billing": content.innerHTML = viewBilling(); bindBilling(); break;
    case "profile": content.innerHTML = viewProfile(); break;
    case "admin": content.innerHTML = `<div class="card p-6"><h2 class="text-xl font-bold mb-2">Admin</h2><p class="text-ink-500">Open the dedicated admin panel: <a href="/admin" class="text-brand-600 hover:underline">/admin</a></p></div>`; break;
    default: content.innerHTML = viewDashboard();
  }
}

function setView(v) { state.view = v; state.currentOpt = null; render(); }

function renderLandingContent() {
  // scroll reveal observer
  if (!window._revealObs) {
    window._revealObs = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add("revealed"); window._revealObs.unobserve(e.target); } });
    }, { threshold: 0.12 });
  }
  document.querySelectorAll("#landing section, #landing .card").forEach(el => {
    if (!el.classList.contains("reveal")) el.classList.add("reveal");
    window._revealObs.observe(el);
  });
  const problems = [
    ["71% of resumes are rejected by ATS before a human reads them","Most resumes fail automated screening for fixable reasons: missing keywords, bad formatting, or non-standard section labels.","We score your resume against the job description and show exactly which keywords and formatting issues to fix."],
    ["29% say tailoring a resume is the most annoying part of applying","Manual tailoring takes hours per application, so most people skip it — and get rejected.","ResumeForge rewrites your resume for each job in ~15 seconds, keeping your experience truthful while matching the JD."],
    ["Senior candidates get rejected more often (79% for 15+ years)","Long resumes dilute keyword density; duty-heavy bullets instead of outcomes hurt ATS scoring.","We trim and restructure your resume, convert duties to outcome-focused bullets, and boost keyword density."],
    ["43% feel their resume is never seen by a human","Knockout questions and keyword filters silently reject qualified candidates.","We surface missing keywords and format issues so you pass the first gate and reach a recruiter."],
    ["Multi-column layouts and tables break 34% of ATS parsers","Fancy templates scramble your work history into an unreadable blob.","We output clean, single-column, ATS-safe text you can paste into any template."],
    ["Fast rejections arrive in minutes via knockout questions","Eligibility rules (work auth, location, licenses) auto-reject before review.","We can't change knockout rules, but we make sure your resume clears every keyword and format bar."],
  ];
  const pg = document.getElementById("problems-grid");
  if (pg) pg.innerHTML = problems.map(p=>problemCard(p[0],p[1],p[2])).join("");
  const sg = document.getElementById("steps-grid");
  if (sg) sg.innerHTML = [
    stepCard("1","Upload or paste your resume","PDF, DOCX, or plain text. We extract and clean it automatically."),
    stepCard("2","Paste the job description","We compare your resume to the JD and compute your ATS match score."),
    stepCard("3","Get your tailored package","Tailored resume, cover letter, keyword gaps, and interview prep — ready to send."),
  ].join("");
  const rg = document.getElementById("reviews-grid");
  if (rg) rg.innerHTML = [
    reviewCard("ATS Score","0-100 match score","Instant score with 5-dimension breakdown: keywords, experience, skills, education, format."),
    reviewCard("Keyword Gaps","Missing & matched","See exactly which keywords from the job description are in your resume — and which are missing."),
    reviewCard("Tailored Resume","AI rewrite","A full resume rewrite aligned to the job description, with strong action verbs and impact."),
    reviewCard("Cover Letter","Custom letter","A tailored cover letter highlighting your fit for the specific role."),
    reviewCard("Interview Prep","Questions & answers","Likely interview questions with suggested answers (Premium)."),
    reviewCard("Privacy","Your data, your control","Delete resumes, export data, or delete your account anytime. No resume contents logged."),
  ].join("");
  const fl = document.getElementById("faq-list");
  if (fl) fl.innerHTML = [
    faq("What is an ATS and why does it reject resumes?","An Applicant Tracking System (ATS) is software employers use to filter and rank resumes before a human sees them. Over 98% of Fortune 500 companies use one. Resumes are rejected for missing keywords, bad formatting (tables, columns, graphics), non-standard section labels, or unparseable file types."),
    faq("What ATS score should I aim for?","Aim for 80% or higher. That indicates strong keyword and formatting alignment with the job description. Scores above 75% generally pass initial screening, though thresholds vary by employer."),
    faq("Is the free plan really free?","Yes. You get 3 free optimizations per month with full analysis, tailored resume, and cover letter. No credit card required. Upgrade to Premium for unlimited scans, interview prep, and exports."),
    faq("How is this different from ChatGPT?","ChatGPT is general-purpose. ResumeForge is built specifically for ATS optimization: it scores your resume against a real job description, detects keyword gaps, validates formatting, and produces ATS-safe output. It explains every suggestion."),
    faq("Will it make things up on my resume?","No. The AI rewrites and rephrases your existing experience; it won't invent employers, degrees, or achievements. You should always review before sending."),
    faq("Should I use PDF or DOCX?","DOCX is the safest for ATS parsing. PDFs from design tools can fail. We export both; use DOCX when applying unless the employer requests PDF."),
    faq("Does it work for any industry?","Yes — tech, marketing, healthcare, finance, data, operations, and more. Paste any job description and we adapt."),
    faq("How often should I tailor my resume?","Every application. Tailoring to the specific job description significantly improves ATS scores and interview chances."),
    faq("Can I delete my data?","Yes. Delete individual resumes/optimizations, export your data, or delete your account entirely."),
  ].join("");
}

// ---------- Views ----------
function viewDashboard() {
  const u = state.usage || {};
  const used = u.used_this_month || 0;
  const limit = u.monthly_limit;
  const pct = limit ? Math.min(100, (used/limit)*100) : 0;
  const recent = state.optimizations.slice(0,5);
  return `
  <div class="fade-in">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl font-bold">Welcome back${state.user.name ? ', '+escapeHtml(state.user.name) : ''}</h1>
        <p class="text-ink-500 text-sm">Here's your job-search command center.</p>
      </div>
      <button onclick="setView('optimize')" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-brand-700 text-white font-semibold hover:shadow-lg transition">+ New optimization</button>
    </div>
    <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="card p-5"><div class="text-sm text-ink-500">Plan</div><div class="text-2xl font-bold mt-1">${state.user.plan === 'premium' ? 'Premium' : 'Free'}</div><div class="text-xs text-ink-400 mt-1">${state.user.plan==='premium'?'Unlimited optimizations':'3 per month'}</div></div>
      <div class="card p-5"><div class="text-sm text-ink-500">Optimizations this month</div><div class="text-2xl font-bold mt-1">${used}${limit?'/'+limit:''}</div><div class="h-1.5 bg-ink-100 rounded-full mt-3 overflow-hidden"><div class="h-full bg-gradient-to-r from-brand-400 to-purple-500" style="width:${pct}%"></div></div></div>
      <div class="card p-5"><div class="text-sm text-ink-500">Saved resumes</div><div class="text-2xl font-bold mt-1">${state.resumes.length}</div></div>
      <div class="card p-5"><div class="text-sm text-ink-500">Total optimizations</div><div class="text-2xl font-bold mt-1">${state.optimizations.length}</div></div>
    </div>
    <div class="card p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="font-semibold">Recent optimizations</h2>
        <button onclick="setView('history')" class="text-sm text-brand-600 hover:underline">View all</button>
      </div>
      ${recent.length ? `
      <div class="divide-y divide-ink-100">
        ${recent.map(o => `
        <div class="py-3 flex items-center justify-between gap-4">
          <div class="min-w-0"><div class="font-medium truncate">Optimization #${o.id}</div><div class="text-xs text-ink-400">${fmtDate(o.created_at)}</div></div>
          <div class="flex items-center gap-3">
            <span class="text-sm font-bold ${scoreColor(o.ats_score)}">${o.ats_score}%</span>
            <button onclick="viewOptimization(${o.id})" class="text-sm text-brand-600 hover:underline">Open</button>
          </div>
        </div>`).join("")}
      </div>` : `<p class="text-ink-400 text-sm">No optimizations yet. <button onclick="setView('optimize')" class="text-brand-600 hover:underline">Create your first</button>.</p>`}
    </div>
    <div class="mt-8">
      <h2 class="font-semibold mb-4">What you get</h2>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        ${featureCard("🎯","ATS Score","Instant match score with 5-dimension breakdown.")}
        ${featureCard("✍️","Tailored Resume","AI rewrite aligned to the job description.")}
        ${featureCard("✉️","Cover Letter","Custom letter highlighting your fit.")}
        ${featureCard("🎤","Interview Prep","Likely questions with suggested answers (Premium).")}
      </div>
    </div>
  </div>`;
}

function viewOptimize() {
  return `
  <div class="fade-in max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold mb-1">Optimize your resume</h1>
    <p class="text-ink-500 text-sm mb-6">Paste your resume and a job description. We'll score the match and rewrite for ATS.</p>
    <div class="grid md:grid-cols-2 gap-4 mb-4">
      <div class="card p-4">
        <div class="flex items-center justify-between mb-2">
          <label class="label mb-0">Your resume</label>
          <select id="resume-pick" class="text-xs border border-ink-200 rounded px-2 py-1">
            <option value="">— paste or pick saved —</option>
            ${state.resumes.map(r => `<option value="${r.id}">${escapeHtml(r.title)}</option>`).join("")}
          </select>
        </div>
        <textarea id="resume-text" rows="12" class="input font-mono text-sm" placeholder="Paste your resume here, or upload a file below..."></textarea>
        <div class="mt-2 flex items-center gap-2 flex-wrap">
          <input type="file" id="resume-file" accept=".pdf,.docx,.txt,.md" class="text-xs" />
          <button id="upload-btn" class="text-xs px-3 py-1.5 rounded-lg bg-ink-100 hover:bg-ink-200">Upload</button>
          <span id="upload-status" class="text-xs text-ink-400"></span>
        </div>
      </div>
      <div class="card p-4">
        <div class="flex items-center justify-between mb-2">
          <label class="label mb-0">Job description</label>
          <select id="jd-pick" class="text-xs border border-ink-200 rounded px-2 py-1">
            <option value="">— paste or pick saved —</option>
            ${state.jds.map(j => `<option value="${j.id}">${escapeHtml(j.title||'JD #'+j.id)}</option>`).join("")}
          </select>
        </div>
        <textarea id="jd-text" rows="12" class="input font-mono text-sm" placeholder="Paste the job description here..."></textarea>
      </div>
    </div>
    <div class="card p-4 mb-4 flex flex-wrap items-center gap-4">
      <label class="flex items-center gap-2 text-sm"><input type="checkbox" id="opt-cover" checked /> Generate cover letter</label>
      <label class="flex items-center gap-2 text-sm"><input type="checkbox" id="opt-interview" ${state.user.plan==='premium'?'':'disabled'} /> Interview prep ${state.user.plan!=='premium'?'(Premium)':''}</label>
      <input id="opt-title" placeholder="Title (optional)" class="input text-sm max-w-xs" />
      <div class="flex-1"></div>
      <button id="run-btn" class="px-6 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-brand-700 text-white font-semibold hover:shadow-lg transition">Optimize</button>
    </div>
    <div id="opt-result" class="hidden"></div>
  </div>`;
}

function bindOptimize() {
  document.getElementById("resume-pick").addEventListener("change", async (e) => {
    const id = e.target.value;
    if (!id) return;
    try { const r = await api("/api/resumes/" + id); document.getElementById("resume-text").value = r.content; }
    catch (err) { toast(err.message, "error"); }
  });
  document.getElementById("jd-pick").addEventListener("change", async (e) => {
    const id = e.target.value;
    if (!id) return;
    try { const r = await api("/api/job-descriptions/" + id); document.getElementById("jd-text").value = r.content || ""; }
    catch (err) { toast(err.message, "error"); }
  });
  document.getElementById("upload-btn").addEventListener("click", async () => {
    const file = document.getElementById("resume-file").files[0];
    if (!file) { toast("Choose a file first", "error"); return; }
    const st = document.getElementById("upload-status");
    st.textContent = "Uploading...";
    try {
      const fd = new FormData(); fd.append("file", file); fd.append("title", file.name);
      const res = await fetch("/api/resumes/upload", { method: "POST", headers: { Authorization: "Bearer " + state.token }, body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      state.resumes.unshift({ id: data.id, title: data.title });
      const full = await api("/api/resumes/" + data.id);
      document.getElementById("resume-text").value = full.content;
      st.textContent = "Uploaded ✓";
      toast("Resume uploaded", "success");
    } catch (err) { st.textContent = "Failed"; toast(err.message, "error"); }
  });
  document.getElementById("run-btn").addEventListener("click", runOptimize);
}

async function runOptimize() {
  const resumeText = document.getElementById("resume-text").value.trim();
  const jdText = document.getElementById("jd-text").value.trim();
  if (!resumeText || !jdText) { toast("Both resume and job description are required", "error"); return; }
  const btn = document.getElementById("run-btn");
  btn.disabled = true; btn.textContent = "Optimizing...";
  const resultEl = document.getElementById("opt-result");
  resultEl.classList.remove("hidden");
  resultEl.innerHTML = `<div class="card p-10 text-center"><div class="spinner mx-auto"></div><p class="mt-4 text-ink-500">Analyzing with AI... this may take 15-30s</p></div>`;
  try {
    const data = await api("/api/optimize", { method: "POST", body: JSON.stringify({
      resume_text: resumeText, jd_text: jdText,
      include_cover_letter: document.getElementById("opt-cover").checked,
      include_interview_prep: document.getElementById("opt-interview").checked,
      title: document.getElementById("opt-title").value.trim(),
    }) });
    state.currentOpt = data;
    state.optimizations.unshift(data);
    await loadAll();
    renderOptResult(data);
    toast("Optimization complete", "success");
  } catch (err) {
    resultEl.innerHTML = `<div class="card p-6 text-red-700 bg-red-50">${escapeHtml(err.message)}</div>`;
    toast(err.message, "error");
  } finally { btn.disabled = false; btn.textContent = "Optimize"; }
}

function renderOptResult(data) {
  const a = data.analysis || {};
  const sb = a.score_breakdown || {};
  const resultEl = document.getElementById("opt-result");
  resultEl.innerHTML = `
  <div class="fade-in space-y-4">
    <div class="card p-6">
      <div class="flex flex-col md:flex-row items-center gap-6">
        <div class="relative w-32 h-32">
          <svg viewBox="0 0 120 120" class="w-full h-full -rotate-90">
            <circle cx="60" cy="60" r="52" stroke="#eef0f4" stroke-width="10" fill="none"/>
            <circle cx="60" cy="60" r="52" stroke="url(#g)" stroke-width="10" fill="none" stroke-linecap="round"
              stroke-dasharray="${2*Math.PI*52}" stroke-dashoffset="${2*Math.PI*52*(1-data.ats_score/100)}" class="score-ring"/>
            <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5a99ff"/><stop offset="1" stop-color="#1d5ae6"/></linearGradient></defs>
          </svg>
          <div class="absolute inset-0 flex flex-col items-center justify-center">
            <span class="text-3xl font-extrabold">${data.ats_score}</span>
            <span class="text-xs text-ink-400">ATS score</span>
          </div>
        </div>
        <div class="flex-1">
          <h3 class="font-semibold text-lg">Match analysis</h3>
          <p class="text-ink-500 text-sm mt-1">${escapeHtml(a.summary || "")}</p>
          <div class="grid grid-cols-5 gap-2 mt-4">
            ${["keywords","experience","skills","education","format"].map(k => `<div class="text-center"><div class="text-lg font-bold">${sb[k] ?? 0}</div><div class="text-[10px] uppercase text-ink-400">${k}</div></div>`).join("")}
          </div>
        </div>
      </div>
    </div>
    <div class="grid md:grid-cols-2 gap-4">
      <div class="card p-5"><h4 class="font-semibold text-green-700 mb-2">Matched keywords</h4><div class="flex flex-wrap gap-1.5">${(a.matched_keywords||[]).map(k=>`<span class="px-2 py-1 rounded-md bg-green-50 text-green-700 text-xs">${escapeHtml(k)}</span>`).join("") || '<span class="text-ink-400 text-sm">None</span>'}</div></div>
      <div class="card p-5"><h4 class="font-semibold text-amber-700 mb-2">Missing keywords</h4><div class="flex flex-wrap gap-1.5">${(a.missing_keywords||[]).map(k=>`<span class="px-2 py-1 rounded-md bg-amber-50 text-amber-700 text-xs">${escapeHtml(k)}</span>`).join("") || '<span class="text-ink-400 text-sm">None</span>'}</div></div>
    </div>
    <div class="grid md:grid-cols-2 gap-4">
      <div class="card p-5"><h4 class="font-semibold mb-2">Strengths</h4><ul class="list-disc list-inside text-sm text-ink-700 space-y-1">${(a.strengths||[]).map(s=>`<li>${escapeHtml(s)}</li>`).join("")}</ul></div>
      <div class="card p-5"><h4 class="font-semibold mb-2">Weaknesses</h4><ul class="list-disc list-inside text-sm text-ink-700 space-y-1">${(a.weaknesses||[]).map(s=>`<li>${escapeHtml(s)}</li>`).join("")}</ul></div>
    </div>
    <div class="card p-5"><h4 class="font-semibold mb-2">Suggestions</h4><ul class="list-disc list-inside text-sm text-ink-700 space-y-1">${(a.suggestions||[]).map(s=>`<li>${escapeHtml(s)}</li>`).join("")}</ul></div>
    <div class="card">
      <div class="flex border-b border-ink-100 overflow-x-auto">
        <button class="tab active" onclick="switchResultTab('tailored')">Tailored resume</button>
        ${data.cover_letter ? `<button class="tab" onclick="switchResultTab('cover')">Cover letter</button>` : ""}
        ${data.interview_prep && data.interview_prep.length ? `<button class="tab" onclick="switchResultTab('interview')">Interview prep</button>` : ""}
      </div>
      <div class="p-5">
        <div id="tab-tailored" class="result-tab">
          <div class="flex justify-end gap-2 mb-3 flex-wrap">
            <button onclick="downloadExport(${data.id},'pdf')" class="text-xs px-3 py-1.5 rounded-lg bg-ink-100 hover:bg-ink-200">Download PDF</button>
            <button onclick="downloadExport(${data.id},'docx')" class="text-xs px-3 py-1.5 rounded-lg bg-ink-100 hover:bg-ink-200">Download DOCX</button>
            <button onclick="copyText('tailored-text')" class="text-xs px-3 py-1.5 rounded-lg bg-brand-50 text-brand-700 hover:bg-brand-100">Copy</button>
          </div>
          <pre id="tailored-text" class="resume bg-ink-50 rounded-lg p-4 border border-ink-100">${escapeHtml(data.tailored_resume)}</pre>
        </div>
        ${data.cover_letter ? `<div id="tab-cover" class="result-tab hidden">
          <div class="flex justify-end gap-2 mb-3">
            <button onclick="downloadExport(${data.id},'pdf','cover')" class="text-xs px-3 py-1.5 rounded-lg bg-ink-100 hover:bg-ink-200">Download PDF</button>
            <button onclick="copyText('cover-text')" class="text-xs px-3 py-1.5 rounded-lg bg-brand-50 text-brand-700 hover:bg-brand-100">Copy</button>
          </div>
          <pre id="cover-text" class="resume bg-ink-50 rounded-lg p-4 border border-ink-100">${escapeHtml(data.cover_letter)}</pre>
        </div>` : ""}
        ${data.interview_prep && data.interview_prep.length ? `<div id="tab-interview" class="result-tab hidden">
          <div class="space-y-3">
            ${data.interview_prep.map((q,i) => `<div class="border border-ink-100 rounded-xl p-4">
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <span class="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700">${escapeHtml(q.type||'question')}</span>
                <span class="font-medium">${i+1}. ${escapeHtml(q.question)}</span>
              </div>
              ${q.why_asked ? `<p class="text-xs text-ink-400 mt-1"><b>Why asked:</b> ${escapeHtml(q.why_asked)}</p>` : ""}
              ${q.suggested_answer ? `<p class="text-sm text-ink-700 mt-2 whitespace-pre-wrap">${escapeHtml(q.suggested_answer)}</p>` : ""}
            </div>`).join("")}
          </div>
        </div>` : ""}
      </div>
    </div>
  </div>`;
}

function switchResultTab(tab) {
  document.querySelectorAll(".result-tab").forEach(el => el.classList.add("hidden"));
  const t = document.getElementById("tab-" + tab); if (t) t.classList.remove("hidden");
  document.querySelectorAll(".tab").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(el => { if (el.getAttribute("onclick") && el.getAttribute("onclick").includes("'" + tab + "'")) el.classList.add("active"); });
}

async function downloadExport(id, format, kind = "tailored") {
  try {
    const res = await fetch(`/api/export/${id}/${format}?kind=${kind}`, { headers: { Authorization: "Bearer " + state.token } });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `resume_${id}.${format}`;
    document.body.appendChild(a); a.click(); a.remove();
    toast("Downloaded", "success");
  } catch (err) { toast(err.message, "error"); }
}

function copyText(id) {
  const el = document.getElementById(id);
  navigator.clipboard.writeText(el.textContent).then(() => toast("Copied", "success")).catch(() => toast("Copy failed", "error"));
}

// ---------- Resumes ----------
function viewResumes() {
  return `
  <div class="fade-in max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <div><h1 class="text-2xl font-bold">Saved resumes</h1><p class="text-ink-500 text-sm">Store resumes for quick reuse.</p></div>
    </div>
    <div class="card p-5 mb-6">
      <h3 class="font-semibold mb-3">Add a resume</h3>
      <div class="grid gap-3">
        <input id="new-resume-title" class="input" placeholder="Title (e.g. Software Engineer Resume)" />
        <textarea id="new-resume-content" rows="8" class="input font-mono text-sm" placeholder="Paste resume text..."></textarea>
        <div class="flex items-center gap-2 flex-wrap">
          <input type="file" id="new-resume-file" accept=".pdf,.docx,.txt,.md" class="text-sm" />
          <button id="add-resume-btn" class="px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700">Save resume</button>
        </div>
      </div>
    </div>
    <div class="grid sm:grid-cols-2 gap-4">
      ${state.resumes.length ? state.resumes.map(r => `
      <div class="card p-5">
        <div class="flex items-start justify-between">
          <div class="font-semibold">${escapeHtml(r.title)}</div>
          <button onclick="deleteResume(${r.id})" class="text-xs text-red-600 hover:underline">Delete</button>
        </div>
        <p class="text-xs text-ink-400 mt-1">${r.created_at ? fmtDate(r.created_at) : ''}</p>
        <p class="text-sm text-ink-500 mt-2 line-clamp-3">${escapeHtml(r.preview || '')}</p>
      </div>`).join("") : `<p class="text-ink-400 text-sm">No saved resumes yet.</p>`}
    </div>
  </div>`;
}

function bindResumes() {
  document.getElementById("add-resume-btn").addEventListener("click", async () => {
    const title = document.getElementById("new-resume-title").value.trim();
    const content = document.getElementById("new-resume-content").value.trim();
    const file = document.getElementById("new-resume-file").files[0];
    try {
      if (file) {
        const fd = new FormData(); fd.append("file", file); fd.append("title", title || file.name);
        const res = await fetch("/api/resumes/upload", { method: "POST", headers: { Authorization: "Bearer " + state.token }, body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Upload failed");
        toast("Resume uploaded", "success");
      } else {
        if (!content) { toast("Paste content or choose a file", "error"); return; }
        await api("/api/resumes", { method: "POST", body: JSON.stringify({ title: title || "Untitled Resume", content }) });
        toast("Resume saved", "success");
      }
      await loadAll(); render();
    } catch (err) { toast(err.message, "error"); }
  });
}

async function deleteResume(id) {
  if (!confirm("Delete this resume?")) return;
  try { await api("/api/resumes/" + id, { method: "DELETE" }); await loadAll(); render(); toast("Deleted", "success"); }
  catch (err) { toast(err.message, "error"); }
}

// ---------- History ----------
function viewHistory() {
  return `
  <div class="fade-in max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold mb-1">History</h1>
    <p class="text-ink-500 text-sm mb-6">Your past optimizations.</p>
    ${state.optimizations.length ? `
    <div class="space-y-3">
      ${state.optimizations.map(o => `
      <div class="card p-5 flex items-center justify-between gap-4">
        <div class="min-w-0">
          <div class="font-semibold">Optimization #${o.id}</div>
          <div class="text-xs text-ink-400">${fmtDate(o.created_at)} · ATS ${o.ats_score}%</div>
        </div>
        <div class="flex items-center gap-2">
          <button onclick="viewOptimization(${o.id})" class="text-sm px-3 py-1.5 rounded-lg bg-brand-50 text-brand-700 hover:bg-brand-100">Open</button>
          <button onclick="deleteOptimization(${o.id})" class="text-sm px-3 py-1.5 rounded-lg bg-red-50 text-red-700 hover:bg-red-100">Delete</button>
        </div>
      </div>`).join("")}
    </div>` : `<div class="card p-8 text-center text-ink-400">No history yet.</div>`}
  </div>`;
}

async function viewOptimization(id) {
  try {
    const data = await api("/api/optimizations/" + id);
    state.currentOpt = data;
    state.view = "optimize";
    render();
    setTimeout(() => { const el = document.getElementById("opt-result"); if (el) { el.classList.remove("hidden"); renderOptResult(data); } }, 50);
  } catch (err) { toast(err.message, "error"); }
}

async function deleteOptimization(id) {
  if (!confirm("Delete this optimization?")) return;
  try { await api("/api/optimizations/" + id, { method: "DELETE" }); await loadAll(); render(); toast("Deleted", "success"); }
  catch (err) { toast(err.message, "error"); }
}

// ---------- Billing ----------
function viewBilling() {
  return `
  <div class="fade-in max-w-3xl mx-auto">
    <h1 class="text-2xl font-bold mb-1">Billing & plan</h1>
    <p class="text-ink-500 text-sm mb-6">Manage your subscription.</p>
    <div class="card p-6 mb-4">
      <div class="flex items-center justify-between">
        <div>
          <div class="text-sm text-ink-500">Current plan</div>
          <div class="text-2xl font-bold mt-1">${state.user.plan === 'premium' ? 'Premium' : 'Free'}</div>
        </div>
        <span class="px-3 py-1 rounded-full text-sm font-semibold ${state.user.plan==='premium'?'bg-amber-100 text-amber-700':'bg-ink-100 text-ink-600'}">${state.user.plan}</span>
      </div>
      <div class="mt-4 text-sm text-ink-600">
        ${state.user.plan === 'premium' ? 'You have unlimited optimizations, interview prep, and exports.' : 'Free plan: 3 optimizations per month. Upgrade for unlimited + interview prep.'}
      </div>
    </div>
    ${state.user.plan !== 'premium' ? `
    <div class="card p-6">
      <h3 class="font-semibold text-lg">Upgrade to Premium</h3>
      <ul class="mt-3 space-y-2 text-sm text-ink-700">
        <li>✓ Unlimited optimizations</li><li>✓ AI interview prep questions & answers</li><li>✓ PDF & DOCX exports</li><li>✓ Priority support</li>
      </ul>
      <div class="mt-5 flex gap-3 flex-wrap">
        <button id="demo-upgrade-btn" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-brand-700 text-white font-semibold hover:shadow-lg transition">Upgrade (demo)</button>
        <button id="stripe-upgrade-btn" class="px-5 py-2.5 rounded-xl bg-white border border-ink-200 font-semibold hover:bg-ink-50 transition">Pay with Stripe</button>
      </div>
      <p class="mt-3 text-xs text-ink-400">Demo upgrade activates Premium instantly (no payment). Configure Paddle/Paymob for real payments.</p>
    </div>` : `
    <div class="card p-6 text-center">
      <div class="text-4xl mb-2">🎉</div>
      <p class="font-semibold">You're on Premium</p>
      <p class="text-sm text-ink-500 mt-1">Thank you for your support.</p>
    </div>`}
  </div>`;
}

function bindBilling() {
  const demoBtn = document.getElementById("demo-upgrade-btn");
  if (demoBtn) demoBtn.addEventListener("click", async () => {
    try {
      const data = await api("/api/billing/demo-upgrade", { method: "POST" });
      state.user.plan = "premium";
      toast("Upgraded to Premium (demo)", "success");
      await loadAll(); render();
    } catch (err) { toast(err.message, "error"); }
  });
  const stripeBtn = document.getElementById("stripe-upgrade-btn");
  if (stripeBtn) stripeBtn.addEventListener("click", async () => {
    try {
      const data = await api("/api/billing/checkout", { method: "POST", body: JSON.stringify({ provider: "paddle", plan: "monthly" }) });
      if (data.checkout_url) window.location.href = data.checkout_url;
    } catch (err) { toast(err.message, "error"); }
  });
}

// ---------- Profile ----------
function viewProfile() {
  return `
  <div class="fade-in max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold mb-1">Profile</h1>
    <p class="text-ink-500 text-sm mb-6">Your account information.</p>
    <div class="card p-6 space-y-4">
      <div><div class="text-xs text-ink-400">Name</div><div class="font-medium">${escapeHtml(state.user.name||'-')}</div></div>
      <div><div class="text-xs text-ink-400">Email</div><div class="font-medium">${escapeHtml(state.user.email||state.user.username||'-')}</div></div>
      <div><div class="text-xs text-ink-400">Plan</div><div class="font-medium">${state.user.plan}</div></div>
      <div><div class="text-xs text-ink-400">Role</div><div class="font-medium">${state.user.role}</div></div>
      <div><div class="text-xs text-ink-400">Email verified</div><div class="font-medium">${state.user.email_verified ? 'Yes' : 'No'}</div></div>
    </div>
    <div class="card p-6 mt-4">
      <h3 class="font-semibold mb-3">Two-factor authentication (MFA)</h3>
      <p class="text-sm text-ink-500 mb-3">Add an extra layer of security using an authenticator app (Google Authenticator, Authy, etc.).</p>
      <div id="mfa-status" class="text-sm mb-3">Loading...</div>
      <div id="mfa-setup" class="hidden space-y-3">
        <p class="text-sm text-ink-600">Scan this secret in your authenticator app, then enter the 6-digit code to enable:</p>
        <div class="bg-ink-50 rounded-lg p-3 font-mono text-sm break-all" id="mfa-secret"></div>
        <div class="flex gap-2">
          <input id="mfa-code" class="input text-sm" placeholder="6-digit code" />
          <button onclick="enableMfa()" class="px-4 py-2 rounded-lg bg-brand-600 text-white text-sm hover:bg-brand-700">Enable</button>
        </div>
      </div>
      <div id="mfa-disable" class="hidden space-y-3">
        <p class="text-sm text-ink-600">MFA is enabled. Enter a code to disable:</p>
        <div class="flex gap-2">
          <input id="mfa-code2" class="input text-sm" placeholder="6-digit code" />
          <button onclick="disableMfa()" class="px-4 py-2 rounded-lg bg-red-50 text-red-700 text-sm hover:bg-red-100">Disable</button>
        </div>
      </div>
      <div class="flex gap-2 mt-3">
        <button onclick="setupMfa()" class="px-4 py-2 rounded-lg bg-ink-100 text-ink-700 text-sm hover:bg-ink-200">Set up MFA</button>
      </div>
    </div>
    <div class="card p-6 mt-4">
      <h3 class="font-semibold mb-3">Danger zone</h3>
      <button onclick="deleteAccount()" class="px-4 py-2 rounded-lg bg-red-50 text-red-700 text-sm hover:bg-red-100 transition">Delete account</button>
    </div>
  </div>`;
}

async function deleteAccount() {
  if (!confirm("Delete your account and all data? This cannot be undone.")) return;
  try { await api("/api/auth/account", { method: "DELETE" }); toast("Account deleted", "success"); logout(); }
  catch (err) { toast(err.message, "error"); }
}

let _mfaSecret = null;
async function setupMfa() {
  try {
    const data = await api("/api/auth/mfa/setup", { method: "POST" });
    _mfaSecret = data.secret;
    document.getElementById("mfa-secret").textContent = data.secret;
    document.getElementById("mfa-setup").classList.remove("hidden");
    document.getElementById("mfa-disable").classList.add("hidden");
    toast("Scan the secret in your authenticator app", "info");
  } catch (err) { toast(err.message, "error"); }
}
async function enableMfa() {
  const code = document.getElementById("mfa-code").value.trim();
  try {
    await api("/api/auth/mfa/verify", { method: "POST", body: JSON.stringify({ code }) });
    toast("MFA enabled", "success");
    document.getElementById("mfa-setup").classList.add("hidden");
    document.getElementById("mfa-disable").classList.remove("hidden");
    document.getElementById("mfa-status").textContent = "MFA is enabled.";
  } catch (err) { toast(err.message, "error"); }
}
async function disableMfa() {
  const code = document.getElementById("mfa-code2").value.trim();
  try {
    await api("/api/auth/mfa/disable", { method: "POST", body: JSON.stringify({ code }) });
    toast("MFA disabled", "success");
    document.getElementById("mfa-disable").classList.add("hidden");
    document.getElementById("mfa-status").textContent = "MFA is disabled.";
  } catch (err) { toast(err.message, "error"); }
}

// ---------- Init ----------
document.addEventListener("DOMContentLoaded", () => { boot(); });