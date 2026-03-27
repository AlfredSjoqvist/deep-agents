"""Regulatory compliance analysis for Sentinel incident reports.

Evaluates data breaches against GDPR, HIPAA, FERPA, CCPA, and PCI-DSS
frameworks. Determines which regulations apply based on the data classes
exposed, generates checklists, risk assessments, and (optionally) an
LLM-authored compliance narrative via the Truefoundry gateway.
"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Framework registry
# ---------------------------------------------------------------------------

COMPLIANCE_FRAMEWORKS: dict[str, dict[str, Any]] = {
    "GDPR": {
        "name": "General Data Protection Regulation",
        "region": "EU/EEA",
        "notification_deadline_hours": 72,
        "authority": "Data Protection Authority (DPA)",
        "key_articles": [
            "Art. 33 — Breach Notification",
            "Art. 34 — Communication to Data Subject",
            "Art. 5 — Data Processing Principles",
        ],
        "penalties": "Up to \u20ac20M or 4% of annual global turnover",
        "data_types_covered": [
            "personal_data",
            "special_category_data",
            "genetic_data",
            "biometric_data",
        ],
    },
    "HIPAA": {
        "name": "Health Insurance Portability and Accountability Act",
        "region": "US",
        "notification_deadline_hours": 60 * 24,  # 60 days
        "authority": "HHS Office for Civil Rights",
        "key_articles": [
            "Breach Notification Rule (45 CFR 164.400-414)",
            "Security Rule",
            "Privacy Rule",
        ],
        "penalties": "Up to $1.5M per violation category per year",
        "data_types_covered": ["health_data", "PHI", "ePHI"],
    },
    "FERPA": {
        "name": "Family Educational Rights and Privacy Act",
        "region": "US",
        "notification_deadline_hours": None,  # "reasonable time"
        "authority": "US Dept of Education",
        "key_articles": [
            "34 CFR Part 99",
            "Student Records Protection",
        ],
        "penalties": "Loss of federal funding",
        "data_types_covered": ["education_records", "student_PII"],
    },
    "CCPA": {
        "name": "California Consumer Privacy Act",
        "region": "California, US",
        "notification_deadline_hours": 72,
        "authority": "California AG / CPPA",
        "key_articles": [
            "\u00a71798.150 \u2014 Private Right of Action",
            "\u00a71798.82 \u2014 Breach Notification",
        ],
        "penalties": "Up to $7,500 per intentional violation",
        "data_types_covered": [
            "personal_information",
            "credentials",
            "financial_data",
        ],
    },
    "PCI_DSS": {
        "name": "Payment Card Industry Data Security Standard",
        "region": "Global",
        "notification_deadline_hours": 24,
        "authority": "PCI Security Standards Council",
        "key_articles": [
            "Req 12.10 \u2014 Incident Response",
            "Req 3 \u2014 Protect Stored Data",
        ],
        "penalties": "Fines $5K-$100K/month, loss of card processing",
        "data_types_covered": [
            "payment_card_data",
            "cardholder_data",
            "financial_data",
        ],
    },
}

# ---------------------------------------------------------------------------
# Mapping from common data-class labels to framework data types
# ---------------------------------------------------------------------------

_DATA_CLASS_ALIASES: dict[str, list[str]] = {
    # personal / PII
    "PII": ["personal_data", "personal_information"],
    "personal_data": ["personal_data", "personal_information"],
    "credentials": ["personal_data", "personal_information", "credentials"],
    "emails": ["personal_data", "personal_information"],
    "names": ["personal_data", "personal_information"],
    "addresses": ["personal_data", "personal_information"],
    "phone_numbers": ["personal_data", "personal_information"],
    "session_tokens": ["personal_data", "credentials"],
    # health
    "medical": ["health_data", "PHI", "ePHI"],
    "health_data": ["health_data", "PHI", "ePHI"],
    "PHI": ["health_data", "PHI", "ePHI"],
    # education
    "education_records": ["education_records", "student_PII"],
    "student_PII": ["education_records", "student_PII"],
    "student_records": ["education_records", "student_PII"],
    # financial / payment
    "financial": ["financial_data", "payment_card_data", "cardholder_data"],
    "financial_data": ["financial_data", "payment_card_data"],
    "payment_card_data": ["payment_card_data", "cardholder_data", "financial_data"],
    "credit_card": ["payment_card_data", "cardholder_data", "financial_data"],
    # biometric / genetic
    "biometric_data": ["biometric_data", "special_category_data"],
    "genetic_data": ["genetic_data", "special_category_data"],
}

# ---------------------------------------------------------------------------
# Incident-specific guidance
# ---------------------------------------------------------------------------

_INCIDENT_SPECIFIC_FLAGS: dict[str, dict[str, Any]] = {
    "credential_stuffing": {
        "extra_frameworks": ["GDPR", "CCPA"],
        "articles": [
            "GDPR Art. 33 — personal data breach notification",
            "CCPA \u00a71798.82 — breach notification to California residents",
        ],
        "recommendations": [
            "Force password reset for all affected accounts",
            "Enforce multi-factor authentication (MFA) across all user accounts",
            "Check for impossible-travel patterns in authentication logs",
            "Monitor for credential reuse across services",
        ],
        "notes": [
            "23andMe precedent: data-sharing features can amplify exposure "
            "beyond directly compromised accounts.",
        ],
    },
    "phishing": {
        "extra_frameworks": ["GDPR"],
        "articles": [
            "GDPR Art. 5 — data processing principles; controller has obligation "
            "to train employees and implement appropriate security measures",
        ],
        "recommendations": [
            "Conduct a full email security audit (SPF, DKIM, DMARC)",
            "Implement domain monitoring to detect look-alike/typosquatting domains",
            "Launch mandatory user security-awareness training",
            "Deploy email link-rewriting and sandboxing",
        ],
        "notes": [
            "Phishing is HIPAA's #1 breach vector. If any health data was "
            "accessible, HIPAA Breach Notification Rule likely applies.",
        ],
    },
}

# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def _normalize_data_classes(data_classes: list[str]) -> set[str]:
    """Expand user-supplied data class labels into canonical framework types."""
    canonical: set[str] = set()
    for dc in data_classes:
        dc_lower = dc.lower().strip()
        # Direct match in alias table (case-insensitive key lookup)
        for alias_key, mapped in _DATA_CLASS_ALIASES.items():
            if dc_lower == alias_key.lower():
                canonical.update(mapped)
                break
        else:
            # If no alias matched, keep the raw value so frameworks can still match
            canonical.add(dc_lower)
    return canonical


def _framework_applies(framework_key: str, framework: dict, canonical_types: set[str]) -> bool:
    """Return True if any canonical data type overlaps the framework's coverage."""
    covered = {t.lower() for t in framework["data_types_covered"]}
    return bool(covered & {t.lower() for t in canonical_types})


def _assess_risk(record_count: int, framework: dict, incident_type: str) -> str:
    """Heuristic risk level for a given framework + incident."""
    deadline = framework.get("notification_deadline_hours")

    if record_count >= 10_000:
        return "CRITICAL"
    if record_count >= 1_000:
        return "HIGH"
    if deadline is not None and deadline <= 72:
        # Tight notification window raises the risk
        return "HIGH" if record_count >= 100 else "MEDIUM"
    if incident_type in ("ransomware", "insider_threat"):
        return "HIGH"
    return "MEDIUM" if record_count >= 100 else "LOW"


def _deadline_text(deadline_hours: int | None) -> str:
    if deadline_hours is None:
        return "No fixed deadline (reasonable time)"
    if deadline_hours < 48:
        return f"{deadline_hours} hours from discovery"
    days = deadline_hours // 24
    remainder = deadline_hours % 24
    if remainder:
        return f"{days} days and {remainder} hours from discovery"
    return f"{days} days from discovery"


def _build_checklist(framework_key: str, framework: dict, risk_level: str) -> list[dict[str, str]]:
    """Build a compliance checklist for one framework."""
    authority = framework["authority"]
    deadline = framework.get("notification_deadline_hours")
    items: list[dict[str, str]] = []

    # Notification to authority
    if deadline is not None:
        items.append({
            "item": f"Notify {authority} within {_deadline_text(deadline)}",
            "status": "pending",
            "priority": "critical",
        })
    else:
        items.append({
            "item": f"Notify {authority} within a reasonable timeframe",
            "status": "pending",
            "priority": "high",
        })

    # Document breach
    items.append({
        "item": "Document breach details, scope, and mitigation measures",
        "status": "pending",
        "priority": "high",
    })

    # Notify affected individuals
    items.append({
        "item": "Notify affected data subjects / individuals",
        "status": "pending",
        "priority": "high",
    })

    # Framework-specific items
    if framework_key == "GDPR":
        items.append({
            "item": "Conduct Data Protection Impact Assessment (DPIA)",
            "status": "pending",
            "priority": "medium",
        })
        items.append({
            "item": "Engage Data Protection Officer (DPO) if appointed",
            "status": "pending",
            "priority": "high",
        })
    elif framework_key == "HIPAA":
        items.append({
            "item": "Determine if breach affects 500+ individuals (triggers media notice)",
            "status": "pending",
            "priority": "high",
        })
        items.append({
            "item": "Report to HHS Breach Portal (if 500+ affected)",
            "status": "pending",
            "priority": "high",
        })
        items.append({
            "item": "Conduct risk assessment per 45 CFR 164.402",
            "status": "pending",
            "priority": "medium",
        })
    elif framework_key == "FERPA":
        items.append({
            "item": "Determine if breach qualifies under FERPA's health/safety emergency exception",
            "status": "pending",
            "priority": "medium",
        })
        items.append({
            "item": "Review student consent records and disclosure logs",
            "status": "pending",
            "priority": "medium",
        })
    elif framework_key == "CCPA":
        items.append({
            "item": "Assess whether breach triggers private right of action under \u00a71798.150",
            "status": "pending",
            "priority": "high",
        })
        items.append({
            "item": "Verify security procedures meet 'reasonable security' standard",
            "status": "pending",
            "priority": "medium",
        })
    elif framework_key == "PCI_DSS":
        items.append({
            "item": "Notify acquiring bank and payment card brands within 24 hours",
            "status": "pending",
            "priority": "critical",
        })
        items.append({
            "item": "Engage PCI Forensic Investigator (PFI) for forensic analysis",
            "status": "pending",
            "priority": "high",
        })
        items.append({
            "item": "Preserve all system logs and evidence for investigation",
            "status": "pending",
            "priority": "critical",
        })

    # Legal review is always recommended
    items.append({
        "item": "Engage legal counsel experienced with " + framework["name"],
        "status": "pending",
        "priority": "high",
    })

    return items


def _required_actions(framework_key: str, framework: dict) -> list[str]:
    """Generate a list of required actions for a triggered framework."""
    authority = framework["authority"]
    deadline_text = _deadline_text(framework.get("notification_deadline_hours"))

    actions = [
        f"Notify {authority} ({deadline_text})",
        "Document the breach: scope, affected records, mitigation steps taken",
        "Notify affected individuals without undue delay",
    ]

    if framework_key == "GDPR":
        actions.append("Conduct and record a Data Protection Impact Assessment")
        actions.append("Assess whether cross-border data transfer is involved")
    elif framework_key == "HIPAA":
        actions.append("Perform four-factor risk assessment per 45 CFR 164.402")
        actions.append("If 500+ individuals affected, notify prominent media outlets")
    elif framework_key == "PCI_DSS":
        actions.append("Engage PCI Forensic Investigator (PFI)")
        actions.append("Contain and isolate compromised payment systems")

    return actions


def _applies_because_text(
    framework_key: str,
    framework: dict,
    data_classes: list[str],
    incident_type: str,
) -> str:
    """Human-readable explanation of why a framework applies."""
    covered = {t.lower() for t in framework["data_types_covered"]}
    canonical = _normalize_data_classes(data_classes)
    overlapping = covered & {t.lower() for t in canonical}

    type_label = incident_type.replace("_", " ")

    if framework_key == "GDPR":
        return (
            f"Personal data ({', '.join(data_classes)}) exposed in a {type_label} "
            f"incident. GDPR applies to any processing of EU/EEA residents' data."
        )
    if framework_key == "HIPAA":
        return (
            f"Protected health information ({', '.join(overlapping)}) exposed. "
            f"HIPAA Breach Notification Rule requires disclosure."
        )
    if framework_key == "FERPA":
        return (
            f"Education records or student PII ({', '.join(overlapping)}) exposed. "
            f"FERPA protects student education records at federally funded institutions."
        )
    if framework_key == "CCPA":
        return (
            f"Personal information ({', '.join(data_classes)}) of California "
            f"residents potentially exposed in a {type_label} incident."
        )
    if framework_key == "PCI_DSS":
        return (
            f"Payment card or financial data ({', '.join(overlapping)}) exposed. "
            f"PCI-DSS mandates immediate notification and forensic investigation."
        )

    return f"Data types {', '.join(overlapping)} overlap with {framework['name']} coverage."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_compliance(
    data_classes: list[str],
    incident_type: str,
    record_count: int,
) -> dict[str, Any]:
    """Determine which compliance frameworks apply and build action plans.

    Args:
        data_classes: Labels describing the types of data exposed
                      (e.g. ``["credentials", "PII", "financial"]``).
        incident_type: The classified incident type string
                       (e.g. ``"credential_stuffing"``).
        record_count: Estimated number of records affected.

    Returns:
        A structured dict with applicable frameworks, checklists, and
        an overall risk assessment.
    """
    canonical = _normalize_data_classes(data_classes)

    applicable: list[dict[str, Any]] = []
    deadlines: list[tuple[int, str]] = []

    # Check each framework for applicability
    for fkey, fdata in COMPLIANCE_FRAMEWORKS.items():
        if not _framework_applies(fkey, fdata, canonical):
            continue

        risk = _assess_risk(record_count, fdata, incident_type)
        checklist = _build_checklist(fkey, fdata, risk)
        actions = _required_actions(fkey, fdata)
        reason = _applies_because_text(fkey, fdata, data_classes, incident_type)

        deadline_hours = fdata.get("notification_deadline_hours")
        deadline_str = _deadline_text(deadline_hours)
        if deadline_hours is not None:
            deadlines.append((deadline_hours, f"{deadline_str} ({fkey})"))

        entry: dict[str, Any] = {
            "framework": fkey,
            "full_name": fdata["name"],
            "region": fdata["region"],
            "applies_because": reason,
            "notification_deadline": deadline_str,
            "required_actions": actions,
            "risk_level": risk,
            "penalties": fdata["penalties"],
            "key_articles": fdata["key_articles"],
            "checklist": checklist,
        }
        applicable.append(entry)

    # Incident-specific flags may add frameworks not caught by data-class matching
    specific = _INCIDENT_SPECIFIC_FLAGS.get(incident_type, {})
    if specific:
        existing_keys = {a["framework"] for a in applicable}
        for extra_key in specific.get("extra_frameworks", []):
            if extra_key not in existing_keys and extra_key in COMPLIANCE_FRAMEWORKS:
                fdata = COMPLIANCE_FRAMEWORKS[extra_key]
                risk = _assess_risk(record_count, fdata, incident_type)
                checklist = _build_checklist(extra_key, fdata, risk)
                actions = _required_actions(extra_key, fdata)

                deadline_hours = fdata.get("notification_deadline_hours")
                deadline_str = _deadline_text(deadline_hours)
                if deadline_hours is not None:
                    deadlines.append((deadline_hours, f"{deadline_str} ({extra_key})"))

                reason = (
                    f"Triggered by incident type '{incident_type.replace('_', ' ')}'. "
                    + "; ".join(specific.get("articles", []))
                )

                entry = {
                    "framework": extra_key,
                    "full_name": fdata["name"],
                    "region": fdata["region"],
                    "applies_because": reason,
                    "notification_deadline": deadline_str,
                    "required_actions": actions,
                    "risk_level": risk,
                    "penalties": fdata["penalties"],
                    "key_articles": fdata["key_articles"],
                    "checklist": checklist,
                }
                applicable.append(entry)

        # Attach incident-specific recommendations & notes to every entry
        for entry in applicable:
            entry["incident_recommendations"] = specific.get("recommendations", [])
            entry["incident_notes"] = specific.get("notes", [])

    # Compute overall risk (highest among all applicable frameworks)
    _risk_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    overall_risk = "LOW"
    for a in applicable:
        if _risk_order.get(a["risk_level"], 0) > _risk_order.get(overall_risk, 0):
            overall_risk = a["risk_level"]

    # Most urgent deadline
    most_urgent = "No fixed deadline"
    if deadlines:
        deadlines.sort(key=lambda d: d[0])
        most_urgent = deadlines[0][1]

    result: dict[str, Any] = {
        "applicable_frameworks": applicable,
        "overall_risk": overall_risk,
        "most_urgent_deadline": most_urgent,
        "total_frameworks_triggered": len(applicable),
    }

    log.info(
        "compliance.analysis_complete",
        frameworks_triggered=len(applicable),
        overall_risk=overall_risk,
        most_urgent_deadline=most_urgent,
    )

    return result


# ---------------------------------------------------------------------------
# LLM-powered compliance narrative
# ---------------------------------------------------------------------------


async def generate_compliance_report(
    incident_report: dict[str, Any],
    data_classes: list[str],
    record_count: int,
) -> str:
    """Generate a human-readable compliance report section.

    Uses the Truefoundry LLM gateway (via ``truefoundry_llm.chat``) to
    produce a tailored narrative covering regulatory timelines, required
    notifications, and recommended legal actions.

    Args:
        incident_report: The full incident report dict produced by the
                         deep researcher.
        data_classes: Labels describing the types of data exposed.
        record_count: Estimated number of records affected.

    Returns:
        A formatted compliance report string.
    """
    from sentinel.integrations import truefoundry_llm

    incident_type = incident_report.get("incident_type", "unknown")
    analysis = analyze_compliance(data_classes, incident_type, record_count)

    # Build a compact summary of the analysis for the LLM
    frameworks_summary = []
    for fw in analysis["applicable_frameworks"]:
        frameworks_summary.append(
            f"- {fw['framework']} ({fw['full_name']}): {fw['applies_because']}  "
            f"Deadline: {fw['notification_deadline']}. Risk: {fw['risk_level']}. "
            f"Penalties: {fw['penalties']}."
        )

    frameworks_text = "\n".join(frameworks_summary) if frameworks_summary else "No frameworks triggered."

    incident_specific = _INCIDENT_SPECIFIC_FLAGS.get(incident_type, {})
    notes_text = ""
    if incident_specific:
        notes_lines = incident_specific.get("notes", []) + incident_specific.get("articles", [])
        if notes_lines:
            notes_text = "\nINCIDENT-SPECIFIC NOTES:\n" + "\n".join(f"- {n}" for n in notes_lines)

    prompt = f"""You are a regulatory compliance advisor specializing in data breach response.
Given the following incident and compliance analysis, produce a clear, actionable
compliance report section suitable for inclusion in an executive incident brief.

INCIDENT SUMMARY:
- Source: {incident_report.get('breach_source', 'Unknown')}
- Type: {incident_type}
- Severity: {incident_report.get('severity', 'HIGH')}
- Estimated records affected: {record_count}
- Data classes exposed: {', '.join(data_classes)}
- Detection date: {time.strftime('%Y-%m-%d')}

APPLICABLE REGULATORY FRAMEWORKS:
{frameworks_text}

Overall risk: {analysis['overall_risk']}
Most urgent deadline: {analysis['most_urgent_deadline']}
{notes_text}

Produce a report section with these headings:
1. REGULATORY EXPOSURE SUMMARY — which regulations are triggered and why
2. NOTIFICATION TIMELINE — a chronological list of deadlines and required actions
3. REQUIRED NOTIFICATIONS — who must be notified (authorities, individuals, media)
4. RECOMMENDED LEGAL ACTIONS — specific steps for legal/compliance teams
5. RISK MITIGATION — actions to reduce regulatory penalties

Be specific. Reference article numbers and deadlines. Do not use generic advice.
If the incident type is credential stuffing, mention the 23andMe precedent.
If the incident type is phishing, note it is HIPAA's top breach vector."""

    try:
        response = await truefoundry_llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a regulatory compliance expert. Produce clear, "
                        "structured compliance guidance. Use markdown formatting."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=3072,
        )
        narrative = response.strip()
    except Exception as e:
        log.warning("compliance.llm_narrative_failed", error=str(e))
        narrative = _build_fallback_narrative(analysis, incident_report, data_classes, record_count)

    # Prepend a machine-readable header
    header_lines = [
        "=" * 72,
        "COMPLIANCE ANALYSIS REPORT",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC')}",
        f"Incident: {incident_report.get('breach_source', 'Unknown')} ({incident_type})",
        f"Frameworks triggered: {analysis['total_frameworks_triggered']}",
        f"Overall risk: {analysis['overall_risk']}",
        f"Most urgent deadline: {analysis['most_urgent_deadline']}",
        "=" * 72,
        "",
    ]

    return "\n".join(header_lines) + narrative


def _build_fallback_narrative(
    analysis: dict[str, Any],
    incident_report: dict[str, Any],
    data_classes: list[str],
    record_count: int,
) -> str:
    """Build a structured text report when the LLM is unavailable."""
    incident_type = incident_report.get("incident_type", "unknown")
    sections: list[str] = []

    # 1. Regulatory exposure
    sections.append("## 1. REGULATORY EXPOSURE SUMMARY\n")
    if not analysis["applicable_frameworks"]:
        sections.append("No regulatory frameworks were triggered based on the data classes identified.\n")
    else:
        for fw in analysis["applicable_frameworks"]:
            sections.append(
                f"**{fw['framework']}** ({fw['full_name']}) - Risk: {fw['risk_level']}\n"
                f"  {fw['applies_because']}\n"
                f"  Penalties: {fw['penalties']}\n"
            )

    # 2. Timeline
    sections.append("\n## 2. NOTIFICATION TIMELINE\n")
    sorted_fw = sorted(
        analysis["applicable_frameworks"],
        key=lambda f: (
            COMPLIANCE_FRAMEWORKS.get(f["framework"], {}).get("notification_deadline_hours") or 99999
        ),
    )
    for fw in sorted_fw:
        sections.append(f"- **{fw['framework']}**: {fw['notification_deadline']}")

    # 3. Required notifications
    sections.append("\n\n## 3. REQUIRED NOTIFICATIONS\n")
    for fw in analysis["applicable_frameworks"]:
        sections.append(f"**{fw['framework']}**:")
        for action in fw["required_actions"]:
            sections.append(f"  - {action}")
        sections.append("")

    # 4. Legal actions
    sections.append("\n## 4. RECOMMENDED LEGAL ACTIONS\n")
    sections.append("- Retain legal counsel experienced in data breach response")
    sections.append("- Preserve all logs, communications, and forensic evidence")
    sections.append(f"- Review insurance coverage for data breach (est. {record_count} records)")

    specific = _INCIDENT_SPECIFIC_FLAGS.get(incident_type, {})
    if specific:
        for rec in specific.get("recommendations", []):
            sections.append(f"- {rec}")
        for note in specific.get("notes", []):
            sections.append(f"- NOTE: {note}")

    # 5. Risk mitigation
    sections.append("\n\n## 5. RISK MITIGATION\n")
    sections.append("- Demonstrate good-faith compliance efforts (prompt notification, cooperation)")
    sections.append("- Document all remediation actions with timestamps")
    sections.append("- Engage third-party forensics to establish breach scope")

    return "\n".join(sections)
