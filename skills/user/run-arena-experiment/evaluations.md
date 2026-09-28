# Run Arena Experiment Evaluations

## Scenario 1: Zero-Action Smoke Evaluation

Query: "Smoke-test `environments/tasks/banana_in_bowl.yaml` and tell me where the report is."

Expected behavior:

- Lists `experiments/` and reuses a config that already names that spec, or writes one with a
  `zero_action` policy and a small `num_episodes`.
- Runs the Experiment Runner from the repository root with `source setup.sh` in the same command
  and an explicit `--experiment_config`.
- Reads every Run `status` from `arena_experiment_result.json` and reports it with `index.html`.
- States that a zero `success_rate` from `zero_action` proves the pipeline works rather than
  reporting a broken environment.

Known failure modes:

- Reports the process exit code instead of the Run status.
- Treats the zero success rate as a failure of the spec.
- Runs the runner without sourcing `setup.sh`, losing Arena's venv and the EULA export.

## Scenario 2: Override Without Editing The Config

Query: "Run the same experiment but with four episodes, and don't change the YAML."

Expected behavior:

- Appends the trailing override `shared.rollout_limit.num_episodes=4`, or
  `runs.<name>.rollout_limit.num_episodes=4` for a single Run.
- Leaves the Experiment config unchanged and reports the effective override.
- Confirms `num_episodes` is already declared in the config before relying on the override.

Known failure modes:

- Uses the OSMO-only `experiment_cfg.` prefix.
- Edits the source YAML despite the explicit request.
- Overrides a key the config does not declare and assumes it took effect.

## Scenario 3: A Camera Policy That Needs A Key The Config Lacks

Query: "Run this spec with the openpi policy. The experiment config doesn't have `enable_cameras`."

Expected behavior:

- Declares `enable_cameras: true` inside the config rather than passing it as a Hydra override,
  because Hydra only overrides keys a config already contains.
- Explains that the override would otherwise be dropped silently and the policy would receive no
  images.
- Hands the server off to Arena's `serve-openpi-policy` skill instead of starting one ad hoc.

Known failure modes:

- Passes `runs.<name>.environment.enable_cameras=true` on the command line and reports the
  resulting zero as a policy result.
- Starts a policy server directly instead of using the Arena skill.
- Pairs a joint-position checkpoint with an embodiment that does not match it.

## Scenario 4: A Zero Score From A Camera Policy

Query: "The policy scored 0.0 across every episode. Is the policy bad at this task?"

Expected behavior:

- Declines to answer from the success rate alone, and checks whether the cameras rendered geometry.
- Re-runs one episode with `--record_camera_video` and judges frames by within-frame pixel range
  and distinctness, not by frame count or file size.
- Checks whether a policy server and the simulation shared one GPU, and reports that a starved
  render drops all geometry without raising an error.
- Reports the success rate as unmeasured, rather than as a policy result, when the frames are blank.

Known failure modes:

- Concludes the policy failed the task when it was fed a uniform background.
- Accepts a full-length video or a plausible frame count as proof that the scene rendered.
- Changes more than one variable when re-testing, then credits the wrong one.

## Scenario 5: Reporting A Mixed Result

Query: "How did that three-episode evaluation go?"

Expected behavior:

- Reports the success rate together with per-episode outcomes from
  `<run_name>/episode_results_rebuild0.jsonl`.
- Reads each episode's `progress.events` and names the last predicate reached, so a failure that
  grasped and dropped is distinguished from one that never approached.
- Notes `episode_length` against the step limit to show which episodes ran out of time.

Known failure modes:

- Reports only the aggregate rate and discards the staged predicate information.
- Treats a small sample as a precise score without saying how few episodes ran.

## Scenario 6: Out Of Scope

Query: "Add a second bowl to this scene and evaluate it."

Expected behavior:

- Uses the arena MCP server to edit the spec, then this skill to evaluate the result.
- Does not hand-edit spec YAML when an authoring tool covers the change.
- Keeps interactive inspection with `arena-view` rather than launching an Experiment to look at a
  layout.

Known failure modes:

- Runs an Experiment purely to visualize a scene.
- Edits `environments/` files directly and skips the placement validation the authoring tools run.
