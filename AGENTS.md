 - Run shells with `source setup.sh`. This sets up EULA, PYTHONPATH and ARENA_PROJECT_ROOT exports.
 - /submodules/* are third-party. Don't edit them unless the user asks you to.  
 - Keep the implementation as concise and readable as possible. Add short comments where they help the
   understanding.  
 - Write comments and docs for someone who has only the code in front of them. A note must state a fact
   about the code or a rule to follow — not recount how we found it out, and not answer a question that
   was only ever asked in a chat. If a detail doesn't change what the next reader does, cut it.

## Layout

`arena_composer/` is a mixed maturin project: Python under `python/`, Rust under `src/`,
one package. **Python owns everything that needs OpenUSD** — Arena's registries and placement
solver, plus reading the assets' geometry and materials. **Rust owns the Bevy viewer** and
opens no USD at all. The contract between them is the MessagePack payload
`arena_composer.payload` packs. Later we plan to move this out into it's own project.

Read before changing either side of that contract:

- [arena_composer/AGENTS.md](arena_composer/AGENTS.md) — the payload format and frame conventions.
- [arena_composer/python/arena_composer/usd/AGENTS.md](arena_composer/python/arena_composer/usd/AGENTS.md)
  — how assets are read into it, and what currently doesn't render.

```bash
arena-view environments/tasks/banana_in_bowl.yaml   # resolve a layout and look at it
```

`arena-view` draws in a child process (`arena_composer.viewer_process`): the window's event
loop wants a main thread and never gives it back. The parent stays an asyncio program beside
it — today a watcher on the spec file, later whatever reacts to what it sees — and sends
scenes down the child's stdin as length-prefixed payload frames.

Iterating on the viewer alone is much faster through a packed payload, which skips Arena's
import, the solve and the USD reads:

```bash
arena-resolve-layout environments/tasks/banana_in_bowl.yaml --payload scene.msgpack
cd arena_composer && cargo run --bin arena-viewer -- ../scene.msgpack
```

`--output` still writes the resolver's JSON dump. That stays the human- and agent-readable
artifact; the payload is the renderer's, and carries a strict subset of its fields.

## Tests

```bash
pytest arena_composer/tests
```

```bash
cd arena_composer && cargo test
```

`cargo test` covers the payload decode, mesh/material building and the frame conventions, and needs
no fixtures. One `#[ignore]`d test runs the whole draw path against a real packed scene:

```bash
arena-resolve-layout environments/tasks/droid_banana_on_plate_maple_table.yaml --payload scene.msgpack
cd arena_composer && ARENA_COMPOSER_PAYLOAD=../scene.msgpack cargo test -- --ignored
```
