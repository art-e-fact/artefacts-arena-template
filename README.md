# artefacts-arena-template

> [!WARNING]
> Under heavy development, on an alpha release of Isaac Lab-Arena. Expect the layout, the commands
> and the pinned versions to change, and things to break.

A template for a new [Isaac Lab-Arena](https://github.com/isaac-sim/IsaacLab-Arena) project: Arena
and Isaac Lab installed by one command, [arena-composer](https://github.com/art-e-fact/arena-composer)
wired into your editor and your agent, specs to start from, and the Experiments and
[Artefacts](https://docs.artefacts.com/) jobs that evaluate a policy on them.

## Highlights

- **One command to a working Arena.** `source setup.sh` syncs Arena's uv venv — Isaac Lab, Isaac
  Sim, Arena and the GR00T policy client — installs arena-composer into it, links the skills it
  ships, accepts the Isaac Sim EULA and activates the venv in your shell.
- **arena-composer, wired in.** A visual editor, headless renderer and MCP server for Arena's YAML
  specs, running without a GPU. The configs that point Claude Code, VS Code and Cursor at the MCP
  server are committed, so an agent has the `arena` tools the moment it opens the project.
- **Specs to start from.** A pick-and-place, and a gallery of specs showing most relation kinds in
  use, in the two-file layout Arena reads: a task, and the scene it includes.
- **Experiments to run on them.** Configs for Arena's Experiment Runner: a zero-action smoke test, a
  look through the cameras, and GR00T N1.6 and openpi pi05 against their policy servers.
- **Experiments as Artefacts jobs.** `artefacts run <job>` evaluates an Experiment and uploads its
  report, the camera videos and a JUnit verdict per episode to the dashboard.
- **Agent-ready.** `AGENTS.md` maps the project, and Agent Skills hold the procedures: authoring a
  spec with the MCP tools, running an Experiment, and Arena's own setup and policy-server workflows.

## Start a project

Linux x86_64, with [uv](https://docs.astral.sh/uv/) and [gh](https://cli.github.com/) on PATH — gh
signed in, since the arena-composer wheel is a GitHub Release asset — and an NVIDIA RTX GPU for
whatever runs Isaac Sim. The arena-composer commands do without one.

1. Create a repository from this template on GitHub, and clone it with its submodules:

   ```bash
   git clone --recurse-submodules git@github.com:<you>/<project>.git
   ```

   Arena names its own submodules by SSH URL. Without an SSH key for GitHub, have git rewrite them:

   ```bash
   git -c url."https://github.com/".insteadOf=git@github.com: clone --recurse-submodules https://github.com/<you>/<project>.git
   ```

2. Set up, and look at the starter spec:

   ```bash
   source setup.sh
   arena-view environments/tasks/banana_in_bowl.yaml
   ```

   The first `source setup.sh` syncs Arena's venv, which downloads Isaac Sim and takes a while;
   later ones take a second. Source it in every new shell: it also exports the EULA acceptance that
   Isaac Sim asks for.

3. Open the project in Claude Code, VS Code or Cursor. Each finds the `arena` MCP server through its
   committed config, and the skills through `.claude/skills/` and `.agents/skills/`.

Then make it yours: `project:` in [artefacts.yaml](artefacts.yaml), and the specs.

## Layout

- `environments/` — the specs: `tasks/`, and the `scenes/` they include.
- `experiments/` — Experiment configs for Arena's Experiment Runner.
- `skills/` — this project's Agent Skills, linked from `.agents/skills/` and `.claude/skills/`.
- `bin/` — `arena-mcp`, the MCP launcher every client config names, and `artefacts-experiment`,
  which runs an Experiment as an Artefacts scenario.
- `artefacts.yaml` — the Artefacts jobs.
- `setup.sh` — the environment, and the arena-composer release it pins.
- `submodules/IsaacLab-Arena` — Arena and Isaac Lab, and the venv everything installs into.

## Author an environment

A spec is two YAML files: a task under `environments/tasks/`, and the scene it includes through
`external_yaml`, under `environments/scenes/`. A key lives in one file or the other, never both.
arena-composer edits, solves and draws them; its
[README](https://github.com/art-e-fact/arena-composer#readme) has the details.

- `arena-composer new environments/tasks/<name>.yaml` starts a spec: a task and its scene, holding
  a pick-and-place that validates, solves and builds.
- `arena-view <spec>` opens the visual editor: the layout Arena solves for the spec in 3D, beside a
  form that edits it. Every change is re-solved and redrawn, whoever made it.
- `arena-render <spec>...` draws the solved layout headless, a PNG per view.
- `arena-resolve-layout <spec>` prints where the solver put things.
- The `arena` MCP server gives an agent the same: search Arena's assets and NVIDIA's SimReady
  props, add and remove objects, pick the robot, check a spec, and describe and render the solved
  layout. The `author-arena-spec` skill is the procedure it follows, through to every sampled
  layout passing.

Ask your agent for "a kitchen where the robot puts the mug in the sink", with `arena-view` open on
the file it writes.

## Evaluate a policy

Arena's Experiment Runner pairs a spec with a policy for a number of episodes and writes a report,
with per-episode results, under `outputs/`:

```bash
source setup.sh
python submodules/IsaacLab-Arena/isaaclab_arena/evaluation/experiment_runner.py \
  --experiment_config experiments/banana_in_bowl.yaml --viz none
```

| Experiment | Policy | Needs |
| --- | --- | --- |
| `banana_in_bowl.yaml` | `zero_action`: holds still; proves the spec builds, steps and scores | nothing |
| `banana_in_bowl_viz.yaml` | `zero_action`, with the cameras spawned, to see where they look | `--viz kit` |
| `banana_in_bowl_gr00t.yaml` | GR00T N1.6, the DROID checkpoint | its server on port 5555 |
| `banana_in_bowl_openpi.yaml` | openpi pi05 | its server on port 8000 |

The comment at the top of each config says how to start its server, and Arena's
`serve-gr00t-policy` and `serve-openpi-policy` skills do it for an agent. The `run-arena-experiment`
skill runs the whole thing — the server check, the run, reading the result — and knows the ways a
run fails quietly, such as a camera policy scoring zero because the renderer ran out of GPU memory.

## Put it on Artefacts

[artefacts.yaml](artefacts.yaml) runs the Experiments as [Artefacts](https://docs.artefacts.com/)
jobs, one per policy. With the job's policy server running, and the
[Artefacts CLI](https://docs.artefacts.com/getting-started/) installed:

```bash
artefacts config add artefacts/artefacts-arena-template   # once: the project's API key
artefacts run gr00t
```

`bin/artefacts-experiment` runs the Experiment and leaves what the dashboard reads at the top of the
run's upload: the report, the camera videos, `metrics.json` and a `tests_junit.xml` with a case per
episode, failed where the episode did not succeed. A video with no scene in it fails too: a render
starved of GPU memory looks like a clean policy miss otherwise. The jobs run on your machine for
now; see *Planned*.

## Working with an agent

- [AGENTS.md](AGENTS.md) is the map: where things are, and the rules. Claude Code reads it through
  `.claude/CLAUDE.md`.
- `setup.sh` runs `arena-composer init`, which keeps the committed MCP configs and `bin/arena-mcp`,
  writes any that are missing, and links the skills arena-composer ships into `.agents/skills/`.
  The link follows the install and is not committed.
- The skills, linked from `.agents/skills/` and `.claude/skills/`:
  - `author-arena-spec`, from arena-composer: a spec from a description, with the MCP tools,
    through to every sampled layout passing.
  - `run-arena-experiment`: select or write an Experiment, run it, coordinate the policy server, and
    report what the result files say.
  - Arena's own, under `submodules/IsaacLab-Arena/skills/`: `setup-arena`, `serve-gr00t-policy`,
    `serve-openpi-policy` and `run-experiment`, written against the submodule as their root.

## Planned

- **LeRobot training and evaluation.** A LeRobot environment type that builds any spec here, so
  `lerobot-train` and `lerobot-eval` run on it with no wrapper. Prototyped on the `lerobot-envhub`
  branch.
- **Parametric asset generation skills**, for the objects no registry holds.
- **Artefacts jobs in the cloud.** They run locally until Artefacts has an Isaac Sim base image.
- **Spec checks in CI.** Validate and `arena-render` every spec on a pull request, on a runner with
  no GPU.
- **A dev container**, beside the host setup.

## Developing

See [AGENTS.md](AGENTS.md). `setup.sh` pins the arena-composer release it installs, and a release
is tested against one Arena commit: bump the pin and the submodule together. To work on
arena-composer itself, name a checkout in `.env`:

```bash
ARENA_COMPOSER_SRC=~/repos/arena-composer
```

Every `source setup.sh` then installs that checkout editable, rebuilding its Rust part when it
changed, and `source setup.sh --pinned` ignores it for one run.

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))
- MIT license ([LICENSE-MIT](LICENSE-MIT))

at your option.

Unless you explicitly state otherwise, any contribution intentionally submitted for
inclusion in this work by you, as defined in the Apache-2.0 license, shall be dual
licensed as above, without any additional terms or conditions.
