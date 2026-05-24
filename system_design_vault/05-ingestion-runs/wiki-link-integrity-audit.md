---
type: vault-link-audit
project: agent-studio-system-design
status: active
updated: 2026-05-19
scope:
  - system_design_vault/**/*.md
---

# Wiki Link Integrity Audit

## Purpose

This audit verifies that Obsidian wiki links resolve to current Markdown notes in the vault. It checks navigation integrity only; it does not prove source understanding, source freshness, or design correctness.

## Current Result

| Check | Result |
|---|---:|
| Markdown notes scanned | 292 |
| Internal wiki links scanned | 1,698 |
| Missing link targets | 0 |

## Resolution Rules

- Exact vault-relative note paths are accepted.
- Unique basename links are accepted.
- Relative links using `../` or `./` are resolved from the source note directory.
- Heading anchors and display aliases are ignored for target-existence checks.

## Agent Studio Implications

- The current vault is navigable as an Obsidian knowledge graph without known missing note targets.
- Broken-link checks should run after adding source notes, chapter notes, MOC entries, source-map notes, or ingestion-run audit notes.
- Link integrity is a routing/audit convenience, not source-canon evidence. A resolved link still needs source status, rights status, and coverage granularity before it is used as architecture evidence.
