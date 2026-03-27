# Research Pipeline Upgrade — Sponsor Logos + API Visualization

## For Alfred: Changes to apply to index.html

### 1. Add sponsor logo SVGs (add inside `<style>` block)

Replace the `.rp-icon` emoji icons with colored SVG logo circles for each sponsor.
Add these CSS classes after the existing `.rp-node` styles:

```css
/* Sponsor logo circles for research pipeline */
.rp-logo {
  width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: 12px; font-weight: 800; font-family: 'JetBrains Mono', monospace;
  flex-shrink: 0; letter-spacing: -0.5px;
}
.rp-logo.aerospike { background: rgba(239,68,68,.15); color: #ef4444; border: 1.5px solid rgba(239,68,68,.3); }
.rp-logo.senso { background: rgba(16,185,129,.15); color: #10b981; border: 1.5px solid rgba(16,185,129,.3); }
.rp-logo.airbyte { background: rgba(99,102,241,.15); color: #6366f1; border: 1.5px solid rgba(99,102,241,.3); }
.rp-logo.claude { background: rgba(212,165,116,.15); color: #d4a574; border: 1.5px solid rgba(212,165,116,.3); }
.rp-logo.ghost { background: rgba(124,58,237,.15); color: #a78bfa; border: 1.5px solid rgba(124,58,237,.3); }
.rp-logo.overmind { background: rgba(99,102,241,.15); color: #818cf8; border: 1.5px solid rgba(99,102,241,.3); }
.rp-logo.truefoundry { background: rgba(245,158,11,.15); color: #f59e0b; border: 1.5px solid rgba(245,158,11,.3); }
.rp-logo.auth0 { background: rgba(235,84,36,.15); color: #eb5424; border: 1.5px solid rgba(235,84,36,.3); }

/* API endpoint badge in research nodes */
.rp-api {
  font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--t3);
  background: rgba(255,255,255,.04); padding: 2px 8px; border-radius: 4px;
  margin-top: 2px; display: inline-block;
}
.rp-api .method { color: var(--green); font-weight: 700; margin-right: 4px; }
.rp-api .status { color: var(--green); margin-left: 8px; }
.rp-api .latency { color: var(--t3); margin-left: 4px; }
```

### 2. Update research steps to use logo classes

Replace the `researchSteps` array (lines ~683-696) with:

```javascript
const researchSteps=[
  {logo:'aerospike', abbr:'AS', src:'Aerospike', detail:'Vector search: similar past breaches in incident database', api:'aerospike/vector-search', ms:89},
  {logo:'senso', abbr:'S', src:'Senso.ai', detail:'Querying knowledge base: credential breach mitigation playbooks', api:'senso.ai/v1/knowledge/query', ms:234},
  {logo:'airbyte', abbr:'AB', src:'Airbyte', detail:'Ingesting NIST CVE database for darkforum_x vulnerabilities', api:'airbyte/sources/nist-cve/sync', ms:412},
  {logo:'claude', abbr:'C', src:'Claude', detail:'Analyzing 12 similar incidents from 2024-2026 for pattern matching', api:'truefoundry/gateway/chat', ms:1842},
  {logo:'ghost', abbr:'G', src:'Ghost DB', detail:'Retrieving historical response outcomes for credential breaches', api:'ghost-db/incidents?type=credential', ms:45},
  {logo:'senso', abbr:'S', src:'Senso.ai', detail:'Searching academic literature: password reuse attack vectors', api:'senso.ai/v1/research/search', ms:567},
  {logo:'claude', abbr:'C', src:'Claude', detail:'Cross-referencing CA Civil Code 1798.82 notification requirements', api:'truefoundry/gateway/chat', ms:923},
  {logo:'airbyte', abbr:'AB', src:'Airbyte', detail:'Syncing CCPA enforcement actions database for compliance patterns', api:'airbyte/sources/ccpa-enforcement/sync', ms:389},
  {logo:'aerospike', abbr:'AS', src:'Aerospike', detail:'Finding nearest-neighbor mitigation strategies (cosine similarity: 0.94)', api:'aerospike/vector-search', ms:67},
  {logo:'claude', abbr:'C', src:'Claude', detail:'Synthesizing research into actionable recommendations', api:'truefoundry/gateway/chat', ms:2103},
  {logo:'ghost', abbr:'G', src:'Ghost DB', detail:'Storing research findings + updating incident knowledge graph', api:'ghost-db/research/store', ms:34},
  {logo:'overmind', abbr:'OM', src:'Overmind', detail:'Tracing research chain for audit + observability', api:'overmind/v1/traces', ms:28},
];
```

### 3. Update the node rendering (line ~700-708)

Replace:
```javascript
node.innerHTML=`<div class="rp-icon">${s.icon}</div><div class="rp-src">${s.src}</div><div class="rp-detail">${s.detail}</div><div class="rp-status" ...>RUNNING</div>`;
```

With:
```javascript
node.innerHTML=`<div class="rp-logo ${s.logo}">${s.abbr}</div><div style="flex:1;min-width:0;"><div class="rp-src">${s.src}</div><div class="rp-detail">${s.detail}</div><div class="rp-api"><span class="method">POST</span>${s.api}<span class="status">200</span><span class="latency">${s.ms}ms</span></div></div><div class="rp-status" style="background:rgba(161,161,170,.1);color:var(--t2);">RUNNING</div>`;
```

This shows each research step with:
- Colored logo circle with sponsor abbreviation
- API endpoint path with method/status/latency
- Clearer visual hierarchy
