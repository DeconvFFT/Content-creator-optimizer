---
type: ingestion-audit
project: agent-studio-system-design
status: active
updated: 2026-05-19
---

# Source Map Path Integrity Audit

## Scope

This audit checks whether `output/viewers/system-design-source-map.json` and the embedded `source-data` block in `output/viewers/system-design-source-map.html` use vault-relative paths that resolve to existing Obsidian notes. It is operational metadata only; it stores no raw book text, transcripts, copied source excerpts, or source payload files.

## Result

| Check | Result | Evidence |
|---|---:|---|
| JSON source records | pass | 175 records checked during the 2026-05-19 nightly maintenance pass; 0 missing `path` fields. |
| JSON path style | pass | 0 records retain the redundant `system_design_vault/` prefix; all paths are vault-relative. |
| JSON path resolution | pass | 175 record paths resolve under `system_design_vault/`; 0 missing note targets. |
| HTML embedded source records | pass | 175 embedded records checked during the same pass. |
| HTML path style | pass | 0 embedded records retain the redundant `system_design_vault/` prefix. |
| HTML path resolution | pass | 175 embedded record paths resolve under `system_design_vault/`; 0 missing note targets. |

## Current Rule

Treat source-map record paths as vault-relative note paths. For example, use `01-sources/official-open/openai-evals-and-agent-evals.md`, not `system_design_vault/01-sources/official-open/openai-evals-and-agent-evals.md`.

When regenerating the source map, update both:

- `output/viewers/system-design-source-map.json`
- the embedded `source-data` JSON block in `output/viewers/system-design-source-map.html`

Then rerun this audit before relying on the viewer for downstream route planning.
