"""Build LLM messages from an EstateSummary."""
from __future__ import annotations

from briefing.parser import EstateSummary, CloudSummary

_SYSTEM = """\
You are a senior multi-cloud Solution Architect reviewing an automated estate inventory.
You receive a normalised summary of cloud resources across AWS, Azure, and/or GCP and produce
a concise, actionable briefing for an engineering or leadership audience.

Your output must be plain markdown (no outer code fences wrapping the entire response).
Structure your response as follows:

1. **Overview** — 2-4 sentences describing what is running, across which clouds, and the overall complexity level.

2. **Anomaly Callouts** — bullet list of anything unexpected or worth flagging (e.g. default VPCs, unusually high resource counts, empty environments, missing resources that should be present). Omit if none.

3. **Security Observations** — bullet list of security-relevant findings (open firewall rules, default service accounts, high public IP counts, etc.). Omit if none.

4. **Drift Summary** — only include this section if drift data is provided. Describe what changed between the two inventory snapshots in plain English.

5. **Recommended Next Actions** — numbered list of 2-5 prioritised, specific actions based on what you found. Reference the multicloud-sa-toolkit use cases (UC01 landing zone, UC02 inventory, UC03 monitoring, UC04 sandbox, UC05 identity) where relevant.

Be concise. A briefing is a decision-support document, not an exhaustive report."""


def build_messages(summary: EstateSummary) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _format_estate_context(summary)},
    ]


def _format_estate_context(summary: EstateSummary) -> str:
    lines = [f"Estate spans {len(summary.clouds)} cloud(s): {', '.join(c.cloud.upper() for c in summary.clouds)}", ""]

    for cloud in summary.clouds:
        lines.append(_format_cloud(cloud))

    if summary.has_drift:
        lines.append("## Drift detected")
        lines.append(summary.drift_description)
        lines.append("")

    return "\n".join(lines)


def _format_cloud(c: CloudSummary) -> str:
    lines = [
        f"### {c.cloud.upper()}",
        f"Scope: {c.scope} | Region: {c.region} | Snapshot: {c.generated_at}",
        "",
        "Resource counts:",
        f"  VPCs/VNets: {c.vpc_count}",
        f"  Subnets: {c.subnet_count}",
        f"  Security groups / NSGs / Firewall rules: {c.security_group_count}",
        f"  Public IPs: {c.public_ip_count}",
        f"  Compute instances: {c.instance_count}",
        f"  IAM roles: {c.iam_role_count}",
        f"  Service accounts: {c.service_account_count}",
        f"  Storage accounts/buckets: {c.storage_count}",
        "",
    ]

    signals: list[str] = []
    if c.uses_default_vpc:
        signals.append("Default VPC is present and in use")
    if c.uses_default_service_account:
        signals.append("Default compute service account in use")
    if c.has_open_firewall_rules:
        signals.append("Firewall rules with open ingress (0.0.0.0/0) detected")
    if c.untagged_resource_count > 0:
        signals.append(f"{c.untagged_resource_count} untagged resources")

    if signals:
        lines.append("Risk signals:")
        for s in signals:
            lines.append(f"  - {s}")
        lines.append("")

    return "\n".join(lines)
