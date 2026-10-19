#!/usr/bin/env bash
# Runs one skill's Harbor tasks in both arms: no_skill (task instruction only) and
# with_skill (skill installed + instructions/use-<skill>.md appended).
#
#   evaluation/harbor/run_arms.sh <skill> <model> [attempts=3] [job-prefix=<date>]
#
# TASKS="a b" limits the run to those tasks of the skill (default: all of them).
#
# Jobs land in evaluation/harbor/jobs/<prefix>-<skill>-{no_skill,with_skill}/ (not
# committed); report.py turns them into a result. Needs harbor, docker and the model
# provider's credentials in the environment (for Bedrock: CLAUDE_CODE_USE_BEDROCK=1,
# AWS_REGION and AWS_BEARER_TOKEN_BEDROCK). Behind a proxy, point DOCKER_CONFIG at a
# docker config with "proxies" so image builds and the agent can reach the network.
set -euo pipefail

skill=${1:?skill name}
model=${2:?model id}
attempts=${3:-3}
prefix=${4:-$(date +%Y-%m-%d)}
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)

# A task belongs to a skill by its metadata.skill, not by its directory name.
tasks=()
for toml in "$here"/tasks/*/task.toml; do
  name=$(basename "$(dirname "$toml")")
  if [ -n "${TASKS:-}" ] && [[ " $TASKS " != *" $name "* ]]; then continue; fi
  grep -q "^skill = \"$skill\"$" "$toml" && tasks+=(-i "$name")
done
[ ${#tasks[@]} -gt 0 ] || { echo "no tasks for skill $skill" >&2; exit 1; }

export HARBOR_TELEMETRY=off
# Same agent, model, version, settings and attempts in both arms; only the skill and
# the treatment instruction differ. Bundled Claude Code skills are off so the only
# skill in the with_skill arm is the one under test.
common=(-p "$here/tasks" "${tasks[@]}" -k "$attempts" -n 2
  -a claude-code -m "$model" --ak version=2.1.296 --ak config="$here/claude-settings.json"
  --ak disable_web_search=true --ae CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1
  --ae CLAUDE_CODE_DISABLE_CLAUDE_API_SKILL=1 -o "$here/jobs" --yes)

mkdir -p "$here/jobs"
harbor run "${common[@]}" --job-name "$prefix-$skill-no_skill" \
  > "$here/jobs/$prefix-$skill-no_skill.log" 2>&1 &
harbor run "${common[@]}" --job-name "$prefix-$skill-with_skill" \
  --skill "$root/skills/$skill" --extra-instruction-path "$here/instructions/use-$skill.md" \
  > "$here/jobs/$prefix-$skill-with_skill.log" 2>&1 &
wait
echo "jobs: $here/jobs/$prefix-$skill-{no_skill,with_skill}"
