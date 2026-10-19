# linux-perf: with vs without the skill

Measured 2026-10-18 with 0.24.0, agent claude-code 2.1.296, model `us.anthropic.claude-haiku-5-5`, 5 attempts per task and arm. Repo commit `3e33aecabb95`, skill digest `f826553cb4f0`, graded with the verifiers at `0ddcd93e8758`. Medians with (min–max). Per-trial evidence: `trials/`.

| task | arm | reward | errored | cost $ | agent time s | input tok | output tok | Skill calls |
|---|---|---|---|---|---|---|---|---|
| lp-c2c-contention | no_skill | 0.00 (0/0/0) | 0 | 0.01 (0.01–0.01) | 81 (72–92) | 119k (116k–154k) | 16k (14k–19k) | 0, 0, 0 |
| lp-c2c-contention | with_skill | 0.67 (1/1/0) | 0 | 0.01 (0.01–0.01) | 53 (47–53) | 175k (165k–179k) | 10k (9k–10k) | 1, 1, 1 |
| lp-hotspot-report | no_skill | 0.20 (0/0/0/1/0) | 0 | 0.02 (0.01–0.02) | 105 (83–121) | 207k (148k–238k) | 21k (16k–25k) | 0, 0, 0, 0, 0 |
| lp-hotspot-report | with_skill | 1.00 (1/1/1/1/1) | 0 | 0.02 (0.01–0.02) | 90 (80–92) | 239k (140k–298k) | 18k (17k–20k) | 1, 1, 1, 1, 1 |
| lp-scaling-bottleneck | no_skill | 0.67 (1/1/0) | 0 | 0.01 (0.01–0.01) | 76 (65–76) | 142k (107k–184k) | 14k (12k–15k) | 0, 0, 0 |
| lp-scaling-bottleneck | with_skill | 0.67 (1/1/0) | 0 | 0.01 (0.01–0.01) | 58 (55–77) | 181k (178k–225k) | 11k (10k–15k) | 1, 1, 1 |

Verifier checks, pass rate per arm (no_skill / with_skill):

- **lp-c2c-contention**: l0_false 1.00 / 1.00; l0_fields 1.00 / 1.00; l0_fix 1.00 / 1.00; l1_fix 1.00 / 1.00; l1_true 1.00 / 1.00; l2_fix 0.33 / 1.00; l2_true 1.00 / 1.00; reported_lines 0.00 / 0.67; valid_json 1.00 / 1.00
- **lp-hotspot-report**: annotated_hot_line 0.80 / 1.00; annotated_second_function 0.40 / 1.00; false_sharing 1.00 / 1.00; no_fix_claims 1.00 / 1.00; report_written 1.00 / 1.00; scalar_fp 1.00 / 1.00; serial_accumulator 0.80 / 1.00; sources_untouched 1.00 / 1.00; top_table 0.80 / 1.00; top_table_cutoff 0.20 / 1.00
- **lp-scaling-bottleneck**: counter_category 1.00 / 1.00; jumpers_found 1.00 / 1.00; lock_category 1.00 / 1.00; next_is_c2c 1.00 / 1.00; no_other_functions 0.67 / 0.67; valid_json 1.00 / 1.00

Skill files the with_skill agent named in a tool call: `references`, `references/`, `references/building-blocks.md`, `references/flow-c.md`, `references/flow-d.md`, `references/flow-e.md`.
