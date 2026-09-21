# artefacts-arena-template

An Isaac Lab Arena project: environment specs under `environments/`, and the tooling that
resolves and draws them under `arena_composer/`.

 - Run shells with `source setup.sh`. This sets up EULA, PYTHONPATH and ARENA_PROJECT_ROOT exports.
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
- `arena_composer/` — everything that resolves a spec and draws it: Arena and the placement solver,
  the Bevy viewer, the headless renderer, the MCP server. Read
  [arena_composer/AGENTS.md](arena_composer/AGENTS.md) before changing any of it.
- `envhub/` — the LeRobot side: registers the specs as a LeRobot environment type so
  `lerobot-eval` can roll a policy out in them. Read [envhub/AGENTS.md](envhub/AGENTS.md)
  before changing it; [docs/lerobot.md](docs/lerobot.md) has the commands.
- `bin/arena-mcp`, `.mcp.json`, `.vscode/`, `.cursor/` — how an agent's client starts the MCP server.
- `skills/` — recurring multi-step workflows as Agent Skills. When a task matches one, invoke it
  instead of re-deriving the procedure from this file.
- `submodules/IsaacLab-Arena` — Arena and Isaac Lab, and the venv `setup.sh` installs this repo into.

## Skills

Canonical sources live under `skills/user/` and `skills/developer/`, named for the primary audience;
the folder does not restrict who may use a skill. Each is a directory holding `SKILL.md` and an
`evaluations.md` of worked scenarios and known failure modes.

Clients find them through flat aliases: `.agents/skills/<name>` symlinks to the canonical directory,
and `.claude/skills` symlinks to `.agents/skills`. Both are committed. Adding, removing or renaming a
skill means updating the canonical source and its alias together, or a client silently stops seeing
it. This mirrors the layout in `submodules/IsaacLab-Arena`, whose skills are usable from here and
are written against that submodule as their repository root.

## Starting the MCP server

`bin/arena-mcp` is the launcher every client config points at. It re-makes `setup.sh`'s exports,
because a client starts a server with a stripped environment, and finds the repo from its own path,
so a client that is not at the repo root still works. `.mcp.json` walks up from the working directory
to find it: Claude Code runs a server from wherever `claude` was started, and does not expand
`CLAUDE_PROJECT_DIR` in the command. VS Code and Cursor have `${workspaceFolder}` and use it directly.

The server itself lives in `arena_composer/`, and documents its own tools — see that AGENTS.md.
