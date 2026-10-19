"""Turns a no_skill and a with_skill Harbor job into a committed result.

  python3 evaluation/harbor/report.py JOBS/<prefix>-<skill>-no_skill JOBS/<prefix>-<skill>-with_skill \
      --out evaluation/harbor/results/<prefix>-<skill>

Writes into --out:
  summary.json   what was measured, under what (skill digest, the repo commit the trials
                 ran at and whether the measured files differed from it, the commit whose
                 verifiers graded them, harbor, agent, model, attempts), and per task and
                 arm: reward, every verifier check's pass rate, cost, tokens, agent time,
                 skill use; plus the with-minus-no reward delta per task
  report.md      the same as tables, for a reader
  NOTES.md       not written here: the reader's interpretation, kept across re-runs
  trials/<arm>/<trial>/  Harbor's own result.json, the verifier's reward.json and
                 test-stdout.txt (host paths shortened); for a re-graded trial, Harbor's
                 originals too, as *.harbor.*

and skills/<skill>/evals/benchmarks/<date>-<model>/benchmark.json: the same runs in
skill-creator's benchmark.json schema (references/schemas.md in anthropics/skills), the
results format skill_search's /guide asks for, inside the skill folder where catalogs
look. One file per model. pass_rate is the share of a run's verifier checks that passed.

--measured-at <commit>: the trials ran at that commit (re-graded later, or reported from
another checkout). The digest is then taken over the skill as committed there.

Per-trial files are the evidence; summary.json is derived from them and can be rebuilt.
A trial with an exception or no reward counts as errored, never as a pass or a 0.
Standard library only.
"""

import argparse
import hashlib
import json
import re
import shutil
import statistics
import subprocess  # nosec B404  # git rev-parse
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ARMS = ("no_skill", "with_skill")


# Evidence about the skill, not instructions to the agent (intel/skills'
# tools/behavior_digest.py, EXCLUDED_DIRS).
DIGEST_EXCLUDED = {"evals", "perf"}


def git(*args, binary=False):
    out = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,  # nosec B603 B607
                         check=True).stdout
    return out if binary else out.decode().strip()


def skill_files(skill, commit=None):
    """{path in the skill folder: bytes}: the files git tracks (or would), at `commit` or
    in the working tree. Untracked caches such as __pycache__ are not the skill."""
    prefix = f"skills/{skill}/"
    if commit:
        names = git("ls-tree", "-r", "--name-only", commit, "--", prefix).splitlines()
        return {n[len(prefix):]: git("show", f"{commit}:{n}", binary=True) for n in names}
    names = git("ls-files", "--cached", "--others", "--exclude-standard", "--", prefix).splitlines()
    return {n[len(prefix):]: (ROOT / n).read_bytes() for n in names if (ROOT / n).is_file()}


def behavior_digest(files):
    """sha256 binding a result to the skill bytes it measured, computed exactly as
    intel/skills' tools/behavior_digest.py does, so the same skill gets the same digest
    there, here and on skill_search: every file outside evals/ and perf/, in path order
    (by component, as sorting pathlib paths does), each as path NUL length NUL bytes."""
    digest = hashlib.sha256()
    for rel in sorted(files, key=lambda r: r.split("/")):
        if rel.split("/")[0] in DIGEST_EXCLUDED:
            continue
        content = files[rel]
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(content)).encode("ascii"))
        digest.update(b"\0")
        digest.update(content)
    return digest.hexdigest()


def seconds(phase):
    if not phase or not phase.get("started_at") or not phase.get("finished_at"):
        return None
    start, end = (datetime.fromisoformat(phase[k].replace("Z", "+00:00"))
                  for k in ("started_at", "finished_at"))
    return (end - start).total_seconds()


def skill_use(trial, skill):
    """Skill tool calls and reads of the skill's files, from the agent's stream-json log."""
    log = trial / "agent" / "claude-code.txt"
    calls, reads = 0, set()
    if not log.exists():
        return None, []
    for line in log.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message") if isinstance(event, dict) else None
        for block in (message.get("content") or []) if isinstance(message, dict) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            args = block.get("input") or {}
            if block.get("name") == "Skill":
                calls += 1
            text = json.dumps(args)
            for m in re.finditer(r"skills/" + re.escape(skill) + r"/([\w./-]+)", text):
                reads.add(m.group(1))
    return calls, sorted(reads)


def trial_row(trial, skill):
    r = json.loads((trial / "result.json").read_text())
    agent = r.get("agent_result") or {}
    rewards = (r.get("verifier_result") or {}).get("rewards")
    exception = (r.get("exception_info") or {}).get("exception_type")
    calls, reads = skill_use(trial, skill)
    return {
        "trial": r["trial_name"], "task": r["task_name"],
        "errored": bool(exception) or not rewards, "exception": exception,
        "rewards": rewards or {},
        "cost_usd": agent.get("cost_usd"),
        "input_tokens": agent.get("n_input_tokens"), "cache_tokens": agent.get("n_cache_tokens"),
        "output_tokens": agent.get("n_output_tokens"),
        "agent_s": seconds(r.get("agent_execution")),
        "skill_calls": calls, "skill_files_read": reads,
        "model": ((r.get("agent_info") or {}).get("model_info") or {}).get("name"),
        "agent": (r.get("agent_info") or {}).get("name"),
        "agent_version": (r.get("agent_info") or {}).get("version"),
    }


def spread(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {"median": statistics.median(values), "min": min(values), "max": max(values)}


def summarize(rows):
    scored = [r for r in rows if not r["errored"]]
    checks = sorted({k for r in scored for k in r["rewards"] if k != "reward"})
    return {
        "trials": len(rows), "errored": len(rows) - len(scored),
        "reward_mean": (statistics.mean(r["rewards"]["reward"] for r in scored)
                        if scored else None),
        "rewards": [r["rewards"].get("reward") for r in scored],
        "checks": {c: statistics.mean(r["rewards"].get(c, 0.0) for r in scored) for c in checks},
        **{k: spread([r[k] for r in scored]) for k in
           ("cost_usd", "input_tokens", "cache_tokens", "output_tokens", "agent_s")},
        "skill_calls": [r["skill_calls"] for r in rows],
        "skill_files_read": sorted({f for r in rows for f in r["skill_files_read"]}),
    }


def shorten(text):
    """Host paths to <repo>/...: Harbor records the path it was given, which need not be
    the resolved one (a symlinked home), so match on what follows the checkout root."""
    text = re.sub(r"/[^\"\s:]*?/(?=(evaluation/harbor|skills)/)", "<repo>/", text)
    return text.replace(str(Path.home()), "~")


def model_name(model):
    """The vendor's own model id: Bedrock's region and vendor prefix and version suffix
    off (us.anthropic.claude-haiku-5-5 -> claude-haiku-5-5), so a catalog can date it."""
    name = re.sub(r"^(?:[a-z]{2,6}\.)?anthropic\.", "", model or "")
    return re.sub(r"-v\d+:\d+$", "", name) or None


def described(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {"mean": round(statistics.mean(values), 4),
            "stddev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
            "min": min(values), "max": max(values)}


def benchmark(summary, rows, tasks, results_dir):
    """The runs in skill-creator's benchmark.json schema. Errored trials are left out and
    counted in the notes: they have no checks to report."""
    configuration = {"no_skill": "without_skill", "with_skill": "with_skill"}
    runs, errored = [], 0
    for arm in ARMS:
        for n, task in enumerate(tasks, 1):
            mine = [r for r in rows[arm] if r["task"] == task]
            errored += sum(r["errored"] for r in mine)
            for k, r in enumerate([r for r in mine if not r["errored"]], 1):
                checks = {c: v for c, v in r["rewards"].items() if c != "reward"}
                passed = sum(1 for v in checks.values() if v == 1.0)
                tokens = (r["input_tokens"] or 0) + (r["output_tokens"] or 0) or None
                runs.append({
                    "eval_id": n, "eval_name": task, "configuration": configuration[arm],
                    "run_number": k, "trial": r["trial"],
                    "result": {
                        "pass_rate": round(passed / len(checks), 4) if checks else None,
                        "passed": passed, "failed": len(checks) - passed, "total": len(checks),
                        "time_seconds": r["agent_s"], "tokens": tokens,
                        "tool_calls": None, "errors": 0, "cost_usd": r["cost_usd"],
                    },
                    "expectations": [{"text": c, "passed": v == 1.0} for c, v in sorted(checks.items())],
                })
    run_summary = {}
    for arm in ARMS:
        mine = [r["result"] for r in runs if r["configuration"] == configuration[arm]]
        run_summary[configuration[arm]] = {k: described([m[k] for m in mine])
                                           for k in ("pass_rate", "time_seconds", "tokens")}
    with_, without = run_summary["with_skill"], run_summary["without_skill"]
    run_summary["delta"] = {k: f"{with_[k]['mean'] - without[k]['mean']:+.2f}"
                            for k in ("pass_rate", "time_seconds", "tokens")
                            if with_.get(k) and without.get(k)}
    notes = [f"Harbor tasks in evaluation/harbor/tasks/, graded by each task's tests/verify.py; "
             f"full trials and tables in {results_dir}/.",
             "pass_rate is the share of a run's verifier checks that passed; the task's reward "
             "is 1 only when all of them pass."]
    notes += [f"{t}: reward {summary['tasks'][t]['no_skill']['reward_mean']} without the skill, "
              f"{summary['tasks'][t]['with_skill']['reward_mean']} with it" for t in tasks]
    if errored:
        notes.append(f"{errored} errored trial(s) left out of runs.")
    return {
        "metadata": {
            "skill_name": summary["skill"],
            "skill_path": f"skills/{summary['skill']}",
            "executor_model": model_name(summary["model"]),
            "executor_model_id": summary["model"],
            "timestamp": summary["started_at"],
            "evals_run": tasks,
            "runs_per_configuration": summary["attempts_per_task"],
            "skill_behavior_sha256": summary["skill_behavior_sha256"],
            "harness": f"harbor {summary['harbor']}".strip(),
            "agent": summary["agent"], "agent_version": summary["agent_version"],
            "repo_commit": summary["repo_commit"],
            "results": results_dir,
        },
        "runs": runs,
        "run_summary": run_summary,
        "notes": notes,
    }


def fmt(s, key, unit=""):
    v = s.get(key)
    if not v:
        return "–"
    lo, md, hi = v["min"], v["median"], v["max"]
    f = (lambda x: f"{x:.2f}") if key == "cost_usd" else \
        (lambda x: f"{x / 1000:.0f}k") if "tokens" in key else (lambda x: f"{x:.0f}")
    return f"{f(md)}{unit} ({f(lo)}–{f(hi)})"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("no_skill", type=Path)
    ap.add_argument("with_skill", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--measured-at", metavar="COMMIT",
                    help="the commit the trials ran at, when it is not HEAD")
    ap.add_argument("--no-benchmark", action="store_true",
                    help="do not write skills/<skill>/evals/benchmarks/.../benchmark.json")
    a = ap.parse_args()
    jobs = {"no_skill": a.no_skill, "with_skill": a.with_skill}
    # <prefix>-<skill>-with_skill, where the prefix may hold letters and hyphens too
    # (run_arms.sh takes any job prefix): the skill is the folder name it ends with.
    names = [d.name for d in (ROOT / "skills").iterdir() if d.is_dir()]
    found = [n for n in names if a.with_skill.name.endswith(f"-{n}-with_skill")]
    if not found:
        sys.exit(f"cannot tell the skill from job name {a.with_skill.name!r}")
    skill = max(found, key=len)

    rows = {arm: [trial_row(t, skill) for t in sorted(job.iterdir())
                  if (t / "result.json").exists() and t.is_dir()]
            for arm, job in jobs.items()}
    tasks = sorted({r["task"] for arm in ARMS for r in rows[arm]})
    per_task = {t: {arm: summarize([r for r in rows[arm] if r["task"] == t]) for arm in ARMS}
                for t in tasks}
    for t in tasks:
        m = [per_task[t][arm]["reward_mean"] for arm in ARMS]
        per_task[t]["delta_reward"] = None if None in m else round(m[1] - m[0], 4)

    first = next((r for arm in ARMS for r in rows[arm]), {})
    harbor = subprocess.run(["harbor", "--version"], capture_output=True, text=True,  # nosec
                            check=False).stdout.strip()
    head = git("rev-parse", "HEAD")
    commit = git("rev-parse", a.measured_at) if a.measured_at else head
    # Measured files that differ from that commit make the commit a poor pointer. Only
    # knowable for a run reported from the checkout it ran in.
    measured = ["skills", "evaluation/harbor/tasks", "evaluation/harbor/instructions"]
    dirty = None if a.measured_at else git("status", "--porcelain", "--", *measured) != ""
    graders_dirty = git("status", "--porcelain", "--", "evaluation/harbor/tasks") != ""
    job_result = json.loads((a.with_skill / "result.json").read_text())
    summary = {
        "schema_version": "1.1",
        "skill": skill,
        "skill_behavior_sha256": behavior_digest(skill_files(skill, a.measured_at and commit)),
        "repo_commit": commit,
        "repo_dirty": dirty,
        # The verifiers that produced the rewards: HEAD, which is the run's own commit
        # unless the trials were re-graded since.
        "graded_at": head,
        "graded_dirty": graders_dirty,
        "measured_on": job_result.get("started_at", "")[:10],
        "started_at": job_result.get("started_at"),
        "harbor": harbor,
        "agent": first.get("agent"), "agent_version": first.get("agent_version"),
        "model": first.get("model"),
        "attempts_per_task": max((per_task[t][arm]["trials"] for t in tasks for arm in ARMS),
                                 default=0),
        "arms": {"no_skill": "task instruction only",
                 "with_skill": f"--skill skills/{skill} + instructions/use-{skill}.md"},
        "tasks": per_task,
    }

    # Only what this script writes is replaced; a hand-written NOTES.md stays.
    out = a.out
    shutil.rmtree(out / "trials", ignore_errors=True)
    for arm, job in jobs.items():
        for t in sorted(job.iterdir()):
            if not (t / "result.json").exists():
                continue
            dest = out / "trials" / arm / t.name
            dest.mkdir(parents=True)
            (dest / "result.json").write_text(shorten((t / "result.json").read_text()))
            if (t / "result.harbor.json").exists():
                (dest / "result.harbor.json").write_text(
                    shorten((t / "result.harbor.json").read_text()))
            for name in ("reward.json", "test-stdout.txt", "reward.harbor.json",
                         "test-stdout.harbor.txt"):
                if (t / "verifier" / name).exists():
                    (dest / name).write_text(shorten((t / "verifier" / name).read_text()))
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    lines = [f"# {skill}: with vs without the skill", "",
             f"Measured {summary['measured_on']} with {summary['harbor']}, agent "
             f"{summary['agent']} {summary['agent_version']}, model `{summary['model']}`, "
             f"{summary['attempts_per_task']} attempts per task and arm. Repo commit "
             f"`{commit[:12]}`, skill digest `{summary['skill_behavior_sha256'][:12]}`"
             + (f", graded with the verifiers at `{head[:12]}`" if head != commit else "")
             + ". Medians with (min–max). Per-trial evidence: `trials/`.", "",
             "| task | arm | reward | errored | cost $ | agent time s | input tok | "
             "output tok | Skill calls |", "|---|---|---|---|---|---|---|---|---|"]
    for t in tasks:
        for arm in ARMS:
            s = per_task[t][arm]
            reward = "–" if s["reward_mean"] is None else \
                f"{s['reward_mean']:.2f} ({'/'.join(f'{x:.0f}' for x in s['rewards'])})"
            lines.append(f"| {t} | {arm} | {reward} | {s['errored']} | {fmt(s, 'cost_usd')} | "
                         f"{fmt(s, 'agent_s')} | {fmt(s, 'input_tokens')} | "
                         f"{fmt(s, 'output_tokens')} | "
                         f"{', '.join(str(c) for c in s['skill_calls'])} |")
    lines += ["", "Verifier checks, pass rate per arm (no_skill / with_skill):", ""]
    for t in tasks:
        names = sorted(set(per_task[t]["no_skill"]["checks"]) | set(per_task[t]["with_skill"]
                                                                     ["checks"]))
        cells = [f"{c} {per_task[t]['no_skill']['checks'].get(c, 0):.2f} / "
                 f"{per_task[t]['with_skill']['checks'].get(c, 0):.2f}" for c in names]
        lines.append(f"- **{t}**: " + "; ".join(cells))
    read = sorted({f for t in tasks for f in per_task[t]["with_skill"]["skill_files_read"]})
    lines += ["", f"Skill files the with_skill agent named in a tool call: "
              f"{', '.join(f'`{f}`' for f in read) or 'none'}.", ""]
    (out / "report.md").write_text("\n".join(lines))
    print("\n".join(lines))
    if not a.no_benchmark:
        try:
            results_dir = out.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            results_dir = out.as_posix()
        stamp = re.sub(r"[^\w.-]", "-", f"{summary['measured_on']}-{model_name(summary['model'])}")
        path = ROOT / "skills" / skill / "evals" / "benchmarks" / stamp / "benchmark.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(benchmark(summary, rows, tasks, results_dir), indent=2) + "\n")
        print(f"\nbenchmark -> {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
