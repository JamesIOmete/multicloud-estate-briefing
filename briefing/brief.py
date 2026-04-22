"""CLI entrypoint for the Multi-Cloud Estate Briefing tool."""
from __future__ import annotations

import argparse
import json
import os
import sys

from briefing.parser import build_estate, EstateSummary
from briefing.prompt import build_messages
from briefing.llm import call_llm
from briefing.formatter import format_briefing


def post_workflow_summary(body: str) -> None:
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if not summary_file:
        raise EnvironmentError("GITHUB_STEP_SUMMARY is not set — cannot post workflow summary.")
    with open(summary_file, "a") as f:
        f.write("\n" + body + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an AI estate briefing from UC02 inventory artifacts")

    # Single-cloud mode
    parser.add_argument("--inventory", help="Path to a single inventory.json (any cloud)")
    parser.add_argument("--previous", help="Previous inventory.json for drift detection")

    # Multi-cloud mode
    parser.add_argument("--inventory-aws", help="Path to AWS inventory.json")
    parser.add_argument("--inventory-azure", help="Path to Azure inventory.json")
    parser.add_argument("--inventory-gcp", help="Path to GCP inventory.json")

    # Output options
    parser.add_argument("--output", help="Write briefing markdown to this file")
    parser.add_argument("--post-summary", action="store_true",
                        help="Append briefing to GITHUB_STEP_SUMMARY")

    args = parser.parse_args(argv)

    inventories: list[dict] = []

    # Collect single or multi-cloud inputs
    for path in [args.inventory, args.inventory_aws, args.inventory_azure, args.inventory_gcp]:
        if path:
            with open(path) as f:
                inventories.append(json.load(f))

    if not inventories:
        print("Error: at least one --inventory* path must be provided.", file=sys.stderr)
        return 1

    estate = build_estate(inventories)

    # Drift detection
    if args.previous:
        with open(args.previous) as f:
            prev_data = json.load(f)
        estate.has_drift = True
        estate.drift_description = _summarise_drift(prev_data, inventories[0])

    messages = build_messages(estate)
    raw_text = call_llm(messages)
    briefing = format_briefing(raw_text, estate)

    if args.post_summary:
        post_workflow_summary(briefing)
        print("Briefing posted to GitHub Actions workflow summary.")
    elif args.output:
        with open(args.output, "w") as f:
            f.write(briefing)
        print(f"Briefing written to {args.output}")
    else:
        print(briefing)

    return 0


def _summarise_drift(old: dict, new: dict) -> str:
    """Produce a simple count-delta string for the LLM to interpret."""
    def counts(inv: dict) -> dict:
        c = inv.get("counts", {})
        return {
            "vpcs": c.get("network", {}).get("vpcs", 0),
            "subnets": c.get("network", {}).get("subnets", 0),
            "instances": c.get("compute", {}).get("instances", 0),
            "security_groups": c.get("network", {}).get("security_groups", 0),
        }

    old_c = counts(old)
    new_c = counts(new)
    deltas = {k: new_c.get(k, 0) - old_c.get(k, 0) for k in old_c}
    parts = [f"{k}: {'+' if v >= 0 else ''}{v}" for k, v in deltas.items() if v != 0]
    return "Resource count deltas since last snapshot: " + (", ".join(parts) if parts else "no count changes") + "."


if __name__ == "__main__":
    sys.exit(main())
