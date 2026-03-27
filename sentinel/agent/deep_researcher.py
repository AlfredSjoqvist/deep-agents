"""Phase 2 (Advanced): Deep research agent that searches the web for real CVEs,
security advisories, and attack intelligence, then produces a comprehensive
incident report a security team can act on.

Pipeline:
    1. Initial Classification (Claude)
    2. Web Search (NVD CVE API + security advisories)
    3. Context Enrichment (Senso knowledge base)
    4. Analysis & Synthesis (Claude)
    5. Persistence (Ghost DB)
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from typing import Any

import httpx
import structlog

from sentinel.config import config
from sentinel.integrations import ghost_db, senso_context, truefoundry_llm

log = structlog.get_logger()

# NVD CVE 2.0 API — free, no key required
NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"

# ── Event emission ──────────────────────────────────────────────────────────

async def _emit(run_id: str | None, event_type: str, message: str, data: dict | None = None) -> None:
    """Emit a pipeline event if a run_id is provided.

    Imports the orchestrator's _emit at call time to avoid circular imports.
    """
    if run_id is None:
        log.info(f"deep_research.{event_type}", message=message, **(data or {}))
        return

    try:
        from sentinel.agent.orchestrator import _emit as orchestrator_emit
        await orchestrator_emit(run_id, event_type, message, phase="research", data=data)
    except Exception:
        # If orchestrator is unavailable, just log
        log.info(f"deep_research.{event_type}", message=message, **(data or {}))


# ── Step 1: Classification ──────────────────────────────────────────────────

_INCIDENT_TYPE_PATTERNS: dict[str, list[str]] = {
    "credential_stuffing": ["credential", "stuffing", "darkforum", "combo", "brute", "password"],
    "phishing": ["phish", "spear", "social_eng", "phishing"],
    "ransomware": ["ransom", "encrypt", "lockbit", "revil", "blackcat", "alphv"],
    "insider_threat": ["insider", "internal", "employee", "disgruntled"],
    "exposed_api": ["api", "endpoint", "token_leak", "exposed_key", "s3_bucket"],
    "sql_injection": ["sqli", "sql_inject", "injection", "database_dump", "sql"],
    "malware": ["malware", "trojan", "stealer", "keylog", "infostealer", "raccoon", "redline"],
    "man_in_the_middle": ["mitm", "man_in_the_middle", "intercept", "ssl_strip"],
    "physical_theft": ["physical", "theft", "stolen_device", "lost_laptop"],
}


def _classify_heuristic(breach_source: str) -> str:
    """Quick keyword-based incident type classification."""
    source_lower = breach_source.lower().replace(" ", "").replace("-", "").replace("_", "")
    for incident_type, keywords in _INCIDENT_TYPE_PATTERNS.items():
        for keyword in keywords:
            if keyword.lower().replace("_", "") in source_lower:
                return incident_type
    return "unknown"


async def _classify_with_llm(
    breach_source: str,
    total_leaked: int,
    critical_count: int,
    matched_emails: list[str] | None,
) -> dict[str, Any]:
    """Use Claude to classify the incident and decide what to search for."""

    email_sample = ""
    if matched_emails:
        domains = list({e.split("@")[1] for e in matched_emails[:20] if "@" in e})
        email_sample = f"\n- Affected email domains: {', '.join(domains[:10])}"

    prompt = f"""You are a cybersecurity incident classifier. Analyze this breach and tell me:
1. The most likely incident type
2. What CVE keywords to search for in the NVD database
3. What software/products might be affected

BREACH DETAILS:
- Source: {breach_source}
- Total leaked credentials: {total_leaked}
- Critical matches (password reuse): {critical_count}{email_sample}
- Heuristic classification: {_classify_heuristic(breach_source)}

Respond in this exact JSON format:
{{
    "incident_type": "one of: credential_stuffing, phishing, ransomware, insider_threat, exposed_api, sql_injection, malware, man_in_the_middle, physical_theft, unknown",
    "confidence": 0.0 to 1.0,
    "search_queries": ["keyword1", "keyword2", "keyword3"],
    "likely_software": ["software1", "software2"],
    "reasoning": "brief explanation"
}}

Return ONLY valid JSON."""

    try:
        response = await truefoundry_llm.chat(
            messages=[
                {"role": "system", "content": "You are a cybersecurity expert. Respond only in valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        text = response.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(text)
    except Exception as e:
        log.warning("deep_research.classify_llm_failed", error=str(e))
        # Fallback: generate search queries from the breach source name
        heuristic = _classify_heuristic(breach_source)
        return {
            "incident_type": heuristic,
            "confidence": 0.3,
            "search_queries": [
                breach_source,
                f"{heuristic} vulnerability",
                "authentication bypass",
            ],
            "likely_software": [],
            "reasoning": "LLM unavailable; fell back to heuristic classification.",
        }


# ── Step 2: Web Search (NVD + advisories) ──────────────────────────────────

async def _search_nvd(keyword: str, results_per_page: int = 5) -> list[dict]:
    """Search the NVD CVE 2.0 API for vulnerabilities matching a keyword.

    Returns a list of simplified CVE records.
    """
    cves: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "keywordSearch": keyword,
                "resultsPerPage": results_per_page,
            }
            resp = await client.get(NVD_API_BASE, params=params)

            if resp.status_code == 200:
                data = resp.json()
                vulnerabilities = data.get("vulnerabilities", [])

                for vuln in vulnerabilities:
                    cve_data = vuln.get("cve", {})
                    cve_id = cve_data.get("id", "")

                    # Extract description (English preferred)
                    descriptions = cve_data.get("descriptions", [])
                    description = ""
                    for desc in descriptions:
                        if desc.get("lang") == "en":
                            description = desc.get("value", "")
                            break
                    if not description and descriptions:
                        description = descriptions[0].get("value", "")

                    # Extract CVSS score
                    metrics = cve_data.get("metrics", {})
                    cvss_score = None
                    cvss_severity = None
                    cvss_vector = None

                    # Try CVSS v3.1 first, then v3.0, then v2.0
                    for version_key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                        metric_list = metrics.get(version_key, [])
                        if metric_list:
                            cvss_data = metric_list[0].get("cvssData", {})
                            cvss_score = cvss_data.get("baseScore")
                            cvss_severity = cvss_data.get("baseSeverity", "")
                            cvss_vector = cvss_data.get("vectorString", "")
                            break

                    # Extract affected configurations (CPE)
                    configurations = cve_data.get("configurations", [])
                    affected_products: list[str] = []
                    for config_node in configurations:
                        for node in config_node.get("nodes", []):
                            for cpe_match in node.get("cpeMatch", []):
                                criteria = cpe_match.get("criteria", "")
                                if criteria:
                                    # CPE format: cpe:2.3:a:vendor:product:version:...
                                    parts = criteria.split(":")
                                    if len(parts) >= 5:
                                        vendor = parts[3]
                                        product = parts[4]
                                        version = parts[5] if len(parts) > 5 else "*"
                                        affected_products.append(f"{vendor}/{product} {version}")

                    # Extract references
                    references = cve_data.get("references", [])
                    ref_urls = [ref.get("url", "") for ref in references[:5]]

                    # Published and modified dates
                    published = cve_data.get("published", "")
                    last_modified = cve_data.get("lastModified", "")

                    cves.append({
                        "cve_id": cve_id,
                        "description": description[:500],
                        "cvss_score": cvss_score,
                        "cvss_severity": cvss_severity,
                        "cvss_vector": cvss_vector,
                        "affected_products": affected_products[:10],
                        "references": ref_urls,
                        "published": published,
                        "last_modified": last_modified,
                    })
            elif resp.status_code == 403:
                log.warning("deep_research.nvd_rate_limited", keyword=keyword)
            else:
                log.warning("deep_research.nvd_error", status=resp.status_code, keyword=keyword)

    except httpx.TimeoutException:
        log.warning("deep_research.nvd_timeout", keyword=keyword)
    except Exception as e:
        log.warning("deep_research.nvd_search_failed", keyword=keyword, error=str(e))

    return cves


async def _search_all_nvd(queries: list[str], run_id: str | None) -> list[dict]:
    """Search NVD for multiple keywords, deduplicating results.

    Adds a small delay between queries to respect NVD rate limits.
    """
    all_cves: list[dict] = []
    seen_ids: set[str] = set()

    for i, query in enumerate(queries[:5]):  # Cap at 5 queries to stay polite
        await _emit(run_id, "research", f"Searching NVD for \"{query}\"...")

        results = await _search_nvd(query)
        new_count = 0
        for cve in results:
            cve_id = cve["cve_id"]
            if cve_id not in seen_ids:
                seen_ids.add(cve_id)
                all_cves.append(cve)
                new_count += 1

        if new_count > 0:
            await _emit(run_id, "research", f"Found {new_count} new CVEs for \"{query}\"")

        # NVD rate limit: ~5 requests per 30 seconds without an API key
        if i < len(queries) - 1:
            await asyncio.sleep(6)

    return all_cves


# ── Step 3: Senso Context Enrichment ────────────────────────────────────────

async def _enrich_with_senso(
    breach_source: str,
    incident_type: str,
    cves: list[dict],
    run_id: str | None,
) -> str:
    """Search Senso for existing context and upload new findings."""
    context_text = ""

    # Search for existing context
    try:
        senso_results = await senso_context.search(
            f"data breach {breach_source} {incident_type} CVE vulnerability"
        )
        if isinstance(senso_results, dict) and senso_results.get("results"):
            context_text = "\n".join(
                str(r.get("content", r.get("text", "")))
                for r in senso_results["results"][:3]
            )
            if context_text.strip():
                await _emit(run_id, "research", "Found existing context in Senso knowledge base.")
    except Exception as e:
        log.warning("deep_research.senso_search_failed", error=str(e))

    # Upload new CVE findings to Senso for future queries
    if cves:
        try:
            cve_summary = "\n".join(
                f"- {c['cve_id']}: {c['description'][:200]}" for c in cves[:10]
            )
            await senso_context.upload_content(
                content=f"CVE findings related to {breach_source} ({incident_type}):\n{cve_summary}",
                title=f"Sentinel Research: {breach_source} - {time.strftime('%Y-%m-%d')}",
            )
        except Exception as e:
            log.warning("deep_research.senso_upload_failed", error=str(e))

    return context_text


# ── Step 4: Analysis & Synthesis ────────────────────────────────────────────

async def _synthesize_report(
    breach_source: str,
    total_leaked: int,
    critical_count: int,
    classification: dict,
    cves: list[dict],
    senso_context_text: str,
    matched_emails: list[str] | None,
    run_id: str | None,
) -> dict:
    """Use Claude to synthesize all gathered data into a structured incident report."""

    await _emit(run_id, "research", "Analyzing attack patterns...")

    # Build CVE context for the prompt
    cve_details = ""
    if cves:
        cve_entries = []
        for cve in cves[:10]:
            entry = f"- {cve['cve_id']}"
            if cve.get("cvss_score"):
                entry += f" (CVSS {cve['cvss_score']}/{cve.get('cvss_severity', 'N/A')})"
            entry += f": {cve['description'][:300]}"
            if cve.get("affected_products"):
                entry += f"\n  Affected: {', '.join(cve['affected_products'][:5])}"
            if cve.get("references"):
                entry += f"\n  Refs: {cve['references'][0]}"
            cve_entries.append(entry)
        cve_details = "\n".join(cve_entries)

    email_domains = ""
    if matched_emails:
        domains = list({e.split("@")[1] for e in matched_emails[:50] if "@" in e})
        email_domains = f"\n- Affected email domains: {', '.join(domains[:15])}"

    prompt = f"""You are a senior cybersecurity incident analyst producing a comprehensive incident report.

BREACH DETAILS:
- Source: {breach_source}
- Total leaked credentials: {total_leaked}
- Critical matches (password reuse): {critical_count}{email_domains}

CLASSIFICATION (from initial analysis):
- Incident type: {classification.get('incident_type', 'unknown')}
- Confidence: {classification.get('confidence', 0)}
- Reasoning: {classification.get('reasoning', 'N/A')}
- Likely software: {', '.join(classification.get('likely_software', []))}

REAL CVE DATA FROM NVD:
{cve_details if cve_details else "No CVEs found in NVD search."}

{f"SECURITY CONTEXT FROM KNOWLEDGE BASE:{chr(10)}{senso_context_text}" if senso_context_text else ""}

Based on ALL the above data, produce a comprehensive incident report. If real CVEs were found, use them.
If no exact CVE match exists, identify the most relevant CVE from the search results and explain how it
relates to this breach. Be specific about version numbers, patch versions, and remediation steps.

Respond in this exact JSON format:
{{
    "breach_source": "{breach_source}",
    "incident_type": "one of: credential_stuffing, phishing, ransomware, insider_threat, exposed_api, sql_injection, malware, man_in_the_middle, physical_theft, unknown",
    "attack_vector": "detailed description of the attack method used",
    "cve_ids": ["CVE-YYYY-NNNNN", ...],
    "primary_cve": {{
        "id": "CVE-YYYY-NNNNN",
        "cvss_score": 0.0,
        "cvss_severity": "CRITICAL|HIGH|MEDIUM|LOW",
        "description": "what this CVE is about",
        "relevance": "why this CVE is relevant to this breach"
    }},
    "affected_software": [
        {{
            "name": "software name",
            "vendor": "vendor name",
            "affected_versions": "version range",
            "patched_version": "specific version that fixes the issue"
        }}
    ],
    "severity": "CRITICAL|HIGH|MEDIUM|LOW",
    "data_classes_exposed": ["credentials", "PII", "financial", "medical", "session_tokens"],
    "estimated_records": {total_leaked},
    "timeline": {{
        "estimated_breach_date": "YYYY-MM-DD or Unknown",
        "detection_date": "{time.strftime('%Y-%m-%d')}",
        "estimated_exposure_window": "description of how long data was exposed"
    }},
    "recommended_patches": [
        "specific patch or upgrade instruction with version numbers",
        "additional mitigation step"
    ],
    "remediation_plan": [
        {{
            "step": 1,
            "action": "immediate action to take",
            "priority": "CRITICAL|HIGH|MEDIUM",
            "details": "specific instructions"
        }}
    ],
    "indicators_of_compromise": [
        "IOC description"
    ],
    "references": [
        "URL to relevant advisory or documentation"
    ],
    "summary": "3-5 sentence executive summary covering what happened, impact, and key actions needed"
}}

Return ONLY valid JSON, no markdown fences."""

    await _emit(run_id, "research", "Generating remediation plan...")

    try:
        response = await truefoundry_llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior cybersecurity analyst. Respond only in valid JSON. Be specific and actionable.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=4096,
        )
        text = response.strip().removeprefix("```json").removesuffix("```").strip()
        report = json.loads(text)
    except Exception as e:
        log.warning("deep_research.synthesis_failed", error=str(e))
        # Build a report from raw data even if LLM fails
        report = _build_fallback_report(
            breach_source, total_leaked, critical_count, classification, cves,
        )

    return report


def _build_fallback_report(
    breach_source: str,
    total_leaked: int,
    critical_count: int,
    classification: dict,
    cves: list[dict],
) -> dict:
    """Build a structured report from raw data when the LLM is unavailable."""
    incident_type = classification.get("incident_type", "unknown")

    # Pick the highest-scoring CVE as primary
    primary_cve: dict[str, Any] = {}
    cve_ids: list[str] = []
    if cves:
        sorted_cves = sorted(cves, key=lambda c: c.get("cvss_score") or 0, reverse=True)
        top = sorted_cves[0]
        primary_cve = {
            "id": top["cve_id"],
            "cvss_score": top.get("cvss_score"),
            "cvss_severity": top.get("cvss_severity", "HIGH"),
            "description": top.get("description", ""),
            "relevance": "Highest CVSS score among search results related to this breach.",
        }
        cve_ids = [c["cve_id"] for c in sorted_cves[:5]]

    # Extract affected software from CVEs
    affected_sw = []
    for cve in cves[:3]:
        for product in cve.get("affected_products", [])[:2]:
            parts = product.split(" ", 1)
            name = parts[0] if parts else "Unknown"
            version = parts[1] if len(parts) > 1 else "*"
            affected_sw.append({
                "name": name,
                "vendor": name.split("/")[0] if "/" in name else "Unknown",
                "affected_versions": version,
                "patched_version": "See vendor advisory",
            })

    references = []
    for cve in cves[:5]:
        references.extend(cve.get("references", [])[:2])

    return {
        "breach_source": breach_source,
        "incident_type": incident_type,
        "attack_vector": f"Likely {incident_type.replace('_', ' ')} attack targeting credential databases.",
        "cve_ids": cve_ids,
        "primary_cve": primary_cve,
        "affected_software": affected_sw[:5],
        "severity": "CRITICAL" if critical_count > 0 else "HIGH",
        "data_classes_exposed": ["credentials", "PII"],
        "estimated_records": total_leaked,
        "timeline": {
            "estimated_breach_date": "Unknown",
            "detection_date": time.strftime("%Y-%m-%d"),
            "estimated_exposure_window": "Unknown — requires forensic analysis",
        },
        "recommended_patches": [
            "Force password reset for all matched users",
            "Enable MFA for all user accounts",
            "Rotate all API keys and session tokens",
            "Review and patch affected software (see CVE details)",
        ],
        "remediation_plan": [
            {
                "step": 1,
                "action": "Isolate affected systems",
                "priority": "CRITICAL",
                "details": "Immediately lock compromised accounts and revoke active sessions.",
            },
            {
                "step": 2,
                "action": "Force credential rotation",
                "priority": "CRITICAL",
                "details": "Reset passwords for all affected users. Invalidate API tokens.",
            },
            {
                "step": 3,
                "action": "Patch vulnerable software",
                "priority": "HIGH",
                "details": f"Apply patches for {', '.join(cve_ids[:3]) if cve_ids else 'identified vulnerabilities'}.",
            },
            {
                "step": 4,
                "action": "Enable enhanced monitoring",
                "priority": "HIGH",
                "details": "Deploy additional logging and alerting for authentication anomalies.",
            },
            {
                "step": 5,
                "action": "Conduct forensic analysis",
                "priority": "MEDIUM",
                "details": "Determine full scope of breach and timeline of unauthorized access.",
            },
        ],
        "indicators_of_compromise": [
            f"Credentials from {breach_source} appearing in dark web dumps",
            f"{total_leaked} email/password pairs leaked",
        ],
        "references": references[:10],
        "summary": (
            f"A {incident_type.replace('_', ' ')} incident was detected from {breach_source}, "
            f"exposing {total_leaked} credentials. {critical_count} users had reused passwords, "
            f"making them critically compromised. "
            f"{'CVE ' + cve_ids[0] + ' may be related. ' if cve_ids else ''}"
            f"Immediate password resets and enhanced monitoring are recommended."
        ),
    }


# ── Step 5: Persistence ────────────────────────────────────────────────────

async def _store_report(report: dict) -> None:
    """Persist the full research report to Ghost DB's research_cache table."""
    try:
        # Extract the primary CVE ID for the table column
        primary_cve_id = ""
        if report.get("primary_cve") and isinstance(report["primary_cve"], dict):
            primary_cve_id = report["primary_cve"].get("id", "")
        elif report.get("cve_ids"):
            primary_cve_id = report["cve_ids"][0]

        patches = report.get("recommended_patches", [])
        if isinstance(patches, list):
            patches_json = json.dumps(patches)
        else:
            patches_json = json.dumps([str(patches)])

        await ghost_db.execute(
            """INSERT INTO research_cache
               (breach_source, cve_id, attack_vector, affected_software, severity,
                recommended_patches, summary, raw_analysis)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            report.get("breach_source", ""),
            primary_cve_id,
            report.get("attack_vector", ""),
            json.dumps(report.get("affected_software", [])),
            report.get("severity", "HIGH"),
            patches_json,
            report.get("summary", ""),
            json.dumps(report),
        )
        log.info("deep_research.stored", breach_source=report.get("breach_source"))
    except Exception as e:
        log.warning("deep_research.store_failed", error=str(e))


# ── Main entry point ────────────────────────────────────────────────────────

async def deep_research(
    breach_source: str,
    total_leaked: int,
    critical_count: int,
    matched_emails: list[str] | None = None,
    run_id: str | None = None,
) -> dict:
    """Execute the full deep research pipeline and return a comprehensive incident report.

    Args:
        breach_source: Human-readable name of the breach source (e.g. "DarkForum X").
        total_leaked: Total number of leaked credentials detected.
        critical_count: Number of critical matches (password reuse).
        matched_emails: Optional list of matched email addresses for domain analysis.
        run_id: Optional pipeline run ID for SSE event emission.

    Returns:
        A comprehensive incident report dict with CVE details, attack analysis,
        remediation plan, and references.
    """
    start = time.monotonic()

    # ── Step 1: Classification ──────────────────────────────────────
    await _emit(run_id, "research", "Classifying incident type...")

    classification = await _classify_with_llm(
        breach_source, total_leaked, critical_count, matched_emails,
    )

    incident_type = classification.get("incident_type", "unknown")
    search_queries = classification.get("search_queries", [breach_source])
    likely_software = classification.get("likely_software", [])

    await _emit(
        run_id,
        "research",
        f"Classified as {incident_type} (confidence: {classification.get('confidence', 0):.0%})",
        data={"incident_type": incident_type, "confidence": classification.get("confidence", 0)},
    )

    # ── Step 2: NVD CVE Search ──────────────────────────────────────
    # Build search queries from classification + breach source + likely software
    all_queries = list(dict.fromkeys(search_queries))  # deduplicate while preserving order
    for sw in likely_software[:2]:
        if sw not in all_queries:
            all_queries.append(sw)

    cves = await _search_all_nvd(all_queries, run_id)

    if cves:
        cve_summary = ", ".join(c["cve_id"] for c in cves[:5])
        extra = f" (and {len(cves) - 5} more)" if len(cves) > 5 else ""
        await _emit(
            run_id,
            "research",
            f"Found {len(cves)} relevant CVEs: {cve_summary}{extra}",
            data={"cve_count": len(cves), "cve_ids": [c["cve_id"] for c in cves[:10]]},
        )
    else:
        await _emit(run_id, "research", "No exact CVE matches found in NVD. Will use LLM analysis.")

    # ── Step 3: Senso Context Enrichment ────────────────────────────
    await _emit(run_id, "research", "Checking security knowledge base...")

    senso_text = await _enrich_with_senso(breach_source, incident_type, cves, run_id)

    # ── Step 4: Analysis & Synthesis ────────────────────────────────
    report = await _synthesize_report(
        breach_source=breach_source,
        total_leaked=total_leaked,
        critical_count=critical_count,
        classification=classification,
        cves=cves,
        senso_context_text=senso_text,
        matched_emails=matched_emails,
        run_id=run_id,
    )

    # Attach raw CVE data so the frontend can display it
    report["_raw_cves"] = cves[:10]
    report["_classification"] = classification
    report["_research_duration_seconds"] = round(time.monotonic() - start, 2)

    # ── Step 5: Persist to Ghost DB ─────────────────────────────────
    await _store_report(report)

    await _emit(
        run_id,
        "research",
        "Research complete.",
        data={
            "cve_count": len(cves),
            "incident_type": report.get("incident_type", incident_type),
            "severity": report.get("severity", "HIGH"),
            "duration_seconds": report["_research_duration_seconds"],
        },
    )

    log.info(
        "deep_research.complete",
        breach_source=breach_source,
        incident_type=report.get("incident_type"),
        cve_count=len(cves),
        severity=report.get("severity"),
        duration=report["_research_duration_seconds"],
    )

    return report
