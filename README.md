# multicloud-estate-briefing

A GitHub Actions workflow + Python tool that ingests UC02 inventory artifacts from [multicloud-sa-toolkit](https://github.com/JamesIOmete/multicloud-sa-toolkit) — across AWS, Azure, and GCP — and uses an LLM to produce a natural-language **"state of the estate" briefing**.

---

## How it fits the portfolio

```
multicloud-sa-toolkit (UC02)          multicloud-estate-briefing
─────────────────────────────         ──────────────────────────────────
discover.sh                           parser.py
  → inventory.json          ──────►     normalise across clouds
  → SUMMARY.md                          │
  → SCORECARD.md                        ▼
                                      prompt.py  →  llm.py
                                        │
                                        ▼
                                      formatter.py
                                        → BRIEFING.md (artifact)
                                        → posted as workflow summary
```

The toolkit discovers and documents what's running. This project interprets it and tells you what matters.

---

## What the briefing contains

- **Estate overview** — plain-English summary of resources across all clouds in scope
- **Anomaly callouts** — unexpected resource counts, untagged resources, default-VPC usage
- **Security observations** — public IPs without purpose, open firewall rules, default service accounts
- **Drift detection** (optional) — what changed between two inventory snapshots, using `uc02_diff.py`
- **Recommended next actions** — prioritised, actionable, scoped to what was found

---

## Quick start

### Single-cloud, single snapshot

```yaml
jobs:
  estate-brief:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Assumes UC02 discovery already ran and uploaded inventory.json as an artifact.
      # Download it here, or pass a path to an existing file.

      - name: Generate estate briefing
        uses: JamesIOmete/multicloud-estate-briefing@v1
        with:
          inventory-path: out/artifacts/inventory.json
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Multi-cloud (all three in one briefing)

```yaml
      - name: Generate multi-cloud estate briefing
        uses: JamesIOmete/multicloud-estate-briefing@v1
        with:
          inventory-path-aws: out/aws/artifacts/inventory.json
          inventory-path-azure: out/azure/artifacts/inventory.json
          inventory-path-gcp: out/gcp/artifacts/inventory.json
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

### With drift detection

```yaml
      - name: Generate estate briefing with drift
        uses: JamesIOmete/multicloud-estate-briefing@v1
        with:
          inventory-path: out/artifacts/inventory.json
          previous-inventory-path: previous/artifacts/inventory.json
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

---

## Running locally

```bash
pip install -r requirements.txt

# Single cloud
python -m briefing.brief --inventory path/to/inventory.json

# Multi-cloud
python -m briefing.brief \
  --inventory-aws path/to/aws/inventory.json \
  --inventory-azure path/to/azure/inventory.json \
  --inventory-gcp path/to/gcp/inventory.json

# With drift detection
python -m briefing.brief \
  --inventory path/to/new/inventory.json \
  --previous path/to/old/inventory.json \
  --output BRIEFING.md
```

---

## Example briefing output

> ## 🌐 Multi-Cloud Estate Briefing
> *Generated: 2026-04-22 | Clouds: AWS, Azure, GCP*
>
> ### Overview
> The estate spans 3 cloud environments with a modest compute footprint (5 EC2 instances, 0 Azure VMs, 1 GCP instance). Networking is minimal — no load balancers in Azure or GCP, and AWS carries the primary workload behind a single ALB.
>
> ### Anomaly Callouts
> - **AWS**: Default VPC is present and in use. Default VPCs carry broader-than-needed permissions and should be replaced with a purpose-built VPC before workload expansion.
> - **GCP**: Default service account in use. Consider creating a dedicated least-privilege service account.
>
> ### Security Observations
> - **AWS**: 22 security groups detected for 1 VPC — high ratio suggests accumulation of unused rules. Audit recommended.
> - **GCP**: `privateIpGoogleAccess: false` on default subnet — services may be routing traffic externally unnecessarily.
>
> ### Recommended Next Actions
> 1. Replace default VPC (AWS) with a purpose-built network — use UC01 landing zone module.
> 2. Audit and consolidate security groups (AWS) — target < 5 active groups for this footprint.
> 3. Create a dedicated GCP service account scoped to required APIs only.

---

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `inventory-path` | No* | — | Path to a single `inventory.json` (any cloud) |
| `inventory-path-aws` | No* | — | Path to AWS `inventory.json` |
| `inventory-path-azure` | No* | — | Path to Azure `inventory.json` |
| `inventory-path-gcp` | No* | — | Path to GCP `inventory.json` |
| `previous-inventory-path` | No | — | Previous snapshot for drift detection |
| `anthropic-api-key` | No† | — | Anthropic API key (takes priority if set) |
| `anthropic-model` | No | `claude-sonnet-4-5` | Anthropic model name |
| `openai-api-key` | No† | — | OpenAI API key |
| `azure-openai-endpoint` | No† | — | Azure OpenAI endpoint |
| `azure-openai-key` | No† | — | Azure OpenAI key |
| `azure-openai-deployment` | No | `gpt-4o` | Azure OpenAI deployment name |
| `model` | No | `gpt-4o` | OpenAI model name |
| `github-token` | Yes | `${{ github.token }}` | Token for posting workflow summary |

\* At least one `inventory-path*` must be provided.
† One of `anthropic-api-key`, `openai-api-key`, or the `azure-openai-*` pair must be provided. Anthropic is used by default if `anthropic-api-key` is set.

---

## Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Fixtures in `tests/fixtures/` are sanitized inventory samples drawn from
multicloud-sa-toolkit UC02 discovery runs.

---

## Related projects

- **[multicloud-sa-toolkit](https://github.com/JamesIOmete/multicloud-sa-toolkit)** — the UC02 discovery toolkit that produces the `inventory.json` files this briefing tool consumes.
- **[tf-plan-ai-reviewer](https://github.com/JamesIOmete/tf-plan-ai-reviewer)** — AI-powered Terraform plan reviewer; complements this tool by catching risks before they reach the estate.
- **[tf-scaffold-ai](https://github.com/JamesIOmete/tf-scaffold-ai)** — generates a working Terraform scaffold from a plain-language architecture description; the upstream generative counterpart to this briefing tool.

---

## License

MIT
