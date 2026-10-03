# artefacts-arena-template

An Isaac Lab Arena project: environment specs under `environments/`, and the Experiments that run
them. The tooling that resolves and draws a spec — `arena-view`, `arena-mcp` — is the
[arena-composer](https://github.com/art-e-fact/arena-composer) package, which `setup.sh` installs.

 - Run shells with `source setup.sh`. It activates Arena's venv and accepts the Isaac Sim EULA.
 - /submodules/* are third-party. Don't edit them unless the user asks you to.  
 - Keep the implementation as concise and readable as possible. Add short comments where they help the
   understanding.  
 - Write comments and docs for someone who has only the code in front of them. A note must state a fact
   about the code or a rule to follow — not recount how we found it out, and not answer a question that
   was only ever asked in a chat. If a detail doesn't change what the next reader does, cut it.
 - These files obey that rule too. A note belongs in the deepest `AGENTS.md` whose directory holds the
   code it is about: this one is read on every request, the nested ones only when that code is opened.

```bash
source setup.sh
arena-view environments/tasks/banana_in_bowl.yaml   # resolve a layout and look at it
```

## Where things are

- `environments/` — the specs. A task includes its scene through `external_yaml`, and the two are a
  disjoint union: a key lives in one file or the other, never both.
- `setup.sh` — pins the arena-composer release it installs. The composer imports private Arena
  functions, so a release is tested against one Arena commit: bump the pin and the submodule
  together. A change to the composer itself belongs in its repo: `ARENA_COMPOSER_SRC=<checkout>` in
  `.env` makes `setup.sh` install that checkout editable instead, and `--pinned` ignores it.
- `bin/arena-mcp`, `.mcp.json`, `.vscode/mcp.json`, `.cursor/mcp.json` — how an agent's client starts
  the MCP server. `arena-composer init` writes them: change its templates in arena-composer, then
  delete the files and run it in a `source setup.sh` shell, rather than editing them here.
- `artefacts.yaml`, `bin/artefacts-experiment` — Experiments as Artefacts jobs: `artefacts run <job>`
  uploads each Experiment's report, camera videos and a JUnit verdict to the dashboard.
- `skills/` — recurring multi-step workflows as Agent Skills. When a task matches one, invoke it
  instead of re-deriving the procedure from this file.
- `submodules/IsaacLab-Arena` — Arena and Isaac Lab, and the venv `setup.sh` installs arena-composer
  into.

## Skills

Canonical sources live under `skills/user/` and `skills/developer/`, named for the primary audience;
the folder does not restrict who may use a skill. Each is a directory holding `SKILL.md` and an
`evaluations.md` of worked scenarios and known failure modes.

Clients find them through flat aliases: `.agents/skills/<name>` symlinks to the canonical directory,
and `.claude/skills` symlinks to `.agents/skills`. Both are committed. Adding, removing or renaming a
skill means updating the canonical source and its alias together, or a client silently stops seeing
it. This mirrors the layout in `submodules/IsaacLab-Arena`, whose skills are usable from here and
are written against that submodule as their repository root.

`author-arena-spec`, for writing and repairing specs with the arena MCP server, comes from
arena-composer instead. `arena-composer init`, which `setup.sh` runs, links it into `.agents/skills/`
from the installed package, so it is the installed release's own, or the editable checkout's. The
link points into the venv or that checkout, so it is not committed. Change the skill in
arena-composer.
