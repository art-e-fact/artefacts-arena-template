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
videos in `<output_dir>/videos/<env_name>_0/`, where `env_name` is the spec's own.

Useful flags:

| Flag | Effect |
| --- | --- |
| `--eval.batch_size=N` | N environments batched inside the one simulation. **Always set it.** Left at its default it is auto-tuned from the CPU core count, which for Isaac Lab means that many GPU environments, each rendering every camera — 11 of them exhaust a 16 GB card. Isaac Lab vectorizes on the GPU whatever `--eval.use_async_envs` says, so leave that one alone. |
| `--env.visualizer=kit` | Watch the rollout in a window. |
| `--env.episode_length=N` | Cap rollout steps. Default: the task's own `episode_length_s`. |
| `--env.seed=N` | Seeds the simulation. Object placement still varies per reset, which is what you want across episodes. |
| `--rename_map=...` | Bridge naming differences between the env and the policy (below). |

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

Cameras render at the resolution the embodiment declares (720×1280 for DROID), which is
larger than most policies expect. LeRobot's eval pipeline does not resize, so a policy
trained on smaller frames needs its own resize step.

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
