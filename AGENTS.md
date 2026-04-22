# Agent Guidance

## Command approvals
- Ask before any cloud-CLI commands (`aws`, `az`, `gcloud`).
- Ask before any command that writes outside the repo or requires network access (except `pip install`).
- After important code changes and testing, offer to push updates to GitHub with a clear commit message.

## Validation defaults
- Do not run tests or validation unless explicitly requested.
- If asked to validate, run: `pytest tests/ -v`

## Credentials
- Do not read, modify, echo, or log any API keys, tokens, or secrets.
- `OPENAI_API_KEY`, `AZURE_OPENAI_KEY`, and `GITHUB_TOKEN` are secrets — never print them.

## Inventory files
- `inventory.json` files may contain account IDs, subscription IDs, and project IDs.
- Treat these as sensitive — do not commit real inventory files; use only sanitized fixtures.
- Do not commit any `out/` directory content.
