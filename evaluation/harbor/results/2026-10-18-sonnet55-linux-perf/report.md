# linux-perf: with vs without the skill

Measured 2026-10-18 with 0.24.0, agent claude-code 2.1.296, model `us.anthropic.claude-sonnet-5-5`, 3 attempts per task and arm. Repo commit `3e33aecabb95`, skill digest `f826553cb4f0`, graded with the verifiers at `0ddcd93e8758`. Medians with (min–max). Per-trial evidence: `trials/`.

| task | arm | reward | errored | cost $ | agent time s | input tok | output tok | Skill calls |
|---|---|---|---|---|---|---|---|---|
| lp-hotspot-report | no_skill | 0.33 (0/0/1) | 0 | 0.12 (0.11–0.14) | 64 (62–74) | 105k (101k–129k) | 7k (7k–9k) | 0, 0, 0 |
| lp-hotspot-report | with_skill | 1.00 (1/1/1) | 0 | 0.12 (0.11–0.15) | 48 (47–65) | 157k (157k–159k) | 6k (5k–8k) | 1, 1, 1 |

Verifier checks, pass rate per arm (no_skill / with_skill):

- **lp-hotspot-report**: annotated_hot_line 0.33 / 1.00; annotated_second_function 0.67 / 1.00; false_sharing 1.00 / 1.00; no_fix_claims 1.00 / 1.00; report_written 1.00 / 1.00; scalar_fp 1.00 / 1.00; serial_accumulator 1.00 / 1.00; sources_untouched 1.00 / 1.00; top_table 1.00 / 1.00; top_table_cutoff 1.00 / 1.00

Skill files the with_skill agent named in a tool call: `references`, `references/flow-e.md`.
