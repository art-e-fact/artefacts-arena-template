# envhub

Registers this project's environment specs as a LeRobot environment type
(`--env.type=arena_yaml`), so the stock `lerobot-eval` can roll a policy out in any spec
under `environments/`. See [docs/lerobot.md](../docs/lerobot.md) for the commands.

| File | Purpose |
| --- | --- |
| `config.py` | The `arena_yaml` env config: a `lerobot.envs.IsaaclabArenaEnv` subclass |
| `env.py` | `make_env()` — launches Isaac Sim, turns `--env.spec` into a batched env |
| `isaaclab_env_wrapper.py` | Adapts that env to the vector-env API LeRobot expects |
| `zero_action_rollout.py` | Smoke test: builds a spec and steps zero actions, no policy |
| `tests/` | The checks that run without Isaac Sim (`pytest envhub`) — outside the package, so plugin discovery does not import them |

Rules this code has to keep:

- **No `isaaclab` import at module level, anywhere in this package.** LeRobot's plugin
  discovery imports the package *and every submodule* while parsing CLI arguments, long
  before `make_env` launches Isaac Sim. Import inside the function instead.
- `envhub` is a plain package importable from the repo root, which `setup.sh` puts on
  `PYTHONPATH` — not an installed distribution. Installing it under this name would not
  work anyway: the repo root shadows it on `sys.path`.
- LeRobot is installed by `setup.sh`, with overrides that hold numpy and packaging at
  the versions Isaac Sim needs. Installing it any other way downgrades both.
- `_apply_observation_layout` measures the state, action and camera dimensions off the
  built environment and writes them back onto the config, because LeRobot's processor
  silently drops a `state_key` it cannot find. It runs before the policy is made, so the
  policy features follow.
- `IsaacLabEnvWrapper.close()` closes the env but leaves Kit to atexit: `lerobot-eval`
  closes envs *before* writing `eval_info.json`, and Kit's `app.close()` can hard-exit
  the process.
