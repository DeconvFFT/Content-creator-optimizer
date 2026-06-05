# CS25 Video Cache

Caches the known-good set of CS25 YouTube embed IDs to detect false deltas from content-identical redeployments (Variant D — YouTube embed ID rotation).

## Current Known IDs (as of 2026-06-03 ~10:05 UTC)

All 5 YouTube embed IDs rotated. oEmbed confirmed identical video titles — Variant D redeployment, no new content.

| # | Video ID | Title | Speaker |
|---|----------|-------|---------|
| 1 | `bHSDPgZYie0` | Stanford CS25: Transformers United V6 I Overview of Transformers | (V6) |
| 2 | `3gb-ZkVRemQ` | Stanford CS25: V4 I Jason Wei & Hyung Won Chung of OpenAI | V4 |
| 3 | `1GbDTTK3aR4` | Stanford CS25: V3 I How I Learned to Stop Worrying and Love the Transformer | V3 |
| 4 | `AdLgPmcrXwQ` | Stanford CS25: V4 I Aligning Open Language Models | V4 |
| 5 | `mE7IDf2SmJg` | Stanford CS25: V3 I Retrieval Augmented Language Models | V3 |

## Previous Known IDs (stale — all return HTTP 404 from oEmbed)

| # | Video ID | Title |
|---|----------|-------|
| 1 | `N67UoRcouDY` | Stanford CS25: Transformers United V6 I Overview of Transformers |
| 2 | `bZQ1LJhHjYQ` | Stanford CS25: V4 I Jason Wei & Hyung Won Chung of OpenAI |
| 3 | `r2TzMo1tXXc` | Stanford CS25: V3 I How I Learned to Stop Worrying and Love the Transformer |
| 4 | `MNQhYKCJn18` | Stanford CS25: V4 I Aligning Open Language Models |
| 5 | `GDmhJ8d40Nc` | Stanford CS25: V3 I Retrieval Augmented Language Models |

## Usage

When running CS25 recheck, compare extracted IDs against `current_ids` above. If they differ:
1. Fetch oEmbed titles for ALL current IDs and the stored current IDs
2. If the title sets are identical → Variant D (redeployment), update `current_ids`, do NOT report a delta
3. If new titles appear → real queue change, report as delta