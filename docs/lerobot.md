# Training and evaluating with LeRobot

`source setup.sh` installs [LeRobot](https://huggingface.co/docs/lerobot) into Arena's
venv, and `envhub/` adds a LeRobot environment type, `arena_yaml`, that builds any spec
under `environments/`. The stock `lerobot-train` and `lerobot-eval` CLIs then work here
with no wrapper script — `--env.spec` picks the environment.

```bash
source setup.sh
python -m envhub.zero_action_rollout \
  --env.type=arena_yaml \
  --env.spec=environments/tasks/banana_in_bowl.yaml \
  --eval.batch_size=1 \
  --env.visualizer=kit
```

That is the smoke test: it builds the spec, steps 100 zero actions and prints the
observation terms the robot publishes. No policy and no dataset involved. Drop
`--env.visualizer=kit` to run without a window.

## Evaluate a policy

```bash
lerobot-eval \
  --policy.path=<hub repo id or checkpoint dir> \
  --policy.device=cuda \
  --env.discover_packages_path=envhub \
  --env.type=arena_yaml \
  --env.spec=environments/tasks/banana_in_bowl.yaml \
  --env.state_keys=joint_pos,gripper_pos \
  --env.camera_keys=external_camera_rgb,wrist_camera_rgb \
  --eval.batch_size=1 \
  --eval.n_episodes=10 \
  --output_dir=outputs/eval/banana_in_bowl
```

`--env.discover_packages_path=envhub` is what registers `arena_yaml`, so every
`lerobot-eval` call needs it. Metrics land in `<output_dir>/eval_info.json` and rollout
videos, recorded from the first `--env.camera_keys` camera, in
`<output_dir>/videos/<env_name>_0/`, where `env_name` is the spec's own.

Useful flags:

| Flag | Effect |
| --- | --- |
| `--eval.batch_size=N` | N environments batched inside the one simulation. **Always set it.** Left at its default it is auto-tuned from the CPU core count, which for Isaac Lab means that many GPU environments, each rendering every camera — 11 of them exhaust a 16 GB card. Isaac Lab vectorizes on the GPU whatever `--eval.use_async_envs` says, so leave that one alone. |
| `--env.visualizer=kit` | Watch the rollout in a window. |
| `--env.episode_length=N` | Cap rollout steps. Default: the task's own `episode_length_s`. |
| `--env.seed=N` | Seeds the simulation. Object placement still varies per reset, which is what you want across episodes. |
| `--rename_map=...` | Bridge naming differences between the env and the policy (below). |
| `--env.embodiment=NAME` | Run the spec's scene under another registered embodiment, e.g. a different control variant of the same robot (`droid_abs_joint_pos`, `droid_rel_joint_pos`, `droid_differential_ik`). |
| `--env.arm_action_scale=X` | Replace the embodiment's `arm_action` scale, to match the units a policy emits (below). |

## Zero-shot with π0.5-DROID

Arena's DROID embodiment is the DROID rig — Panda, Robotiq 2F-85, cameras where DROID has
them — so a policy trained on DROID data runs in it without finetuning.
[`lerobot/pi05_droid`](https://huggingface.co/lerobot/pi05_droid) is LeRobot's port of
openpi's π0.5-DROID. Two things stand between the Hub checkpoint and a rollout:

- The port ships no normalization stats, and LeRobot passes a key with no stats through
  untouched. `envhub/add_openpi_stats.py` writes openpi's own stats into a local copy.
- Its actions are DROID joint velocities, applied as `velocity * 0.2` rad per 15 Hz step.
  `droid_rel_joint_pos` adds `scale * action` to the joint targets and this env steps at
  15 Hz, so `--env.arm_action_scale=0.2` reproduces that.

The policy tokenizes with `google/paligemma-3b-pt-224`, a gated repo: accept its license
on the Hub once, then `hf auth login`.

```bash
source setup.sh
python -m envhub.add_openpi_stats lerobot/pi05_droid \
  https://storage.googleapis.com/openpi-assets/checkpoints/pi05_droid/assets/droid/norm_stats.json \
  --out outputs/checkpoints/pi05_droid
lerobot-eval \
  --policy.path=outputs/checkpoints/pi05_droid \
  --policy.device=cuda \
  --policy.dtype=bfloat16 \
  --env.discover_packages_path=envhub \
  --env.type=arena_yaml \
  --env.spec=environments/tasks/banana_in_bowl.yaml \
  --env.embodiment=droid_rel_joint_pos \
  --env.arm_action_scale=0.2 \
  --rename_map='{"observation.images.external_camera_rgb": "observation.images.base_0_rgb", "observation.images.wrist_camera_rgb": "observation.images.left_wrist_0_rgb"}' \
  --eval.batch_size=1 \
  --eval.n_episodes=10 \
  --output_dir=outputs/eval/pi05_droid_banana_in_bowl
```

The default `state_keys`, `joint_pos,gripper_pos`, are DROID's state. The policy's third
camera slot, `right_wrist_0_rgb`, stays empty, as on the real rig.

Memory: even with `--policy.dtype=bfloat16` the policy takes 8.7 GiB of GPU memory (LeRobot
keeps the vision tower in float32 and instantiates PaliGemma's unused `lm_head`s), and Isaac
Sim about 5.3 GB for this scene, so the rollout needs ~14 GB free on the card. Where that is
not available, `--policy.device=cpu` keeps the policy off the GPU at 1–3 env steps per second
of wall time on an 8-core CPU (one inference per 15 steps). The video still plays at
simulation speed.

### What a checkpoint expects

A checkpoint carries its contract in two places. `config.json` names the feature keys and
the normalization kind per feature type; the `*_normalizer_processor.safetensors` files
hold the per-key stats. Only the stats bind: a state or action of another width than its
stats fails inside the normalizer, a key with no stats is passed through silently, and
the shapes in `config.json` are never checked (and are stale in several Hub checkpoints).

```bash
python -m envhub.checkpoint_contract lerobot/pi05_droid
```

prints both, plus every pre- and post-processing step with its settings. Compare the
stats widths with the `selected: state ... action ...` line the smoke test prints. Widths
and key names are all this catches. What each number *means* — frame, units, absolute or
relative — is in the training dataset's `meta/info.json` and in the env adapter it was
recorded with (`lerobot/envs/vlabench.py` for `smolvla_vlabench`, which is a Franka in
end-effector space and does not fit DROID's joint-space state at any width).

### Observation keys

`--env.state_keys` and `--env.camera_keys` select which of the robot's observation
terms become `observation.state` and `observation.images.*`. They must match what the
policy was trained on. The defaults are the DROID arm's; for another embodiment, run
the smoke test above and read the term names it prints.

A key that names no term aborts the build with the valid names listed. Everything the
keys imply — state width, action width, camera resolution — is measured off the built
environment, so `--env.state_dim`, `--env.action_dim`, `--env.camera_height` and
`--env.camera_width` are ignored.

The keys are Arena's term names. Where the training dataset used different ones, map
them over rather than renaming either side:

```bash
  --rename_map='{"observation.images.external_camera_rgb": "observation.images.exterior_image"}'
```

Cameras render at the resolution the embodiment declares (720×1280 for DROID). LeRobot's
env processor does not resize; π0/π0.5 and SmolVLA resize inside the policy, any other
policy needs its own resize step or a matching resolution.

## Train a policy

Training never touches the environment: `lerobot-train` reads a `LeRobotDataset` and
writes a checkpoint.

```bash
lerobot-train \
  --dataset.repo_id=<hub dataset id> \
  --policy.type=act \
  --policy.device=cuda \
  --output_dir=outputs/train/act_banana_in_bowl \
  --job_name=act-banana-in-bowl \
  --policy.repo_id=<hub model id>
```

Recording a dataset from these environments is not wired up yet, so the dataset has to
come from elsewhere — a Hub dataset, or one recorded with your own teleop or scripted
policy. [LeRobot's training guide](https://huggingface.co/docs/lerobot/main/en/il_robots#train-a-policy)
covers the policy types and their flags.

A run saves a checkpoint every `--save_freq` steps, and the last one is rarely the best.
Evaluate a few and pick by success rate:

```bash
hf download <hub model id> --include "checkpoints/010000/pretrained_model/*" --local-dir ckpt
# then --policy.path=ckpt/checkpoints/010000/pretrained_model
```
