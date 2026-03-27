/**
 * Sentinel Dashboard — Client-side application.
 * Vanilla TypeScript, no frameworks. Connects to FastAPI backend via REST + SSE.
 *
 * Features:
 *   - Agent activity feed with tool-branded event lines
 *   - Tool call summary with real-time counts per sponsor
 *   - Structured incident report with compliance badges
 *   - Response time tracking and industry comparison
 *   - Scenario selector and call status
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

interface ScenarioOption {
  id: string;
  name: string;
  description?: string;
}

// ── Sponsor Tool Mapping ─────────────────────────────────────────────────────

interface SponsorTool {
  name: string;
  color: string;
}

const SPONSOR_TOOLS: Record<string, SponsorTool> = {
  "ghost-db":     { name: "Ghost DB",     color: "#7C3AED" },
  "aerospike":    { name: "Aerospike",    color: "#FF3B3B" },
  "auth0":        { name: "Auth0",        color: "#EB5424" },
  "bland-ai":     { name: "Bland AI",     color: "#2563EB" },
  "claude":       { name: "Claude",       color: "#D4A574" },
  "senso":        { name: "Senso",        color: "#10B981" },
  "overmind":     { name: "Overmind",     color: "#6366F1" },
  "truefoundry":  { name: "Truefoundry",  color: "#F59E0B" },
};

// Map event types to their primary sponsor tool(s)
const EVENT_TO_TOOLS: Record<string, string[]> = {
  "setup":    ["ghost-db"],
  "ingest":   ["ghost-db"],
  "matching": ["aerospike"],
  "research": ["claude", "senso"],
  "lockdown": ["auth0"],
  "notify":   ["bland-ai"],
  "complete": ["ghost-db"],
};

// ── Compliance Framework Mapping ─────────────────────────────────────────────

interface ComplianceFramework {
  name: string;
  cssClass: string;
  deadline: string;
}

const COMPLIANCE_FRAMEWORKS: Record<string, ComplianceFramework> = {
  "GDPR":    { name: "GDPR",    cssClass: "gdpr",  deadline: "72h" },
  "HIPAA":   { name: "HIPAA",   cssClass: "hipaa",  deadline: "60d" },
  "CCPA":    { name: "CCPA",    cssClass: "ccpa",   deadline: "72h" },
  "PCI-DSS": { name: "PCI-DSS", cssClass: "pci",    deadline: "72h" },
  "FERPA":   { name: "FERPA",   cssClass: "ferpa",  deadline: "72h" },
};

// Determine applicable frameworks from incident type and data classes
function determineCompliance(incidentType?: string, dataClasses?: string[]): string[] {
  const frameworks: Set<string> = new Set();
  const type = (incidentType || "").toLowerCase();
  const classes = (dataClasses || []).map((c) => c.toLowerCase());

  // Credential-related incidents
  if (type.includes("credential") || type.includes("stuffing") || type.includes("brute_force") ||
      classes.some((c) => c.includes("credential") || c.includes("password") || c.includes("email"))) {
    frameworks.add("GDPR");
    frameworks.add("CCPA");
  }

  // Health data
  if (classes.some((c) => c.includes("health") || c.includes("medical") || c.includes("hipaa"))) {
    frameworks.add("HIPAA");
  }

  // Education data
  if (classes.some((c) => c.includes("education") || c.includes("student") || c.includes("ferpa"))) {
    frameworks.add("FERPA");
  }

  // Payment / financial
  if (classes.some((c) => c.includes("payment") || c.includes("card") || c.includes("financial") || c.includes("pci"))) {
    frameworks.add("PCI-DSS");
  }

  // Default: always include GDPR for personal data breaches
  if (frameworks.size === 0) {
    frameworks.add("GDPR");
    frameworks.add("CCPA");
  }

  return Array.from(frameworks);
}

// ── State ────────────────────────────────────────────────────────────────────

let currentRunId: string | null = null;
let eventSource: EventSource | null = null;
let isRunning = false;
let backendConnected = false;
let uploadedCSV: File | null = null;
let runStartTime: number | null = null;
let responseTimerInterval: ReturnType<typeof setInterval> | null = null;
let callActive = false;

// Tool call counts — increments as events arrive
const toolCallCounts: Record<string, number> = {};

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
  metricRecords: $("metric-records"),
  metricMatches: $("metric-matches"),
  metricCritical: $("metric-critical"),
  metricLocked: $("metric-locked"),
  metricCalled: $("metric-called"),
  metricResponseTime: $("metric-response-time"),
  eventLog: $("event-log"),
  eventLogEmpty: $("event-log-empty"),
  toolCallSummary: $("tool-call-summary"),
  reportContent: $("report-content"),
  reportHeader: $("report-header"),
  callStatusBody: $("call-status-body"),
  sentinelTimeBar: $("sentinel-time-bar"),
  sentinelTimeValue: $("sentinel-time-value"),
  triggerBtn: $("trigger-btn") as HTMLButtonElement,
  callTestBtn: $("call-test-btn") as HTMLButtonElement,
  csvUpload: $("csv-upload") as HTMLInputElement,
  csvUploadBtn: $("csv-upload-btn"),
  scenarioSelect: $("scenario-select") as HTMLSelectElement,
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
    dom.csvUploadBtn.innerHTML = `&#x2705; ${escapeHtml(uploadedCSV.name)}`;
    dom.csvUploadBtn.classList.add("has-file");
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
    <div class="integration-item" title="${escapeHtml(ig.detail || ig.role)}">
      <div class="integration-dot ${ig.status}"></div>
      <div class="integration-info">
        <div class="integration-name">${escapeHtml(ig.name)}</div>
        <div class="integration-role">${escapeHtml(ig.role)}</div>
      </div>
    </div>
  `).join("");
}

// ── Scenario Loading ─────────────────────────────────────────────────────────

async function loadScenarios(): Promise<void> {
  try {
    const resp = await fetch(`${API_BASE}/api/scenarios`, { signal: AbortSignal.timeout(5000) });
    if (!resp.ok) throw new Error("Failed to fetch scenarios");
    const data = await resp.json() as { scenarios: ScenarioOption[] };
    renderScenarios(data.scenarios);
  } catch {
    // Keep default options
    renderScenarios([
      { id: "default", name: "Default" },
      { id: "credential_stuffing", name: "Credential Stuffing" },
      { id: "phishing", name: "Phishing" },
    ]);
  }
}

function renderScenarios(scenarios: ScenarioOption[]): void {
  dom.scenarioSelect.innerHTML = scenarios.map((s) =>
    `<option value="${escapeHtml(s.id)}">${escapeHtml(s.name)}</option>`
  ).join("");
}

// ── Trigger ──────────────────────────────────────────────────────────────────

dom.triggerBtn.addEventListener("click", () => {
  if (isRunning) return;
  triggerSentinel();
});

async function triggerSentinel(): Promise<void> {
  if (!backendConnected) {
    addEventLine("error", "Backend is not connected. Cannot trigger.", []);
    return;
  }

  // Reset UI
  resetDashboard();
  setRunning(true);
  startResponseTimer();

  try {
    const body: Record<string, unknown> = {
      breach_source: "DarkForum X",
      use_sample: true,
      scenario_id: dom.scenarioSelect.value,
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

    addEventLine("setup", `Sentinel triggered. Run ID: ${currentRunId}`, ["ghost-db"]);
    connectSSE(currentRunId);
  } catch (err) {
    addEventLine("error", `Failed to trigger: ${err}`, []);
    setRunning(false);
    stopResponseTimer();
  }
}

// ── Call Test ────────────────────────────────────────────────────────────────

dom.callTestBtn.addEventListener("click", async () => {
  if (dom.callTestBtn.disabled) return;
  dom.callTestBtn.disabled = true;
  dom.callTestBtn.innerHTML = "&#x23F3; Calling...";
  setCallActive(true);

  try {
    const resp = await fetch(`${API_BASE}/api/call`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone_number: "+18782280111" }),
    });

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`Call failed: ${resp.status} — ${errText}`);
    }

    const data = await resp.json();
    addEventLine("notify", `Call test initiated: ${data.status || "sent"}`, ["bland-ai"]);
    dom.callTestBtn.innerHTML = "&#x2705; Call Sent";

    setTimeout(() => {
      dom.callTestBtn.disabled = false;
      dom.callTestBtn.innerHTML = "&#x1f4de; CALL TEST";
      setCallActive(false);
    }, 5000);
  } catch (err) {
    addEventLine("error", `Call test failed: ${err}`, []);
    dom.callTestBtn.disabled = false;
    dom.callTestBtn.innerHTML = "&#x1f4de; CALL TEST";
    setCallActive(false);
  }
});

// ── Call Status ──────────────────────────────────────────────────────────────

function setCallActive(active: boolean): void {
  callActive = active;
  if (active) {
    dom.callStatusBody.innerHTML = `
      <div class="call-active">
        <div class="call-waveform">
          <div class="bar"></div>
          <div class="bar"></div>
          <div class="bar"></div>
          <div class="bar"></div>
          <div class="bar"></div>
        </div>
        <div class="call-active-text"><strong>Bland AI</strong> — Call in progress</div>
      </div>
    `;
  } else {
    dom.callStatusBody.innerHTML = `<div class="call-idle">No active calls</div>`;
  }
}

// ── Response Timer ───────────────────────────────────────────────────────────

function startResponseTimer(): void {
  runStartTime = Date.now();
  stopResponseTimer();
  responseTimerInterval = setInterval(updateResponseTime, 100);
}

function stopResponseTimer(): void {
  if (responseTimerInterval) {
    clearInterval(responseTimerInterval);
    responseTimerInterval = null;
  }
}

function updateResponseTime(): void {
  if (!runStartTime) return;
  const elapsed = (Date.now() - runStartTime) / 1000;
  const display = elapsed < 60 ? `${elapsed.toFixed(1)}s` : `${Math.floor(elapsed / 60)}m ${Math.floor(elapsed % 60)}s`;
  dom.metricResponseTime.textContent = display;
  dom.sentinelTimeValue.textContent = display;

  // Update bar width — scale: 30s = ~8% of the 277-day bar
  const pct = Math.min(10, (elapsed / 30) * 8);
  dom.sentinelTimeBar.style.width = `${Math.max(2, pct)}%`;
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
  const evtType = evt.type;
  const tools = EVENT_TO_TOOLS[evtType] || [];

  // Increment tool call counts
  for (const toolKey of tools) {
    toolCallCounts[toolKey] = (toolCallCounts[toolKey] || 0) + 1;
  }
  renderToolCallSummary();

  // Add to activity feed with tool badges
  addEventLine(evtType, evt.message, tools);

  // Handle event-specific updates
  if (evtType === "ingest") {
    if (evt.data && typeof evt.data.count === "number") {
      animateMetric("records", evt.data.count as number);
    }
  } else if (evtType === "matching") {
    if (evt.data) {
      if (typeof evt.data.total === "number") animateMetric("matches", evt.data.total as number);
      if (typeof evt.data.critical === "number") animateMetric("critical", evt.data.critical as number);
    }
  } else if (evtType === "research") {
    // Also count Truefoundry as used (Claude runs via Truefoundry)
    toolCallCounts["truefoundry"] = (toolCallCounts["truefoundry"] || 0) + 1;
    renderToolCallSummary();

    if (evt.data && (evt.data.cve_id || evt.data.attack_vector || evt.data.severity)) {
      updatePartialReport(evt.data);
    }
  } else if (evtType === "lockdown") {
    if (evt.data && typeof evt.data.locked === "number") {
      animateMetric("locked", evt.data.locked as number);
    }
  } else if (evtType === "notify") {
    if (evt.data && typeof evt.data.calls_initiated === "number") {
      animateMetric("called", evt.data.calls_initiated as number);
    }
    setCallActive(true);
  } else if (evtType === "complete") {
    setRunning(false);
    stopResponseTimer();
    setGlobalStatus("complete");
    setCallActive(false);
    // Fetch final status for the full report
    if (currentRunId) {
      fetchFinalStatus(currentRunId);
    }
  } else if (evtType === "error") {
    setGlobalStatus("error");
    setRunning(false);
    stopResponseTimer();
  }
}

// ── Tool Call Summary ────────────────────────────────────────────────────────

function renderToolCallSummary(): void {
  const entries = Object.entries(toolCallCounts).filter(([, count]) => count > 0);
  if (entries.length === 0) {
    dom.toolCallSummary.innerHTML = "";
    return;
  }

  dom.toolCallSummary.innerHTML = entries.map(([toolKey, count]) => {
    const tool = SPONSOR_TOOLS[toolKey];
    if (!tool) return "";
    return `<span class="tool-call-chip" style="background: ${hexToRgba(tool.color, 0.12)}; border: 1px solid ${hexToRgba(tool.color, 0.3)}; color: ${tool.color};">${escapeHtml(tool.name)}: <span class="chip-count">${count}</span></span>`;
  }).join("");
}

// ── Global Status ────────────────────────────────────────────────────────────

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

    // Update response time from actual data
    if (data.duration_seconds) {
      const dur = data.duration_seconds;
      const display = dur < 60 ? `${dur.toFixed(1)}s` : `${Math.floor(dur / 60)}m ${Math.floor(dur % 60)}s`;
      dom.metricResponseTime.textContent = display;
      dom.sentinelTimeValue.textContent = display;
    }

    if (data.status === "complete" || data.status === "complete_no_matches") {
      setGlobalStatus("complete");
    } else if (data.status === "error") {
      setGlobalStatus("error");
    }

    // Build the full structured incident report
    if (data.incident_report && Object.keys(data.incident_report).length > 0) {
      renderStructuredReport(data.incident_report);
    }

    setRunning(false);
    stopResponseTimer();
  } catch (e) {
    console.error("Failed to fetch final status:", e);
    setRunning(false);
    stopResponseTimer();
  }
}

// ── Event Log / Activity Feed ────────────────────────────────────────────────

function addEventLine(type: string, message: string, tools: string[]): void {
  // Remove empty placeholder
  if (dom.eventLogEmpty) {
    dom.eventLogEmpty.style.display = "none";
  }

  const now = new Date();
  const ts = now.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const line = document.createElement("div");
  line.className = "event-line";

  // Build tool badge(s)
  let toolBadgesHtml = "";
  if (tools.length > 0) {
    for (const toolKey of tools) {
      const tool = SPONSOR_TOOLS[toolKey];
      if (tool) {
        toolBadgesHtml += `<span class="event-tool-badge" style="background: ${hexToRgba(tool.color, 0.15)}; border: 1px solid ${hexToRgba(tool.color, 0.35)}; color: ${tool.color};">${escapeHtml(tool.name)}</span>`;
      }
    }
  } else {
    // Fallback: generic event tag
    toolBadgesHtml = `<span class="event-tag ${escapeHtml(type)}">${escapeHtml(type)}</span>`;
  }

  line.innerHTML = `
    <span class="event-timestamp">${ts}</span>
    ${toolBadgesHtml}
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
  for (const key of Object.keys(metricTargets) as (keyof typeof metricTargets)[]) {
    const target = metricTargets[key];
    const current = metricCurrent[key];

    if (current !== target) {
      // Animate: move ~12% of the remaining distance each frame, minimum 1
      const diff = target - current;
      const step = Math.max(1, Math.ceil(Math.abs(diff) * 0.12));
      metricCurrent[key] = diff > 0 ? Math.min(target, current + step) : Math.max(target, current - step);

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

// ── Incident Report — Partial Update (during research phase) ─────────────────

function updatePartialReport(data: Record<string, unknown>): void {
  let html = "";

  // Severity + Incident Type header
  html += `<div class="report-severity-header">`;
  if (data.severity) {
    const sevClass = (data.severity as string).toLowerCase();
    html += `<span class="severity-badge ${sevClass}">${escapeHtml((data.severity as string).toUpperCase())}</span>`;
  }
  if (data.incident_type) {
    const typeName = (data.incident_type as string).replace(/_/g, " ").toUpperCase();
    html += `<span class="incident-type-pill">${escapeHtml(typeName)}</span>`;
  }
  html += `</div>`;

  // Attack Vector
  if (data.attack_vector) {
    html += `
      <div class="report-section">
        <div class="report-section-label">Attack Vector</div>
        <div class="report-section-value">${escapeHtml(data.attack_vector as string)}</div>
      </div>
    `;
  }

  // CVE
  html += buildCVESection(data.cve_id as string | undefined);

  dom.reportContent.innerHTML = html;
}

// ── Incident Report — Full Structured Report ─────────────────────────────────

function renderStructuredReport(report: Record<string, unknown>): void {
  let html = "";

  // Severity + Incident Type header
  html += `<div class="report-severity-header">`;
  if (report.severity) {
    const sevClass = (report.severity as string).toLowerCase();
    html += `<span class="severity-badge ${sevClass}">${escapeHtml((report.severity as string).toUpperCase())}</span>`;
  }
  if (report.incident_type) {
    const typeName = (report.incident_type as string).replace(/_/g, " ").toUpperCase();
    html += `<span class="incident-type-pill">${escapeHtml(typeName)}</span>`;
  }
  html += `</div>`;

  // Attack Vector
  if (report.attack_vector) {
    html += `
      <div class="report-section">
        <div class="report-section-label">Attack Vector</div>
        <div class="report-section-value">${escapeHtml(report.attack_vector as string)}</div>
      </div>
    `;
  }

  // CVE
  html += buildCVESection(report.cve_id as string | undefined);

  // Affected Software
  if (report.affected_software) {
    const software = report.affected_software;
    const softwareStr = Array.isArray(software)
      ? (software as string[]).map((s) => escapeHtml(String(s))).join(", ")
      : escapeHtml(String(software));
    html += `
      <div class="report-section">
        <div class="report-section-label">Affected Software</div>
        <div class="report-section-value">${softwareStr}</div>
      </div>
    `;
  }

  // Compliance frameworks
  const dataClasses = report.data_classes_exposed
    ? (Array.isArray(report.data_classes_exposed) ? report.data_classes_exposed as string[] : [String(report.data_classes_exposed)])
    : [];
  const applicableFrameworks = determineCompliance(
    report.incident_type as string | undefined,
    dataClasses
  );

  if (applicableFrameworks.length > 0) {
    html += `
      <div class="report-section">
        <div class="report-section-label">Compliance</div>
        <div class="compliance-badges">
          ${applicableFrameworks.map((fwName) => {
            const fw = COMPLIANCE_FRAMEWORKS[fwName];
            if (!fw) return "";
            return `<span class="compliance-badge ${fw.cssClass}">${escapeHtml(fw.name)}<span class="badge-deadline">${escapeHtml(fw.deadline)}</span></span>`;
          }).join("")}
        </div>
      </div>
    `;
  }

  // Remediation Steps
  const patches = report.recommended_patches as string[] | undefined;
  const remediationSteps = report.remediation_steps as string[] | undefined;
  const steps = remediationSteps || patches;
  if (steps && steps.length > 0) {
    html += `
      <div class="report-section">
        <div class="report-section-label">Remediation Steps</div>
        <ol class="remediation-list">
          ${steps.map((step, i) => {
            const priority = i === 0 ? "p1" : i < 3 ? "p2" : "p3";
            return `<li class="remediation-item"><span class="remediation-priority ${priority}">${priority.toUpperCase()}</span>${escapeHtml(String(step))}</li>`;
          }).join("")}
        </ol>
      </div>
    `;
  }

  // Summary
  if (report.summary) {
    html += `
      <div class="report-section">
        <div class="report-section-label">Summary</div>
        <div class="report-section-value">${escapeHtml(report.summary as string)}</div>
      </div>
    `;
  }

  // References
  const references = report.references as Array<{ url: string; source?: string }> | undefined;
  if (references && references.length > 0) {
    html += `
      <div class="report-section">
        <div class="report-section-label">References</div>
        <ul class="reference-list">
          ${references.map((ref) => {
            const url = typeof ref === "string" ? ref : ref.url;
            const source = typeof ref === "string" ? "" : (ref.source || "");
            return `<li class="reference-item">${source ? `<span class="reference-source">${escapeHtml(source)}</span> ` : ""}<a class="reference-link" href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(url)}</a></li>`;
          }).join("")}
        </ul>
      </div>
    `;
  }

  if (html) {
    dom.reportContent.innerHTML = html;
  }
}

// ── CVE Section Builder ──────────────────────────────────────────────────────

function buildCVESection(cveId: string | undefined): string {
  if (!cveId || cveId.toLowerCase() === "unknown" || cveId.toLowerCase() === "n/a") {
    return `
      <div class="report-section">
        <div class="report-section-label">CVE</div>
        <div class="cve-unknown">No known CVE — novel attack</div>
      </div>
    `;
  }

  const nistUrl = `https://nvd.nist.gov/vuln/detail/${encodeURIComponent(cveId)}`;
  return `
    <div class="report-section">
      <div class="report-section-label">CVE</div>
      <a class="cve-link" href="${escapeHtml(nistUrl)}" target="_blank" rel="noopener">${escapeHtml(cveId)}</a>
    </div>
  `;
}

// ── Reset ────────────────────────────────────────────────────────────────────

function resetDashboard(): void {
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
  dom.metricResponseTime.textContent = "0s";

  // Reset tool call counts
  for (const key of Object.keys(toolCallCounts)) {
    delete toolCallCounts[key];
  }
  renderToolCallSummary();

  // Reset event log
  dom.eventLog.innerHTML = "";
  if (dom.eventLogEmpty) {
    dom.eventLogEmpty.style.display = "none";
  }

  // Reset report
  dom.reportContent.innerHTML = `<div class="report-empty">Awaiting incident data...</div>`;

  // Reset call status
  setCallActive(false);

  // Reset response timer
  dom.sentinelTimeValue.textContent = "0s";
  dom.sentinelTimeBar.style.width = "2%";
  stopResponseTimer();
  runStartTime = null;

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

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ── Init ─────────────────────────────────────────────────────────────────────

async function init(): Promise<void> {
  await checkBackendConnection();
  loadIntegrations();
  loadScenarios();
}

init();
