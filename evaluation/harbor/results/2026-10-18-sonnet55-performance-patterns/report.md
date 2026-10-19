# performance-patterns: with vs without the skill

Measured 2026-10-18 with 0.24.0, agent claude-code 2.1.296, model `us.anthropic.claude-sonnet-5-5`, 3 attempts per task and arm. Repo commit `3e33aecabb95`, skill digest `a1016a874b6f`, graded with the verifiers at `0ddcd93e8758`. Medians with (min–max). Per-trial evidence: `trials/`.

| task | arm | reward | errored | cost $ | agent time s | input tok | output tok | Skill calls |
|---|---|---|---|---|---|---|---|---|
| pp-crc32c-throughput | no_skill | 0.00 (0/0/0) | 0 | 0.06 (0.06–0.11) | 38 (38–39) | 91k (90k–91k) | 4k (4k–4k) | 0, 0, 0 |
| pp-crc32c-throughput | with_skill | 1.00 (1/1/1) | 0 | 0.08 (0.06–0.09) | 34 (25–36) | 173k (124k–182k) | 3k (3k–3k) | 1, 1, 1 |
| pp-hamming-search | no_skill | 1.00 (1/1/1) | 0 | 0.05 (0.05–0.07) | 29 (27–43) | 89k (87k–114k) | 4k (3k–4k) | 0, 0, 0 |
| pp-hamming-search | with_skill | 1.00 (1/1/1) | 0 | 0.09 (0.07–0.09) | 37 (30–38) | 137k (96k–164k) | 4k (4k–5k) | 1, 1, 1 |

Verifier checks, pass rate per arm (no_skill / with_skill):

- **pp-crc32c-throughput**: builds 1.00 / 1.00; correct 1.00 / 1.00; dispatch 1.00 / 1.00; fast 0.00 / 1.00
- **pp-hamming-search**: builds 1.00 / 1.00; correct 1.00 / 1.00; dispatch 1.00 / 1.00; fast 1.00 / 1.00

Skill files the with_skill agent named in a tool call: `library`.
