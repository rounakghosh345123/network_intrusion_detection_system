// Intrushield V2 - frontend logic (plain JavaScript, no libraries)
const API_BASE = "";   // Flask serves this page, so requests go to the same origin

// Simple shared state: the chosen file, the last API result, and model info
const state = { file: null, result: null, featureNames: [], classMapping: {} };

const $ = (id) => document.getElementById(id);   // short helper

const PAGE_TITLES = { overview: "Overview", analyze: "Analyze Traffic", intelligence: "Intelligence", reports: "Reports" };
const ICON_CHECK = '<svg class="icon sm"><use href="#i-check"/></svg>';
const ICON_X = '<svg class="icon sm"><use href="#i-x"/></svg>';

// ---------- Navigation: show one page, highlight its sidebar item ----------
function showPage(pageName) {
  document.querySelectorAll(".page").forEach((p) => p.classList.toggle("active", p.id === "page-" + pageName));
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.page === pageName));
  $("pageTitle").textContent = PAGE_TITLES[pageName];
}
document.querySelectorAll(".nav-item").forEach((b) => b.addEventListener("click", () => showPage(b.dataset.page)));
document.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => showPage(b.dataset.goto)));

// ---------- Load model status and info from Flask (/health and /model-info) ----------
async function loadModelInfo() {
  try {
    const health = await (await fetch(API_BASE + "/health")).json();
    setStatus("online", "Model Online");
    $("sideModelMeta").textContent = health.classes + " classes · " + health.features + " features";
    $("engClasses").textContent = health.classes;
    $("engFeatures").textContent = health.features;
    $("engStatus").innerHTML = '<span class="pill safe">ONLINE</span>';

    const info = await (await fetch(API_BASE + "/model-info")).json();
    state.featureNames = info.feature_names;
    state.classMapping = info.class_mapping;
    drawCoverage();
  } catch (err) {
    setStatus("offline", "Model Offline");
    $("engStatus").innerHTML = '<span class="pill attack">OFFLINE</span>';
  }
}

function setStatus(kind, text) {
  ["sideStatusDot", "topStatusDot"].forEach((id) => ($(id).className = "dot " + kind));
  $("sideStatusText").textContent = text.replace("Model ", "");
  $("topStatusText").textContent = text;
}

// Detection Coverage grid: BENIGN in teal, attack classes in red
function drawCoverage() {
  const ids = Object.keys(state.classMapping).sort((a, b) => a - b);
  $("coverageGrid").innerHTML = ids.map((id) => {
    const label = state.classMapping[id];
    const color = label.toUpperCase() === "BENIGN" ? "safe" : "danger";
    return `<div class="coverage-item"><i class="swatch ${color}"></i>${escapeHtml(label)}</div>`;
  }).join("");
}

// ---------- File selection: click, keyboard, drag and drop ----------
const dropZone = $("dropZone"), fileInput = $("fileInput");
dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); } });
fileInput.addEventListener("change", () => { if (fileInput.files[0]) handleFile(fileInput.files[0]); });
["dragenter", "dragover"].forEach((ev) => dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.add("dragover"); }));
["dragleave", "drop"].forEach((ev) => dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.remove("dragover"); }));
dropZone.addEventListener("drop", (e) => { if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); });
$("removeBtn").addEventListener("click", removeFile);
$("analyzeBtn").addEventListener("click", analyzeFile);

// Show the file card and check the CSV header against the model's required features
async function handleFile(file) {
  hideMessages();
  if (!file.name.toLowerCase().endsWith(".csv")) {
    removeFile();
    showError("Please upload a CSV file.");
    return;
  }
  state.file = file;
  $("fileCard").hidden = false;
  $("fileName").textContent = file.name;
  $("fileMeta").textContent = formatSize(file.size);
  setCompat("Checking...", "");
  $("analyzeBtn").disabled = false;

  // Read the header line (first 200 KB is enough) to count columns
  const head = await file.slice(0, 200000).text();
  const columns = head.split(/\r?\n/)[0].split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
  let rowsText = "";
  if (file.size <= 100 * 1024 * 1024) {
    const text = await file.text();
    const rows = Math.max(text.split("\n").filter((l) => l.trim()).length - 1, 0);
    rowsText = " · " + rows.toLocaleString() + " rows";
  }
  $("fileMeta").textContent = formatSize(file.size) + rowsText + " · " + columns.length + " columns";

  const missing = state.featureNames.filter((f) => !columns.includes(f));
  if (state.featureNames.length === 0) setCompat("Could not verify features (server offline?)", "");
  else if (missing.length === 0) setCompat(ICON_CHECK + " Compatible - all " + state.featureNames.length + " features found", "ok");
  else setCompat(ICON_X + " Missing required features (" + missing.length + ")", "bad");
}

function setCompat(html, kind) { $("fileCompat").innerHTML = html; $("fileCompat").className = "file-compat " + kind; }

function removeFile() {
  state.file = null;
  fileInput.value = "";
  $("fileCard").hidden = true;
  hideMessages();
}

// ---------- Send the CSV to Flask (POST /predict, FormData field "file") ----------
async function analyzeFile() {
  if (!state.file) return;
  hideMessages();
  setLoading(true);

  const formData = new FormData();
  formData.append("file", state.file);

  try {
    const response = await fetch(API_BASE + "/predict", { method: "POST", body: formData });
    const result = await response.json();
    if (!result.success) {
      let msg = result.error;
      if (result.missing_features) msg += " Missing: " + result.missing_features.slice(0, 6).join(", ") + (result.missing_features.length > 6 ? ", ..." : "");
      showError(msg);
    } else {
      state.result = result;
      updateDashboard(result);
      $("successBox").textContent = "Analysis complete. " + result.rows_analyzed.toLocaleString() + " network flows classified. View the Overview page for results.";
      $("successBox").hidden = false;
    }
  } catch (err) {
    showError("Could not reach the server. Is backend/app.py running?");
  }
  setLoading(false);
}

function setLoading(on) {
  $("analyzeBtn").disabled = on;
  $("spinner").hidden = !on;
  $("analyzeLabel").textContent = on ? "Analyzing..." : "Analyze Traffic";
}

// ---------- Update every dashboard section from the real API response ----------
function updateDashboard(r) {
  const total = r.rows_analyzed;
  const benignPct = (r.benign_count / total) * 100;
  const attackPct = (r.attack_count / total) * 100;

  $("overviewEmpty").hidden = true;
  $("totalFlows").textContent = total.toLocaleString();
  $("totalSub").textContent = "Current analysis";
  $("benignCount").textContent = r.benign_count.toLocaleString();
  $("benignSub").textContent = benignPct.toFixed(1) + "% of traffic";
  $("attackCount").textContent = r.attack_count.toLocaleString();
  $("attackSub").textContent = attackPct.toFixed(1) + "% of traffic";
  $("avgConfidence").textContent = (r.average_confidence * 100).toFixed(1) + "%";

  updateTrafficOverview(r, benignPct, attackPct);
  updateThreatDistribution(r);
  updatePredictionTable(r);

  // Reports: enable exports
  $("exportCsvBtn").disabled = false;
  $("exportSummaryBtn").disabled = false;
  $("reportHint").textContent = "Latest analysis: " + total.toLocaleString() + " flows, " + r.attack_count.toLocaleString() + " attacks.";
}

function updateTrafficOverview(r, benignPct, attackPct) {
  $("benignVal").textContent = r.benign_count.toLocaleString();
  $("attackVal").textContent = r.attack_count.toLocaleString();
  $("benignPct").textContent = benignPct.toFixed(1) + "%";
  $("attackPct").textContent = attackPct.toFixed(1) + "%";
  $("benignBar").style.height = benignPct + "%";
  $("attackBar").style.height = attackPct + "%";
}

function updateThreatDistribution(r) {
  // Only attack classes actually returned by the backend (everything except BENIGN)
  const attacks = Object.entries(r.distribution).filter(([label]) => label.toUpperCase() !== "BENIGN").sort((a, b) => b[1] - a[1]);
  if (attacks.length === 0) {
    $("threatList").innerHTML = '<div class="empty-state good"><svg class="icon"><use href="#i-check"/></svg><strong>No threats detected in this analysis.</strong></div>';
    return;
  }
  $("threatList").innerHTML = attacks.map(([label, count]) => `
    <div class="threat-row">
      <i class="swatch"></i><span>${escapeHtml(label)}</span><span class="threat-count">${count.toLocaleString()}</span>
      <div class="threat-bar"><div style="width:${(count / r.attack_count) * 100}%"></div></div>
    </div>`).join("");
}

function updatePredictionTable(r) {
  const time = new Date().toLocaleTimeString("en-GB");   // time the analysis finished
  $("recentBody").innerHTML = r.predictions.map((p) => {
    const isAttack = p.status === "ATTACK";
    return `<tr>
      <td class="num">${time}</td>
      <td>${escapeHtml(p.label)}</td>
      <td class="num">${(p.confidence * 100).toFixed(1)}%</td>
      <td><span class="pill ${isAttack ? "attack" : "safe"}">${isAttack ? "ATTACK" : "SAFE"}</span></td>
    </tr>`;
  }).join("");
}

// ---------- Report export: build CSV files in the browser from the API result ----------
function downloadCsv(filename, rows) {
  const csv = rows.map((r) => r.map((v) => '"' + String(v).replace(/"/g, '""') + '"').join(",")).join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function exportPredictions() {
  if (!state.result) return;
  const rows = [["row", "class_id", "label", "confidence", "status"]];
  state.result.predictions.forEach((p) => rows.push([p.row, p.class_id, p.label, p.confidence, p.status]));
  downloadCsv("intrushield_predictions.csv", rows);
}

function exportSummary() {
  if (!state.result) return;
  const r = state.result;
  const rows = [["metric", "value"], ["rows_analyzed", r.rows_analyzed], ["benign_count", r.benign_count],
    ["attack_count", r.attack_count], ["average_confidence", r.average_confidence]];
  Object.entries(r.distribution).forEach(([label, n]) => rows.push(["class: " + label, n]));
  downloadCsv("intrushield_summary.csv", rows);
}
$("exportCsvBtn").addEventListener("click", exportPredictions);
$("exportSummaryBtn").addEventListener("click", exportSummary);

// ---------- Small helpers ----------
function showError(msg) { $("errorBox").textContent = msg; $("errorBox").hidden = false; }
function hideMessages() { $("errorBox").hidden = true; $("successBox").hidden = true; }
function formatSize(bytes) { return bytes > 1048576 ? (bytes / 1048576).toFixed(1) + " MB" : (bytes / 1024).toFixed(1) + " KB"; }
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

loadModelInfo();
