---
name: run-arena-experiment
description: Evaluates this project's environment specs with Isaac Lab-Arena's Experiment Runner - selects or writes an Experiment config under experiments/, runs experiment_runner.py against a spec under environments/, coordinates any policy server the Runs require, and reports per-Run status and success rate from outputs/. Use when asked to run, evaluate, score, benchmark or smoke-test an environment, a task spec or a policy. Do not use for interactive no-policy inspection (arena-view), for authoring or editing specs (the arena MCP server), for pytest, or for OSMO submission.
allowed-tools: Read Grep Glob Skill Bash(git rev-parse --show-toplevel) Bash(ls *) Bash(test -f *) Bash(test -d *) Bash(nvidia-smi *) Bash(source setup.sh && python submodules/IsaacLab-Arena/isaaclab_arena/evaluation/experiment_runner.py *) Bash(source setup.sh && python -c *) Bash(ffmpeg *)
---

# Run an Arena Experiment

Execute an Experiment Definition against a spec in this project and finish with evidence from the
canonical artifacts. An Experiment names one or more Runs; a Run pairs an environment with a policy
and a rollout limit. The Experiment Runner lives in the Arena submodule; the specs and the
Experiment configs live in this project.

Keep spec authoring, interactive inspection, regression testing, and managed submission outside
this skill.

## Read the checked-out project

Treat the checkout as the source of truth. If this skill disagrees with a config or the runner CLI,
follow the checkout and report the mismatch.

- `AGENTS.md` for the project layout.
- `experiments/` for existing Experiment configs. List them before writing a new one; an existing
  config that already names the wanted spec and policy is the template to copy.
- `environments/tasks/` and `environments/scenes/` for the specs a Run can target.
- `submodules/IsaacLab-Arena/isaaclab_arena/evaluation/experiment_runner_cli.py` for the flags this
  checkout actually accepts.

## Preflight the run

1. Confirm the repository root with `git rev-parse --show-toplevel`. Every command below runs from
   there, because config paths resolve against the working directory.
2. Resolve an explicit Experiment path. Never rely on the runner's default configuration.
3. Read the Run's spec and note its `embodiment`. A policy's action space must match it; the openpi
   simeval and GR00T DROID checkpoints are joint-position and pair with `droid_abs_joint_pos`.
4. Estimate the cost before starting it. Episode length is the task's `episode_length_s` x 15 Hz,
   Arena's default control rate, so `episode_length_s: 70.0` is 1050 steps. Wall time per episode
   depends on the policy and on whether cameras render; a remote VLA policy at 1050 steps takes a
   few minutes. Summarize unexpectedly large work before launching it.
5. Identify each Run's policy from its resolved `policy.type`, not from the Experiment filename.

## Write or adjust the Experiment config

```yaml
runs:
  <run_name>:
    environment:
      type: environments/tasks/<task>.yaml   # or a registered environment name
      enable_cameras: true                   # required for any camera-driven policy
    policy:
      type: zero_action
    environment_builder:
      num_envs: 1
      language_instruction: <the task's description>
    rollout_limit:
      num_episodes: 2
```

An `environment.type` ending in `.yaml` selects a spec path instead of a registered environment.

Declare every key the run needs. **Hydra only overrides keys a config already contains**, so
setting an undeclared key from the command line is silently dropped and the run proceeds without
it. `enable_cameras` is the usual casualty: a camera policy then receives no images and scores
zero with no error.

`zero_action` drives the arm to the zero joint-position target and holds it. It never solves a
task; it proves the environment builds, steps, renders and scores. Use it for a smoke run.

## Select execution options

- Default to `--viz none`. Use `--viz kit` only when a human wants to watch.
- Change a declared value with a trailing Hydra override instead of editing the YAML:
  `shared.<path>=<value>` for every Run, `runs.<name>.<path>=<value>` for one. The `experiment_cfg.`
  prefix belongs to OSMO submission, not here.
- `--list_variations` prints a Run's configurable variations and exits without rolling out or
  producing artifacts.
- `--record_camera_video` writes one mp4 per camera per episode. Use it when asked, and when a
  result needs the verification in *Verify the outcome*.
- `--serve_evaluation_report` binds an HTTP server and keeps the process running until interrupted.
- `--continue_on_error` attempts the remaining Runs after a failure and lets the process exit zero
  even though a Run failed. Preserve the default stop-on-first-error behavior otherwise.
- Let the runner create a timestamped directory under `outputs/` unless the user chooses one. An
  exact `--experiment_output_directory` must be missing or empty; never clear or reuse a nonempty
  one.

## Build the command

```bash
source setup.sh && python submodules/IsaacLab-Arena/isaaclab_arena/evaluation/experiment_runner.py \
  --experiment_config experiments/<name>.yaml \
  --viz none \
  <override>...
```

`setup.sh` must be sourced in the same command, not relied on from a previous shell: it exports the
EULA acceptance, `PYTHONPATH` and `ARENA_PROJECT_ROOT` that the runner needs.

## Execute and monitor

Run it and wait. Runs execute in YAML order inside one SimulationApp, each building a fresh
environment. Report progress during a long evaluation.

Do not pipe the run through `tail` or `head`: a crash reason appears in the middle of the output,
and a truncating filter hides it. On failure, preserve the logs and partial output rather than
deleting artifacts or silently rerunning with different settings.

## Verify the outcome

1. Locate the output directory the runner printed, under `outputs/<timestamp>/`.
2. Read each Run's `status` from `arena_experiment_result.json`. Report that, not the process exit
   code.
3. Read per-episode rows from `<run_name>/episode_results_rebuild0.jsonl`. Each row carries
   `success`, `episode_length` and a `progress` tree whose `events` name the predicates the episode
   reached; report where failed episodes stalled, not just the rate.
4. `index.html` is the HTML report.

Keep execution success separate from task success. A zero `success_rate` from `zero_action` is the
expected result, not a failure.

**A success rate is only meaningful if the cameras rendered the scene.** When a camera policy
scores zero, or whenever the policy server and the simulation share one GPU, confirm the
observations contain geometry before reporting the number. Re-run one episode with
`--record_camera_video` and judge the frames by content:

```bash
ffmpeg -v error -i <video>.mp4 -vf scale=64:64 -pix_fmt gray -f rawvideo - | od -An -tu1 -v | \
  awk 'BEGIN{m=256;M=-1}{for(i=1;i<=NF;i++){if($i<m)m=$i;if($i>M)M=$i}} END{print "range",M-m}'
```

A rendered scene gives a wide range — above 200 for these cameras. A render starved of GPU memory
silently drops all geometry and returns a uniform background, whose range is 0, while still
producing a full-length video and a clean zero success rate. Initialize `m` as shown: left unset it
reports the maximum, and a uniform light background then scores as high as a real scene. Frame
count and file size alone never prove content.

## Policies that need a server

`zero_action` and `replay` run in-process. An openpi or GR00T policy needs its server running
first, and the Run's `environment.enable_cameras` declared.

Those servers are Arena's own workflows. Use the `serve-openpi-policy` or `serve-gr00t-policy`
skill, whose canonical sources are under `submodules/IsaacLab-Arena/skills/user/`. They are written
against `submodules/IsaacLab-Arena` as their repository root. Leave a server running after the
Experiment unless asked to stop it.

Two things stay this project's responsibility:

- **Client imports.** A GR00T Run imports `gr00t.policy.server_client` lazily inside the policy
  builder, so a missing client passes every startup check and fails only once a rollout begins.
  `setup.sh` installs it through Arena's `gr00t-client` group, and re-syncs when it is missing.
  A `uv sync` or `uv run` inside `submodules/IsaacLab-Arena` removes it again; source `setup.sh`
  after one.

- **Policy config paths.** A policy's `policy_config_yaml_path`, and the joint-space paths inside
  that file, resolve against the working directory and are asserted to exist. Arena's own copies
  therefore only work when run from the Arena repository root. Keep a copy under `experiments/`
  with the paths rewritten relative to this project root, and point the Run at that copy.

Before launching, check free GPU memory with `nvidia-smi`. A server and a rendering simulation on
one card must both fit, and the simulation needs materially more headroom than its steady-state
allocation to stream geometry. When they do not fit, the failure is silent: see *Verify the
outcome*.

## Hand off other workflows

- Use `arena-view` or the Environment Runner for interactive inspection without a policy.
- Use the arena MCP server to author or edit a spec.
- Use Arena's `setup-arena` for installation or runtime repair, and `run-tests` for pytest.
- Use an OSMO submission workflow for cluster runs. An unqualified request to "run" an Experiment
  means local execution.

## References

- [Evaluations](evaluations.md)
- [Project layout](../../../AGENTS.md)
- [OpenPI server skill](../../../submodules/IsaacLab-Arena/skills/user/serve-openpi-policy/SKILL.md)
- [GR00T server skill](../../../submodules/IsaacLab-Arena/skills/user/serve-gr00t-policy/SKILL.md)
- [Arena run-experiment skill](../../../submodules/IsaacLab-Arena/skills/user/run-experiment/SKILL.md)
- [Experiment Runner CLI](../../../submodules/IsaacLab-Arena/isaaclab_arena/evaluation/experiment_runner_cli.py)
