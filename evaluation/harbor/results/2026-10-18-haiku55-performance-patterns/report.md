# performance-patterns: with vs without the skill

Measured 2026-10-18 with 0.24.0, agent claude-code 2.1.296, model `us.anthropic.claude-haiku-5-5`, 5 attempts per task and arm. Repo commit `3e33aecabb95`, skill digest `a1016a874b6f`, graded with the verifiers at `0ddcd93e8758`. Medians with (min–max). Per-trial evidence: `trials/`.

| task | arm | reward | errored | cost $ | agent time s | input tok | output tok | Skill calls |
|---|---|---|---|---|---|---|---|---|
| pp-crc32c-throughput | no_skill | 0.00 (0/0/0/0/0) | 0 | 0.01 (0.01–0.01) | 57 (55–76) | 167k (137k–241k) | 11k (10k–13k) | 0, 0, 0, 0, 0 |
| pp-crc32c-throughput | with_skill | 1.00 (1/1/1/1/1) | 0 | 0.02 (0.01–0.02) | 79 (58–98) | 442k (390k–627k) | 13k (9k–16k) | 1, 1, 1, 1, 1 |
| pp-hamming-search | no_skill | 0.60 (0/0/1/1/1) | 0 | 0.01 (0.01–0.01) | 58 (44–62) | 163k (130k–255k) | 11k (7k–12k) | 0, 0, 0, 0, 0 |
| pp-hamming-search | with_skill | 1.00 (1/1/1/1/1) | 0 | 0.01 (0.01–0.02) | 76 (59–83) | 372k (262k–430k) | 16k (12k–17k) | 1, 1, 1, 1, 1 |
| pp-simd-sort | no_skill | 0.33 (1/0/0) | 0 | 0.02 (0.01–0.03) | 114 (60–208) | 369k (96k–945k) | 17k (7k–27k) | 0, 0, 0 |
| pp-simd-sort | with_skill | 0.67 (1/0/1) | 0 | 0.05 (0.03–0.20) | 1100 (737–1748) | 2282k (1275k–3176k) | 35k (25k–52k) | 1, 1, 1 |
| pp-source-review | no_skill | 0.67 (0/1/1) | 0 | 0.01 (0.01–0.01) | 81 (78–84) | 183k (138k–183k) | 15k (15k–16k) | 0, 0, 0 |
| pp-source-review | with_skill | 1.00 (1/1/1) | 0 | 0.01 (0.01–0.02) | 65 (56–79) | 211k (165k–316k) | 12k (11k–15k) | 1, 1, 1 |

Verifier checks, pass rate per arm (no_skill / with_skill):

- **pp-crc32c-throughput**: builds 1.00 / 1.00; correct 1.00 / 1.00; dispatch 1.00 / 1.00; fast 0.00 / 1.00
- **pp-hamming-search**: builds 1.00 / 1.00; correct 1.00 / 1.00; dispatch 1.00 / 1.00; fast 0.60 / 1.00
- **pp-simd-sort**: builds 1.00 / 1.00; correct 1.00 / 1.00; dispatch 0.33 / 0.67; fast 0.33 / 0.67; single_thread 1.00 / 1.00
- **pp-source-review**: decoy_false_positives 1.00 / 1.00; recall 0.67 / 1.00; valid_json 1.00 / 1.00

Skill files the with_skill agent named in a tool call: `library`, `library/`, `library/cpu-dispatch.md`, `library/crc32c_avx512_vpclmulqdq.c`, `library/crc32c_sse42.c`, `patterns/`, `patterns/fast-crc32c-impl.md`, `patterns/per-cpu-stats.md`, `patterns/simd-sort.md`, `references/known-algorithms-impl.md`, `triggers/from-source.md`.
