/**
 * Sentinel Dashboard — Client-side application.
 * Vanilla TypeScript, no frameworks. Connects to FastAPI backend via REST + SSE.
 *
 * Features:
 *   - Data pipeline visualization with sponsor tool badges
 *   - Agent activity feed with tool-branded event lines
 *   - Active tools panel with live spinner indicators
 *   - Overmind decision trace line across pipeline
 *   - Call test button for Bland AI phone demo
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

type NodeState = "pending" | "active" | "done" | "error";

// ── Sponsor Tool Mapping ─────────────────────────────────────────────────────

interface SponsorTool {
  name: string;
  color: string;
}

const SPONSOR_TOOLS: Record<string, SponsorTool> = {
  "ghost-db":     { name: "Ghost DB",     color: "#7C3AED" },
  "aerospike":    { name: "Aerospike",    color: "#7C3AED" },
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

// Map event types to pipeline node IDs
const EVENT_TO_NODE: Record<string, string> = {
  "setup":    "breach-csv",
  "ingest":   "ingest",
  "matching": "match",
  "research": "research",
  "lockdown": "lockdown",
  "notify":   "notify",
  "complete": "complete",
};

// Pipeline node order for sequential activation
const PIPELINE_NODES: string[] = [
  "breach-csv", "ingest", "match", "research", "lockdown", "notify", "complete"
];

// Connector IDs between nodes (index corresponds to connector between node[i] and node[i+1])
const CONNECTOR_IDS: string[] = [
  "conn-0-1", "conn-1-2", "conn-2-3", "conn-3-4", "conn-4-5", "conn-5-6"
];

// ── State ────────────────────────────────────────────────────────────────────

let currentRunId: string | null = null;
let eventSource: EventSource | null = null;
let isRunning = false;
let backendConnected = false;
let uploadedCSV: File | null = null;

// Track pipeline node states
const nodeStates: Record<string, NodeState> = {};
for (const node of PIPELINE_NODES) {
  nodeStates[node] = "pending";
}

// Track currently active tools for the Active Tools panel
const activeTools: Map<string, string> = new Map(); // tool-key -> last action

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
  eventLog: $("event-log"),
  eventLogEmpty: $("event-log-empty"),
  reportContent: $("report-content"),
  classificationContent: $("classification-content"),
  activeToolsContent: $("active-tools-content"),
  overmindTrace: $("overmind-trace"),
  triggerBtn: $("trigger-btn") as HTMLButtonElement,
  callTestBtn: $("call-test-btn") as HTMLButtonElement,
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
    addEventLine("error", "Backend is not connected. Cannot trigger.", []);
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

    addEventLine("setup", `Sentinel triggered. Run ID: ${currentRunId}`, ["ghost-db"]);
    connectSSE(currentRunId);
  } catch (err) {
    addEventLine("error", `Failed to trigger: ${err}`, []);
    setRunning(false);
  }
}

// ── Call Test ────────────────────────────────────────────────────────────────

dom.callTestBtn.addEventListener("click", async () => {
  if (dom.callTestBtn.disabled) return;
  dom.callTestBtn.disabled = true;
  dom.callTestBtn.innerHTML = "&#x23F3; Calling...";

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
    }, 3000);
  } catch (err) {
    addEventLine("error", `Call test failed: ${err}`, []);
    dom.callTestBtn.disabled = false;
    dom.callTestBtn.innerHTML = "&#x1f4de; CALL TEST";
  }
});

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
  const nodeId = EVENT_TO_NODE[evtType];

  // Add to activity feed with tool badges
  addEventLine(evtType, evt.message, tools);

  // Update active tools
  updateActiveTools(evtType, tools, evt.message);

  // Activate the Overmind trace when pipeline starts
  if (evtType === "setup" || evtType === "ingest") {
    dom.overmindTrace.classList.add("visible");
    // Overmind is always tracing
    setActiveTool("overmind", "Tracing decisions");
  }

  // Map event types to pipeline node states
  if (evtType === "setup") {
    setPipelineNode("breach-csv", "active");
  } else if (evtType === "ingest") {
    setPipelineNode("breach-csv", "done");
    setPipelineNode("ingest", "active");
    if (evt.data && typeof evt.data.count === "number") {
      animateMetric("records", evt.data.count as number);
    }
  } else if (evtType === "matching") {
    setPipelineNode("ingest", "done");
    setPipelineNode("match", "active");
    if (evt.data) {
      if (typeof evt.data.total === "number") animateMetric("matches", evt.data.total as number);
      if (typeof evt.data.critical === "number") animateMetric("critical", evt.data.critical as number);
    }
  } else if (evtType === "research") {
    setPipelineNode("match", "done");
    setPipelineNode("research", "active");
    // Show Truefoundry as active (Claude runs via Truefoundry)
    setActiveTool("truefoundry", "LLM gateway for Claude");
    if (evt.data && evt.data.cve_id) {
      updateIncidentReport(evt.data);
    }
  } else if (evtType === "lockdown") {
    setPipelineNode("research", "done");
    setPipelineNode("lockdown", "active");
    if (evt.data && typeof evt.data.locked === "number") {
      animateMetric("locked", evt.data.locked as number);
    }
  } else if (evtType === "notify") {
    setPipelineNode("lockdown", "done");
    setPipelineNode("notify", "active");
    if (evt.data && typeof evt.data.calls_initiated === "number") {
      animateMetric("called", evt.data.calls_initiated as number);
    }
  } else if (evtType === "complete") {
    // Mark all remaining nodes as done
    for (const node of PIPELINE_NODES) {
      setPipelineNode(node, "done");
    }
    setRunning(false);
    setGlobalStatus("complete");
    clearActiveTools();
    // Fetch final status for the full report
    if (currentRunId) {
      fetchFinalStatus(currentRunId);
    }
  } else if (evtType === "error") {
    // Mark current active node as error
    if (nodeId) {
      setPipelineNode(nodeId, "error");
    }
    setGlobalStatus("error");
    setRunning(false);
    clearActiveTools();
  }
}

// ── Pipeline Node Management ─────────────────────────────────────────────────

function setPipelineNode(nodeId: string, state: NodeState): void {
  // Don't downgrade state (e.g., done -> active)
  const currentState = nodeStates[nodeId];
  if (currentState === "done" && state === "active") return;
  if (currentState === "done" && state === "pending") return;

  nodeStates[nodeId] = state;

  const circle = document.getElementById(`node-${nodeId}`);
  const label = document.getElementById(`label-${nodeId}`);
  if (!circle || !label) return;

  // Update circle class
  circle.className = `pipeline-circle ${state}`;

  // Update label class
  label.className = `pipeline-node-label ${state}`;

  // Add/remove state overlay
  const existingOverlay = circle.querySelector(".state-overlay");
  if (existingOverlay) {
    existingOverlay.remove();
  }

  if (state === "done") {
    const overlay = document.createElement("span");
    overlay.className = "state-overlay done-overlay";
    overlay.textContent = "\u2713";
    circle.appendChild(overlay);
  } else if (state === "error") {
    const overlay = document.createElement("span");
    overlay.className = "state-overlay error-overlay";
    overlay.textContent = "\u2717";
    circle.appendChild(overlay);
  }

  // Update connectors
  updateConnectors();
}

function updateConnectors(): void {
  for (let i = 0; i < CONNECTOR_IDS.length; i++) {
    const connEl = document.getElementById(CONNECTOR_IDS[i]);
    if (!connEl) continue;

    const leftNode = PIPELINE_NODES[i];
    const rightNode = PIPELINE_NODES[i + 1];
    const leftState = nodeStates[leftNode];
    const rightState = nodeStates[rightNode];

    if (leftState === "done" && (rightState === "done" || rightState === "error")) {
      connEl.className = "pipeline-connector done";
    } else if (leftState === "done" && rightState === "active") {
      connEl.className = "pipeline-connector active";
    } else if (leftState === "active") {
      connEl.className = "pipeline-connector active";
    } else {
      connEl.className = "pipeline-connector pending";
    }
  }
}

// ── Active Tools Panel ───────────────────────────────────────────────────────

function updateActiveTools(evtType: string, tools: string[], message: string): void {
  // Trim the message for display
  const shortMsg = message.length > 50 ? message.substring(0, 47) + "..." : message;

  for (const toolKey of tools) {
    setActiveTool(toolKey, shortMsg);
  }
}

function setActiveTool(toolKey: string, action: string): void {
  activeTools.set(toolKey, action);
  renderActiveTools();
}

function clearActiveTools(): void {
  activeTools.clear();
  renderActiveTools();
}

function renderActiveTools(): void {
  if (activeTools.size === 0) {
    dom.activeToolsContent.innerHTML = `<div class="report-empty">No tools active. Trigger Sentinel to begin.</div>`;
    return;
  }

  let html = "";
  for (const [toolKey, action] of activeTools) {
    const tool = SPONSOR_TOOLS[toolKey];
    if (!tool) continue;
    html += `
      <div class="active-tool-item">
        <div class="tool-spinner" style="color: ${tool.color}; border-top-color: ${tool.color};"></div>
        <span class="active-tool-name" style="color: ${tool.color};">${escapeHtml(tool.name)}</span>
        <span class="active-tool-action">${escapeHtml(action)}</span>
      </div>
    `;
  }

  dom.activeToolsContent.innerHTML = html;
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

    // Update pipeline nodes
    if (data.status === "complete" || data.status === "complete_no_matches") {
      for (const node of PIPELINE_NODES) {
        setPipelineNode(node, "done");
      }
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
  // Reset pipeline nodes
  for (const nodeId of PIPELINE_NODES) {
    nodeStates[nodeId] = "pending";
    const circle = document.getElementById(`node-${nodeId}`);
    const label = document.getElementById(`label-${nodeId}`);
    if (circle) {
      circle.className = "pipeline-circle pending";
      // Remove any state overlays
      const overlay = circle.querySelector(".state-overlay");
      if (overlay) overlay.remove();
    }
    if (label) {
      label.className = "pipeline-node-label";
    }
  }

  // Reset connectors
  for (const connId of CONNECTOR_IDS) {
    const conn = document.getElementById(connId);
    if (conn) conn.className = "pipeline-connector pending";
  }

  // Hide overmind trace
  dom.overmindTrace.classList.remove("visible");

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

  // Reset active tools
  clearActiveTools();

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
}

init();
