/**
 * Sentinel Dashboard — Client-side application.
 * Vanilla TypeScript, no frameworks. Connects to FastAPI backend via REST + SSE.
 */

// ── Configuration ────────────────────────────────────────────────────────────

const API_BASE = "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────────────────────

interface TriggerResponse {
  run_id: string;
  status: string;
}

interface SSEEvent {
  type: string;
  message: string;
  data: Record<string, unknown>;
  timestamp: number;
}

interface IntegrationStatus {
  name: string;
  status: "active" | "partial" | "inactive";
  role: string;
  detail: string;
}

interface RunStatus {
  status: string;
  start_time: number;
  end_time: number;
  duration_seconds: number;
  total_breach_records: number;
  total_matches: number;
  critical_count: number;
  warning_count: number;
  incident_report: Record<string, unknown>;
  accounts_locked: number;
  sessions_revoked: number;
  calls_initiated: number;
  lock_failures: number;
  call_failures: number;
  events: Record<string, unknown>[];
}

// ── State ────────────────────────────────────────────────────────────────────

let currentRunId: string | null = null;
let eventSource: EventSource | null = null;
let isRunning = false;
let backendConnected = false;
let uploadedCSV: File | null = null;

// Metric targets for counter animation
const metricTargets = {
  records: 0,
  matches: 0,
  critical: 0,
  locked: 0,
  called: 0,
};
const metricCurrent = {
  records: 0,
  matches: 0,
  critical: 0,
  locked: 0,
  called: 0,
};

// ── DOM References ───────────────────────────────────────────────────────────

const $ = (id: string) => document.getElementById(id) as HTMLElement;

const dom = {
  sidebar: $("sidebar"),
  sidebarToggle: $("sidebar-toggle"),
  sidebarClose: $("sidebar-close"),
  integrationsList: $("integrations-list"),
  globalStatus: $("global-status"),
  globalStatusText: $("global-status-text"),
  phaseIngest: $("phase-ingest"),
  phaseResearch: $("phase-research"),
  phaseRespond: $("phase-respond"),
  phaseIngestLabel: $("phase-ingest-label"),
  phaseResearchLabel: $("phase-research-label"),
  phaseRespondLabel: $("phase-respond-label"),
  connector12: $("connector-1-2"),
  connector23: $("connector-2-3"),
  metricRecords: $("metric-records"),
  metricMatches: $("metric-matches"),
  metricCritical: $("metric-critical"),
  metricLocked: $("metric-locked"),
  metricCalled: $("metric-called"),
  eventLog: $("event-log"),
  eventLogEmpty: $("event-log-empty"),
  reportContent: $("report-content"),
  classificationContent: $("classification-content"),
  triggerBtn: $("trigger-btn") as HTMLButtonElement,
  csvUpload: $("csv-upload") as HTMLInputElement,
  csvUploadBtn: $("csv-upload-btn"),
  useSample: $("use-sample") as HTMLInputElement,
  connectionBar: $("connection-bar"),
  connectionText: $("connection-text"),
};

// ── Sidebar Toggle ───────────────────────────────────────────────────────────

dom.sidebarClose.addEventListener("click", () => {
  dom.sidebar.classList.add("collapsed");
});

dom.sidebarToggle.addEventListener("click", () => {
  dom.sidebar.classList.remove("collapsed");
});

// ── File Upload ──────────────────────────────────────────────────────────────

dom.csvUploadBtn.addEventListener("click", () => {
  dom.csvUpload.click();
});

dom.csvUpload.addEventListener("change", () => {
  const files = dom.csvUpload.files;
  if (files && files.length > 0) {
    uploadedCSV = files[0];
    dom.csvUploadBtn.innerHTML = `&#x2705; ${uploadedCSV.name}`;
    dom.csvUploadBtn.classList.add("has-file");
    // Uncheck sample data when a file is uploaded
    dom.useSample.checked = false;
  }
});

// ── Connection Check ─────────────────────────────────────────────────────────

async function checkBackendConnection(): Promise<void> {
  try {
    const resp = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(3000) });
    if (resp.ok) {
      backendConnected = true;
      dom.connectionBar.className = "connection-bar connected";
      dom.connectionText.textContent = "Backend connected — Sentinel ready";
    } else {
      throw new Error("Not OK");
    }
  } catch {
    backendConnected = false;
    dom.connectionBar.className = "connection-bar disconnected";
    dom.connectionText.textContent = "Backend offline — Waiting for connection at localhost:8000...";
  }
}

// Poll backend connection every 5s if not connected
setInterval(() => {
  if (!backendConnected) {
    checkBackendConnection();
  }
}, 5000);

// ── Integration Status ───────────────────────────────────────────────────────

async function loadIntegrations(): Promise<void> {
  try {
    const resp = await fetch(`${API_BASE}/api/integrations`, { signal: AbortSignal.timeout(5000) });
    if (!resp.ok) throw new Error("Failed to fetch");
    const data = await resp.json() as { integrations: IntegrationStatus[] };
    renderIntegrations(data.integrations);
  } catch {
    // Show default integrations with unknown status
    renderIntegrations(getDefaultIntegrations());
  }
}

function getDefaultIntegrations(): IntegrationStatus[] {
  return [
    { name: "Ghost DB", status: "inactive", role: "Core Postgres database", detail: "" },
    { name: "Auth0", status: "inactive", role: "Account lockdown", detail: "" },
    { name: "Bland AI", status: "inactive", role: "Phone notifications", detail: "" },
    { name: "Overmind", status: "inactive", role: "Decision tracing", detail: "" },
    { name: "Truefoundry", status: "inactive", role: "LLM gateway", detail: "" },
    { name: "Aerospike", status: "inactive", role: "Fast email lookup", detail: "" },
    { name: "Airbyte", status: "inactive", role: "CSV ingestion", detail: "" },
    { name: "Senso", status: "inactive", role: "Context retrieval", detail: "" },
  ];
}

function renderIntegrations(integrations: IntegrationStatus[]): void {
  dom.integrationsList.innerHTML = integrations.map((ig) => `
    <div class="integration-item" title="${ig.detail || ig.role}">
      <div class="integration-dot ${ig.status}"></div>
      <div class="integration-info">
        <div class="integration-name">${escapeHtml(ig.name)}</div>
        <div class="integration-role">${escapeHtml(ig.role)}</div>
      </div>
    </div>
  `).join("");
}

// ── Trigger ──────────────────────────────────────────────────────────────────

dom.triggerBtn.addEventListener("click", () => {
  if (isRunning) return;
  triggerSentinel();
});

async function triggerSentinel(): Promise<void> {
  if (!backendConnected) {
    addEventLine("error", "Backend is not connected. Cannot trigger.");
    return;
  }

  // Reset UI
  resetDashboard();
  setRunning(true);

  try {
    const body: Record<string, unknown> = {
      breach_source: "DarkForum X",
      use_sample: dom.useSample.checked,
    };

    const resp = await fetch(`${API_BASE}/api/trigger`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`Trigger failed: ${resp.status} — ${errText}`);
    }

    const data = (await resp.json()) as TriggerResponse;
    currentRunId = data.run_id;

    addEventLine("setup", `Sentinel triggered. Run ID: ${currentRunId}`);
    connectSSE(currentRunId);
  } catch (err) {
    addEventLine("error", `Failed to trigger: ${err}`);
    setRunning(false);
  }
}

// ── SSE Connection ───────────────────────────────────────────────────────────

function connectSSE(runId: string): void {
  if (eventSource) {
    eventSource.close();
  }

  const url = `${API_BASE}/api/events/${runId}`;
  eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const evt = JSON.parse(event.data) as SSEEvent;
      handleSSEEvent(evt);
    } catch (e) {
      console.error("Failed to parse SSE event:", e);
    }
  };

  eventSource.onerror = () => {
    // SSE connection closed — could be normal end or error
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    // If still running, try fetching final status
    if (isRunning && currentRunId) {
      fetchFinalStatus(currentRunId);
    }
  };
}

function handleSSEEvent(evt: SSEEvent): void {
  // Add to event log
  addEventLine(evt.type, evt.message);

  // Update phases based on event type
  const evtType = evt.type;

  if (evtType === "setup") {
    setPhase("ingest", "active");
  } else if (evtType === "ingest") {
    setPhase("ingest", "active");
    if (evt.data && typeof evt.data.count === "number") {
      animateMetric("records", evt.data.count as number);
    }
  } else if (evtType === "matching") {
    setPhase("ingest", "active");
    if (evt.data) {
      if (typeof evt.data.total === "number") animateMetric("matches", evt.data.total as number);
      if (typeof evt.data.critical === "number") animateMetric("critical", evt.data.critical as number);
    }
  } else if (evtType === "research") {
    setPhase("ingest", "done");
    setPhase("research", "active");
    if (evt.data && evt.data.cve_id) {
      updateIncidentReport(evt.data);
    }
  } else if (evtType === "lockdown") {
    setPhase("research", "done");
    setPhase("respond", "active");
    if (evt.data && typeof evt.data.locked === "number") {
      animateMetric("locked", evt.data.locked as number);
    }
  } else if (evtType === "notify") {
    setPhase("respond", "active");
    if (evt.data && typeof evt.data.calls_initiated === "number") {
      animateMetric("called", evt.data.calls_initiated as number);
    }
  } else if (evtType === "complete") {
    setPhase("respond", "done");
    setRunning(false);
    setGlobalStatus("complete");
    // Fetch final status for the full report
    if (currentRunId) {
      fetchFinalStatus(currentRunId);
    }
  } else if (evtType === "error") {
    setGlobalStatus("error");
    setRunning(false);
  }
}

// ── Fetch Final Status ───────────────────────────────────────────────────────

async function fetchFinalStatus(runId: string): Promise<void> {
  try {
    const resp = await fetch(`${API_BASE}/api/status/${runId}`);
    if (!resp.ok) return;
    const data = (await resp.json()) as RunStatus;

    // Update all metrics from final data
    animateMetric("records", data.total_breach_records);
    animateMetric("matches", data.total_matches);
    animateMetric("critical", data.critical_count);
    animateMetric("locked", data.accounts_locked);
    animateMetric("called", data.calls_initiated);

    // Update phases
    if (data.status === "complete" || data.status === "complete_no_matches") {
      setPhase("ingest", "done");
      setPhase("research", "done");
      setPhase("respond", "done");
      setGlobalStatus("complete");
    } else if (data.status === "error") {
      setGlobalStatus("error");
    }

    // Update incident report
    if (data.incident_report && Object.keys(data.incident_report).length > 0) {
      renderFullIncidentReport(data.incident_report);
    }

    setRunning(false);
  } catch (e) {
    console.error("Failed to fetch final status:", e);
    setRunning(false);
  }
}

// ── Phase Management ─────────────────────────────────────────────────────────

type PhaseState = "pending" | "active" | "done" | "error";

function setPhase(phase: "ingest" | "research" | "respond", state: PhaseState): void {
  const circleId = `phase-${phase}`;
  const labelId = `phase-${phase}-label`;
  const circle = $(circleId);
  const label = $(labelId);

  circle.className = `phase-circle ${state}`;
  label.className = `phase-label ${state}`;

  // Update circle content
  if (state === "done") {
    circle.innerHTML = "&#x2713;";
  } else if (state === "active") {
    const num = phase === "ingest" ? "1" : phase === "research" ? "2" : "3";
    circle.textContent = num;
  } else if (state === "error") {
    circle.innerHTML = "&#x2717;";
  }

  // Update connectors
  if (phase === "research" && (state === "active" || state === "done")) {
    dom.connector12.className = state === "done" ? "phase-connector done" : "phase-connector active";
  }
  if (phase === "respond" && (state === "active" || state === "done")) {
    dom.connector12.className = "phase-connector done";
    dom.connector23.className = state === "done" ? "phase-connector done" : "phase-connector active";
  }
}

function setGlobalStatus(status: "idle" | "running" | "complete" | "error"): void {
  dom.globalStatus.className = `status-indicator ${status}`;
  const labels: Record<string, string> = {
    idle: "IDLE",
    running: "RUNNING",
    complete: "COMPLETE",
    error: "ERROR",
  };
  dom.globalStatusText.textContent = labels[status] || status.toUpperCase();
}

function setRunning(running: boolean): void {
  isRunning = running;
  dom.triggerBtn.disabled = running;
  if (running) {
    dom.triggerBtn.classList.remove("pulsing");
    dom.triggerBtn.classList.add("running");
    dom.triggerBtn.innerHTML = "&#x23F3; SENTINEL RUNNING...";
    setGlobalStatus("running");
  } else {
    dom.triggerBtn.classList.remove("running");
    dom.triggerBtn.classList.add("pulsing");
    dom.triggerBtn.disabled = false;
    dom.triggerBtn.innerHTML = "&#x26a1; TRIGGER SENTINEL";
  }
}

// ── Event Log ────────────────────────────────────────────────────────────────

function addEventLine(type: string, message: string): void {
  // Remove empty placeholder
  if (dom.eventLogEmpty) {
    dom.eventLogEmpty.style.display = "none";
  }

  const now = new Date();
  const ts = now.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const line = document.createElement("div");
  line.className = "event-line";
  line.innerHTML = `
    <span class="event-timestamp">${ts}</span>
    <span class="event-tag ${escapeHtml(type)}">${escapeHtml(type)}</span>
    <span class="event-message">${escapeHtml(message)}</span>
  `;

  dom.eventLog.appendChild(line);

  // Auto-scroll to bottom
  dom.eventLog.scrollTop = dom.eventLog.scrollHeight;
}

// ── Metric Animation ─────────────────────────────────────────────────────────

function animateMetric(metric: keyof typeof metricTargets, target: number): void {
  metricTargets[metric] = target;
}

function tickMetrics(): void {
  let needsAnotherFrame = false;

  for (const key of Object.keys(metricTargets) as (keyof typeof metricTargets)[]) {
    const target = metricTargets[key];
    const current = metricCurrent[key];

    if (current !== target) {
      // Animate: move ~10% of the remaining distance each frame, minimum 1
      const diff = target - current;
      const step = Math.max(1, Math.ceil(Math.abs(diff) * 0.12));
      metricCurrent[key] = diff > 0 ? Math.min(target, current + step) : Math.max(target, current - step);
      needsAnotherFrame = true;

      // Update DOM
      const el = {
        records: dom.metricRecords,
        matches: dom.metricMatches,
        critical: dom.metricCritical,
        locked: dom.metricLocked,
        called: dom.metricCalled,
      }[key];

      el.textContent = metricCurrent[key].toLocaleString();
    }
  }

  requestAnimationFrame(tickMetrics);
}

// Start the metric animation loop
requestAnimationFrame(tickMetrics);

// ── Incident Report ──────────────────────────────────────────────────────────

function updateIncidentReport(data: Record<string, unknown>): void {
  if (data.cve_id || data.attack_vector || data.severity) {
    const partialHtml = buildReportField("CVE", data.cve_id as string, true) +
      buildReportField("Attack Vector", data.attack_vector as string) +
      buildSeverityField(data.severity as string);

    dom.reportContent.innerHTML = partialHtml;
  }
}

function renderFullIncidentReport(report: Record<string, unknown>): void {
  let html = "";

  if (report.cve_id) {
    html += buildReportField("CVE", report.cve_id as string, true);
  }
  if (report.attack_vector) {
    html += buildReportField("Attack Vector", report.attack_vector as string);
  }
  if (report.severity) {
    html += buildSeverityField(report.severity as string);
  }
  if (report.affected_software) {
    const software = report.affected_software;
    const softwareStr = Array.isArray(software) ? software.join(", ") : String(software);
    html += buildReportField("Affected Software", softwareStr);
  }
  if (report.recommended_patches) {
    const patches = report.recommended_patches as string[];
    if (patches.length > 0) {
      html += `
        <div class="report-field">
          <div class="report-label">Recommended Patches</div>
          <ul class="patch-list">
            ${patches.map((p) => `<li class="patch-item">${escapeHtml(String(p))}</li>`).join("")}
          </ul>
        </div>
      `;
    }
  }
  if (report.summary) {
    html += buildReportField("Summary", report.summary as string);
  }
  if (report.incident_type) {
    updateClassification(report.incident_type as string, report.attack_vector as string);
  }

  if (html) {
    dom.reportContent.innerHTML = html;
  }
}

function buildReportField(label: string, value: string, isCode = false): string {
  if (!value) return "";
  const valueHtml = isCode
    ? `<code>${escapeHtml(value)}</code>`
    : escapeHtml(value);
  return `
    <div class="report-field">
      <div class="report-label">${escapeHtml(label)}</div>
      <div class="report-value">${valueHtml}</div>
    </div>
  `;
}

function buildSeverityField(severity: string): string {
  if (!severity) return "";
  const badgeClass = severity.toLowerCase();
  return `
    <div class="report-field">
      <div class="report-label">Severity</div>
      <div class="report-value">
        <span class="severity-badge ${badgeClass}">${escapeHtml(severity.toUpperCase())}</span>
      </div>
    </div>
  `;
}

// ── Incident Classification ──────────────────────────────────────────────────

const classificationIcons: Record<string, string> = {
  "credential_stuffing": "\u{1F511}",
  "credential stuffing": "\u{1F511}",
  "phishing": "\u{1F3A3}",
  "sql_injection": "\u{1F489}",
  "sql injection": "\u{1F489}",
  "ransomware": "\u{1F4B0}",
  "insider_threat": "\u{1F575}",
  "insider threat": "\u{1F575}",
  "zero_day": "\u{1F4A3}",
  "zero day": "\u{1F4A3}",
  "supply_chain": "\u{1F517}",
  "supply chain": "\u{1F517}",
  "brute_force": "\u{1F528}",
  "brute force": "\u{1F528}",
  "data_exfiltration": "\u{1F4E4}",
  "data exfiltration": "\u{1F4E4}",
  "default": "\u{26A0}\u{FE0F}",
};

const classificationDescs: Record<string, string> = {
  "credential_stuffing": "Automated injection of stolen username/password pairs to fraudulently access accounts.",
  "credential stuffing": "Automated injection of stolen username/password pairs to fraudulently access accounts.",
  "phishing": "Social engineering attack using fraudulent communications to extract sensitive information.",
  "sql_injection": "Exploitation of SQL vulnerabilities to access or modify backend databases.",
  "sql injection": "Exploitation of SQL vulnerabilities to access or modify backend databases.",
  "ransomware": "Malicious software encrypting data with ransom demands for decryption keys.",
  "insider_threat": "Security threat originating from within the organization by authorized users.",
  "insider threat": "Security threat originating from within the organization by authorized users.",
  "zero_day": "Exploitation of previously unknown software vulnerability before patch availability.",
  "zero day": "Exploitation of previously unknown software vulnerability before patch availability.",
  "supply_chain": "Attack targeting less-secure elements in the software or hardware supply chain.",
  "supply chain": "Attack targeting less-secure elements in the software or hardware supply chain.",
  "brute_force": "Systematic exhaustive attempt of all possible passwords or encryption keys.",
  "brute force": "Systematic exhaustive attempt of all possible passwords or encryption keys.",
  "data_exfiltration": "Unauthorized transfer of data from within an organization to an external destination.",
  "data exfiltration": "Unauthorized transfer of data from within an organization to an external destination.",
};

function updateClassification(incidentType: string, attackVector?: string): void {
  const key = incidentType.toLowerCase();
  const icon = classificationIcons[key] || classificationIcons["default"];
  const desc = classificationDescs[key] || attackVector || "Unclassified incident type.";
  const displayName = incidentType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  dom.classificationContent.innerHTML = `
    <div class="classification-type">
      <span class="classification-icon">${icon}</span>
      <div>
        <div class="classification-label">${escapeHtml(displayName)}</div>
        <div class="classification-desc">${escapeHtml(String(desc))}</div>
      </div>
    </div>
  `;
}

// ── Reset ────────────────────────────────────────────────────────────────────

function resetDashboard(): void {
  // Reset phases
  for (const phase of ["ingest", "research", "respond"] as const) {
    const circle = $(`phase-${phase}`);
    const label = $(`phase-${phase}-label`);
    circle.className = "phase-circle pending";
    label.className = "phase-label";
    const num = phase === "ingest" ? "1" : phase === "research" ? "2" : "3";
    circle.textContent = num;
  }
  dom.connector12.className = "phase-connector pending";
  dom.connector23.className = "phase-connector pending";

  // Reset metrics
  for (const key of Object.keys(metricTargets) as (keyof typeof metricTargets)[]) {
    metricTargets[key] = 0;
    metricCurrent[key] = 0;
  }
  dom.metricRecords.textContent = "0";
  dom.metricMatches.textContent = "0";
  dom.metricCritical.textContent = "0";
  dom.metricLocked.textContent = "0";
  dom.metricCalled.textContent = "0";

  // Reset event log
  dom.eventLog.innerHTML = "";
  if (dom.eventLogEmpty) {
    dom.eventLogEmpty.style.display = "none";
  }

  // Reset report
  dom.reportContent.innerHTML = `<div class="report-empty">Awaiting incident data...</div>`;
  dom.classificationContent.innerHTML = `<div class="report-empty">Classification will appear after research phase.</div>`;

  // Reset global status
  setGlobalStatus("idle");

  // Close existing SSE
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  currentRunId = null;
}

// ── Utilities ────────────────────────────────────────────────────────────────

function escapeHtml(str: string): string {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── Init ─────────────────────────────────────────────────────────────────────

async function init(): Promise<void> {
  await checkBackendConnection();
  loadIntegrations();
}

init();
