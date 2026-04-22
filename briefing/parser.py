"""Normalise UC02 inventory.json files (AWS, Azure, GCP) into a common EstateSummary."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CloudSummary:
    cloud: str                          # "aws" | "azure" | "gcp"
    generated_at: str
    scope: str                          # account/subscription/project identifier
    region: str

    # Normalised counts
    vpc_count: int = 0
    subnet_count: int = 0
    security_group_count: int = 0
    public_ip_count: int = 0
    instance_count: int = 0
    iam_role_count: int = 0
    service_account_count: int = 0
    storage_count: int = 0

    # Risk signals
    uses_default_vpc: bool = False
    uses_default_service_account: bool = False
    has_open_firewall_rules: bool = False
    untagged_resource_count: int = 0

    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class EstateSummary:
    clouds: list[CloudSummary]
    has_drift: bool = False
    drift_description: str = ""


def parse_inventory(data: dict[str, Any]) -> CloudSummary:
    """Detect cloud from inventory structure and dispatch to the right parser."""
    cloud = _detect_cloud(data)
    if cloud == "aws":
        return _parse_aws(data)
    if cloud == "azure":
        return _parse_azure(data)
    if cloud == "gcp":
        return _parse_gcp(data)
    raise ValueError(f"Unrecognised inventory cloud: {cloud!r}")


def build_estate(inventories: list[dict[str, Any]]) -> EstateSummary:
    return EstateSummary(clouds=[parse_inventory(inv) for inv in inventories])


# ── cloud detection ───────────────────────────────────────────────────────────

def _detect_cloud(data: dict[str, Any]) -> str:
    meta = data.get("meta", {})
    # Normalised schema carries an explicit scope.cloud field
    if "scope" in data:
        return data["scope"].get("cloud", "aws")
    # AWS: identity.account_id or identity.caller
    if "identity" in data and "caller" in data.get("identity", {}):
        return "aws"
    # Azure: meta.subscription_id
    if "subscription_id" in meta or "tenant_id" in meta:
        return "azure"
    # GCP: meta.project_id or iam.service_accounts
    if "project_id" in meta or "service_accounts" in data.get("iam", {}):
        return "gcp"
    return "aws"


# ── AWS ───────────────────────────────────────────────────────────────────────

def _parse_aws(data: dict[str, Any]) -> CloudSummary:
    meta = data.get("meta", {})
    identity = data.get("identity", {})
    network = data.get("network", {})
    compute = data.get("compute", {})
    iam = data.get("iam", {})

    account_id = (
        identity.get("account_id")
        or data.get("scope", {}).get("account_id", "unknown")
    )
    region = meta.get("region") or data.get("scope", {}).get("region", "unknown")

    vpcs = network.get("vpcs", []) or []
    subnets = network.get("subnets", []) or []
    sgs = network.get("security_groups", []) or []
    instances = compute.get("instances", []) or []
    elbv2 = compute.get("load_balancers_v2", []) or []

    # Default VPC check
    uses_default_vpc = any(v.get("IsDefault") for v in vpcs)

    # IAM roles from normalised schema counts if available
    counts = data.get("counts", {})
    iam_count = counts.get("iam", {}).get("roles", 0)

    return CloudSummary(
        cloud="aws",
        generated_at=meta.get("generated_at", ""),
        scope=account_id,
        region=region,
        vpc_count=len(vpcs) or counts.get("network", {}).get("vpcs", 0),
        subnet_count=len(subnets) or counts.get("network", {}).get("subnets", 0),
        security_group_count=len(sgs) or counts.get("network", {}).get("security_groups", 0),
        instance_count=len(instances) or counts.get("compute", {}).get("instances", 0),
        iam_role_count=iam_count,
        uses_default_vpc=uses_default_vpc,
        raw=data,
    )


# ── Azure ─────────────────────────────────────────────────────────────────────

def _parse_azure(data: dict[str, Any]) -> CloudSummary:
    meta = data.get("meta", {})
    network = data.get("network", {})
    compute = data.get("compute", {})

    subscription_id = (
        meta.get("subscription_id")
        or data.get("scope", {}).get("subscription_id", "unknown")
    )
    # Azure inventories are typically multi-region; pick first location or 'multi'
    locations = data.get("locations", [])
    region = locations[0].get("name", "multi") if locations else "multi"

    vnets = network.get("vnets", []) or []
    nsgs = network.get("nsgs", []) or []
    public_ips = network.get("public_ips", []) or []
    vms = compute.get("virtual_machines", []) or []
    storage = data.get("storage", {}).get("accounts", []) or []

    counts = data.get("counts", {})

    return CloudSummary(
        cloud="azure",
        generated_at=meta.get("generated_at", ""),
        scope=subscription_id,
        region=region,
        vpc_count=len(vnets) or counts.get("network", {}).get("vnets", 0),
        subnet_count=counts.get("network", {}).get("subnets", 0),
        security_group_count=len(nsgs) or counts.get("network", {}).get("nsgs", 0),
        public_ip_count=len(public_ips) or counts.get("network", {}).get("public_ips", 0),
        instance_count=len(vms) or counts.get("compute", {}).get("instances", 0),
        storage_count=len(storage) or counts.get("storage", {}).get("accounts", 0),
        raw=data,
    )


# ── GCP ───────────────────────────────────────────────────────────────────────

def _parse_gcp(data: dict[str, Any]) -> CloudSummary:
    meta = data.get("meta", {})
    network = data.get("network", {})
    compute = data.get("compute", {})
    iam = data.get("iam", {})

    project_id = (
        meta.get("project_id")
        or data.get("scope", {}).get("project_id", "unknown")
    )
    region = meta.get("region") or data.get("scope", {}).get("region", "unknown")

    vpcs = network.get("vpcs", []) or []
    subnets = network.get("subnets", []) or []
    firewall_rules = network.get("firewall_rules", []) or []
    instances = compute.get("instances", []) or []
    service_accounts = iam.get("service_accounts", []) or []

    # Default service account check (GCP default SA has '-compute@developer' pattern)
    uses_default_sa = any(
        "compute@developer" in sa.get("email", "") for sa in service_accounts
    )

    # Open firewall rule: direction INGRESS with IPranges containing 0.0.0.0/0
    has_open_fw = any(
        r.get("direction") == "INGRESS"
        and "0.0.0.0/0" in (r.get("sourceRanges") or [])
        for r in firewall_rules
    )

    counts = data.get("counts", {})

    return CloudSummary(
        cloud="gcp",
        generated_at=meta.get("generated_at", ""),
        scope=project_id,
        region=region,
        vpc_count=len(vpcs) or counts.get("network", {}).get("vpcs", 0),
        subnet_count=len(subnets) or counts.get("network", {}).get("subnets", 0),
        security_group_count=len(firewall_rules) or counts.get("network", {}).get("firewall_rules", 0),
        instance_count=len(instances) or counts.get("compute", {}).get("instances", 0),
        service_account_count=len(service_accounts),
        uses_default_service_account=uses_default_sa,
        has_open_firewall_rules=has_open_fw,
        raw=data,
    )
